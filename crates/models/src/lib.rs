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

#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct Store {
    pub id: i32,
    pub name: String,
    pub base_url: String,
    pub method: String,
    pub parser: String,
    pub unstable: bool,
    pub created_at: DateTime<Utc>,
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
    pub specs: serde_json::Value,
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
