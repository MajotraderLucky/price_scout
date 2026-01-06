# Price Scout Telegram Bot

Interactive Telegram bot for price tracking and analytics.

## Features

- **Product Search**: Find products by name or description
- **Price Comparison**: View current prices across all stores
- **Price Trends**: Analyze historical price changes (7-30 days)
- **ML Predictions**: Get AI-powered 7-day price forecasts
- **Arbitrage Detection**: Find profitable price differences across stores
- **Store Comparison**: Compare stores by average price and reliability

## Bot Commands

| Command                        | Description                      | Example                  |
|--------------------------------|----------------------------------|--------------------------|
| `/start`                       | Welcome message and introduction | `/start`                 |
| `/help`                        | Show all available commands      | `/help`                  |
| `/search <query>`              | Search for products              | `/search MacBook Pro 16` |
| `/price <product_id>`          | Get current prices               | `/price 1`               |
| `/trends <product_id> [days]`  | Show price trends                | `/trends 1 7`            |
| `/predict <product_id>`        | Get ML price prediction          | `/predict 1`             |
| `/arbitrage [min_profit]`      | Find arbitrage opportunities     | `/arbitrage 10`          |
| `/compare <product_id> [days]` | Compare stores                   | `/compare 1 30`          |

## Setup

### Prerequisites

1. **Telegram Bot Token**: Obtain from [@BotFather](https://t.me/BotFather)
2. **Price Scout API**: Running on localhost:3000 or Archbook (192.168.0.10:3000)
3. **PostgreSQL Database**: With product and price data

### Environment Variables

Create `.env` file or set environment variables:

```bash
# Required
TELOXIDE_TOKEN=<your_bot_token>

# Optional (defaults to localhost)
PRICE_SCOUT_API_URL=http://192.168.0.10:3000

# Optional (defaults to info)
RUST_LOG=info,price_scout=debug
```

### Running the Bot

**Development Mode:**
```bash
# Local development
export TELOXIDE_TOKEN=8165489394:AAEh2lZnd0V8c9lGp7xoY6CW8PHnB2pIZfM
export PRICE_SCOUT_API_URL=http://localhost:3000
cargo run --bin price-scout-bot
```

**Production Mode:**
```bash
# Build release binary
cargo build --release --bin price-scout-bot

# Run on Archbook
export TELOXIDE_TOKEN=8165489394:AAEh2lZnd0V8c9lGp7xoY6CW8PHnB2pIZfM
export PRICE_SCOUT_API_URL=http://localhost:3000
./target/release/price-scout-bot
```

**Systemd Service:**
```bash
# Copy service file
sudo cp config/price-scout-bot.service /etc/systemd/system/

# Enable and start
sudo systemctl enable --now price-scout-bot.service

# Check status
sudo systemctl status price-scout-bot.service

# View logs
sudo journalctl -u price-scout-bot.service -f
```

## Usage Examples

### 1. Search for Products

```
/search MacBook Pro 16

Results:
1. MacBook Pro 16" M3 Max (ID: 1)
2. MacBook Pro 16" M2 Pro (ID: 2)
3. MacBook Pro 16" M1 Pro (ID: 3)

Use /price <id> to see prices
```

### 2. View Current Prices

```
/price 1

[P] MacBook Pro 16" M3 Max

[+] dns-shop: 627990 ₽
[+] ozon: 650000 ₽
[X] citilink: N/A

[+] Best price: 627990 ₽ at dns-shop

Use /trends 1 to see price history
```

### 3. Analyze Price Trends

```
/trends 1 7

[T] Price Trends (7 days)
Product: MacBook Pro 16" M3 Max

2026-01-05: 627990 ₽ (range: 625000-650000)
[v] -2.3% vs yesterday

2026-01-04: 642000 ₽ (range: 640000-660000)
2026-01-03: 638500 ₽ (range: 635000-655000)
...
```

### 4. Get ML Price Prediction

```
/predict 1

[P] Price Prediction (Product ID: 1)

Current Price: 627990 ₽
Predicted (7 days): 615000 ₽

[v] Change: -12990 ₽ (-2.1%)
[++] Confidence: medium

Price Range:
  Low: 590000 ₽
  High: 640000 ₽

Model Accuracy:
  R² Score: 0.716
  MAE: 14567 ₽

Prediction made: 2026-01-05T18:45:00+03:00
Model trained: 2026-01-05T18:30:00+03:00
```

### 5. Find Arbitrage Opportunities

```
/arbitrage 10

[A] Arbitrage Opportunities

Found 3 opportunities with 10%+ profit:

1. MacBook Pro 16" M3 Max
[<] Buy at dns-shop: 627990 ₽
[>] Sell at ozon: 750240 ₽
[$$] Profit: 122250 ₽ (19.5%)

2. iPhone 15 Pro Max
[<] Buy at regard: 140000 ₽
[>] Sell at citilink: 165000 ₽
[$$] Profit: 25000 ₽ (17.9%)

...

[i] Showing top 5 of 3 opportunities
```

### 6. Compare Stores

```
/compare 1 30

[C] Store Comparison (30 days)
Product: MacBook Pro 16" M3 Max

1. dns-shop
   [$] Avg: 625000 ₽ | [#] Updates: 45 | [+] Available: 100%

2. ozon
   [$] Avg: 648000 ₽ | [#] Updates: 42 | [+] Available: 95%

3. citilink
   [$] Avg: 655000 ₽ | [#] Updates: 12 | [+] Available: 40%

[i] Lower average = better price
[i] Higher availability = more reliable
```

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│         Telegram Bot (teloxide)         │
│                                         │
│  Commands:                              │
│  - /start, /help                        │
│  - /search, /price                      │
│  - /trends, /predict                    │
│  - /arbitrage, /compare                 │
└─────────────────┬───────────────────────┘
                  │ HTTP/JSON
                  ▼
┌─────────────────────────────────────────┐
│      ApiClient (reqwest)                │
│                                         │
│  Methods:                               │
│  - search_products()                    │
│  - get_product_prices()                 │
│  - get_price_trends()                   │
│  - get_price_prediction()               │
│  - get_arbitrage_opportunities()        │
│  - get_store_comparison()               │
└─────────────────┬───────────────────────┘
                  │ HTTP/JSON
                  ▼
┌─────────────────────────────────────────┐
│    Price Scout REST API (Axum)          │
│                                         │
│  13 Endpoints:                          │
│  - Core: 7 endpoints                    │
│  - Analytics: 6 endpoints               │
└─────────────────┬───────────────────────┘
                  │ SQL
                  ▼
┌─────────────────────────────────────────┐
│       PostgreSQL 17.5 Database          │
│                                         │
│  Tables:                                │
│  - products, stores                     │
│  - store_prices, price_history          │
│  - scraper_jobs, currency_rates         │
└─────────────────────────────────────────┘
```

### Message Flow

1. **User sends command** → `/search MacBook`
2. **Bot parses command** → Extract query parameter
3. **ApiClient makes HTTP request** → `POST /api/search`
4. **API queries database** → PostgreSQL
5. **API returns JSON** → Search results
6. **Bot formats response** → HTML with Telegram markup
7. **User receives message** → Pretty formatted results

### Error Handling

- **API Unavailable**: Shows friendly error with suggestion to retry
- **No Results**: Suggests alternative search terms
- **Invalid Product ID**: Prompts user to search first
- **ML Model Not Trained**: Explains need for historical data
- **Network Timeout**: Suggests checking connection

## Configuration

### Bot Token

**Obtain from BotFather:**
1. Message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts to create bot
4. Save token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Bot Info:**
- Name: `price_scout_majobot`
- Token: `8165489394:AAEh2lZnd0V8c9lGp7xoY6CW8PHnB2pIZfM`

### API URL Configuration

The bot connects to the Price Scout API. Configure via environment variable:

```bash
# Local development
export PRICE_SCOUT_API_URL=http://localhost:3000

# Archbook deployment
export PRICE_SCOUT_API_URL=http://192.168.0.10:3000

# Remote deployment with port forwarding
export PRICE_SCOUT_API_URL=http://127.0.0.1:3000
```

### Logging

Configure logging level via `RUST_LOG`:

```bash
# Default: info level
export RUST_LOG=info

# Debug mode (verbose)
export RUST_LOG=debug,price_scout=trace

# Quiet mode (errors only)
export RUST_LOG=error
```

## Deployment

### Systemd Service

**Service File:** `config/price-scout-bot.service`

```ini
[Unit]
Description=Price Scout Telegram Bot
After=network.target price-scout-api.service

[Service]
Type=simple
User=sergey
WorkingDirectory=/home/sergey/price_scout
Environment="TELOXIDE_TOKEN=8165489394:AAEh2lZnd0V8c9lGp7xoY6CW8PHnB2pIZfM"
Environment="PRICE_SCOUT_API_URL=http://localhost:3000"
Environment="RUST_LOG=info,price_scout=debug"
ExecStart=/home/sergey/price_scout/target/release/price-scout-bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Deployment Steps:**

```bash
# 1. Build release binary
cargo build --release --bin price-scout-bot

# 2. Copy to Archbook
rsync -avz -e "ssh -p 2222" target/release/price-scout-bot \
  sergey@192.168.0.10:/home/sergey/price_scout/target/release/

# 3. Copy service file
rsync -avz -e "ssh -p 2222" config/price-scout-bot.service \
  sergey@192.168.0.10:/home/sergey/price_scout/config/

# 4. Install service
ssh -p 2222 sergey@192.168.0.10 \
  "sudo cp /home/sergey/price_scout/config/price-scout-bot.service /etc/systemd/system/ && \
   sudo systemctl daemon-reload && \
   sudo systemctl enable --now price-scout-bot.service"

# 5. Check status
ssh -p 2222 sergey@192.168.0.10 \
  "sudo systemctl status price-scout-bot.service"
```

## Troubleshooting

### Bot doesn't respond

**Check 1: Service running?**
```bash
sudo systemctl status price-scout-bot.service
```

**Check 2: API accessible?**
```bash
curl http://localhost:3000/health
```

**Check 3: Logs show errors?**
```bash
sudo journalctl -u price-scout-bot.service -f
```

### API connection errors

**Symptom:** `Failed to connect to API`

**Solution:**
1. Verify API is running: `curl http://localhost:3000/health`
2. Check firewall rules: `sudo ufw status`
3. Verify PRICE_SCOUT_API_URL is correct

### ML predictions fail

**Symptom:** `ML predictor failed: No trained model found`

**Solution:**
1. Train model first:
   ```bash
   python3 scripts/ml_predictor.py train --product-id 1
   ```
2. Verify model file exists:
   ```bash
   ls -lh models/product_1_predictor.pkl
   ```

### Search returns no results

**Symptom:** `No products found matching "..."`

**Solution:**
1. Check database has products:
   ```sql
   SELECT COUNT(*) FROM products;
   ```
2. Try broader search terms
3. Verify product names in database

## Development

### Running Tests

```bash
# Unit tests
cargo test --bin price-scout-bot

# Integration tests (requires API)
export TELOXIDE_TOKEN=test_token
export PRICE_SCOUT_API_URL=http://localhost:3000
cargo test --bin price-scout-bot -- --ignored
```

### Adding New Commands

1. **Add to Command enum** (main.rs):
```rust
#[derive(BotCommands, Clone)]
enum Command {
    // ... existing commands
    #[command(description = "New command: /new <arg>")]
    New(String),
}
```

2. **Add handler** (main.rs):
```rust
Command::New(arg) => {
    let result = api_client.new_method(&arg).await?;
    let message = format_new_result(&result);
    bot.send_message(msg.chat.id, message)
        .parse_mode(ParseMode::Html)
        .await?;
}
```

3. **Add API method** (api_client.rs):
```rust
pub async fn new_method(&self, arg: &str) -> Result<NewResponse> {
    let url = format!("{}/api/new/{}", self.base_url, arg);
    // ... implementation
}
```

4. **Add formatter** (main.rs):
```rust
fn format_new_result(result: &NewResponse) -> String {
    format!("<b>New Result</b>\n{}", result.data)
}
```

### Code Structure

```
crates/bot/
├── Cargo.toml              # Dependencies
└── src/
    ├── main.rs             # Bot logic, command handlers
    └── api_client.rs       # API client, request/response types
```

## Future Enhancements

### Planned Features

- [ ] **Price Alerts**: Notify when price drops below threshold
- [ ] **Watchlist**: Track multiple products
- [ ] **Daily Digest**: Summary of price changes
- [ ] **Product Comparison**: Side-by-side comparison
- [ ] **Historical Charts**: Graphical price trends
- [ ] **Store Ratings**: User reviews and ratings

### Tracking (Future Implementation)

```rust
// Future: Track product command
Command::Track(args) => {
    let parts: Vec<&str> = args.split_whitespace().collect();
    if parts.len() != 2 {
        bot.send_message(msg.chat.id, "Usage: /track <product_id> <target_price>").await?;
        return Ok(());
    }

    let product_id = parts[0].parse::<i64>()?;
    let target_price = parts[1].parse::<i32>()?;

    // TODO: Save to user_tracking table
    // TODO: Implement price alert worker
}
```

## Support

- **Documentation**: `/help` in bot
- **API Docs**: [ANALYTICS_API.md](ANALYTICS_API.md)
- **GitHub Issues**: Report bugs and feature requests

---

**Bot Version**: 0.1.0
**Last Updated**: 2026-01-05
**Status**: ✅ Ready for Testing
