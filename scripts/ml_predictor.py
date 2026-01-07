#!/usr/bin/env python3
"""
ML Price Predictor for Price Scout

Trains and uses machine learning models to predict future product prices
based on historical data and currency exchange rates.

Usage:
    # Train model for a product
    python ml_predictor.py train --product-id 1

    # Predict future price
    python ml_predictor.py predict --product-id 1

    # Predict with custom features
    python ml_predictor.py predict --product-id 1 --output json

Requirements:
    pip install pandas scikit-learn psycopg2-binary joblib
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import pandas as pd
    import psycopg2
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    import joblib
except ImportError as e:
    print(f"Error: Missing required package: {e}", file=sys.stderr)
    print("Install with: pip install pandas scikit-learn psycopg2-binary joblib", file=sys.stderr)
    sys.exit(1)


# Configuration
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def get_db_connection():
    """Get PostgreSQL database connection from environment variable."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Parse postgresql://user:pass@host:port/dbname format
    if database_url.startswith("postgresql://"):
        # Remove postgresql:// prefix for psycopg2
        database_url = database_url.replace("postgresql://", "")
        parts = database_url.split("@")
        if len(parts) == 2:
            # Has user@host format
            user_part = parts[0]
            host_part = parts[1]

            # Extract user (no password in our case)
            user = user_part.split(":")[0] if ":" in user_part else user_part

            # Extract host and database
            if "/" in host_part:
                host_db = host_part.split("/")
                host_port = host_db[0]
                database = host_db[1] if len(host_db) > 1 else "price_scout"

                # Extract port if present
                if ":" in host_port:
                    host, port = host_port.split(":")
                else:
                    host = host_port
                    port = "5432"
            else:
                host = host_part
                port = "5432"
                database = "price_scout"

            return psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user
            )

    # Fallback: assume it's already in psycopg2 format
    return psycopg2.connect(database_url)


def fetch_training_data(product_id: int, days: int = 90) -> pd.DataFrame:
    """
    Fetch historical price data and currency rates for training.

    Args:
        product_id: Product ID to fetch data for
        days: Number of days of historical data to fetch

    Returns:
        DataFrame with columns: recorded_at, price, usd_rate, eur_rate
    """
    conn = get_db_connection()

    # Note: Using store_prices instead of price_history
    # since price_history table might not exist yet
    # Using CTE to avoid subquery reference issues with GROUP BY
    query = """
        WITH prices AS (
            SELECT
                DATE(scraped_at) as date,
                AVG(price)::float as price
            FROM store_prices
            WHERE product_id = %s
              AND available = true
              AND scraped_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(scraped_at)
        ),
        usd_rates AS (
            SELECT DATE(recorded_at) as date, AVG(rate_to_rub)::float as rate
            FROM currency_rates
            WHERE currency_code = 'USD'
            GROUP BY DATE(recorded_at)
        ),
        eur_rates AS (
            SELECT DATE(recorded_at) as date, AVG(rate_to_rub)::float as rate
            FROM currency_rates
            WHERE currency_code = 'EUR'
            GROUP BY DATE(recorded_at)
        )
        SELECT p.date, p.price, u.rate as usd_rate, e.rate as eur_rate
        FROM prices p
        LEFT JOIN usd_rates u ON p.date = u.date
        LEFT JOIN eur_rates e ON p.date = e.date
        ORDER BY p.date
    """

    df = pd.read_sql(query, conn, params=(product_id, days))
    conn.close()

    if df.empty:
        raise ValueError(f"No data found for product {product_id}")

    # Handle missing currency rates (fill with previous values)
    df['usd_rate'] = df['usd_rate'].fillna(method='ffill').fillna(method='bfill')
    df['eur_rate'] = df['eur_rate'].fillna(method='ffill').fillna(method='bfill')

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create features for machine learning model.

    Features:
    - price_7d_avg: 7-day rolling average of price
    - price_30d_avg: 30-day rolling average of price
    - price_trend: Price change over last 7 days
    - usd_rate: USD to RUB exchange rate
    - eur_rate: EUR to RUB exchange rate
    - day_of_week: Day of week (0=Monday, 6=Sunday)
    - days_since_start: Days since first observation

    Target:
    - target: Price 7 days in the future
    """
    df = df.copy()

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Rolling averages
    df['price_7d_avg'] = df['price'].rolling(window=7, min_periods=1).mean()
    df['price_30d_avg'] = df['price'].rolling(window=30, min_periods=1).mean()

    # Price trend (change over last 7 days)
    df['price_trend'] = df['price'] - df['price'].shift(7)

    # Day of week (electronics prices might vary by day)
    df['day_of_week'] = df['date'].dt.dayofweek

    # Days since start (captures overall time trend)
    df['days_since_start'] = (df['date'] - df['date'].min()).dt.days

    # Target: price 7 days in the future
    df['target'] = df['price'].shift(-7)

    # Drop rows with NaN in target (last 7 days have no future price)
    df = df.dropna(subset=['target'])

    # Drop rows with NaN in features (first few rows due to rolling windows)
    df = df.dropna()

    return df


def train_model(product_id: int, model_type: str = 'random_forest', days: int = 90):
    """
    Train ML model for price prediction.

    Args:
        product_id: Product ID to train model for
        model_type: 'random_forest' or 'linear'
        days: Number of days of historical data to use

    Returns:
        Trained model and metrics dictionary
    """
    print(f"Fetching training data for product {product_id}...")
    df = fetch_training_data(product_id, days)
    print(f"Found {len(df)} days of data")

    print("Engineering features...")
    df = engineer_features(df)
    print(f"Training set size: {len(df)} samples")

    if len(df) < 20:
        raise ValueError(f"Insufficient data for training (need at least 20 samples, got {len(df)})")

    # Define features
    feature_cols = ['price_7d_avg', 'price_30d_avg', 'price_trend',
                    'usd_rate', 'eur_rate', 'day_of_week', 'days_since_start']

    X = df[feature_cols]
    y = df['target']

    # Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False  # Don't shuffle time series
    )

    # Train model
    print(f"Training {model_type} model...")
    if model_type == 'random_forest':
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
    elif model_type == 'linear':
        model = LinearRegression()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    model.fit(X_train, y_train)

    # Evaluate
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    metrics = {
        'model_type': model_type,
        'product_id': product_id,
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'train_r2': r2_score(y_train, y_pred_train),
        'test_r2': r2_score(y_test, y_pred_test),
        'train_mae': mean_absolute_error(y_train, y_pred_train),
        'test_mae': mean_absolute_error(y_test, y_pred_test),
        'train_rmse': mean_squared_error(y_train, y_pred_train, squared=False),
        'test_rmse': mean_squared_error(y_test, y_pred_test, squared=False),
        'trained_at': datetime.now().isoformat(),
    }

    print("\nModel Performance:")
    print(f"  R² Score (train): {metrics['train_r2']:.4f}")
    print(f"  R² Score (test):  {metrics['test_r2']:.4f}")
    print(f"  MAE (train):      {metrics['train_mae']:.2f} kopecks ({metrics['train_mae']/100:.2f} RUB)")
    print(f"  MAE (test):       {metrics['test_mae']:.2f} kopecks ({metrics['test_mae']/100:.2f} RUB)")
    print(f"  RMSE (train):     {metrics['train_rmse']:.2f} kopecks ({metrics['train_rmse']/100:.2f} RUB)")
    print(f"  RMSE (test):      {metrics['test_rmse']:.2f} kopecks ({metrics['test_rmse']/100:.2f} RUB)")

    # Save model
    model_path = MODELS_DIR / f"product_{product_id}_predictor.pkl"
    metrics_path = MODELS_DIR / f"product_{product_id}_metrics.json"

    joblib.dump(model, model_path)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\nModel saved to: {model_path}")
    print(f"Metrics saved to: {metrics_path}")

    return model, metrics


def predict_price(product_id: int):
    """
    Predict future price for a product using trained model.

    Args:
        product_id: Product ID to predict for

    Returns:
        Dictionary with prediction results
    """
    model_path = MODELS_DIR / f"product_{product_id}_predictor.pkl"
    metrics_path = MODELS_DIR / f"product_{product_id}_metrics.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"No trained model found for product {product_id}. "
            f"Train first with: python ml_predictor.py train --product-id {product_id}"
        )

    # Load model and metrics
    model = joblib.load(model_path)
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Fetch recent data
    df = fetch_training_data(product_id, days=60)
    df = engineer_features(df)

    if df.empty:
        raise ValueError("Insufficient recent data for prediction")

    # Use most recent data point for prediction
    latest = df.iloc[-1]

    feature_cols = ['price_7d_avg', 'price_30d_avg', 'price_trend',
                    'usd_rate', 'eur_rate', 'day_of_week', 'days_since_start']

    X_pred = latest[feature_cols].values.reshape(1, -1)

    # Make prediction
    predicted_price = model.predict(X_pred)[0]

    # Calculate prediction interval (rough approximation using test RMSE)
    rmse = metrics.get('test_rmse', 0)
    lower_bound = predicted_price - 2 * rmse  # ~95% confidence
    upper_bound = predicted_price + 2 * rmse

    result = {
        'product_id': product_id,
        'current_price': int(latest['price']),
        'predicted_price': int(predicted_price),
        'prediction_horizon_days': 7,
        'lower_bound': int(max(0, lower_bound)),
        'upper_bound': int(upper_bound),
        'confidence': 'medium' if metrics['test_r2'] > 0.5 else 'low',
        'model_accuracy': {
            'r2_score': metrics['test_r2'],
            'mae_kopecks': metrics['test_mae'],
            'mae_rub': round(metrics['test_mae'] / 100, 2),
        },
        'predicted_at': datetime.now().isoformat(),
        'model_trained_at': metrics['trained_at'],
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="ML Price Predictor for Price Scout")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Train command
    train_parser = subparsers.add_parser('train', help='Train model for a product')
    train_parser.add_argument('--product-id', type=int, required=True, help='Product ID')
    train_parser.add_argument('--model', choices=['random_forest', 'linear'],
                             default='random_forest', help='Model type')
    train_parser.add_argument('--days', type=int, default=90,
                             help='Days of historical data to use')

    # Predict command
    predict_parser = subparsers.add_parser('predict', help='Predict price for a product')
    predict_parser.add_argument('--product-id', type=int, required=True, help='Product ID')
    predict_parser.add_argument('--output', choices=['json', 'text'], default='text',
                               help='Output format')

    args = parser.parse_args()

    if args.command == 'train':
        try:
            model, metrics = train_model(args.product_id, args.model, args.days)
            print("\nTraining completed successfully!")
        except Exception as e:
            print(f"Error during training: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == 'predict':
        try:
            result = predict_price(args.product_id)

            if args.output == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(f"\nPrice Prediction for Product {result['product_id']}:")
                print(f"  Current Price:    {result['current_price']:,} kopecks ({result['current_price']/100:,.2f} RUB)")
                print(f"  Predicted Price:  {result['predicted_price']:,} kopecks ({result['predicted_price']/100:,.2f} RUB)")
                print(f"  Prediction Range: {result['lower_bound']:,} - {result['upper_bound']:,} kopecks")
                print(f"  Horizon:          {result['prediction_horizon_days']} days")
                print(f"  Confidence:       {result['confidence']}")
                print(f"  Model Accuracy:   R²={result['model_accuracy']['r2_score']:.3f}, MAE={result['model_accuracy']['mae_rub']} RUB")
        except Exception as e:
            print(f"Error during prediction: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
