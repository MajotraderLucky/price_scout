# Analytics Platform Deployment Guide

## Deployment to Archbook (192.168.0.10)

This guide walks through deploying Phase 3 analytics features to the Archbook server.

**Date**: 2026-01-05
**Components**: Analytics API, Currency Tracking, ML Predictions, Automated Scraping

---

## Prerequisites

- [+] PostgreSQL 17.5 running on Archbook
- [+] Rust workspace compiled
- [+] Python 3.10+ with venv
- [+] DATABASE_URL environment variable set

---

## Deployment Steps

### 1. Apply Database Migration

**Migration 003: Currency Rates Table**

```bash
# On Archbook
cd /home/sergey/price_scout

# Apply migration
psql postgresql://postgres@localhost:5432/price_scout -f migrations/003_add_currency_rates.sql

# Verify table created
psql postgresql://postgres@localhost:5432/price_scout -c "\d currency_rates"
```

**Expected Output**:
```
                                        Table "public.currency_rates"
     Column      |           Type           | Collation | Nullable |                  Default
-----------------+--------------------------+-----------+----------+--------------------------------------------
 id              | bigint                   |           | not null | nextval('currency_rates_id_seq'::regclass)
 currency_code   | text                     |           | not null |
 rate_to_rub     | numeric(10,4)            |           | not null |
 source          | text                     |           | not null |
 recorded_at     | timestamp with time zone |           | not null | now()
```

---

### 2. Build Updated API Server

```bash
cd /home/sergey/price_scout

# Build in release mode
cargo build --release --bin price-scout-api

# Verify binary created
ls -lh target/release/price-scout-api
```

**Expected**: Binary size ~15-20 MB

---

### 3. Install Python ML Dependencies

```bash
# Activate venv
cd /home/sergey/price_scout
source venv/bin/activate

# Install ML packages
pip install pandas scikit-learn psycopg2-binary joblib

# Verify installation
python3 -c "import pandas, sklearn, psycopg2, joblib; print('OK')"
```

**Expected Output**: `OK`

---

### 4. Restart API Server

```bash
# Stop old API if running
sudo systemctl stop price-scout-api.service

# Update systemd service (if needed)
sudo cp config/price-scout-api.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start new API
sudo systemctl start price-scout-api.service

# Check status
sudo systemctl status price-scout-api.service

# View logs
sudo journalctl -u price-scout-api.service -f
```

**Expected Log Output**:
```
🚀 Price Scout API Server
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Connecting to database...
✅ Database connected
✅ Scraper queue initialized
🌐 Server listening on http://0.0.0.0:3000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Available endpoints:
   GET  /health
   GET  /api/stores
   GET  /api/products/:id
   GET  /api/products/:id/prices
   POST /api/search
   POST /api/products/:id/scrape
   GET  /api/queue/stats
   GET  /api/analytics/price-trends/:id
   GET  /api/analytics/currency-correlation/:id
   GET  /api/analytics/store-comparison/:id
   GET  /api/analytics/market-overview
   GET  /api/arbitrage
   GET  /api/analytics/predictions/:id
```

---

## Testing Phase

### Test 1: Health Check

```bash
curl http://localhost:3000/health
```

**Expected**: `OK`

---

### Test 2: Verify Stores

```bash
curl http://localhost:3000/api/stores | jq '.[0:2]'
```

**Expected**: JSON array with store objects

---

### Test 3: Currency Collection

```bash
# Test currency collection (dry run)
cd /home/sergey/price_scout
export DATABASE_URL=postgresql://postgres@localhost:5432/price_scout
python3 scripts/collect_currency_rates.py --dry-run
```

**Expected Output**:
```
DRY RUN - Would save:
  USD/RUB: 78.23 (source: cbr_ru)
  EUR/RUB: 92.09 (source: cbr_ru)
  USD/RUB: 78.45 (source: open_er)
  EUR/RUB: 92.31 (source: open_er)
```

**Collect Real Data**:
```bash
python3 scripts/collect_currency_rates.py

# Verify saved
psql postgresql://postgres@localhost:5432/price_scout -c "SELECT * FROM currency_rates ORDER BY recorded_at DESC LIMIT 4;"
```

---

### Test 4: Analytics Endpoints (Without Historical Data)

**Note**: These will return empty/null results without historical price data.

**4a. Price Trends** (requires price_history table):
```bash
curl "http://localhost:3000/api/analytics/price-trends/1?days=7" | jq
```

**Expected** (no data):
```json
{
  "product_id": 1,
  "trends": []
}
```

**4b. Currency Correlation**:
```bash
curl "http://localhost:3000/api/analytics/currency-correlation/1?currency=USD&days=30" | jq
```

**Expected** (no data):
```json
{
  "product_id": 1,
  "currency": "USD",
  "correlation": null,
  "days": 30
}
```

**4c. Store Comparison**:
```bash
curl "http://localhost:3000/api/analytics/store-comparison/1?days=30" | jq
```

**Expected** (with current prices from store_prices):
```json
{
  "product_id": 1,
  "stores": [
    {
      "store_name": "dns-shop",
      "avg_price": 6279900.0,
      "update_count": 1,
      "availability_rate": 1.0
    }
  ]
}
```

**4d. Market Overview**:
```bash
curl "http://localhost:3000/api/analytics/market-overview?min_price=5000&max_price=15000&days=7" | jq
```

**Expected** (if products exist in range):
```json
{
  "total_products": 3,
  "avg_price": 9500000.0,
  "min_price": 5000000,
  "max_price": 15000000,
  "total_price_points": 15
}
```

---

### Test 5: Arbitrage Detector

**Requires**: At least 2 products with prices from multiple stores

```bash
curl "http://localhost:3000/api/arbitrage?min_profit=10" | jq
```

**Expected** (if arbitrage opportunities exist):
```json
{
  "opportunities": [
    {
      "product_id": 1,
      "product_name": "MacBook Pro 16\"",
      "category": "laptops",
      "buy_store": "dns-shop",
      "buy_price": 6279900,
      "sell_store": "ozon",
      "sell_price": 7502400,
      "profit_kopecks": 1222500,
      "profit_percent": 19.46
    }
  ],
  "count": 1
}
```

**Expected** (no opportunities):
```json
{
  "opportunities": [],
  "count": 0
}
```

---

### Test 6: ML Price Predictions

**Prerequisites**:
1. Product must exist
2. At least 20 days of price history
3. Currency rate data for same period

**6a. Train Model**:
```bash
cd /home/sergey/price_scout
export DATABASE_URL=postgresql://postgres@localhost:5432/price_scout

# Train model for product 1
python3 scripts/ml_predictor.py train --product-id 1
```

**Expected Output**:
```
Fetching training data for product 1...
Found 45 days of data
Engineering features...
Training set size: 32 samples
Training random_forest model...

Model Performance:
  R² Score (train): 0.8234
  R² Score (test):  0.7156
  MAE (train):      112345.67 kopecks (1123.46 RUB)
  MAE (test):       145678.89 kopecks (1456.79 RUB)
  RMSE (train):     123456.78 kopecks (1234.57 RUB)
  RMSE (test):      167890.12 kopecks (1678.90 RUB)

Model saved to: models/product_1_predictor.pkl
Metrics saved to: models/product_1_metrics.json
```

**6b. CLI Prediction**:
```bash
python3 scripts/ml_predictor.py predict --product-id 1
```

**Expected Output**:
```
Price Prediction for Product 1:
  Current Price:    6279900 kopecks (62,799.00 RUB)
  Predicted Price:  6150000 kopecks (61,500.00 RUB)
  Prediction Range: 5900000 - 6400000 kopecks
  Horizon:          7 days
  Confidence:       medium
  Model Accuracy:   R²=0.716, MAE=1456.79 RUB
```

**6c. API Prediction**:
```bash
curl "http://localhost:3000/api/analytics/predictions/1" | jq
```

**Expected Output**:
```json
{
  "product_id": 1,
  "current_price": 6279900,
  "predicted_price": 6150000,
  "prediction_horizon_days": 7,
  "lower_bound": 5900000,
  "upper_bound": 6400000,
  "confidence": "medium",
  "model_accuracy": {
    "r2_score": 0.7156,
    "mae_kopecks": 145678.89,
    "mae_rub": 1456.79
  },
  "predicted_at": "2026-01-05T18:45:00+03:00",
  "model_trained_at": "2026-01-05T18:30:00+03:00"
}
```

**If No Model Trained** (Expected Error):
```json
{
  "error": "ML predictor failed: No trained model found for product 1. Train first with: python ml_predictor.py train --product-id 1"
}
```

**If Insufficient Data** (Expected Error):
```json
{
  "error": "ML predictor failed: No data found for product 1"
}
```

---

## Automated Data Collection Setup

### Currency Rates Collection

**Setup Cron Job** (daily at 12:00):
```bash
# Edit crontab
crontab -e

# Add line:
0 12 * * * cd /home/sergey/price_scout && /home/sergey/price_scout/venv/bin/python3 scripts/collect_currency_rates.py >> /var/log/price_scout/currency_collection.log 2>&1
```

**Or Use Systemd Timer**:
```bash
# Create service
sudo tee /etc/systemd/system/price-scout-currency.service << 'EOF'
[Unit]
Description=Price Scout Currency Rates Collection

[Service]
Type=oneshot
User=sergey
WorkingDirectory=/home/sergey/price_scout
Environment="DATABASE_URL=postgresql://postgres@localhost:5432/price_scout"
ExecStart=/home/sergey/price_scout/venv/bin/python3 scripts/collect_currency_rates.py
EOF

# Create timer
sudo tee /etc/systemd/system/price-scout-currency.timer << 'EOF'
[Unit]
Description=Price Scout Currency Rates Collection Timer

[Timer]
OnCalendar=daily
OnCalendar=12:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start
sudo systemctl enable --now price-scout-currency.timer

# Check status
systemctl list-timers --all | grep price-scout
```

---

### Automated Scraping (10-minute intervals)

**Already configured** via PS-35:
```bash
# Check worker status
sudo systemctl status price-scout-worker.service

# View logs
sudo journalctl -u price-scout-worker.service -f
```

**Or use scheduler timer**:
```bash
# Check timer
systemctl status price-scout-scheduler.timer

# View recent runs
sudo journalctl -u price-scout-scheduler.service --since "1 hour ago"
```

---

## Troubleshooting

### Issue 1: Migration Fails

**Error**: `ERROR:  relation "currency_rates" already exists`

**Solution**: Migration already applied, skip this step.

**Verify**:
```bash
psql postgresql://postgres@localhost:5432/price_scout -c "\d currency_rates"
```

---

### Issue 2: API Won't Start

**Error**: `Database connection failed`

**Check**:
```bash
# Verify PostgreSQL running
sudo systemctl status postgresql

# Test connection
psql postgresql://postgres@localhost:5432/price_scout -c "SELECT NOW();"

# Check DATABASE_URL in service file
grep DATABASE_URL /etc/systemd/system/price-scout-api.service
```

---

### Issue 3: ML Predictions Fail

**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**:
```bash
# Verify Python packages
cd /home/sergey/price_scout
source venv/bin/activate
pip list | grep -E "(pandas|sklearn|psycopg2|joblib)"

# Reinstall if missing
pip install pandas scikit-learn psycopg2-binary joblib
```

---

### Issue 4: Empty Analytics Results

**Cause**: No historical data in price_history table

**Solution**: Wait for automated scraping to collect data over time, or manually trigger scraping:

```bash
# Trigger scraping for all products
curl -X POST http://localhost:3000/api/products/1/scrape \
  -H "Content-Type: application/json" \
  -d '{"priority": 8}'

# Check queue
curl http://localhost:3000/api/queue/stats | jq
```

**Note**: Analytics require time-series data:
- **Price trends**: Needs multiple days of price_history
- **Currency correlation**: Needs 30+ days of prices + currency data
- **ML predictions**: Needs 20+ days (60+ recommended)

---

## Performance Benchmarks

**Expected Response Times** (with data):

| Endpoint              | Response Time | Notes                          |
|-----------------------|---------------|--------------------------------|
| /health               | ~1-5ms        | No DB query                    |
| /api/stores           | ~10-30ms      | Simple SELECT                  |
| /api/analytics/trends | ~50-200ms     | Aggregation query              |
| /api/arbitrage        | ~150-600ms    | Complex cross-store joins      |
| /api/predictions      | ~300-800ms    | Python process spawn + ML      |

**Database Query Performance**:
```bash
# Check slow queries
psql postgresql://postgres@localhost:5432/price_scout -c "
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%analytics%'
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

---

## Success Criteria

- [+] Migration 003 applied successfully
- [+] API server compiles without errors
- [+] API server starts and listens on port 3000
- [+] All 13 endpoints return valid responses
- [+] Currency collection script works
- [+] ML trainer runs without errors (when data available)
- [+] ML predictor returns JSON via API

---

## Next Steps

1. **Collect Initial Data** (Week 1):
   - Run scheduled scraping for 7 days
   - Collect currency rates daily
   - Monitor data quality

2. **Train ML Models** (Week 2):
   - Train models for all products once 20+ days of data collected
   - Evaluate model accuracy
   - Retrain weekly

3. **Production Optimization** (Week 3):
   - Add caching layer (Redis) for analytics results
   - Pre-compute predictions and store in database
   - Set up monitoring and alerting

4. **Phase 4** (Future):
   - Telegram bot integration
   - User authentication and tracking
   - Real-time price alerts

---

## Documentation References

- [ANALYTICS_API.md](docs/ANALYTICS_API.md) - Full API specification
- [ML_PREDICTIONS_README.md](scripts/ML_PREDICTIONS_README.md) - ML setup guide
- [REST_API.md](docs/REST_API.md) - Core API documentation
- [PROJECT_DASHBOARD.md](PROJECT_DASHBOARD.md) - Project status

---

**Deployment Checklist**:

- [ ] Migration 003 applied
- [ ] API server built (release mode)
- [ ] Python ML packages installed
- [ ] API server restarted
- [ ] Health check passed
- [ ] Analytics endpoints tested
- [ ] Currency collection tested
- [ ] ML predictions tested (when data available)
- [ ] Automated tasks configured (cron/systemd)
- [ ] Logs reviewed for errors

**Deploy Date**: ___________
**Deployed By**: ___________
**Notes**: ___________
