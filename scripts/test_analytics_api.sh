#!/bin/bash
#
# Analytics API Test Script
#
# Tests all 13 Price Scout API endpoints including the new analytics features.
#
# Usage:
#   ./test_analytics_api.sh [API_URL]
#
# Example:
#   ./test_analytics_api.sh http://localhost:3000
#   ./test_analytics_api.sh http://192.168.0.10:3000
#

set -e

# Configuration
API_URL="${1:-http://localhost:3000}"
PRODUCT_ID="${2:-1}"
MIN_PRICE=5000
MAX_PRICE=15000

echo "========================================="
echo "Price Scout Analytics API Test"
echo "========================================="
echo "API URL: $API_URL"
echo "Product ID: $PRODUCT_ID"
echo "Price Range: $MIN_PRICE-$MAX_PRICE RUB"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="$4"

    echo -n "Testing $name... "

    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        if command -v jq &> /dev/null; then
            echo "$body" | jq -C . 2>/dev/null || echo "$body"
        else
            echo "$body"
        fi
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "$body"
    fi
    echo ""
}

# Test Core Endpoints
echo "========================================="
echo "CORE ENDPOINTS (7)"
echo "========================================="
echo ""

test_endpoint "1. Health Check" "$API_URL/health"
test_endpoint "2. List Stores" "$API_URL/api/stores"
test_endpoint "3. Get Product" "$API_URL/api/products/$PRODUCT_ID"
test_endpoint "4. Get Product Prices" "$API_URL/api/products/$PRODUCT_ID/prices"
test_endpoint "5. Search Products" "$API_URL/api/search" "POST" '{"query":"MacBook"}'
test_endpoint "6. Queue Statistics" "$API_URL/api/queue/stats"

# Note: Scrape endpoint is destructive, so we test with dry-run comment
echo -n "7. Scrape Product (skipped - destructive)... "
echo -e "${YELLOW}⊘ SKIP${NC}"
echo "   To test manually: curl -X POST $API_URL/api/products/$PRODUCT_ID/scrape -H 'Content-Type: application/json' -d '{\"priority\":8}'"
echo ""

# Test Analytics Endpoints
echo "========================================="
echo "ANALYTICS ENDPOINTS (6)"
echo "========================================="
echo ""

test_endpoint "8. Price Trends (7 days)" "$API_URL/api/analytics/price-trends/$PRODUCT_ID?days=7"
test_endpoint "9. Currency Correlation (USD, 30 days)" "$API_URL/api/analytics/currency-correlation/$PRODUCT_ID?currency=USD&days=30"
test_endpoint "10. Store Comparison (30 days)" "$API_URL/api/analytics/store-comparison/$PRODUCT_ID?days=30"
test_endpoint "11. Market Overview" "$API_URL/api/analytics/market-overview?min_price=$MIN_PRICE&max_price=$MAX_PRICE&days=7"
test_endpoint "12. Arbitrage Opportunities (10% profit)" "$API_URL/api/arbitrage?min_profit=10"
test_endpoint "13. ML Price Prediction" "$API_URL/api/analytics/predictions/$PRODUCT_ID"

# Summary
echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo ""
echo "Endpoints tested: 13 total"
echo "  - Core: 7 (6 tested, 1 skipped)"
echo "  - Analytics: 6"
echo ""
echo "Expected behaviors:"
echo "  ✓ Endpoints 1-6, 8-12: Should return HTTP 200"
echo "  ✓ Endpoint 13 (ML Predictions): May return 500 if model not trained"
echo "  ℹ Empty results are OK if no historical data collected yet"
echo ""
echo "Next steps:"
echo "  1. Run automated scraping for 7+ days to collect data"
echo "  2. Collect currency rates: python3 scripts/collect_currency_rates.py"
echo "  3. Train ML model: python3 scripts/ml_predictor.py train --product-id $PRODUCT_ID"
echo "  4. Re-run this test script to verify analytics with real data"
echo ""
echo "========================================="
