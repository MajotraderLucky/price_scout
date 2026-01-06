# Analytics Platform Deployment Summary

**Date**: 2026-01-05
**Status**: Ready for Deployment to Archbook
**Phase**: 3 Complete - Analytics Platform

---

## What's Ready

### ✅ Compiled Binaries (Release Mode)

All binaries compiled successfully in optimized release mode:

| Binary                      | Size  | Purpose                              |
|-----------------------------|-------|--------------------------------------|
| price-scout-api             | 3.5MB | REST API server (13 endpoints)       |
| price-scout-worker          | 2.9MB | Continuous scraping worker           |
| price-scout-scheduler       | 2.7MB | One-shot job scheduler (timer-based) |

**Location**: `target/release/`

**Build Command Used**:
```bash
cargo build --release --bin price-scout-api --bin price-scout-worker --bin price-scout-scheduler
```

---

### ✅ Database Migration

**Migration 003**: Currency Rates Table

**File**: `migrations/003_add_currency_rates.sql`

**Ready to apply** on Archbook PostgreSQL database.

**Table Schema**:
- `currency_rates` - Stores USD/EUR exchange rates from dual sources
- Indexes on `(currency_code, recorded_at)` for performance
- CHECK constraints for data validation

---

### ✅ Python Scripts

#### 1. Currency Collection Script

**File**: `scripts/collect_currency_rates.py` (5.5KB)

**Sources**:
- ЦБ РФ API (https://www.cbr-xml-daily.ru/daily_json.js)
- open.er-api.com (https://open.er-api.com/v6/latest/USD)

**Usage**:
```bash
python3 scripts/collect_currency_rates.py --dry-run  # Test
python3 scripts/collect_currency_rates.py            # Collect
```

**Dependencies**: requests, psycopg2-binary (already installed)

---

#### 2. ML Price Predictor

**File**: `scripts/ml_predictor.py` (14KB)

**Features**:
- Train Random Forest models for price forecasting
- Predict 7-day future prices
- CLI and JSON output modes

**Usage**:
```bash
python3 scripts/ml_predictor.py train --product-id 1
python3 scripts/ml_predictor.py predict --product-id 1 --output json
```

**Dependencies Required** (NOT yet installed on Archbook):
```bash
pip install pandas scikit-learn psycopg2-binary joblib
```

---

#### 3. API Test Script

**File**: `scripts/test_analytics_api.sh` (executable)

**Tests**: All 13 API endpoints automatically

**Usage**:
```bash
./scripts/test_analytics_api.sh http://localhost:3000
./scripts/test_analytics_api.sh http://192.168.0.10:3000
```

---

### ✅ API Endpoints

**Total**: 13 endpoints (7 core + 6 analytics)

#### Core Endpoints (7)
1. GET /health - Health check
2. GET /api/stores - List stores
3. GET /api/products/:id - Get product
4. GET /api/products/:id/prices - Get prices
5. POST /api/search - Search products
6. POST /api/products/:id/scrape - Trigger scraping
7. GET /api/queue/stats - Queue statistics

#### Analytics Endpoints (6)
8. GET /api/analytics/price-trends/:id?days=7
9. GET /api/analytics/currency-correlation/:id?currency=USD&days=30
10. GET /api/analytics/store-comparison/:id?days=30
11. GET /api/analytics/market-overview?min_price=5000&max_price=15000&days=7
12. GET /api/arbitrage?min_profit=10
13. GET /api/analytics/predictions/:id

---

### ✅ Documentation

#### Complete Documentation Package

| Document                         | Size  | Purpose                                |
|----------------------------------|-------|----------------------------------------|
| DEPLOY_ANALYTICS.md              | 17KB  | Step-by-step deployment guide          |
| docs/ANALYTICS_API.md            | 28KB  | Full analytics API specification       |
| scripts/ML_PREDICTIONS_README.md | 11KB  | ML setup and usage guide               |
| docs/REST_API.md                 | 24KB  | Core API documentation (updated)       |
| PROJECT_DASHBOARD.md             | 52KB  | Project status (updated with PS-33-38) |

---

### ✅ Configuration Files

#### Systemd Services

**Files Created**:
- `config/price-scout-api.service` - API server
- `config/price-scout-worker.service` - Continuous worker
- `config/price-scout-scheduler.service` - Scheduler service
- `config/price-scout-scheduler.timer` - Systemd timer (10-min intervals)

**Status**: Ready to copy to `/etc/systemd/system/`

---

## Deployment Checklist

### On Archbook Server (192.168.0.10)

- [ ] **Step 1**: Apply migration 003
  ```bash
  psql postgresql://postgres@localhost:5432/price_scout -f migrations/003_add_currency_rates.sql
  ```

- [ ] **Step 2**: Install Python ML dependencies
  ```bash
  source venv/bin/activate
  pip install pandas scikit-learn psycopg2-binary joblib
  ```

- [ ] **Step 3**: Copy release binaries
  ```bash
  cp target/release/price-scout-* /home/sergey/price_scout/target/release/
  ```

- [ ] **Step 4**: Update systemd services
  ```bash
  sudo cp config/*.service /etc/systemd/system/
  sudo cp config/*.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  ```

- [ ] **Step 5**: Restart API server
  ```bash
  sudo systemctl restart price-scout-api.service
  sudo systemctl status price-scout-api.service
  ```

- [ ] **Step 6**: Test endpoints
  ```bash
  ./scripts/test_analytics_api.sh http://localhost:3000
  ```

- [ ] **Step 7**: Collect initial currency data
  ```bash
  python3 scripts/collect_currency_rates.py
  ```

- [ ] **Step 8**: Set up automated currency collection
  ```bash
  sudo systemctl enable --now price-scout-currency.timer
  ```

---

## Testing Results Expected

### With Current Data

**Working Immediately** (uses current store_prices):
- ✅ Health check
- ✅ Stores list
- ✅ Product endpoints
- ✅ Search
- ✅ Queue stats
- ✅ Store comparison (basic)
- ✅ Market overview
- ✅ Arbitrage detector

**Requires Historical Data** (empty results initially):
- ⏳ Price trends (needs price_history table populated over days)
- ⏳ Currency correlation (needs 30+ days of data)
- ⏳ ML predictions (needs 20-60 days of data + trained model)

---

## Post-Deployment Tasks

### Week 1: Data Collection
1. **Run automated scraping** for 7 days minimum
2. **Collect currency rates** daily (automated via cron/timer)
3. **Monitor logs** for errors
4. **Verify data quality** in price_history and currency_rates tables

### Week 2: ML Model Training
1. **Check data availability**:
   ```sql
   SELECT product_id, COUNT(*) as days
   FROM price_history
   WHERE recorded_at >= NOW() - INTERVAL '60 days'
   GROUP BY product_id
   HAVING COUNT(*) >= 20;
   ```

2. **Train models** for products with sufficient data:
   ```bash
   for product_id in $(psql -t -c "SELECT DISTINCT product_id FROM price_history"); do
     python3 scripts/ml_predictor.py train --product-id $product_id
   done
   ```

3. **Evaluate accuracy**:
   ```bash
   cat models/product_*_metrics.json | jq '{product_id, test_r2, test_mae}'
   ```

### Week 3: Optimization
1. **Add caching** (Redis) for analytics results
2. **Pre-compute predictions** and store in database
3. **Set up monitoring** (Prometheus/Grafana)
4. **Configure alerts** for failures

---

## Performance Benchmarks

### Binary Sizes (Release Mode)

Total size: ~9 MB for all 3 binaries

**Comparison to Debug Mode**:
- Debug: ~15-20 MB per binary
- Release: ~3-4 MB per binary
- **Reduction**: ~60-70% smaller

### Expected Response Times

| Endpoint         | Cold Start | Warm (cached) | Notes                    |
|------------------|------------|---------------|--------------------------|
| Health           | 1-5ms      | <1ms          | No DB query              |
| Stores           | 10-30ms    | 5-10ms        | Simple SELECT            |
| Price Trends     | 50-200ms   | 30-100ms      | Aggregation query        |
| Arbitrage        | 150-600ms  | 100-300ms     | Complex joins            |
| ML Predictions   | 300-800ms  | 200-500ms     | Python subprocess + ML   |

---

## Known Limitations

### Current Limitations

1. **No Historical Data Yet**
   - Price trends, correlation, ML predictions will return empty/null
   - **Solution**: Wait 7-60 days for data collection

2. **ML Dependencies Not Installed**
   - ML predictions will fail until packages installed
   - **Solution**: `pip install pandas scikit-learn psycopg2-binary joblib`

3. **No Caching Layer**
   - Analytics queries run on every request
   - **Solution**: Add Redis caching (Phase 4)

4. **No Authentication**
   - API is public (safe on local network)
   - **Solution**: Add JWT auth (Phase 4)

5. **Single Server**
   - No load balancing or redundancy
   - **Solution**: Add replica server (Phase 4)

---

## Rollback Plan

If issues occur, rollback procedure:

```bash
# 1. Stop new services
sudo systemctl stop price-scout-api.service

# 2. Restore old binary (if backed up)
sudo cp /home/sergey/price_scout/target/release/price-scout-api.backup \
        /home/sergey/price_scout/target/release/price-scout-api

# 3. Rollback migration (if needed)
psql postgresql://postgres@localhost:5432/price_scout -c "DROP TABLE IF EXISTS currency_rates CASCADE;"

# 4. Restart with old version
sudo systemctl start price-scout-api.service

# 5. Verify
curl http://localhost:3000/health
```

**Backup Recommendation**: Before deployment, backup current binary:
```bash
cp target/release/price-scout-api target/release/price-scout-api.backup.$(date +%Y%m%d)
```

---

## Success Criteria

Deployment is successful when:

- [+] All 3 binaries compiled in release mode
- [+] Migration 003 applied without errors
- [+] API server starts and listens on port 3000
- [+] All 13 endpoints return valid HTTP responses
- [+] No errors in systemd service logs
- [+] Currency collection script works
- [+] Test script passes all non-ML tests
- [+] ML predictions work after training (when data available)

---

## Support Information

### Logs Location

```bash
# API server logs
sudo journalctl -u price-scout-api.service -f

# Worker logs
sudo journalctl -u price-scout-worker.service -f

# Scheduler logs
sudo journalctl -u price-scout-scheduler.service -f

# Currency collection logs
sudo journalctl -u price-scout-currency.service -f
```

### Configuration Files

- **API config**: `/etc/systemd/system/price-scout-api.service`
- **Database URL**: Set in systemd service files
- **ML models**: `models/product_{id}_predictor.pkl`
- **Metrics**: `models/product_{id}_metrics.json`

### Useful Commands

```bash
# Check API status
curl http://localhost:3000/health

# View queue stats
curl http://localhost:3000/api/queue/stats | jq

# Check database
psql postgresql://postgres@localhost:5432/price_scout -c "SELECT COUNT(*) FROM currency_rates;"

# Test ML predictor
python3 scripts/ml_predictor.py predict --product-id 1

# List trained models
ls -lh models/
```

---

## Related Documentation

- **Deployment Guide**: DEPLOY_ANALYTICS.md (step-by-step instructions)
- **API Documentation**: docs/ANALYTICS_API.md (endpoint specs)
- **ML Guide**: scripts/ML_PREDICTIONS_README.md (training & usage)
- **Project Status**: PROJECT_DASHBOARD.md (overall progress)

---

**Status**: ✅ **Ready for Production Deployment**

**Estimated Deployment Time**: 30-45 minutes

**Recommended Deployment Window**: Off-peak hours (avoid business hours)

**Deployed By**: _________________

**Deployment Date**: _________________

**Verification Signature**: _________________
