# Analytics API Documentation

## Overview

The Analytics API provides endpoints for market analysis, price trends tracking, currency correlations, and store comparisons. These endpoints enable data-driven insights into electronics pricing patterns across multiple marketplaces.

**Base URL**: `http://localhost:3000/api/analytics`

**Authentication**: Not required (currently)

---

## Endpoints

### 1. Price Trends

Get historical price trends for a specific product.

**Endpoint**: `GET /api/analytics/price-trends/:product_id`

**URL Parameters**:
- `product_id` (required): Product ID (integer)

**Query Parameters**:
- `days` (optional): Number of days to analyze (default: 7)

**Request Example**:
```bash
curl "http://localhost:3000/api/analytics/price-trends/1?days=30"
```

**Response Schema**:
```json
{
  "product_id": 1,
  "trends": [
    {
      "date": "2025-01-05",
      "avg_price": 125000.50,
      "min_price": 120000,
      "max_price": 130000,
      "volatility": 2547.32
    }
  ]
}
```

**Response Fields**:
- `product_id`: Product identifier
- `trends`: Array of daily trend data points
  - `date`: Date in YYYY-MM-DD format
  - `avg_price`: Average price across all stores (kopecks)
  - `min_price`: Minimum price found (kopecks)
  - `max_price`: Maximum price found (kopecks)
  - `volatility`: Standard deviation of prices (null if insufficient data)

**Use Cases**:
- Track price changes over time
- Identify pricing volatility
- Detect price drops or spikes
- Forecast price trends

---

### 2. Currency Correlation

Calculate correlation between product prices and currency exchange rates.

**Endpoint**: `GET /api/analytics/currency-correlation/:product_id`

**URL Parameters**:
- `product_id` (required): Product ID (integer)

**Query Parameters**:
- `currency` (optional): Currency code (default: "USD")
  - Supported: `USD`, `EUR`
- `days` (optional): Analysis period in days (default: 30)

**Request Example**:
```bash
curl "http://localhost:3000/api/analytics/currency-correlation/1?currency=USD&days=30"
```

**Response Schema**:
```json
{
  "product_id": 1,
  "currency": "USD",
  "correlation": 0.87,
  "days": 30
}
```

**Response Fields**:
- `product_id`: Product identifier
- `currency`: Currency code analyzed
- `correlation`: Pearson correlation coefficient (-1.0 to 1.0, null if insufficient data)
- `days`: Analysis period used

**Correlation Interpretation**:
- `1.0`: Perfect positive correlation (price rises with currency rate)
- `0.0`: No correlation
- `-1.0`: Perfect negative correlation (price falls as currency rate rises)
- `null`: Insufficient data for analysis

**Use Cases**:
- Identify imported products (high USD/EUR correlation)
- Detect currency-dependent pricing strategies
- Predict price changes based on forex trends
- Optimize purchasing timing

---

### 3. Store Comparison

Compare pricing and availability across different stores for a product.

**Endpoint**: `GET /api/analytics/store-comparison/:product_id`

**URL Parameters**:
- `product_id` (required): Product ID (integer)

**Query Parameters**:
- `days` (optional): Analysis period in days (default: 30)

**Request Example**:
```bash
curl "http://localhost:3000/api/analytics/store-comparison/1?days=7"
```

**Response Schema**:
```json
{
  "product_id": 1,
  "stores": [
    {
      "store_name": "dns-shop",
      "avg_price": 123456.78,
      "update_count": 42,
      "availability_rate": 0.95
    },
    {
      "store_name": "ozon",
      "avg_price": 125000.00,
      "update_count": 38,
      "availability_rate": 0.89
    }
  ]
}
```

**Response Fields**:
- `product_id`: Product identifier
- `stores`: Array of store statistics (sorted by avg_price ascending)
  - `store_name`: Store identifier
  - `avg_price`: Average price over the period (kopecks)
  - `update_count`: Number of price updates recorded
  - `availability_rate`: Percentage of time product was available (0.0-1.0)

**Use Cases**:
- Find cheapest stores for a product
- Identify reliable stores (high availability_rate)
- Track store pricing strategies
- Monitor price update frequency

---

### 4. Market Overview

Get aggregated market statistics for a price range.

**Endpoint**: `GET /api/analytics/market-overview`

**Query Parameters** (all required):
- `min_price`: Minimum price in RUB (integer)
- `max_price`: Maximum price in RUB (integer)
- `days` (optional): Analysis period in days (default: 7)

**Request Example**:
```bash
curl "http://localhost:3000/api/analytics/market-overview?min_price=5000&max_price=15000&days=7"
```

**Response Schema**:
```json
{
  "total_products": 127,
  "avg_price": 980567.89,
  "min_price": 500000,
  "max_price": 1499000,
  "total_price_points": 3542
}
```

**Response Fields**:
- `total_products`: Number of distinct products in price range
- `avg_price`: Average price across all products and stores (kopecks)
- `min_price`: Lowest price found (kopecks)
- `max_price`: Highest price found (kopecks)
- `total_price_points`: Total number of price records analyzed

**Use Cases**:
- Market size estimation
- Competitive pricing analysis
- Price range validation
- Market health monitoring

---

### 5. Arbitrage Opportunities

Detect price differences across stores for the same product to identify arbitrage opportunities.

**Endpoint**: `GET /api/arbitrage`

**Query Parameters**:
- `min_profit` (optional): Minimum profit percentage (default: 10.0)

**Request Example**:
```bash
curl "http://localhost:3000/api/arbitrage?min_profit=15"
```

**Response Schema**:
```json
{
  "opportunities": [
    {
      "product_id": 42,
      "product_name": "MacBook Pro 16\" M1 Pro 32GB 512GB",
      "category": "laptops",
      "buy_store": "dns-shop",
      "buy_price": 10500000,
      "sell_store": "ozon",
      "sell_price": 12000000,
      "profit_kopecks": 1500000,
      "profit_percent": 14.29
    }
  ],
  "count": 1
}
```

**Response Fields**:
- `opportunities`: Array of arbitrage opportunities
  - `product_id`: Product identifier
  - `product_name`: Product name
  - `category`: Product category
  - `buy_store`: Store with lowest price (where to buy)
  - `buy_price`: Purchase price in kopecks
  - `sell_store`: Store with highest price (theoretical sell point)
  - `sell_price`: Selling price in kopecks
  - `profit_kopecks`: Absolute profit (sell_price - buy_price)
  - `profit_percent`: Profit as percentage of buy_price
- `count`: Number of opportunities found

**Sorting**: Results sorted by `profit_percent` descending (most profitable first)

**Limit**: Maximum 100 opportunities returned

**Use Cases**:
- Identify price discrepancies across stores
- Find buy-low opportunities
- Detect pricing errors or inconsistencies
- Market efficiency analysis
- Competitive intelligence

**Real-world Application**:
While physical arbitrage (buying from one store to sell at another) is impractical for consumer electronics, this endpoint helps:
- Consumers find the best deals
- Retailers monitor competitor pricing
- Market analysts identify pricing inefficiencies
- Price tracking services alert users to significant price drops

**Example Interpretation**:
```json
{
  "buy_store": "dns-shop",
  "buy_price": 10500000,  // 105,000 RUB
  "sell_store": "ozon",
  "sell_price": 12000000,  // 120,000 RUB
  "profit_percent": 14.29  // 14.29% price difference
}
```

This means the same MacBook Pro costs 14.29% more at Ozon than at DNS-Shop, saving 15,000 RUB by purchasing from DNS-Shop.

---

### 6. ML Price Predictions

Get machine learning-based price predictions for future pricing trends.

**Endpoint**: `GET /api/analytics/predictions/:product_id`

**URL Parameters**:
- `product_id` (required): Product ID (integer)

**Request Example**:
```bash
curl "http://localhost:3000/api/analytics/predictions/1"
```

**Response Schema**:
```json
{
  "product_id": 1,
  "current_price": 10500000,
  "predicted_price": 10350000,
  "prediction_horizon_days": 7,
  "lower_bound": 10100000,
  "upper_bound": 10600000,
  "confidence": "medium",
  "model_accuracy": {
    "r2_score": 0.78,
    "mae_kopecks": 125000.5,
    "mae_rub": 1250.01
  },
  "predicted_at": "2025-01-05T18:30:00+03:00",
  "model_trained_at": "2025-01-05T12:00:00+03:00"
}
```

**Response Fields**:
- `product_id`: Product identifier
- `current_price`: Current average price in kopecks
- `predicted_price`: Predicted price in 7 days (kopecks)
- `prediction_horizon_days`: Prediction timeframe (always 7)
- `lower_bound`: Lower 95% confidence interval (kopecks)
- `upper_bound`: Upper 95% confidence interval (kopecks)
- `confidence`: Model confidence level ("low", "medium", "high")
- `model_accuracy`: Model performance metrics
  - `r2_score`: R² score (0-1, higher is better)
  - `mae_kopecks`: Mean Absolute Error in kopecks
  - `mae_rub`: Mean Absolute Error in rubles
- `predicted_at`: Timestamp of prediction
- `model_trained_at`: When the model was last trained

**Confidence Levels**:
- `high`: R² > 0.7 (model explains >70% of price variance)
- `medium`: R² 0.5-0.7 (moderate predictive power)
- `low`: R² < 0.5 (limited predictive power)

**Prerequisites**:
The ML model must be trained before predictions can be made:
```bash
# Train model for product
python3 scripts/ml_predictor.py train --product-id 1

# Make prediction via API
curl "http://localhost:3000/api/analytics/predictions/1"
```

**Training Requirements**:
- Minimum 20 days of historical price data
- At least 60 days recommended for better accuracy
- Currency rate data should be available for the same period

**ML Model Details**:
- **Algorithm**: Random Forest Regressor (default) or Linear Regression
- **Features**:
  - 7-day rolling average price
  - 30-day rolling average price
  - Price trend (change over 7 days)
  - USD to RUB exchange rate
  - EUR to RUB exchange rate
  - Day of week (0=Monday, 6=Sunday)
  - Days since first observation
- **Target**: Price 7 days in the future
- **Training**: 80/20 train/test split
- **Saved**: Models stored in `models/product_{id}_predictor.pkl`

**Use Cases**:
- Predict when prices will drop
- Optimal purchase timing
- Budget planning
- Price trend forecasting
- Market analysis

**Limitations**:
- Predictions are statistical forecasts, not guarantees
- Accuracy depends on data quality and market stability
- Cannot predict sudden market shocks or promotions
- Requires regular retraining as new data arrives
- Best for stable, predictable products

**Error Responses**:

**404 No Model Found**:
```json
{
  "error": "ML predictor failed: No trained model found for product 1. Train first with: python ml_predictor.py train --product-id 1"
}
```

**500 Insufficient Data**:
```json
{
  "error": "ML predictor failed: No data found for product 1"
}
```

**Example Interpretation**:
```json
{
  "current_price": 10500000,  // 105,000 RUB today
  "predicted_price": 10350000, // 103,500 RUB in 7 days
  "lower_bound": 10100000,     // Could be as low as 101,000 RUB
  "upper_bound": 10600000      // Could be as high as 106,000 RUB
}
```

This predicts a 1.43% price decrease (1,500 RUB drop) over the next week, with 95% confidence the price will be between 101,000-106,000 RUB.

---

## Data Types

### Price Format
All prices are returned in **kopecks** (1 RUB = 100 kopecks) to avoid floating-point precision issues.

**Conversion**:
```javascript
const rubPrice = kopecksPrice / 100;  // 125000 kopecks = 1250.00 RUB
```

### Date Format
Dates are returned in ISO 8601 format: `YYYY-MM-DD`

### Correlation Values
Pearson correlation coefficient ranges from -1.0 to 1.0:
- Values > 0.7: Strong positive correlation
- Values 0.3 to 0.7: Moderate positive correlation
- Values -0.3 to 0.3: Weak or no correlation
- Values -0.7 to -0.3: Moderate negative correlation
- Values < -0.7: Strong negative correlation

---

## Error Handling

All endpoints return standard error responses with HTTP status codes:

**404 Not Found**:
```json
{
  "error": "Product not found"
}
```

**500 Internal Server Error**:
```json
{
  "error": "Database connection failed: connection refused"
}
```

**Common Error Scenarios**:
- Product ID doesn't exist → 500 (returns empty data arrays)
- Invalid date range → 500
- Database connection issues → 500
- No data available for analysis → 200 with null/empty values

---

## Integration Examples

### Python
```python
import requests

# Get price trends
response = requests.get(
    "http://localhost:3000/api/analytics/price-trends/1",
    params={"days": 30}
)
trends = response.json()

print(f"Product {trends['product_id']} trends:")
for point in trends['trends']:
    print(f"  {point['date']}: {point['avg_price']/100:.2f} RUB")
```

### JavaScript (Node.js)
```javascript
const axios = require('axios');

async function getCurrencyCorrelation(productId) {
  const response = await axios.get(
    `http://localhost:3000/api/analytics/currency-correlation/${productId}`,
    { params: { currency: 'USD', days: 30 } }
  );

  const { correlation, currency } = response.data;
  console.log(`${currency} correlation: ${correlation?.toFixed(2) ?? 'N/A'}`);
}
```

### cURL
```bash
# Price trends for last 7 days
curl "http://localhost:3000/api/analytics/price-trends/1?days=7" | jq

# Store comparison
curl "http://localhost:3000/api/analytics/store-comparison/1" | jq '.stores[] | {name: .store_name, price: (.avg_price/100)}'

# Market overview
curl "http://localhost:3000/api/analytics/market-overview?min_price=5000&max_price=15000" | jq

# Arbitrage opportunities (min 15% profit)
curl "http://localhost:3000/api/arbitrage?min_profit=15" | jq '.opportunities[] | {product: .product_name, profit: .profit_percent}'

# ML price prediction
curl "http://localhost:3000/api/analytics/predictions/1" | jq '{current: (.current_price/100), predicted: (.predicted_price/100), confidence: .confidence}'
```

---

## Performance Considerations

### Database Queries
Analytics endpoints execute complex SQL queries with aggregations and joins. Performance depends on:
- **Data volume**: More price history = slower queries
- **Date range**: Larger `days` parameter = more data to process
- **Indexing**: Ensure `recorded_at` columns are indexed

### Optimization Tips
1. **Use appropriate date ranges**: Don't request 365 days if 30 days is sufficient
2. **Cache results**: Analytics data changes slowly, cache for 10-15 minutes
3. **Batch requests**: Fetch trends for multiple products in parallel
4. **Database indexes**: Ensure indexes exist on:
   - `price_history(product_id, recorded_at)`
   - `currency_rates(currency_code, recorded_at)`

### Expected Response Times
- Price trends (7 days): ~50-200ms
- Currency correlation (30 days): ~100-300ms
- Store comparison (30 days): ~100-400ms
- Market overview: ~200-500ms (depends on product count)
- Arbitrage opportunities: ~150-600ms (complex cross-store joins)
- ML predictions: ~300-800ms (Python process spawn + model inference)

---

## Database Schema Dependencies

Analytics endpoints rely on the following tables:

**price_history**:
```sql
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    price INT NOT NULL,
    available BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**currency_rates**:
```sql
CREATE TABLE currency_rates (
    id BIGSERIAL PRIMARY KEY,
    currency_code TEXT NOT NULL,
    rate_to_rub NUMERIC(10, 4) NOT NULL,
    source TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Required Indexes**:
```sql
CREATE INDEX idx_price_history_product_time ON price_history(product_id, recorded_at DESC);
CREATE INDEX idx_currency_rates_time ON currency_rates(currency_code, recorded_at DESC);
```

---

## Future Enhancements

Planned features for analytics API:

1. **Historical Comparisons**:
   - Year-over-year price changes
   - Seasonal trend analysis
   - Holiday pricing patterns

3. **Real-time Alerts**:
   - WebSocket endpoints for price drop notifications
   - Currency correlation threshold alerts
   - Arbitrage opportunity alerts

4. **Advanced Filters**:
   - Filter arbitrage by product category
   - Geographic/regional price analysis
   - Time-of-day pricing patterns

---

## Related Documentation

- [REST API Specification](REST_API.md) - Core API endpoints
- [Database Schema](../migrations/) - Database structure
- [Architecture Overview](TECH_STACK.md) - System architecture

---

**Last Updated**: 2025-01-05
**API Version**: 1.0.0
**Maintainer**: Price Scout Team
