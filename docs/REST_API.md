# Price Scout REST API Documentation

## Overview

The Price Scout API is a RESTful service built with Axum that provides endpoints for:
- Product search and management
- Price comparison across stores
- Scraping job management
- Queue monitoring

**Base URL**: `http://localhost:3000`

**Technology Stack**:
- Framework: Axum 0.7
- Runtime: Tokio (async)
- Database: PostgreSQL via sqlx
- CORS: Enabled for all origins

---

## Authentication

Currently, no authentication is required. This will be added in future versions.

---

## Endpoints

### Health Check

Check if the API server is running.

**Endpoint**: `GET /health`

**Response**:
```
OK
```

**Status Codes**:
- `200 OK` - Server is healthy

**Example**:
```bash
curl http://localhost:3000/health
```

---

### List Stores

Get a list of all stable (active) stores.

**Endpoint**: `GET /api/stores`

**Response**:
```json
[
  {
    "id": 1,
    "name": "dns",
    "base_url": "https://www.dns-shop.ru",
    "method": "firefox",
    "parser": "dns_parser",
    "unstable": false,
    "created_at": "2026-01-02T10:00:00Z"
  },
  {
    "id": 2,
    "name": "ozon",
    "base_url": "https://www.ozon.ru",
    "method": "ozon_firefox",
    "parser": "ozon_parser",
    "unstable": false,
    "created_at": "2026-01-02T10:00:00Z"
  }
]
```

**Status Codes**:
- `200 OK` - Success
- `500 Internal Server Error` - Database error

**Example**:
```bash
curl http://localhost:3000/api/stores
```

---

### Get Product

Get details of a specific product by ID.

**Endpoint**: `GET /api/products/:id`

**Path Parameters**:
- `id` (integer) - Product ID

**Response**:
```json
{
  "id": 1,
  "name": "MacBook Pro 16\" M1 Pro 32GB 512GB",
  "category": "laptops",
  "specs": {
    "screen": "16",
    "cpu": "M1 Pro",
    "ram": 32,
    "ssd": 512,
    "article": "Z14V0008D"
  },
  "search_query": "MacBook Pro 16",
  "created_at": "2026-01-02T10:00:00Z",
  "updated_at": "2026-01-04T15:30:00Z"
}
```

**Status Codes**:
- `200 OK` - Success
- `500 Internal Server Error` - Product not found or database error

**Example**:
```bash
curl http://localhost:3000/api/products/1
```

---

### Get Product Prices

Get current prices for a product across all stores.

**Endpoint**: `GET /api/products/:id/prices`

**Path Parameters**:
- `id` (integer) - Product ID

**Response**:
```json
{
  "product": {
    "id": 1,
    "name": "MacBook Pro 16\" M1 Pro 32GB 512GB",
    "category": "laptops",
    "specs": { ... },
    "search_query": "MacBook Pro 16",
    "created_at": "2026-01-02T10:00:00Z",
    "updated_at": "2026-01-04T15:30:00Z"
  },
  "prices": [
    {
      "store": {
        "id": 3,
        "name": "i-ray",
        "base_url": "https://www.i-ray.ru",
        "method": "playwright_direct",
        "parser": "iray_parser",
        "unstable": false,
        "created_at": "2026-01-02T10:00:00Z"
      },
      "price": {
        "id": 123,
        "product_id": 1,
        "store_id": 3,
        "price": 10799900,
        "url": "https://www.i-ray.ru/product/123",
        "available": true,
        "scraped_at": "2026-01-04T16:45:23Z"
      }
    }
  ]
}
```

**Notes**:
- Prices are stored in kopecks (1/100 of ruble)
- To get price in rubles: `price / 100`
- Results are sorted by price (ascending)
- Limit: 10 best prices

**Status Codes**:
- `200 OK` - Success
- `500 Internal Server Error` - Product not found or database error

**Example**:
```bash
curl http://localhost:3000/api/products/1/prices
```

---

### Search Products

Search for products by name.

**Endpoint**: `POST /api/search`

**Request Body**:
```json
{
  "query": "MacBook"
}
```

**Response**:
```json
{
  "products": [
    {
      "id": 1,
      "name": "MacBook Pro 16\" M1 Pro 32GB 512GB",
      "category": "laptops",
      "specs": { ... },
      "search_query": "MacBook Pro 16",
      "created_at": "2026-01-02T10:00:00Z",
      "updated_at": "2026-01-04T15:30:00Z"
    },
    {
      "id": 2,
      "name": "MacBook Air 13\" M2 16GB 512GB",
      "category": "laptops",
      "specs": { ... },
      "search_query": "MacBook Air 13",
      "created_at": "2026-01-03T11:20:00Z",
      "updated_at": "2026-01-04T14:10:00Z"
    }
  ]
}
```

**Notes**:
- Case-insensitive search
- Uses ILIKE for partial matching
- Results sorted by `updated_at` (descending)
- Limit: 50 products

**Status Codes**:
- `200 OK` - Success (empty array if no matches)
- `500 Internal Server Error` - Database error

**Example**:
```bash
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "MacBook"}'
```

---

### Trigger Scraping

Enqueue scraping jobs for a product.

**Endpoint**: `POST /api/products/:id/scrape`

**Path Parameters**:
- `id` (integer) - Product ID

**Request Body**:
```json
{
  "stores": ["dns", "ozon"],
  "priority": 8
}
```

**Request Fields**:
- `stores` (optional, array of strings) - List of store names to scrape. If omitted, scrapes all stable stores.
- `priority` (optional, integer) - Job priority (1-10, default: 5). Higher priority jobs are processed first.

**Response**:
```json
{
  "job_ids": [45, 46],
  "message": "Enqueued 2 scraping jobs for MacBook Pro 16\" M1 Pro 32GB 512GB"
}
```

**Status Codes**:
- `200 OK` - Jobs enqueued successfully
- `500 Internal Server Error` - Product not found, store not found, or database error

**Examples**:

Scrape all stores:
```bash
curl -X POST http://localhost:3000/api/products/1/scrape \
  -H "Content-Type: application/json" \
  -d '{"priority": 5}'
```

Scrape specific stores:
```bash
curl -X POST http://localhost:3000/api/products/1/scrape \
  -H "Content-Type: application/json" \
  -d '{"stores": ["dns", "ozon"], "priority": 10}'
```

**Notes**:
- Jobs are processed by background workers
- High priority (8-10): User-initiated searches
- Normal priority (5): Scheduled refreshes
- Low priority (1-3): Background updates

---

### Get Queue Statistics

Get statistics about the scraping job queue.

**Endpoint**: `GET /api/queue/stats`

**Response**:
```json
{
  "pending": 8,
  "running": 2,
  "completed": 156,
  "failed": 3
}
```

**Response Fields**:
- `pending` (integer) - Jobs waiting to be processed
- `running` (integer) - Jobs currently being processed
- `completed` (integer) - Successfully completed jobs
- `failed` (integer) - Failed jobs

**Status Codes**:
- `200 OK` - Success
- `500 Internal Server Error` - Database error

**Example**:
```bash
curl http://localhost:3000/api/queue/stats
```

---

## Error Handling

All errors return a JSON response with the following format:

```json
{
  "error": "Product not found"
}
```

**Common Error Codes**:
- `500 Internal Server Error` - Database errors, product/store not found, or processing errors

**Future Improvements**:
- Add `404 Not Found` for missing resources
- Add `400 Bad Request` for validation errors
- Add `401 Unauthorized` for authentication errors
- Add detailed error codes

---

## CORS

CORS is enabled for all origins with the following configuration:
- **Allowed Origins**: Any (`*`)
- **Allowed Methods**: `GET`, `POST`
- **Allowed Headers**: `Content-Type`

---

## Running the API Server

### Prerequisites

1. PostgreSQL database running with schema initialized
2. Environment variable `DATABASE_URL` set

### Start Server

```bash
export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
cargo run --bin price-scout-api
```

### Server Output

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
```

---

## Testing the API

### Using curl

See examples above for each endpoint.

### Using the Test Client

A comprehensive test client is provided:

```bash
cargo run --example test_api
```

This will test all endpoints and display results.

---

## Integration with Other Components

### With Scraper Worker (PS-29)

The API enqueues scraping jobs which are processed by background workers:

```
[API] POST /api/products/1/scrape
  ↓
[ScraperQueue] enqueue_job()
  ↓
[PostgreSQL] INSERT INTO scraping_jobs
  ↓
[ScraperWorker] poll for pending jobs
  ↓
[Python Bridge] run scrapers
  ↓
[Database] save results to store_prices
```

### With Telegram Bot (PS-30, Future)

The bot will use the API for all operations:

```rust
// Bot command: /track MacBook Pro 16
async fn handle_track(bot: Bot, msg: Message) {
    // 1. Search product
    let products = api_client.search("MacBook Pro 16").await?;

    // 2. Trigger scraping
    let response = api_client.scrape(product_id, None, Some(10)).await?;

    // 3. Subscribe user to price alerts
    db.create_tracking(user_id, product_id, target_price).await?;
}
```

---

## Deployment

### Systemd Service

**Service file**: `/etc/systemd/system/price-scout-api.service`

```ini
[Unit]
Description=Price Scout API Server
After=network.target postgresql.service

[Service]
Type=simple
User=sergey
WorkingDirectory=/home/sergey/price_scout
Environment="DATABASE_URL=postgresql://postgres@localhost/price_scout"
Environment="RUST_LOG=info,price_scout=debug"
ExecStart=/home/sergey/price_scout/target/release/price-scout-api
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Commands**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable price-scout-api
sudo systemctl start price-scout-api
sudo systemctl status price-scout-api
```

---

## Future Enhancements

### Phase 3
- Add pagination for search results
- Add filtering (by category, price range)
- Add sorting options
- WebSocket support for real-time price updates
- Batch operations (scrape multiple products)

### Phase 4
- JWT authentication
- User management endpoints
- Tracking subscriptions endpoints
- Price history endpoints
- Export endpoints (CSV, JSON)

---

**Last Updated**: 2026-01-05
**API Version**: 0.1.0
**Status**: Production Ready (Phase 1)
