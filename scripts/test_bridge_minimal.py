#!/usr/bin/env python3
"""
Minimal test script for Python bridge verification.
No dependencies required - just outputs JSON.
"""

import json
import sys


def main():
    # Simulate a successful scraper response
    response = {
        "store": "test-store",
        "status": "success",
        "price": 123456,  # 1234.56 RUB in kopecks
        "count": 5,
        "time": 0.5,
        "error": None,
        "method": "test",
    }

    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
