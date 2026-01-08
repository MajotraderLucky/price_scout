#!/usr/bin/env python3
"""
Store Cleanup Module for Price Scout

Automatically cleans up unhealthy stores and rejects low-quality candidates.
Runs daily via systemd timer.

Cleanup Rules:
1. failure_count >= 10 AND no success in 7 days → disable
2. no success in 30 days → disable
3. auto_import stores with failure_count >= 5 → delete
4. candidates with success_rate < 50% → reject

Usage:
    # Dry run (default) - show what would be cleaned
    python store_cleanup.py

    # Actually perform cleanup
    python store_cleanup.py --execute

    # Verbose output
    python store_cleanup.py --verbose
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


@dataclass
class CleanupAction:
    """Single cleanup action to be performed"""
    table: str  # 'stores' or 'store_candidates'
    item_id: int
    name: str
    action: str  # 'disable', 'delete', 'reject'
    reason: str
    details: dict = field(default_factory=dict)


@dataclass
class CleanupReport:
    """Summary of cleanup operations"""
    timestamp: datetime
    dry_run: bool
    stores_disabled: List[CleanupAction] = field(default_factory=list)
    stores_deleted: List[CleanupAction] = field(default_factory=list)
    candidates_rejected: List[CleanupAction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_actions(self) -> int:
        return len(self.stores_disabled) + len(self.stores_deleted) + len(self.candidates_rejected)

    def to_summary(self) -> str:
        """Generate human-readable summary"""
        mode = "DRY RUN" if self.dry_run else "EXECUTED"
        lines = [
            f"=== Store Cleanup Report ({mode}) ===",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"",
            f"Actions: {self.total_actions} total",
            f"  - Stores disabled: {len(self.stores_disabled)}",
            f"  - Stores deleted: {len(self.stores_deleted)}",
            f"  - Candidates rejected: {len(self.candidates_rejected)}",
        ]

        if self.stores_disabled:
            lines.append("")
            lines.append("Stores to disable:")
            for action in self.stores_disabled:
                lines.append(f"  [{action.item_id}] {action.name}: {action.reason}")

        if self.stores_deleted:
            lines.append("")
            lines.append("Stores to delete:")
            for action in self.stores_deleted:
                lines.append(f"  [{action.item_id}] {action.name}: {action.reason}")

        if self.candidates_rejected:
            lines.append("")
            lines.append("Candidates to reject:")
            for action in self.candidates_rejected:
                rate = action.details.get('success_rate', 0)
                lines.append(f"  [{action.item_id}] {action.name}: {action.reason} (rate: {rate:.1f}%)")

        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  - {error}")

        return "\n".join(lines)


class StoreCleanup:
    """Handles store and candidate cleanup operations"""

    # Cleanup thresholds
    FAILURE_THRESHOLD = 10
    NO_SUCCESS_DAYS_SHORT = 7
    NO_SUCCESS_DAYS_LONG = 30
    AUTO_IMPORT_FAILURE_THRESHOLD = 5
    CANDIDATE_MIN_SUCCESS_RATE = 0.5
    CANDIDATE_MIN_EXTRACTIONS = 3  # Minimum attempts before judging

    def __init__(self, database_url: str, verbose: bool = False):
        self.database_url = database_url
        self.verbose = verbose
        self.conn = None

    def connect(self):
        """Establish database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.database_url)
        return self.conn

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def _log(self, message: str):
        """Print message if verbose mode enabled"""
        if self.verbose:
            print(f"[DEBUG] {message}")

    def find_stores_to_disable(self) -> List[CleanupAction]:
        """Find stores that should be disabled based on cleanup rules"""
        actions = []
        conn = self.connect()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Rule 1: failure_count >= 10 AND no success in 7 days
            cur.execute("""
                SELECT id, name, failure_count, last_success_at, last_failure_at, source
                FROM stores
                WHERE enabled = true
                  AND failure_count >= %s
                  AND (last_success_at IS NULL OR last_success_at < NOW() - INTERVAL '%s days')
            """, (self.FAILURE_THRESHOLD, self.NO_SUCCESS_DAYS_SHORT))

            for row in cur.fetchall():
                self._log(f"Rule 1 match: {row['name']} (failures: {row['failure_count']})")
                actions.append(CleanupAction(
                    table='stores',
                    item_id=row['id'],
                    name=row['name'],
                    action='disable',
                    reason=f"High failures ({row['failure_count']}) with no success in {self.NO_SUCCESS_DAYS_SHORT} days",
                    details={
                        'failure_count': row['failure_count'],
                        'last_success_at': str(row['last_success_at']) if row['last_success_at'] else None,
                        'source': row['source']
                    }
                ))

            # Rule 2: no success in 30 days (not already caught by rule 1)
            already_disabled_ids = [a.item_id for a in actions]
            placeholders = ','.join(['%s'] * len(already_disabled_ids)) if already_disabled_ids else 'NULL'

            query = f"""
                SELECT id, name, failure_count, last_success_at, source
                FROM stores
                WHERE enabled = true
                  AND last_success_at IS NOT NULL
                  AND last_success_at < NOW() - INTERVAL '%s days'
                  AND id NOT IN ({placeholders if already_disabled_ids else 'SELECT 0 WHERE FALSE'})
            """
            params = [self.NO_SUCCESS_DAYS_LONG] + already_disabled_ids if already_disabled_ids else [self.NO_SUCCESS_DAYS_LONG]
            cur.execute(query, params)

            for row in cur.fetchall():
                self._log(f"Rule 2 match: {row['name']} (last success: {row['last_success_at']})")
                actions.append(CleanupAction(
                    table='stores',
                    item_id=row['id'],
                    name=row['name'],
                    action='disable',
                    reason=f"No success in {self.NO_SUCCESS_DAYS_LONG} days",
                    details={
                        'failure_count': row['failure_count'],
                        'last_success_at': str(row['last_success_at']),
                        'source': row['source']
                    }
                ))

        return actions

    def find_stores_to_delete(self) -> List[CleanupAction]:
        """Find auto-imported stores that should be deleted"""
        actions = []
        conn = self.connect()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Rule 3: auto_import stores with failure_count >= 5
            cur.execute("""
                SELECT id, name, failure_count, last_success_at, created_at
                FROM stores
                WHERE source = 'auto_import'
                  AND failure_count >= %s
            """, (self.AUTO_IMPORT_FAILURE_THRESHOLD,))

            for row in cur.fetchall():
                self._log(f"Rule 3 match: {row['name']} (auto_import with {row['failure_count']} failures)")
                actions.append(CleanupAction(
                    table='stores',
                    item_id=row['id'],
                    name=row['name'],
                    action='delete',
                    reason=f"Auto-imported store with {row['failure_count']} failures",
                    details={
                        'failure_count': row['failure_count'],
                        'created_at': str(row['created_at'])
                    }
                ))

        return actions

    def find_candidates_to_reject(self) -> List[CleanupAction]:
        """Find store candidates that should be rejected"""
        actions = []
        conn = self.connect()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Rule 4: candidates with success_rate < 50% (after minimum attempts)
            cur.execute("""
                SELECT id, domain, price_extractions, successful_extractions,
                       CASE WHEN price_extractions > 0
                            THEN (successful_extractions::float / price_extractions::float * 100)
                            ELSE 0
                       END as success_rate
                FROM store_candidates
                WHERE status = 'candidate'
                  AND price_extractions >= %s
                  AND (successful_extractions::float / NULLIF(price_extractions, 0)::float) < %s
            """, (self.CANDIDATE_MIN_EXTRACTIONS, self.CANDIDATE_MIN_SUCCESS_RATE))

            for row in cur.fetchall():
                self._log(f"Rule 4 match: {row['domain']} (success rate: {row['success_rate']:.1f}%)")
                actions.append(CleanupAction(
                    table='store_candidates',
                    item_id=row['id'],
                    name=row['domain'],
                    action='reject',
                    reason=f"Success rate below {self.CANDIDATE_MIN_SUCCESS_RATE * 100}%",
                    details={
                        'success_rate': row['success_rate'],
                        'total_extractions': row['price_extractions'],
                        'successful': row['successful_extractions']
                    }
                ))

        return actions

    def execute_cleanup(self, dry_run: bool = True) -> CleanupReport:
        """Execute cleanup operations and return report"""
        report = CleanupReport(
            timestamp=datetime.now(),
            dry_run=dry_run
        )

        try:
            # Gather all actions
            report.stores_disabled = self.find_stores_to_disable()
            report.stores_deleted = self.find_stores_to_delete()
            report.candidates_rejected = self.find_candidates_to_reject()

            if not dry_run and report.total_actions > 0:
                conn = self.connect()
                with conn.cursor() as cur:
                    # Execute store disables
                    for action in report.stores_disabled:
                        cur.execute("""
                            UPDATE stores
                            SET enabled = false, updated_at = NOW()
                            WHERE id = %s
                        """, (action.item_id,))
                        self._log(f"Disabled store: {action.name}")

                    # Execute store deletes
                    for action in report.stores_deleted:
                        cur.execute("DELETE FROM stores WHERE id = %s", (action.item_id,))
                        self._log(f"Deleted store: {action.name}")

                    # Execute candidate rejections
                    for action in report.candidates_rejected:
                        cur.execute("""
                            UPDATE store_candidates
                            SET status = 'rejected'
                            WHERE id = %s
                        """, (action.item_id,))
                        self._log(f"Rejected candidate: {action.name}")

                    conn.commit()

        except Exception as e:
            report.errors.append(str(e))
            if self.conn:
                self.conn.rollback()

        return report


def get_database_url() -> str:
    """Get database URL from environment or default"""
    return os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres@localhost:5432/price_scout'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Clean up unhealthy stores and reject low-quality candidates'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform cleanup (default is dry run)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed debug output'
    )
    parser.add_argument(
        '--database-url',
        help='Database connection URL (default: from DATABASE_URL env or localhost)'
    )

    args = parser.parse_args()

    database_url = args.database_url or get_database_url()
    dry_run = not args.execute

    cleanup = StoreCleanup(database_url, verbose=args.verbose)

    try:
        report = cleanup.execute_cleanup(dry_run=dry_run)
        print(report.to_summary())

        if dry_run and report.total_actions > 0:
            print("\n[!] This was a dry run. Use --execute to perform cleanup.")

        # Exit code: 0 if no errors, 1 if errors
        sys.exit(0 if not report.errors else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup.close()


if __name__ == '__main__':
    main()
