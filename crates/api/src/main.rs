//! Price Scout API Server
//!
//! REST API server for price tracking built with Axum.
//!
//! ## Endpoints
//!
//! ### Core Endpoints
//! - `GET /api/stores` - List all stores
//! - `GET /api/products/:id` - Get product details
//! - `GET /api/products/:id/prices` - Get product prices
//! - `POST /api/search` - Search products
//! - `POST /api/products/:id/scrape` - Trigger scraping
//! - `GET /api/queue/stats` - Get queue statistics
//! - `GET /health` - Health check
//!
//! ### Analytics Endpoints
//! - `GET /api/analytics/price-trends/:id?days=7` - Get price trends for product
//! - `GET /api/analytics/currency-correlation/:id?currency=USD&days=30` - Get price-currency correlation
//! - `GET /api/analytics/store-comparison/:id?days=30` - Compare stores for product
//! - `GET /api/analytics/market-overview?min_price=5000&max_price=15000&days=30` - Market overview
//! - `GET /api/arbitrage?min_profit=10` - Find arbitrage opportunities (price differences across stores)
//! - `GET /api/analytics/predictions/:id` - Get ML-based price prediction for product (7-day forecast)
//!
//! ### Market Research Endpoints
//! - `GET /api/market-research/top-100?limit=100` - Get top 100 popular products by score
//! - `GET /api/market-research/popular-queries?limit=50` - Get popular search queries
//! - `GET /api/market-research/categories` - Get list of product categories
//! - `POST /api/market-research/refresh` - Refresh popularity metrics (materialized view)
//!
//! ### Bot Statistics Endpoints
//! - `GET /api/stats/summary?days=7` - Get comprehensive bot statistics
//! - `GET /api/stats/health?days=7` - Get system health metrics
//! - `GET /api/stats/users?days=7` - Get user statistics
//! - `GET /api/stats/market?days=7` - Get market analytics
//! - `GET /api/stats/stores` - Get store rankings
//! - `GET /api/stats/commands?days=7` - Get command usage statistics
//!
//! ## Usage
//!
//! ```bash
//! export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
//! cargo run --bin price-scout-api
//! ```

use anyhow::Context;
use axum::{
    extract::{Path, Query, State},
    http::{header, Method, StatusCode},
    response::{IntoResponse, Response},
    routing::{delete, get, post, put},
    Json, Router,
};
use price_scout_db::Database;
use price_scout_models::{
    CommandUsage, MarketStats as ModelMarketStats, NewStore, Product, Store,
    StoreHealthStats, StorePrice, StoreRanking, SystemStats, UpdateStore, UserStats,
};
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

/// Query parameters for price trends endpoint
#[derive(Debug, Deserialize)]
struct PriceTrendsQuery {
    #[serde(default = "default_days")]
    days: i32,
}

/// Query parameters for currency correlation endpoint
#[derive(Debug, Deserialize)]
struct CurrencyCorrelationQuery {
    #[serde(default = "default_currency")]
    currency: String,
    #[serde(default = "default_correlation_days")]
    days: i32,
}

/// Query parameters for store comparison endpoint
#[derive(Debug, Deserialize)]
struct StoreComparisonQuery {
    #[serde(default = "default_days")]
    days: i32,
}

/// Query parameters for market overview endpoint
#[derive(Debug, Deserialize)]
struct MarketOverviewQuery {
    min_price: i32,  // In RUB
    max_price: i32,  // In RUB
    #[serde(default = "default_days")]
    days: i32,
}

/// Price trend data point
#[derive(Debug, Serialize)]
struct PriceTrendPoint {
    date: String,
    avg_price: f64,
    min_price: i32,
    max_price: i32,
    volatility: Option<f64>,
}

/// Price trends response
#[derive(Debug, Serialize)]
struct PriceTrendsResponse {
    product_id: i64,
    trends: Vec<PriceTrendPoint>,
}

/// Currency correlation response
#[derive(Debug, Serialize)]
struct CurrencyCorrelationResponse {
    product_id: i64,
    currency: String,
    correlation: Option<f64>,
    days: i32,
}

/// Store comparison entry
#[derive(Debug, Serialize)]
struct StoreComparisonEntry {
    store_name: String,
    avg_price: f64,
    update_count: i64,
    availability_rate: f64,
}

/// Store comparison response
#[derive(Debug, Serialize)]
struct StoreComparisonResponse {
    product_id: i64,
    stores: Vec<StoreComparisonEntry>,
}

/// Market overview response
#[derive(Debug, Serialize)]
struct MarketOverviewResponse {
    total_products: i64,
    avg_price: f64,
    min_price: i32,
    max_price: i32,
    total_price_points: i64,
}

/// Query parameters for arbitrage endpoint
#[derive(Debug, Deserialize)]
struct ArbitrageQuery {
    #[serde(default = "default_min_profit")]
    min_profit: f64,
}

/// Arbitrage opportunity entry
#[derive(Debug, Serialize)]
struct ArbitrageOpportunity {
    product_id: i64,
    product_name: String,
    category: String,
    buy_store: String,
    buy_price: i32,
    sell_store: String,
    sell_price: i32,
    profit_kopecks: i32,
    profit_percent: f64,
}

/// Arbitrage opportunities response
#[derive(Debug, Serialize)]
struct ArbitrageResponse {
    opportunities: Vec<ArbitrageOpportunity>,
    count: usize,
}

/// ML model accuracy metrics
#[derive(Debug, Serialize, Deserialize)]
struct ModelAccuracy {
    r2_score: f64,
    mae_kopecks: f64,
    mae_rub: f64,
}

// ============================================================================
// MARKET RESEARCH TYPES
// ============================================================================

/// Query parameters for top products endpoint
#[derive(Debug, Deserialize)]
struct TopProductsQuery {
    #[serde(default = "default_top_limit")]
    limit: i32,
}

/// Query parameters for popular queries endpoint
#[derive(Debug, Deserialize)]
struct PopularQueriesQuery {
    #[serde(default = "default_queries_limit")]
    limit: i32,
}

/// Top product entry with rank
#[derive(Debug, Serialize)]
struct TopProductEntry {
    rank: i32,
    product_id: i64,
    name: String,
    category: Option<String>,
    popularity_score: i32,
    tracking_score: i32,
    volatility_score: i32,
    availability_score: i32,
    arbitrage_score: i32,
    tracking_count: i64,
    min_price_rub: Option<i32>,
    max_price_rub: Option<i32>,
    store_count: i64,
}

/// Top products response
#[derive(Debug, Serialize)]
struct TopProductsResponse {
    products: Vec<TopProductEntry>,
    count: usize,
}

/// Popular queries response
#[derive(Debug, Serialize)]
struct PopularQueriesResponse {
    queries: Vec<PopularQueryEntry>,
    count: usize,
}

/// Popular query entry
#[derive(Debug, Serialize)]
struct PopularQueryEntry {
    query: String,
    source: String,
    category: Option<String>,
    search_count: i32,
}

/// Categories response
#[derive(Debug, Serialize)]
struct CategoriesResponse {
    categories: Vec<String>,
    count: usize,
}

/// Refresh metrics response
#[derive(Debug, Serialize)]
struct RefreshMetricsResponse {
    status: String,
    message: String,
}

// ============================================================================
// BOT STATISTICS TYPES
// ============================================================================

/// Query parameters for stats endpoints
#[derive(Debug, Deserialize)]
struct StatsQuery {
    #[serde(default = "default_stats_days")]
    days: i32,
}

fn default_stats_days() -> i32 {
    7
}

/// Stats summary response
#[derive(Debug, Serialize)]
struct StatsSummaryResponse {
    period_days: i32,
    generated_at: String,
    system: SystemStats,
    users: UserStats,
    market: ModelMarketStats,
    stores: Vec<StoreRanking>,
    top_commands: Vec<CommandUsage>,
}

/// Store ranking response
#[derive(Debug, Serialize)]
struct StatsStoresResponse {
    stores: Vec<StoreRanking>,
    count: usize,
}

/// Command usage response
#[derive(Debug, Serialize)]
struct StatsCommandsResponse {
    commands: Vec<CommandUsage>,
    count: usize,
}

/// Price prediction response
#[derive(Debug, Serialize, Deserialize)]
struct PricePredictionResponse {
    product_id: i64,
    current_price: i32,
    predicted_price: i32,
    prediction_horizon_days: i32,
    lower_bound: i32,
    upper_bound: i32,
    confidence: String,
    model_accuracy: ModelAccuracy,
    predicted_at: String,
    model_trained_at: String,
}

// Default values for query parameters
fn default_days() -> i32 {
    7
}

fn default_min_profit() -> f64 {
    10.0
}

fn default_correlation_days() -> i32 {
    30
}

fn default_currency() -> String {
    "USD".to_string()
}

fn default_top_limit() -> i32 {
    100
}

fn default_queries_limit() -> i32 {
    50
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
        .allow_methods([Method::GET, Method::POST, Method::PUT, Method::DELETE])
        .allow_headers([header::CONTENT_TYPE]);

    let app = Router::new()
        .route("/health", get(health_check))
        // Store management endpoints
        .route("/api/stores", get(get_stores).post(create_store))
        .route("/api/stores/:id", get(get_store_by_id).put(update_store).delete(delete_store))
        .route("/api/stores/health", get(get_stores_health))
        .route("/api/products/:id", get(get_product))
        .route("/api/products/:id/prices", get(get_product_prices))
        .route("/api/search", post(search_products))
        .route("/api/products/:id/scrape", post(scrape_product))
        .route("/api/queue/stats", get(get_queue_stats))
        .route("/api/analytics/price-trends/:id", get(get_price_trends))
        .route("/api/analytics/currency-correlation/:id", get(get_currency_correlation))
        .route("/api/analytics/store-comparison/:id", get(get_store_comparison))
        .route("/api/analytics/market-overview", get(get_market_overview))
        .route("/api/arbitrage", get(get_arbitrage_opportunities))
        .route("/api/analytics/predictions/:id", get(get_price_prediction))
        // Market Research endpoints
        .route("/api/market-research/top-100", get(get_top_products))
        .route("/api/market-research/popular-queries", get(get_popular_queries))
        .route("/api/market-research/categories", get(get_categories))
        .route("/api/market-research/refresh", post(refresh_popularity_metrics))
        // Bot Statistics endpoints
        .route("/api/stats/summary", get(get_stats_summary))
        .route("/api/stats/health", get(get_stats_health))
        .route("/api/stats/users", get(get_stats_users))
        .route("/api/stats/market", get(get_stats_market))
        .route("/api/stats/stores", get(get_stats_stores))
        .route("/api/stats/commands", get(get_stats_commands))
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
    info!("   POST /api/stores");
    info!("   GET  /api/stores/:id");
    info!("   PUT  /api/stores/:id");
    info!("   DEL  /api/stores/:id");
    info!("   GET  /api/stores/health");
    info!("   GET  /api/products/:id");
    info!("   GET  /api/products/:id/prices");
    info!("   POST /api/search");
    info!("   POST /api/products/:id/scrape");
    info!("   GET  /api/queue/stats");
    info!("   GET  /api/analytics/price-trends/:id");
    info!("   GET  /api/analytics/currency-correlation/:id");
    info!("   GET  /api/analytics/store-comparison/:id");
    info!("   GET  /api/analytics/market-overview");
    info!("   GET  /api/arbitrage");
    info!("   GET  /api/analytics/predictions/:id");
    info!("   GET  /api/market-research/top-100");
    info!("   GET  /api/market-research/popular-queries");
    info!("   GET  /api/market-research/categories");
    info!("   POST /api/market-research/refresh");
    info!("   GET  /api/stats/summary");
    info!("   GET  /api/stats/health");
    info!("   GET  /api/stats/users");
    info!("   GET  /api/stats/market");
    info!("   GET  /api/stats/stores");
    info!("   GET  /api/stats/commands");

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

/// Get store by ID
async fn get_store_by_id(
    State(state): State<AppState>,
    Path(id): Path<i32>,
) -> Result<Json<Store>, ApiError> {
    let store = state.db.get_store(id).await?;
    Ok(Json(store))
}

/// Create new store
async fn create_store(
    State(state): State<AppState>,
    Json(new_store): Json<NewStore>,
) -> Result<Json<StoreCreatedResponse>, ApiError> {
    let id = state.db.create_store(&new_store).await?;
    Ok(Json(StoreCreatedResponse { id, name: new_store.name }))
}

#[derive(Serialize)]
struct StoreCreatedResponse {
    id: i32,
    name: String,
}

/// Update store
async fn update_store(
    State(state): State<AppState>,
    Path(id): Path<i32>,
    Json(update): Json<UpdateStore>,
) -> Result<Json<SuccessResponse>, ApiError> {
    state.db.update_store(id, &update).await?;
    Ok(Json(SuccessResponse { success: true, message: "Store updated".to_string() }))
}

#[derive(Serialize)]
struct SuccessResponse {
    success: bool,
    message: String,
}

/// Delete (disable) store
async fn delete_store(
    State(state): State<AppState>,
    Path(id): Path<i32>,
) -> Result<Json<SuccessResponse>, ApiError> {
    state.db.disable_store(id).await?;
    Ok(Json(SuccessResponse { success: true, message: "Store disabled".to_string() }))
}

/// Get store health statistics
async fn get_stores_health(
    State(state): State<AppState>,
) -> Result<Json<StoreHealthStats>, ApiError> {
    let stats = state.db.get_store_health_stats().await?;
    Ok(Json(stats))
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

async fn get_price_trends(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Query(query): Query<PriceTrendsQuery>,
) -> Result<Json<PriceTrendsResponse>, ApiError> {
    let trends = state.db.get_price_trends(id, query.days).await?;

    let trend_points: Vec<PriceTrendPoint> = trends
        .into_iter()
        .map(|(date, avg_price, min_price, max_price, volatility)| PriceTrendPoint {
            date: date.to_string(),
            avg_price,
            min_price,
            max_price,
            volatility,
        })
        .collect();

    Ok(Json(PriceTrendsResponse {
        product_id: id,
        trends: trend_points,
    }))
}

async fn get_currency_correlation(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Query(query): Query<CurrencyCorrelationQuery>,
) -> Result<Json<CurrencyCorrelationResponse>, ApiError> {
    let correlation = state
        .db
        .calculate_price_currency_correlation(id, &query.currency, query.days)
        .await?;

    Ok(Json(CurrencyCorrelationResponse {
        product_id: id,
        currency: query.currency,
        correlation,
        days: query.days,
    }))
}

async fn get_store_comparison(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Query(query): Query<StoreComparisonQuery>,
) -> Result<Json<StoreComparisonResponse>, ApiError> {
    let comparison = state.db.get_store_comparison(id, query.days).await?;

    let stores: Vec<StoreComparisonEntry> = comparison
        .into_iter()
        .map(|(store_name, avg_price, update_count, availability_rate)| {
            StoreComparisonEntry {
                store_name,
                avg_price,
                update_count,
                availability_rate,
            }
        })
        .collect();

    Ok(Json(StoreComparisonResponse {
        product_id: id,
        stores,
    }))
}

async fn get_market_overview(
    State(state): State<AppState>,
    Query(query): Query<MarketOverviewQuery>,
) -> Result<Json<MarketOverviewResponse>, ApiError> {
    // Convert RUB to kopecks (multiply by 100)
    let min_price_kopecks = query.min_price * 100;
    let max_price_kopecks = query.max_price * 100;

    let (total_products, avg_price, min_price, max_price, total_price_points) = state
        .db
        .get_market_overview(min_price_kopecks, max_price_kopecks, query.days)
        .await?;

    Ok(Json(MarketOverviewResponse {
        total_products,
        avg_price,
        min_price,
        max_price,
        total_price_points,
    }))
}

async fn get_arbitrage_opportunities(
    State(state): State<AppState>,
    Query(query): Query<ArbitrageQuery>,
) -> Result<Json<ArbitrageResponse>, ApiError> {
    let results = state
        .db
        .find_arbitrage_opportunities(query.min_profit)
        .await?;

    let opportunities: Vec<ArbitrageOpportunity> = results
        .into_iter()
        .map(
            |(
                product_id,
                product_name,
                category,
                _buy_store_id,
                buy_store_name,
                buy_price,
                _sell_store_id,
                sell_store_name,
                sell_price,
                profit_kopecks,
                profit_percent,
            )| {
                ArbitrageOpportunity {
                    product_id,
                    product_name,
                    category,
                    buy_store: buy_store_name,
                    buy_price,
                    sell_store: sell_store_name,
                    sell_price,
                    profit_kopecks,
                    profit_percent,
                }
            },
        )
        .collect();

    let count = opportunities.len();

    Ok(Json(ArbitrageResponse {
        opportunities,
        count,
    }))
}

async fn get_price_prediction(
    State(_state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<PricePredictionResponse>, ApiError> {
    use tokio::process::Command;

    // Call Python ML predictor script
    let output = Command::new("python3")
        .arg("scripts/ml_predictor.py")
        .arg("predict")
        .arg("--product-id")
        .arg(id.to_string())
        .arg("--output")
        .arg("json")
        .output()
        .await
        .context("Failed to execute ML predictor script")?;

    if !output.status.success() {
        let error_msg = String::from_utf8_lossy(&output.stderr);
        return Err(anyhow::anyhow!(
            "ML predictor failed: {}",
            error_msg
        )
        .into());
    }

    // Parse JSON output
    let prediction: PricePredictionResponse = serde_json::from_slice(&output.stdout)
        .context("Failed to parse ML predictor output")?;

    Ok(Json(prediction))
}

// ============================================================================
// MARKET RESEARCH HANDLERS
// ============================================================================

async fn get_top_products(
    State(state): State<AppState>,
    Query(query): Query<TopProductsQuery>,
) -> Result<Json<TopProductsResponse>, ApiError> {
    let products = state.db.get_top_products(query.limit).await?;

    let entries: Vec<TopProductEntry> = products
        .into_iter()
        .enumerate()
        .map(|(idx, p)| {
            let popularity_score = p.popularity_score();
            TopProductEntry {
                rank: (idx + 1) as i32,
                product_id: p.product_id,
                name: p.name,
                category: p.category,
                popularity_score,
                tracking_score: p.tracking_score,
                volatility_score: p.volatility_score,
                availability_score: p.availability_score,
                arbitrage_score: p.arbitrage_score,
                tracking_count: p.tracking_count,
                min_price_rub: p.min_price.map(|p| p / 100),
                max_price_rub: p.max_price.map(|p| p / 100),
                store_count: p.store_count.unwrap_or(0),
            }
        })
        .collect();

    let count = entries.len();

    Ok(Json(TopProductsResponse {
        products: entries,
        count,
    }))
}

async fn get_popular_queries(
    State(state): State<AppState>,
    Query(query): Query<PopularQueriesQuery>,
) -> Result<Json<PopularQueriesResponse>, ApiError> {
    let queries = state.db.get_popular_search_queries(query.limit).await?;

    let entries: Vec<PopularQueryEntry> = queries
        .into_iter()
        .map(|q| PopularQueryEntry {
            query: q.query,
            source: q.source,
            category: q.category,
            search_count: q.search_count,
        })
        .collect();

    let count = entries.len();

    Ok(Json(PopularQueriesResponse {
        queries: entries,
        count,
    }))
}

async fn get_categories(
    State(state): State<AppState>,
) -> Result<Json<CategoriesResponse>, ApiError> {
    let categories = state.db.get_product_categories().await?;
    let count = categories.len();

    Ok(Json(CategoriesResponse { categories, count }))
}

async fn refresh_popularity_metrics(
    State(state): State<AppState>,
) -> Result<Json<RefreshMetricsResponse>, ApiError> {
    state.db.refresh_popularity_metrics().await?;

    Ok(Json(RefreshMetricsResponse {
        status: "success".to_string(),
        message: "Popularity metrics refreshed successfully".to_string(),
    }))
}

// ============================================================================
// BOT STATISTICS HANDLERS
// ============================================================================

async fn get_stats_summary(
    State(state): State<AppState>,
    Query(query): Query<StatsQuery>,
) -> Result<Json<StatsSummaryResponse>, ApiError> {
    let stats = state.db.get_comprehensive_stats(query.days).await?;

    Ok(Json(StatsSummaryResponse {
        period_days: stats.period_days,
        generated_at: chrono::Utc::now().to_rfc3339(),
        system: stats.system,
        users: stats.users,
        market: stats.market,
        stores: stats.stores,
        top_commands: stats.top_commands,
    }))
}

async fn get_stats_health(
    State(state): State<AppState>,
    Query(query): Query<StatsQuery>,
) -> Result<Json<SystemStats>, ApiError> {
    let stats = state.db.get_system_stats(query.days).await?;
    Ok(Json(stats))
}

async fn get_stats_users(
    State(state): State<AppState>,
    Query(query): Query<StatsQuery>,
) -> Result<Json<UserStats>, ApiError> {
    let stats = state.db.get_user_stats(query.days).await?;
    Ok(Json(stats))
}

async fn get_stats_market(
    State(state): State<AppState>,
    Query(query): Query<StatsQuery>,
) -> Result<Json<ModelMarketStats>, ApiError> {
    let stats = state.db.get_market_stats(query.days).await?;
    Ok(Json(stats))
}

async fn get_stats_stores(
    State(state): State<AppState>,
) -> Result<Json<StatsStoresResponse>, ApiError> {
    let stores = state.db.get_store_rankings().await?;
    let count = stores.len();
    Ok(Json(StatsStoresResponse { stores, count }))
}

async fn get_stats_commands(
    State(state): State<AppState>,
    Query(query): Query<StatsQuery>,
) -> Result<Json<StatsCommandsResponse>, ApiError> {
    let commands = state.db.get_command_usage(query.days).await?;
    let count = commands.len();
    Ok(Json(StatsCommandsResponse { commands, count }))
}
