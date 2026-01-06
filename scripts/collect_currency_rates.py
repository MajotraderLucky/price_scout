#!/usr/bin/env python3
"""
Currency Rates Collector - Central Bank of Russia API

Fetches official USD and EUR exchange rates from ЦБ РФ (Central Bank of Russia)
and saves them to the database.

API: https://www.cbr-xml-daily.ru/daily_json.js
Update frequency: Daily at 11:30 AM Moscow time
Currencies: USD, EUR

Usage:
    python3 collect_currency_rates.py                # Fetch and save to DB
    python3 collect_currency_rates.py --dry-run      # Fetch only (no DB write)
    python3 collect_currency_rates.py --source=both  # Fetch from both sources
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Optional, Tuple
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@192.168.0.10:5432/price_scout")


class CurrencyRatesCollector:
    """Collects currency rates from multiple sources"""

    # Central Bank of Russia API
    CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

    # Open Exchange Rates API (free, no API key needed)
    OPEN_ER_API_URL = "https://open.er-api.com/v6/latest/{base}"

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_cbr_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetch rates from Central Bank of Russia

        Returns:
            Dict with USD and EUR rates to RUB, or None on error
            Example: {'USD': 95.5000, 'EUR': 105.2000}
        """
        try:
            print(f"Fetching rates from ЦБ РФ: {self.CBR_API_URL}")
            response = self.session.get(self.CBR_API_URL, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract USD and EUR rates
            valute = data.get('Valute', {})

            usd_data = valute.get('USD', {})
            eur_data = valute.get('EUR', {})

            if not usd_data or not eur_data:
                print(f"✗ Missing currency data in response")
                return None

            rates = {
                'USD': float(usd_data.get('Value', 0)),
                'EUR': float(eur_data.get('Value', 0))
            }

            # Validate rates
            if rates['USD'] <= 0 or rates['EUR'] <= 0:
                print(f"✗ Invalid rates: USD={rates['USD']}, EUR={rates['EUR']}")
                return None

            print(f"✓ ЦБ РФ rates:")
            print(f"  USD: {rates['USD']:.4f} RUB")
            print(f"  EUR: {rates['EUR']:.4f} RUB")

            return rates

        except requests.RequestException as e:
            print(f"✗ Error fetching from ЦБ РФ: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"✗ Error parsing ЦБ РФ response: {e}")
            return None

    def fetch_open_er_rates(self) -> Optional[Dict[str, float]]:
        """
        Fetch rates from open.er-api.com (free, no API key)

        Returns:
            Dict with USD and EUR rates to RUB, or None on error
        """
        rates = {}

        try:
            # Fetch USD -> RUB
            print(f"Fetching USD rate from open.er-api.com...")
            url = self.OPEN_ER_API_URL.format(base='USD')
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('result') == 'success':
                usd_to_rub = data.get('rates', {}).get('RUB', 0)
                if usd_to_rub > 0:
                    rates['USD'] = float(usd_to_rub)
                    print(f"  USD: {rates['USD']:.4f} RUB")

            # Fetch EUR -> RUB
            print(f"Fetching EUR rate from open.er-api.com...")
            url = self.OPEN_ER_API_URL.format(base='EUR')
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('result') == 'success':
                eur_to_rub = data.get('rates', {}).get('RUB', 0)
                if eur_to_rub > 0:
                    rates['EUR'] = float(eur_to_rub)
                    print(f"  EUR: {rates['EUR']:.4f} RUB")

            if not rates:
                print(f"✗ No valid rates from open.er-api.com")
                return None

            print(f"✓ open.er-api.com rates fetched")
            return rates

        except requests.RequestException as e:
            print(f"✗ Error fetching from open.er-api.com: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"✗ Error parsing open.er-api.com response: {e}")
            return None

    def save_to_database(self, rates: Dict[str, float], source: str) -> bool:
        """
        Save rates to PostgreSQL database

        Args:
            rates: Dict with currency codes and rates
            source: Source identifier ('cbr_ru' or 'exchangerate_host')

        Returns:
            True if saved successfully
        """
        if self.dry_run:
            print(f"[DRY RUN] Would save to database (source={source}):")
            for code, rate in rates.items():
                print(f"  {code}: {rate:.4f} RUB")
            return True

        try:
            import psycopg2

            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()

            for currency_code, rate in rates.items():
                cursor.execute(
                    """
                    INSERT INTO currency_rates (currency_code, rate_to_rub, source)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (currency_code, rate, source)
                )
                rate_id = cursor.fetchone()[0]
                print(f"✓ Saved {currency_code} rate: {rate:.4f} RUB (id={rate_id})")

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            print(f"✗ Database error: {e}")
            return False

    def collect(self, source: str = 'cbr_ru') -> bool:
        """
        Collect rates from specified source and save to database

        Args:
            source: 'cbr_ru', 'exchangerate_host', or 'both'

        Returns:
            True if at least one source succeeded
        """
        success = False

        print("=" * 70)
        print("PRICE SCOUT - Currency Rates Collector")
        print("=" * 70)
        print(f"Source: {source}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")

        if source in ['cbr_ru', 'both']:
            print("[1/2] Central Bank of Russia")
            print("-" * 70)
            rates = self.fetch_cbr_rates()
            if rates:
                if self.save_to_database(rates, 'cbr_ru'):
                    success = True
            print("")

        if source in ['open_er', 'both']:
            print("[2/2] open.er-api.com")
            print("-" * 70)
            rates = self.fetch_open_er_rates()
            if rates:
                if self.save_to_database(rates, 'open_er'):
                    success = True
            print("")

        print("=" * 70)
        if success:
            print("✓ Currency rates collection completed successfully")
        else:
            print("✗ Currency rates collection failed")
        print("=" * 70)

        return success


def main():
    parser = argparse.ArgumentParser(description='Collect currency exchange rates')
    parser.add_argument(
        '--source',
        choices=['cbr_ru', 'open_er', 'both'],
        default='cbr_ru',
        help='Data source to fetch from (default: cbr_ru)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch rates but do not save to database'
    )

    args = parser.parse_args()

    collector = CurrencyRatesCollector(dry_run=args.dry_run)
    success = collector.collect(source=args.source)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
