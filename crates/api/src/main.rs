//! Price Scout API Server
//!
//! REST API server for price tracking built with Axum.
//!
//! ## Endpoints
//!
//! - `GET /api/stores` - List all stores
//! - `GET /api/products/:id` - Get product details
//! - `GET /api/products/:id/prices` - Get product prices
//! - `POST /api/search` - Search products
//! - `POST /api/products/:id/scrape` - Trigger scraping
//! - `GET /api/queue/stats` - Get queue statistics
//! - `GET /health` - Health check
//!
//! ## Usage
//!
//! ```bash
//! export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
//! cargo run --bin price-scout-api
//! ```

use anyhow::Context;
use axum::{
    extract::{Path, State},
    http::{header, Method, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use price_scout_db::Database;
use price_scout_models::{Product, Store, StorePrice};
use price_scout_scraper::{JobStats, ScraperQueue};
use serde::{Deserialize, Serialize};
use tower::ServiceBuilder;
use tower_http::cors::{Any, CorsLayer};
use tracing::{error, info};

/// Application state shared across handlers
#[derive(Clone)]
struct AppState {
    db: Database,
    queue: ScraperQueue,
}

/// API error response
#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

/// Search request
#[derive(Debug, Deserialize)]
struct SearchRequest {
    query: String,
}

/// Search response
#[derive(Debug, Serialize)]
struct SearchResponse {
    products: Vec<Product>,
}

/// Scrape request
#[derive(Debug, Deserialize)]
struct ScrapeRequest {
    stores: Option<Vec<String>>,
    priority: Option<i32>,
}

/// Scrape response
#[derive(Debug, Serialize)]
struct ScrapeResponse {
    job_ids: Vec<i64>,
    message: String,
}

/// Product prices response
#[derive(Debug, Serialize)]
struct ProductPricesResponse {
    product: Product,
    prices: Vec<PriceWithStore>,
}

/// Price with store information
#[derive(Debug, Serialize)]
struct PriceWithStore {
    store: Store,
    price: StorePrice,
}

/// Custom error type for API handlers
struct ApiError(anyhow::Error);

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        error!("API error: {:#}", self.0);
        let error_message = format!("{:#}", self.0);
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: error_message,
            }),
        )
            .into_response()
    }
}

impl<E> From<E> for ApiError
where
    E: Into<anyhow::Error>,
{
    fn from(err: E) -> Self {
        Self(err.into())
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    dotenv::dotenv().ok();
    tracing_subscriber::fmt::init();

    let database_url = std::env::var("DATABASE_URL")
        .context("DATABASE_URL must be set")?;

    info!("🚀 Price Scout API Server");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    info!("📡 Connecting to database...");
    let db = Database::connect(&database_url).await?;
    info!("✅ Database connected");

    let queue = ScraperQueue::new(db.clone());
    info!("✅ Scraper queue initialized");

    let state = AppState { db, queue };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST])
        .allow_headers([header::CONTENT_TYPE]);

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/api/stores", get(get_stores))
        .route("/api/products/:id", get(get_product))
        .route("/api/products/:id/prices", get(get_product_prices))
        .route("/api/search", post(search_products))
        .route("/api/products/:id/scrape", post(scrape_product))
        .route("/api/queue/stats", get(get_queue_stats))
        .layer(ServiceBuilder::new().layer(cors))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .context("Failed to bind to port 3000")?;

    info!("🌐 Server listening on http://0.0.0.0:3000");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("📋 Available endpoints:");
    info!("   GET  /health");
    info!("   GET  /api/stores");
    info!("   GET  /api/products/:id");
    info!("   GET  /api/products/:id/prices");
    info!("   POST /api/search");
    info!("   POST /api/products/:id/scrape");
    info!("   GET  /api/queue/stats");

    axum::serve(listener, app)
        .await
        .context("Server error")?;

    Ok(())
}

async fn health_check() -> &'static str {
    "OK"
}

async fn get_stores(State(state): State<AppState>) -> Result<Json<Vec<Store>>, ApiError> {
    let stores = state.db.get_stable_stores().await?;
    Ok(Json(stores))
}

async fn get_product(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Product>, ApiError> {
    let product = state
        .db
        .get_product(id)
        .await?
        .ok_or_else(|| anyhow::anyhow!("Product not found"))?;
    Ok(Json(product))
}

async fn get_product_prices(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<ProductPricesResponse>, ApiError> {
    let product = state
        .db
        .get_product(id)
        .await?
        .ok_or_else(|| anyhow::anyhow!("Product not found"))?;

    let store_prices = state.db.get_best_prices(id, 10).await?;

    let mut prices = Vec::new();
    for price in store_prices {
        let store = state.db.get_store(price.store_id).await?;
        prices.push(PriceWithStore { store, price });
    }

    Ok(Json(ProductPricesResponse { product, prices }))
}

async fn search_products(
    State(state): State<AppState>,
    Json(req): Json<SearchRequest>,
) -> Result<Json<SearchResponse>, ApiError> {
    let products = state.db.search_products(&req.query).await?;
    Ok(Json(SearchResponse { products }))
}

async fn scrape_product(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(req): Json<ScrapeRequest>,
) -> Result<Json<ScrapeResponse>, ApiError> {
    let product = state
        .db
        .get_product(id)
        .await?
        .ok_or_else(|| anyhow::anyhow!("Product not found"))?;

    let priority = req.priority.unwrap_or(5);

    let job_ids = if let Some(store_names) = req.stores {
        let mut ids = Vec::new();
        for store_name in store_names {
            if let Some(store) = state.db.get_store_by_name(&store_name).await? {
                let job_id = state.queue.enqueue(id, Some(store.id), Some(priority)).await?;
                ids.push(job_id);
            } else {
                return Err(anyhow::anyhow!("Store not found: {}", store_name).into());
            }
        }
        ids
    } else {
        state.queue.enqueue_all_stores(id, Some(priority)).await?
    };

    let message = if job_ids.len() == 1 {
        format!("Enqueued 1 scraping job for {}", product.name)
    } else {
        format!("Enqueued {} scraping jobs for {}", job_ids.len(), product.name)
    };

    Ok(Json(ScrapeResponse { job_ids, message }))
}

async fn get_queue_stats(State(state): State<AppState>) -> Result<Json<JobStats>, ApiError> {
    let stats = state.queue.get_stats().await?;
    Ok(Json(stats))
}
