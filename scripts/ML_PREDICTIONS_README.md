# ML Price Predictions Setup Guide

## Overview

The ML Price Predictor uses machine learning to forecast product prices 7 days into the future based on historical price data and currency exchange rates.

**Model**: Random Forest Regressor (default) or Linear Regression
**Prediction Horizon**: 7 days
**Minimum Data**: 20 days of historical prices (60+ days recommended)

---

## Installation

### 1. Install Python Dependencies

```bash
pip install pandas scikit-learn psycopg2-binary joblib
```

Or using a virtual environment (recommended):

```bash
cd /home/ryazanov/Development/price_scout
python3 -m venv venv
source venv/bin/activate
pip install pandas scikit-learn psycopg2-binary joblib
```

### 2. Set Database URL

```bash
export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
```

---

## Usage

### Training a Model

Train a model for a specific product:

```bash
# Train with default settings (Random Forest, 90 days of data)
python3 scripts/ml_predictor.py train --product-id 1

# Train with custom settings
python3 scripts/ml_predictor.py train --product-id 1 --model linear --days 120
```

**Output**:
```
Fetching training data for product 1...
Found 85 days of data
Engineering features...
Training set size: 65 samples
Training random_forest model...

Model Performance:
  R² Score (train): 0.8523
  R² Score (test):  0.7834
  MAE (train):      98543.21 kopecks (985.43 RUB)
  MAE (test):       125432.45 kopecks (1254.32 RUB)
  RMSE (train):     112345.67 kopecks (1123.46 RUB)
  RMSE (test):      145678.89 kopecks (1456.79 RUB)

Model saved to: models/product_1_predictor.pkl
Metrics saved to: models/product_1_metrics.json
```

**Model Files**:
- `models/product_{id}_predictor.pkl` - Trained model
- `models/product_{id}_metrics.json` - Performance metrics

### Making Predictions

#### Via Command Line

```bash
# Text output (human-readable)
python3 scripts/ml_predictor.py predict --product-id 1

# JSON output (for scripting)
python3 scripts/ml_predictor.py predict --product-id 1 --output json
```

**Text Output Example**:
```
Price Prediction for Product 1:
  Current Price:    10500000 kopecks (105,000.00 RUB)
  Predicted Price:  10350000 kopecks (103,500.00 RUB)
  Prediction Range: 10100000 - 10600000 kopecks
  Horizon:          7 days
  Confidence:       medium
  Model Accuracy:   R²=0.783, MAE=1254.32 RUB
```

**JSON Output Example**:
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
    "r2_score": 0.7834,
    "mae_kopecks": 125432.45,
    "mae_rub": 1254.32
  },
  "predicted_at": "2025-01-05T18:30:00.123456",
  "model_trained_at": "2025-01-05T12:00:00.123456"
}
```

#### Via REST API

```bash
# Make sure API server is running
cargo run --bin price-scout-api

# Get prediction
curl "http://localhost:3000/api/analytics/predictions/1" | jq
```

---

## How It Works

### Features Used

The model uses 7 features to predict future prices:

1. **price_7d_avg**: 7-day rolling average of price
2. **price_30d_avg**: 30-day rolling average of price
3. **price_trend**: Price change over last 7 days
4. **usd_rate**: USD to RUB exchange rate
5. **eur_rate**: EUR to RUB exchange rate
6. **day_of_week**: Day of week (0=Monday, 6=Sunday)
7. **days_since_start**: Days since first observation

### Training Process

1. **Data Collection**: Fetch historical prices and currency rates from database
2. **Feature Engineering**: Calculate rolling averages, trends, and time features
3. **Data Splitting**: 80% training, 20% testing (time-ordered, no shuffle)
4. **Model Training**: Random Forest with 100 trees, max depth 10
5. **Evaluation**: Calculate R², MAE, RMSE on test set
6. **Model Saving**: Serialize model to disk for later use

### Prediction Process

1. **Load Model**: Load trained model from disk
2. **Fetch Recent Data**: Get last 60 days of price and currency data
3. **Feature Calculation**: Calculate same features as training
4. **Inference**: Use most recent data point to predict 7 days ahead
5. **Confidence Interval**: ±2 standard deviations (~95% confidence)

---

## Model Management

### List Trained Models

```bash
ls -lh models/
```

### View Model Metrics

```bash
cat models/product_1_metrics.json | jq
```

Output:
```json
{
  "model_type": "random_forest",
  "product_id": 1,
  "training_samples": 65,
  "test_samples": 17,
  "train_r2": 0.8523,
  "test_r2": 0.7834,
  "train_mae": 98543.21,
  "test_mae": 125432.45,
  "train_rmse": 112345.67,
  "test_rmse": 145678.89,
  "trained_at": "2025-01-05T12:00:00.123456"
}
```

### Retrain Model

Models should be retrained periodically as new data arrives:

```bash
# Weekly retraining recommended
python3 scripts/ml_predictor.py train --product-id 1
```

### Delete Model

```bash
rm models/product_1_predictor.pkl
rm models/product_1_metrics.json
```

---

## Confidence Levels

Predictions include a confidence level based on model accuracy:

| Confidence | R² Score | Meaning                                                     |
|------------|----------|-------------------------------------------------------------|
| high       | > 0.7    | Model explains >70% of price variance, reliable predictions |
| medium     | 0.5-0.7  | Moderate predictive power, use with caution                 |
| low        | < 0.5    | Limited predictive power, unreliable predictions            |

**Recommendations**:
- **high**: Trust predictions for purchase timing decisions
- **medium**: Consider predictions alongside other factors
- **low**: Retrain with more data or use alternative analysis

---

## Troubleshooting

### Error: "No data found for product X"

**Cause**: Product has no price history in database

**Solution**:
1. Verify product exists: `SELECT * FROM products WHERE id = X;`
2. Check for price data: `SELECT COUNT(*) FROM store_prices WHERE product_id = X;`
3. Run scrapers to collect data first

### Error: "Insufficient data for training"

**Cause**: Less than 20 days of historical data

**Solution**:
1. Wait for more data to accumulate
2. Run scheduled scraping more frequently
3. Manually trigger scraping: `curl -X POST http://localhost:3000/api/products/X/scrape`

### Error: "No module named 'pandas'"

**Cause**: Python dependencies not installed

**Solution**:
```bash
pip install pandas scikit-learn psycopg2-binary joblib
```

### Low Prediction Accuracy (R² < 0.5)

**Causes**:
- Product has volatile pricing (sales, promotions)
- Insufficient training data
- Missing currency rate data
- Product is new (no stable pricing history)

**Solutions**:
1. Collect more data (60-90 days minimum)
2. Ensure currency rates are populated
3. Try linear regression instead: `--model linear`
4. Accept that some products are inherently unpredictable

---

## Performance Optimization

### Reduce API Response Time

**Problem**: Predictions take 800ms+ via API

**Solutions**:
1. **Pre-compute predictions**: Run predictions in background, store in database
2. **Cache predictions**: Cache results for 1-6 hours (prices change slowly)
3. **Use linear model**: Faster inference than Random Forest

Example caching implementation:
```sql
CREATE TABLE price_predictions (
    product_id BIGINT PRIMARY KEY,
    predicted_price INT NOT NULL,
    lower_bound INT NOT NULL,
    upper_bound INT NOT NULL,
    confidence TEXT NOT NULL,
    predicted_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Update predictions every 6 hours via cron
```

### Batch Training

Train models for multiple products:

```bash
#!/bin/bash
# train_all_models.sh
for product_id in $(psql -t -c "SELECT id FROM products WHERE category = 'laptops'"); do
  echo "Training model for product $product_id..."
  python3 scripts/ml_predictor.py train --product-id $product_id
done
```

---

## Advanced Usage

### Custom Model Parameters

Edit `scripts/ml_predictor.py` to tune hyperparameters:

```python
model = RandomForestRegressor(
    n_estimators=200,      # More trees (default: 100)
    max_depth=15,          # Deeper trees (default: 10)
    min_samples_split=3,   # Split threshold (default: 5)
    random_state=42,
    n_jobs=-1
)
```

### Add Custom Features

Extend feature engineering in `engineer_features()`:

```python
# Add day of month (e.g., for payday effects)
df['day_of_month'] = df['date'].dt.day

# Add is_weekend flag
df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

# Add price acceleration (second derivative)
df['price_acceleration'] = df['price_trend'] - df['price_trend'].shift(1)
```

---

## Integration Examples

### Python Script

```python
import requests

def get_price_prediction(product_id: int):
    response = requests.get(
        f"http://localhost:3000/api/analytics/predictions/{product_id}"
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Current: {data['current_price']/100:.2f} RUB")
        print(f"Predicted: {data['predicted_price']/100:.2f} RUB")
        print(f"Confidence: {data['confidence']}")
        return data
    else:
        print(f"Error: {response.json()['error']}")
        return None

get_price_prediction(1)
```

### Telegram Bot Integration

```python
@bot.message_handler(commands=['predict'])
async def predict_price(message):
    product_id = extract_product_id(message.text)

    response = requests.get(
        f"http://localhost:3000/api/analytics/predictions/{product_id}"
    )

    if response.status_code == 200:
        data = response.json()
        current_rub = data['current_price'] / 100
        predicted_rub = data['predicted_price'] / 100
        change_pct = ((predicted_rub - current_rub) / current_rub) * 100

        await bot.send_message(
            message.chat.id,
            f"Price Forecast:\n"
            f"Current: {current_rub:,.2f} RUB\n"
            f"7-day prediction: {predicted_rub:,.2f} RUB ({change_pct:+.1f}%)\n"
            f"Confidence: {data['confidence']}"
        )
    else:
        await bot.send_message(
            message.chat.id,
            "No prediction available. Train model first."
        )
```

---

## Best Practices

1. **Train models weekly**: Retrain as new data arrives
2. **Monitor accuracy**: Check R² scores regularly
3. **Use ensembles**: Combine multiple models for better predictions
4. **Validate predictions**: Compare predictions to actual prices
5. **Document assumptions**: Note what market conditions the model assumes
6. **Set expectations**: Predictions are forecasts, not guarantees

---

## Related Documentation

- [ANALYTICS_API.md](../docs/ANALYTICS_API.md) - Full API specification
- [REST_API.md](../docs/REST_API.md) - Core API endpoints
- [ROADMAP.md](../docs/ROADMAP.md) - Future ML enhancements

---

**Created**: 2025-01-05
**Author**: Price Scout Team
**Python Version**: 3.10+
**scikit-learn Version**: 1.3.0+
