#!/usr/bin/env python3
"""
Store Discovery Module for Price Scout

Automatically discovers and registers new stores from web search results.
Tracks store candidates and promotes them to full stores after validation.

Usage:
    from store_discovery import StoreDiscovery

    discovery = StoreDiscovery(database_url)
    discovery.track_candidate("example.ru", "https://example.ru/product/123", price_found=True)
    discovery.process_candidates()  # Promote qualified candidates
"""

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


@dataclass
class DiscoveredStore:
    """Store discovered from web search"""
    domain: str
    base_url: str
    sample_urls: List[str]
    price_extractions: int
    successful_extractions: int
    first_seen_at: datetime
    last_seen_at: datetime
    status: str


@dataclass
class ValidationResult:
    """Result of store validation test"""
    success: bool
    price_found: bool
    error: Optional[str]
    response_time: float


# Known store patterns for auto-detection of parser type
STORE_PATTERNS = {
    # Major marketplaces - usually need stealth
    r"ozon\.ru": ("playwright_stealth", "generic"),
    r"wildberries\.ru": ("playwright_stealth", "generic"),
    r"market\.yandex\.ru": ("yandex_market_special", "yandex_json"),
    r"aliexpress": ("playwright_stealth", "generic"),

    # Electronics - mixed
    r"dns-shop\.ru": ("firefox", "dns_json"),
    r"citilink\.ru": ("citilink_firefox", "citilink_json"),
    r"mvideo\.ru": ("playwright_stealth", "generic"),
    r"eldorado\.ru": ("playwright_stealth", "generic"),

    # Simple stores - direct playwright
    r"centershot\.ru": ("playwright_direct", "centershot"),
    r"regard\.ru": ("playwright_stealth", "generic"),

    # Default for unknown stores
    "default": ("generic_playwright", "generic"),
}

# Domains to never import (aggregators, forums, etc.)
BLACKLIST_DOMAINS = {
    "forum.auto.ru",
    "steel-gun.ru",
    "price.ru",
    "e-katalog.ru",
    "sravni.com",
    "goods-price.ru",
    "nadavi.ru",
    "yandex.ru",  # Not marketplace
    "google.com",
    "youtube.com",
    "wikipedia.org",
    "vk.com",
    "ok.ru",
    "avito.ru",  # Already have special handler
}


class StoreDiscovery:
    """
    Discovers and manages store candidates for auto-import.

    Workflow:
    1. track_candidate() - Called when price extracted from unknown domain
    2. After 3+ successful extractions - candidate becomes 'testing'
    3. validate_candidate() - Run 5 test scrapes
    4. If 4/5 pass - promote_to_store() creates full store entry
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None

    def _connect(self):
        """Establish database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.database_url)
        return self.conn

    def _close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract base domain from URL (www.example.com -> example.com)"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain

    @staticmethod
    def extract_base_url(url: str) -> str:
        """Extract base URL (https://example.com)"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def is_blacklisted(domain: str) -> bool:
        """Check if domain is blacklisted"""
        for blacklisted in BLACKLIST_DOMAINS:
            if blacklisted in domain:
                return True
        return False

    @staticmethod
    def detect_store_config(domain: str) -> tuple:
        """Detect best method and parser for domain"""
        for pattern, config in STORE_PATTERNS.items():
            if pattern == "default":
                continue
            if re.search(pattern, domain):
                return config
        return STORE_PATTERNS["default"]

    def track_candidate(
        self,
        domain: str,
        url: str,
        price_found: bool,
    ) -> Optional[int]:
        """
        Track a store candidate from web search.

        Args:
            domain: Store domain (e.g., "shop.ru")
            url: Product URL where price was extracted
            price_found: Whether price was successfully extracted

        Returns:
            Candidate ID if tracked, None if blacklisted or error
        """
        # Skip blacklisted domains
        if self.is_blacklisted(domain):
            return None

        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if candidate exists
                cur.execute(
                    "SELECT id, sample_urls, price_extractions, successful_extractions "
                    "FROM store_candidates WHERE domain = %s",
                    (domain,)
                )
                existing = cur.fetchone()

                if existing:
                    # Update existing candidate
                    sample_urls = existing["sample_urls"] or []
                    if url not in sample_urls and len(sample_urls) < 10:
                        sample_urls.append(url)

                    cur.execute(
                        """
                        UPDATE store_candidates SET
                            sample_urls = %s,
                            price_extractions = price_extractions + 1,
                            successful_extractions = successful_extractions + %s,
                            last_seen_at = NOW()
                        WHERE id = %s
                        RETURNING id
                        """,
                        (sample_urls, 1 if price_found else 0, existing["id"])
                    )
                    candidate_id = cur.fetchone()["id"]
                else:
                    # Create new candidate
                    base_url = self.extract_base_url(url)
                    cur.execute(
                        """
                        INSERT INTO store_candidates
                            (domain, base_url, sample_urls, price_extractions, successful_extractions)
                        VALUES (%s, %s, %s, 1, %s)
                        RETURNING id
                        """,
                        (domain, base_url, [url], 1 if price_found else 0)
                    )
                    candidate_id = cur.fetchone()["id"]

                conn.commit()
                return candidate_id

        except Exception as e:
            conn.rollback()
            print(f"Error tracking candidate {domain}: {e}", file=sys.stderr)
            return None

    def get_candidates_for_testing(self, min_success_rate: float = 0.5, min_extractions: int = 3) -> List[DiscoveredStore]:
        """
        Get candidates ready for validation testing.

        Criteria:
        - At least min_extractions attempts
        - Success rate >= min_success_rate
        - Status is 'candidate' (not already testing/promoted/rejected)
        """
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM store_candidates
                    WHERE status = 'candidate'
                      AND price_extractions >= %s
                      AND successful_extractions::float / NULLIF(price_extractions, 0) >= %s
                    ORDER BY successful_extractions DESC
                    LIMIT 10
                    """,
                    (min_extractions, min_success_rate)
                )
                rows = cur.fetchall()

                return [
                    DiscoveredStore(
                        domain=row["domain"],
                        base_url=row["base_url"],
                        sample_urls=row["sample_urls"] or [],
                        price_extractions=row["price_extractions"],
                        successful_extractions=row["successful_extractions"],
                        first_seen_at=row["first_seen_at"],
                        last_seen_at=row["last_seen_at"],
                        status=row["status"],
                    )
                    for row in rows
                ]
        except Exception as e:
            print(f"Error getting candidates: {e}", file=sys.stderr)
            return []

    def validate_candidate(self, domain: str, test_urls: List[str]) -> ValidationResult:
        """
        Validate a candidate store by testing price extraction.

        Args:
            domain: Store domain
            test_urls: List of product URLs to test

        Returns:
            ValidationResult with success status
        """
        try:
            from store_parsers import fetch_price
        except ImportError:
            return ValidationResult(
                success=False,
                price_found=False,
                error="store_parsers not available",
                response_time=0.0
            )

        import time

        successes = 0
        total_time = 0.0
        last_error = None

        for url in test_urls[:5]:  # Test up to 5 URLs
            start = time.time()
            try:
                result = fetch_price(url, timeout=30)
                elapsed = time.time() - start
                total_time += elapsed

                if result.get("price"):
                    successes += 1
                elif result.get("error"):
                    last_error = result["error"]
            except Exception as e:
                last_error = str(e)

        success_rate = successes / len(test_urls[:5]) if test_urls else 0
        avg_time = total_time / len(test_urls[:5]) if test_urls else 0

        return ValidationResult(
            success=success_rate >= 0.8,  # 4/5 must pass
            price_found=successes > 0,
            error=last_error if success_rate < 0.8 else None,
            response_time=avg_time,
        )

    def update_candidate_status(self, domain: str, status: str) -> bool:
        """Update candidate status (candidate -> testing -> promoted/rejected)"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE store_candidates SET status = %s WHERE domain = %s",
                    (status, domain)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating status for {domain}: {e}", file=sys.stderr)
            return False

    def promote_to_store(self, domain: str) -> Optional[int]:
        """
        Promote a validated candidate to a full store.

        Creates entry in stores table with auto-detected method/parser.
        Updates candidate status to 'promoted'.

        Returns:
            New store ID if successful, None otherwise
        """
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get candidate info
                cur.execute(
                    "SELECT * FROM store_candidates WHERE domain = %s",
                    (domain,)
                )
                candidate = cur.fetchone()

                if not candidate:
                    return None

                # Detect method and parser
                method, parser = self.detect_store_config(domain)

                # Generate store name from domain
                store_name = domain.replace(".ru", "").replace(".com", "").replace(".", "_")

                # Check if store already exists
                cur.execute(
                    "SELECT id FROM stores WHERE name = %s OR base_url ILIKE %s",
                    (store_name, f"%{domain}%")
                )
                existing = cur.fetchone()

                if existing:
                    # Link candidate to existing store
                    cur.execute(
                        """
                        UPDATE store_candidates
                        SET status = 'promoted', promoted_to_store_id = %s
                        WHERE domain = %s
                        """,
                        (existing["id"], domain)
                    )
                    conn.commit()
                    return existing["id"]

                # Create new store
                cur.execute(
                    """
                    INSERT INTO stores (name, base_url, method, parser, source, unstable, priority)
                    VALUES (%s, %s, %s, %s, 'auto_import', true, 30)
                    RETURNING id
                    """,
                    (store_name, candidate["base_url"], method, parser)
                )
                store_id = cur.fetchone()["id"]

                # Update candidate
                cur.execute(
                    """
                    UPDATE store_candidates
                    SET status = 'promoted', promoted_to_store_id = %s
                    WHERE domain = %s
                    """,
                    (store_id, domain)
                )

                conn.commit()
                return store_id

        except Exception as e:
            conn.rollback()
            print(f"Error promoting {domain}: {e}", file=sys.stderr)
            return None

    def reject_candidate(self, domain: str, reason: str = None) -> bool:
        """Mark a candidate as rejected (failed validation)"""
        return self.update_candidate_status(domain, "rejected")

    def process_candidates(self, dry_run: bool = False) -> Dict:
        """
        Process all candidates ready for testing.

        Returns dict with:
        - tested: Number of candidates tested
        - promoted: Number promoted to stores
        - rejected: Number rejected
        """
        results = {"tested": 0, "promoted": 0, "rejected": 0}

        candidates = self.get_candidates_for_testing()

        for candidate in candidates:
            results["tested"] += 1

            # Mark as testing
            if not dry_run:
                self.update_candidate_status(candidate.domain, "testing")

            # Run validation
            validation = self.validate_candidate(
                candidate.domain,
                candidate.sample_urls
            )

            if validation.success:
                print(f"[+] {candidate.domain}: PASSED (avg {validation.response_time:.1f}s)")
                if not dry_run:
                    store_id = self.promote_to_store(candidate.domain)
                    if store_id:
                        results["promoted"] += 1
                        print(f"    -> Promoted as store #{store_id}")
            else:
                print(f"[X] {candidate.domain}: FAILED - {validation.error}")
                if not dry_run:
                    self.reject_candidate(candidate.domain)
                results["rejected"] += 1

        return results

    def get_stats(self) -> Dict:
        """Get candidate statistics"""
        conn = self._connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'candidate') as candidates,
                        COUNT(*) FILTER (WHERE status = 'testing') as testing,
                        COUNT(*) FILTER (WHERE status = 'promoted') as promoted,
                        COUNT(*) FILTER (WHERE status = 'rejected') as rejected
                    FROM store_candidates
                    """
                )
                return dict(cur.fetchone())
        except Exception as e:
            print(f"Error getting stats: {e}", file=sys.stderr)
            return {}


# === CLI Interface ===

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Store Discovery CLI")
    parser.add_argument("command", choices=["stats", "candidates", "process", "track"],
                       help="Command to execute")
    parser.add_argument("--domain", help="Domain for track command")
    parser.add_argument("--url", help="URL for track command")
    parser.add_argument("--price-found", action="store_true", help="Price was found")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify database")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres@localhost:5432/price_scout"
    )

    discovery = StoreDiscovery(database_url)

    try:
        if args.command == "stats":
            stats = discovery.get_stats()
            if args.json:
                print(json.dumps(stats))
            else:
                print("Store Candidate Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")

        elif args.command == "candidates":
            candidates = discovery.get_candidates_for_testing()
            if args.json:
                print(json.dumps([
                    {
                        "domain": c.domain,
                        "base_url": c.base_url,
                        "extractions": c.price_extractions,
                        "successes": c.successful_extractions,
                        "status": c.status,
                    }
                    for c in candidates
                ]))
            else:
                print(f"Candidates ready for testing: {len(candidates)}")
                for c in candidates:
                    rate = c.successful_extractions / c.price_extractions if c.price_extractions else 0
                    print(f"  {c.domain}: {c.successful_extractions}/{c.price_extractions} ({rate:.0%})")

        elif args.command == "process":
            results = discovery.process_candidates(dry_run=args.dry_run)
            if args.json:
                print(json.dumps(results))
            else:
                print(f"Processed: {results['tested']} candidates")
                print(f"  Promoted: {results['promoted']}")
                print(f"  Rejected: {results['rejected']}")

        elif args.command == "track":
            if not args.domain or not args.url:
                print("Error: --domain and --url required for track command")
                sys.exit(1)

            candidate_id = discovery.track_candidate(
                args.domain,
                args.url,
                args.price_found
            )

            if candidate_id:
                print(f"Tracked candidate #{candidate_id}: {args.domain}")
            else:
                print(f"Failed to track: {args.domain} (blacklisted or error)")

    finally:
        discovery._close()
