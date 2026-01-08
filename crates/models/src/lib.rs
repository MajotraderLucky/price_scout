//! Price Scout Data Models
//!
//! Shared data structures used across all crates.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

// ============================================================================
// USER MODELS
// ============================================================================

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct User {
    pub id: i64,
    pub telegram_id: i64,
    pub username: Option<String>,
    pub created_at: DateTime<Utc>,
    pub last_active_at: Option<DateTime<Utc>>,
}

// ============================================================================
// STORE MODELS
// ============================================================================

/// Store with extended fields for management
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct Store {
    pub id: i32,
    pub name: String,
    pub base_url: String,
    pub method: String,
    pub parser: String,
    pub unstable: bool,
    pub created_at: DateTime<Utc>,
    // New fields from migration 007
    #[sqlx(default)]
    pub source: Option<String>,
    #[sqlx(default)]
    pub last_success_at: Option<DateTime<Utc>>,
    #[sqlx(default)]
    pub failure_count: Option<i32>,
    #[sqlx(default)]
    pub last_failure_at: Option<DateTime<Utc>>,
    #[sqlx(default)]
    pub enabled: Option<bool>,
    #[sqlx(default)]
    pub priority: Option<i32>,
    #[sqlx(default)]
    pub updated_at: Option<DateTime<Utc>>,
}

/// Request to create a new store
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewStore {
    pub name: String,
    pub base_url: String,
    pub method: String,
    pub parser: String,
    #[serde(default)]
    pub unstable: bool,
    #[serde(default = "default_source")]
    pub source: String,
    #[serde(default = "default_priority")]
    pub priority: i32,
}

fn default_source() -> String {
    "manual".to_string()
}

fn default_priority() -> i32 {
    50
}

/// Request to update a store
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UpdateStore {
    pub name: Option<String>,
    pub base_url: Option<String>,
    pub method: Option<String>,
    pub parser: Option<String>,
    pub unstable: Option<bool>,
    pub enabled: Option<bool>,
    pub priority: Option<i32>,
}

/// Store source enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StoreSource {
    Migration,
    Manual,
    AutoImport,
}

impl StoreSource {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Migration => "migration",
            Self::Manual => "manual",
            Self::AutoImport => "auto_import",
        }
    }
}

/// Store health statistics
#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct StoreHealthStats {
    pub total_stores: i64,
    pub enabled_stores: i64,
    pub healthy_stores: i64,
    pub unhealthy_stores: i64,
    pub critical_stores: i64,
    pub disabled_stores: i64,
}

/// Store candidate for auto-import
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct StoreCandidate {
    pub id: i64,
    pub domain: String,
    pub base_url: String,
    pub sample_urls: Vec<String>,
    pub price_extractions: i32,
    pub successful_extractions: i32,
    pub first_seen_at: DateTime<Utc>,
    pub last_seen_at: DateTime<Utc>,
    pub status: String,
    pub promoted_to_store_id: Option<i32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StoreMethod {
    Firefox,
    PlaywrightDirect,
    PlaywrightStealth,
    OzonFirefox,
    CitilinkFirefox,
    AvitoFirefox,
    YandexMarketSpecial,
    GenericHttp,
    GenericPlaywright,
}

impl StoreMethod {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Firefox => "firefox",
            Self::PlaywrightDirect => "playwright_direct",
            Self::PlaywrightStealth => "playwright_stealth",
            Self::OzonFirefox => "ozon_firefox",
            Self::CitilinkFirefox => "citilink_firefox",
            Self::AvitoFirefox => "avito_firefox",
            Self::YandexMarketSpecial => "yandex_market_special",
            Self::GenericHttp => "generic_http",
            Self::GenericPlaywright => "generic_playwright",
        }
    }
}

// ============================================================================
// PRODUCT MODELS
// ============================================================================

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct Product {
    pub id: i64,
    pub name: String,
    pub category: Option<String>,
    pub specs: Option<serde_json::Value>,
    pub search_query: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductSpecs {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub screen: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cpu: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ram: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ssd: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub article: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub color: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub condition: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub warranty: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
}

impl ProductSpecs {
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn from_json(value: &serde_json::Value) -> Option<Self> {
        serde_json::from_value(value.clone()).ok()
    }
}

// ============================================================================
// PRICE MODELS
// ============================================================================

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct StorePrice {
    pub id: i64,
    pub product_id: i64,
    pub store_id: i32,
    pub price: i32, // kopecks
    pub url: Option<String>,
    pub available: bool,
    pub scraped_at: DateTime<Utc>,
}

impl StorePrice {
    /// Convert price from kopecks to rubles
    pub fn price_rub(&self) -> f64 {
        self.price as f64 / 100.0
    }

    /// Create from rubles
    pub fn from_rub(rub: f64) -> i32 {
        (rub * 100.0).round() as i32
    }
}

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct PriceHistory {
    pub id: i64,
    pub product_id: i64,
    pub store_id: i32,
    pub price: i32,
    pub available: bool,
    pub recorded_at: DateTime<Utc>,
}

// ============================================================================
// TRACKING MODELS
// ============================================================================

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct Tracking {
    pub id: i64,
    pub user_id: i64,
    pub product_id: i64,
    pub target_price: Option<i32>,
    pub created_at: DateTime<Utc>,
}

// ============================================================================
// SCRAPING JOB MODELS
// ============================================================================

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct ScrapingJob {
    pub id: i64,
    pub product_id: i64,
    pub store_id: Option<i32>,
    pub status: String,
    pub priority: i32,
    pub scheduled_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub error: Option<String>,
    pub result: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum JobStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

impl JobStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Running => "running",
            Self::Completed => "completed",
            Self::Failed => "failed",
        }
    }
}

// ============================================================================
// NOTIFICATION MODELS
// ============================================================================

/// User with notification preferences
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct UserNotification {
    pub id: i64,
    pub telegram_id: i64,
    pub chat_id: Option<i64>,
    pub username: Option<String>,
    pub notifications_enabled: bool,
}

/// Scraping batch statistics for notifications
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct ScrapingBatch {
    pub id: i64,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub jobs_total: i32,
    pub jobs_success: i32,
    pub jobs_failed: i32,
    pub price_changes: i32,
    pub notification_sent: bool,
}

/// Price change event detected during scraping
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct PriceChangeEvent {
    pub id: i64,
    pub batch_id: i64,
    pub product_id: i64,
    pub store_id: i32,
    pub old_price: i32,
    pub new_price: i32,
    pub change_percent: f64,
    pub detected_at: DateTime<Utc>,
}

impl PriceChangeEvent {
    /// Old price in rubles
    pub fn old_price_rub(&self) -> f64 {
        self.old_price as f64 / 100.0
    }

    /// New price in rubles
    pub fn new_price_rub(&self) -> f64 {
        self.new_price as f64 / 100.0
    }

    /// Price change in rubles
    pub fn change_rub(&self) -> f64 {
        (self.new_price - self.old_price) as f64 / 100.0
    }
}

/// Price change with product name for display
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct PriceChangeWithProduct {
    pub product_id: i64,
    pub product_name: String,
    pub store_name: String,
    pub old_price: i32,
    pub new_price: i32,
    pub change_percent: f64,
}

/// Notification log entry
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct NotificationLog {
    pub id: i64,
    pub user_id: i64,
    pub batch_id: Option<i64>,
    pub notification_type: String,
    pub sent_at: DateTime<Utc>,
}

// ============================================================================
// SCRAPER RESPONSE MODELS
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScraperRequest {
    pub store: String,
    pub query: String,
    pub method: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScraperResponse {
    pub store: String,
    pub status: String,
    pub price: Option<i32>,
    pub count: Option<i32>,
    pub time: f64,
    pub error: Option<String>,
    pub method: Option<String>,
}

// ============================================================================
// MARKET RESEARCH MODELS
// ============================================================================

/// Search query tracked for market research
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct SearchQuery {
    pub id: i64,
    pub query: String,
    pub source: String,
    pub category: Option<String>,
    pub search_count: i32,
    pub last_searched_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SearchQuerySource {
    TelegramBot,
    WebDiscovery,
    CatalogParse,
    Manual,
}

impl SearchQuerySource {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::TelegramBot => "telegram_bot",
            Self::WebDiscovery => "web_discovery",
            Self::CatalogParse => "catalog_parse",
            Self::Manual => "manual",
        }
    }
}

/// Discovery job for finding new products
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct DiscoveryJob {
    pub id: i64,
    pub source: String,
    pub category: Option<String>,
    pub query: Option<String>,
    pub status: String,
    pub products_found: Option<i32>,
    pub products_new: Option<i32>,
    pub scheduled_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DiscoverySource {
    Duckduckgo,
    OzonCatalog,
    DnsCatalog,
    YandexMarketCatalog,
}

impl DiscoverySource {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Duckduckgo => "duckduckgo",
            Self::OzonCatalog => "ozon_catalog",
            Self::DnsCatalog => "dns_catalog",
            Self::YandexMarketCatalog => "yandex_market_catalog",
        }
    }
}

/// Product popularity metrics from materialized view
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct ProductPopularity {
    pub product_id: i64,
    pub name: String,
    pub category: Option<String>,
    pub tracking_score: i32,
    pub volatility_score: i32,
    pub availability_score: i32,
    pub arbitrage_score: i32,
    pub tracking_count: i64,
    pub min_price: Option<i32>,
    pub max_price: Option<i32>,
    pub store_count: Option<i64>,
    pub calculated_at: DateTime<Utc>,
}

impl ProductPopularity {
    /// Combined popularity score (0-100)
    pub fn popularity_score(&self) -> i32 {
        self.tracking_score + self.volatility_score + self.availability_score + self.arbitrage_score
    }

    /// Min price in rubles
    pub fn min_price_rub(&self) -> Option<f64> {
        self.min_price.map(|p| p as f64 / 100.0)
    }

    /// Max price in rubles
    pub fn max_price_rub(&self) -> Option<f64> {
        self.max_price.map(|p| p as f64 / 100.0)
    }
}

/// Top product entry for API response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopProduct {
    pub rank: i32,
    pub product_id: i64,
    pub name: String,
    pub category: Option<String>,
    pub popularity_score: i32,
    pub tracking_count: i64,
    pub min_price_rub: Option<i32>,
    pub max_price_rub: Option<i32>,
    pub store_count: i64,
}

// ============================================================================
// BOT STATISTICS MODELS
// ============================================================================

/// Comprehensive bot statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct BotStats {
    /// Period in days
    pub period_days: i32,
    /// System health metrics
    pub system: SystemStats,
    /// User metrics
    pub users: UserStats,
    /// Market metrics
    pub market: MarketStats,
    /// Store rankings
    pub stores: Vec<StoreRanking>,
    /// Top commands
    pub top_commands: Vec<CommandUsage>,
}

/// System health statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SystemStats {
    pub batches_total: i64,
    pub jobs_success: i64,
    pub jobs_failed: i64,
    pub success_rate: f64,
    pub stores_active: i32,
    pub stores_total: i32,
    pub last_batch_at: Option<DateTime<Utc>>,
}

/// User statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct UserStats {
    pub total: i64,
    pub with_notifications: i64,
    pub commands_count: i64,
    pub active_users: i64,
}

/// Market statistics
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MarketStats {
    pub products: i64,
    pub prices_collected: i64,
    pub price_changes: i64,
    pub arbitrage_opportunities: i64,
    pub min_price: Option<i32>,
    pub max_price: Option<i32>,
}

/// Store ranking entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreRanking {
    pub rank: i32,
    pub store_name: String,
    pub avg_price: i32,
    pub prices_count: i64,
    pub success_rate: f64,
    pub is_cheapest: bool,
}

/// Command usage statistics
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct CommandUsage {
    pub command: String,
    pub count: i64,
}

/// Command log entry
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct CommandLog {
    pub id: i64,
    pub user_id: Option<i64>,
    pub command: String,
    pub args: Option<String>,
    pub executed_at: DateTime<Utc>,
}

// ============================================================================
// TESTS
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_price_conversion() {
        let price = StorePrice {
            id: 1,
            product_id: 1,
            store_id: 1,
            price: 15690000, // 156,900 RUB
            url: None,
            available: true,
            scraped_at: Utc::now(),
        };

        assert_eq!(price.price_rub(), 156900.0);
        assert_eq!(StorePrice::from_rub(156900.0), 15690000);
    }

    #[test]
    fn test_product_specs_json() {
        let specs = ProductSpecs {
            screen: Some("16".to_string()),
            cpu: Some("M1 Pro".to_string()),
            ram: Some(32),
            ssd: Some(512),
            article: Some("Z14V0008D".to_string()),
            color: None,
            condition: None,
            warranty: None,
            year: None,
        };

        let json = specs.to_json();
        let restored = ProductSpecs::from_json(&json).unwrap();

        assert_eq!(restored.cpu, Some("M1 Pro".to_string()));
        assert_eq!(restored.ram, Some(32));
    }

    #[test]
    fn test_job_status() {
        assert_eq!(JobStatus::Pending.as_str(), "pending");
        assert_eq!(JobStatus::Running.as_str(), "running");
        assert_eq!(JobStatus::Completed.as_str(), "completed");
        assert_eq!(JobStatus::Failed.as_str(), "failed");
    }
}
