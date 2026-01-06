#!/usr/bin/env python3
"""
Price Scout Discovery Engine

Product discovery from multiple sources:
1. DuckDuckGo web search
2. Ozon catalog parsing
3. DNS catalog parsing
4. Analysis of user search queries

Usage:
    # Run discovery from popular queries
    python3 discovery.py discover --source duckduckgo --limit 10

    # Run all sources
    python3 discovery.py discover --source all

    # Process pending discovery jobs from queue
    python3 discovery.py process-jobs --limit 5

    # Refresh popularity metrics
    python3 discovery.py refresh-metrics

Output: JSON with discovery results for Rust integration.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import asyncpg

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

# Price range for discovery (kopecks)
MIN_PRICE_KOPECKS = 100_000   # 1,000 RUB
MAX_PRICE_KOPECKS = 1_500_000  # 15,000 RUB

# Min/max prices for filtering (rubles)
MIN_PRICE_RUB = MIN_PRICE_KOPECKS / 100
MAX_PRICE_RUB = MAX_PRICE_KOPECKS / 100

# Database connection from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://price_scout:price_scout@localhost:5432/price_scout"
)

# Categories for discovery
DISCOVERY_CATEGORIES = [
    "electronics",
    "gadgets",
    "tools",
    "sports",
    "home",
    "auto",
]

# Known price patterns
PRICE_PATTERNS = [
    r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб\.?|RUB|р\.)',
    r'(?:цена|price|стоимость)[:\s]*(\d{1,3}(?:\s?\d{3})*)',
    r'(\d{1,3}(?:\s?\d{3})*)\s*(?:рублей|рубля)',
    r'(?:от|от\s+|за\s+)(\d{1,3}(?:\s?\d{3})*)',
]

# Aggregators to exclude
AGGREGATORS = {
    "steel-gun.ru", "price.ru", "e-katalog.ru", "sravni.com",
    "goods-price.ru", "nadavi.ru", "yandex.ru/search", "google.com",
}


class DiscoveryEngine:
    """Main discovery engine class."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def discover_duckduckgo(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 20
    ) -> dict:
        """
        Discover products using DuckDuckGo search.

        Returns:
            dict with found products and their prices
        """
        if DDGS is None:
            return {
                "source": "duckduckgo",
                "query": query,
                "products": [],
                "error": "duckduckgo-search not installed"
            }

        results = {
            "source": "duckduckgo",
            "query": query,
            "category": category,
            "products": [],
            "products_found": 0,
            "products_new": 0,
            "error": None
        }

        try:
            with DDGS() as ddgs:
                # Search with price keywords
                search_query = f"купить {query} цена"
                search_results = list(ddgs.text(
                    search_query,
                    region="ru-ru",
                    max_results=max_results
                ))

            seen_products = set()

            for r in search_results:
                url = r.get("href", "")
                title = r.get("title", "")
                snippet = r.get("body", "")

                # Skip aggregators
                domain = urlparse(url).netloc.replace("www.", "")
                if any(agg in domain for agg in AGGREGATORS):
                    continue

                # Extract prices
                combined_text = f"{title} {snippet}"
                prices = self._extract_prices(combined_text)

                # Filter by price range
                valid_prices = [
                    p for p in prices
                    if MIN_PRICE_RUB <= p <= MAX_PRICE_RUB
                ]

                if not valid_prices:
                    continue

                # Create product name from title
                product_name = self._clean_product_name(title)
                if not product_name or product_name in seen_products:
                    continue

                seen_products.add(product_name)

                # Try to create product in DB
                product_id, is_new = await self._create_product_if_not_exists(
                    product_name,
                    category=category,
                    search_query=query
                )

                results["products"].append({
                    "id": product_id,
                    "name": product_name,
                    "prices": valid_prices,
                    "url": url,
                    "domain": domain,
                    "is_new": is_new
                })

                results["products_found"] += 1
                if is_new:
                    results["products_new"] += 1

        except Exception as e:
            results["error"] = str(e)

        return results

    async def analyze_search_queries(self, limit: int = 50) -> list:
        """
        Analyze popular search queries from telegram bot users.

        Returns:
            List of popular queries to use for discovery
        """
        rows = await self.db.fetch(
            """
            SELECT query, source, category, search_count
            FROM search_queries
            WHERE search_count >= 2
            ORDER BY search_count DESC, last_searched_at DESC
            LIMIT $1
            """,
            limit
        )

        return [
            {
                "query": row["query"],
                "source": row["source"],
                "category": row["category"],
                "count": row["search_count"]
            }
            for row in rows
        ]

    async def create_discovery_jobs_from_queries(self, limit: int = 20) -> int:
        """
        Create discovery jobs from popular search queries.

        Returns:
            Number of jobs created
        """
        queries = await self.analyze_search_queries(limit)
        jobs_created = 0

        for q in queries:
            # Check if job already exists for this query
            existing = await self.db.fetchval(
                """
                SELECT id FROM discovery_jobs
                WHERE query = $1 AND status IN ('pending', 'running')
                """,
                q["query"]
            )

            if existing:
                continue

            # Create new job
            await self.db.execute(
                """
                INSERT INTO discovery_jobs (source, category, query, status)
                VALUES ('duckduckgo', $1, $2, 'pending')
                """,
                q["category"],
                q["query"]
            )
            jobs_created += 1

        return jobs_created

    async def process_pending_jobs(self, limit: int = 10) -> list:
        """
        Process pending discovery jobs from queue.

        Returns:
            List of job results
        """
        # Fetch pending jobs
        jobs = await self.db.fetch(
            """
            SELECT id, source, category, query
            FROM discovery_jobs
            WHERE status = 'pending'
            ORDER BY scheduled_at ASC
            LIMIT $1
            """,
            limit
        )

        results = []

        for job in jobs:
            job_id = job["id"]
            source = job["source"]
            category = job["category"]
            query = job["query"]

            # Mark as running
            await self.db.execute(
                """
                UPDATE discovery_jobs
                SET status = 'running', started_at = NOW()
                WHERE id = $1
                """,
                job_id
            )

            try:
                if source == "duckduckgo" and query:
                    result = await self.discover_duckduckgo(
                        query,
                        category=category
                    )
                else:
                    result = {"error": f"Unknown source: {source}"}

                # Update job status
                error = result.get("error")
                status = "failed" if error else "completed"

                await self.db.execute(
                    """
                    UPDATE discovery_jobs
                    SET status = $2,
                        products_found = $3,
                        products_new = $4,
                        error = $5,
                        completed_at = NOW()
                    WHERE id = $1
                    """,
                    job_id,
                    status,
                    result.get("products_found", 0),
                    result.get("products_new", 0),
                    error
                )

                results.append({
                    "job_id": job_id,
                    "source": source,
                    "query": query,
                    "status": status,
                    "products_found": result.get("products_found", 0),
                    "products_new": result.get("products_new", 0),
                    "error": error
                })

            except Exception as e:
                # Mark as failed
                await self.db.execute(
                    """
                    UPDATE discovery_jobs
                    SET status = 'failed', error = $2, completed_at = NOW()
                    WHERE id = $1
                    """,
                    job_id,
                    str(e)
                )

                results.append({
                    "job_id": job_id,
                    "source": source,
                    "query": query,
                    "status": "failed",
                    "error": str(e)
                })

        return results

    async def refresh_popularity_metrics(self) -> dict:
        """
        Refresh the product popularity materialized view.

        Returns:
            dict with refresh status
        """
        try:
            start = datetime.now()

            await self.db.execute(
                "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_popularity"
            )

            elapsed = (datetime.now() - start).total_seconds()

            # Get count of products in view
            count = await self.db.fetchval(
                "SELECT COUNT(*) FROM mv_product_popularity"
            )

            return {
                "status": "success",
                "products_in_view": count,
                "refresh_time_seconds": round(elapsed, 2)
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_top_products(self, limit: int = 100) -> list:
        """
        Get top products by popularity score.

        Returns:
            List of top products with scores
        """
        rows = await self.db.fetch(
            """
            SELECT
                product_id,
                name,
                category,
                tracking_score,
                volatility_score,
                availability_score,
                arbitrage_score,
                (tracking_score + volatility_score + availability_score + arbitrage_score) as total_score,
                tracking_count,
                min_price / 100 as min_price_rub,
                max_price / 100 as max_price_rub,
                store_count,
                calculated_at
            FROM mv_product_popularity
            ORDER BY (tracking_score + volatility_score + availability_score + arbitrage_score) DESC
            LIMIT $1
            """,
            limit
        )

        return [
            {
                "rank": idx + 1,
                "product_id": row["product_id"],
                "name": row["name"],
                "category": row["category"],
                "total_score": row["total_score"],
                "tracking_score": row["tracking_score"],
                "volatility_score": row["volatility_score"],
                "availability_score": row["availability_score"],
                "arbitrage_score": row["arbitrage_score"],
                "tracking_count": row["tracking_count"],
                "min_price_rub": row["min_price_rub"],
                "max_price_rub": row["max_price_rub"],
                "store_count": row["store_count"],
                "calculated_at": row["calculated_at"].isoformat() if row["calculated_at"] else None
            }
            for idx, row in enumerate(rows)
        ]

    def _extract_prices(self, text: str) -> list:
        """Extract prices from text using regex patterns."""
        prices = []
        for pattern in PRICE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                price_str = match.replace(" ", "").replace("\u00a0", "")
                if price_str.isdigit():
                    price = int(price_str)
                    if 100 < price < 10_000_000:
                        prices.append(price)
        return sorted(set(prices))

    def _clean_product_name(self, title: str) -> str:
        """Clean and normalize product name from title."""
        # Remove price mentions
        name = re.sub(r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб|RUB|р\.)', '', title)
        # Remove common suffixes
        name = re.sub(r'\s*[-–—|]\s*купить.*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*[-–—|]\s*цена.*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*в\s+интернет.*', '', name, flags=re.IGNORECASE)
        # Clean whitespace
        name = ' '.join(name.split())
        return name[:200] if name else ""

    async def _create_product_if_not_exists(
        self,
        name: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> tuple:
        """
        Create product if it doesn't exist.

        Returns:
            (product_id, is_new)
        """
        # Check if product exists
        existing = await self.db.fetchval(
            """
            SELECT id FROM products
            WHERE name ILIKE $1 OR search_query = $2
            LIMIT 1
            """,
            f"%{name[:50]}%",
            search_query
        )

        if existing:
            return existing, False

        # Create new product
        product_id = await self.db.fetchval(
            """
            INSERT INTO products (name, category, search_query, specs)
            VALUES ($1, $2, $3, '{}')
            RETURNING id
            """,
            name[:200],
            category,
            search_query
        )

        return product_id, True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Price Scout Discovery Engine"
    )
    parser.add_argument(
        "command",
        choices=["discover", "process-jobs", "refresh-metrics", "top-products", "create-jobs"],
        help="Command to execute"
    )
    parser.add_argument(
        "--source",
        choices=["duckduckgo", "ozon_catalog", "dns_catalog", "all"],
        default="duckduckgo",
        help="Discovery source"
    )
    parser.add_argument(
        "--query",
        help="Search query for discovery"
    )
    parser.add_argument(
        "--category",
        help="Product category"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit for results"
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="json",
        help="Output format"
    )

    args = parser.parse_args()

    # Connect to database
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
    except Exception as e:
        print(json.dumps({"error": f"Database connection failed: {e}"}))
        sys.exit(1)

    try:
        engine = DiscoveryEngine(pool)
        result = {}

        if args.command == "discover":
            if args.query:
                result = await engine.discover_duckduckgo(
                    args.query,
                    category=args.category,
                    max_results=args.limit
                )
            else:
                # Discover from popular queries
                queries = await engine.analyze_search_queries(args.limit)
                all_results = []
                for q in queries[:5]:  # Process top 5 queries
                    r = await engine.discover_duckduckgo(
                        q["query"],
                        category=q["category"]
                    )
                    all_results.append(r)
                result = {
                    "source": "duckduckgo",
                    "queries_processed": len(all_results),
                    "results": all_results
                }

        elif args.command == "process-jobs":
            results = await engine.process_pending_jobs(args.limit)
            result = {
                "jobs_processed": len(results),
                "results": results
            }

        elif args.command == "refresh-metrics":
            result = await engine.refresh_popularity_metrics()

        elif args.command == "top-products":
            products = await engine.get_top_products(args.limit)
            result = {
                "count": len(products),
                "products": products
            }

        elif args.command == "create-jobs":
            jobs_created = await engine.create_discovery_jobs_from_queries(args.limit)
            result = {
                "jobs_created": jobs_created
            }

        # Output
        if args.output == "pretty":
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            print(json.dumps(result, ensure_ascii=False, default=str))

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
