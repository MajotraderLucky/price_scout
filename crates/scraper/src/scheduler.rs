//! Scraping Job Scheduler
//!
//! Automatically schedules scraping jobs for products within a specified price range.
//! Designed to run periodically (e.g., every 10 minutes) to keep product prices up-to-date.

use anyhow::{Context, Result};
use price_scout_db::Database;
use tracing::{info, warn};

use crate::queue::ScraperQueue;

/// Scheduler configuration
#[derive(Debug, Clone)]
pub struct SchedulerConfig {
    /// Minimum price in kopecks (e.g., 500000 = 5,000 RUB)
    pub min_price: i32,

    /// Maximum price in kopecks (e.g., 1500000 = 15,000 RUB)
    pub max_price: i32,

    /// Job priority for scheduled scraping (1-10)
    pub priority: i32,

    /// Whether to schedule jobs for unstable stores
    pub include_unstable: bool,
}

impl Default for SchedulerConfig {
    fn default() -> Self {
        Self {
            min_price: 500_000,      // 5,000 RUB
            max_price: 50_000_000,   // 500,000 RUB
            priority: 5,             // Normal priority
            include_unstable: false,
        }
    }
}

/// Scraping job scheduler
///
/// Automatically creates scraping jobs for products within a price range.
/// Intended to be called periodically by a timer or cron job.
pub struct Scheduler {
    db: Database,
    queue: ScraperQueue,
    config: SchedulerConfig,
}

impl Scheduler {
    /// Create a new scheduler
    pub fn new(db: Database, queue: ScraperQueue, config: SchedulerConfig) -> Self {
        Self { db, queue, config }
    }

    /// Create with default configuration
    pub fn with_default_config(db: Database, queue: ScraperQueue) -> Self {
        Self::new(db, queue, SchedulerConfig::default())
    }

    /// Schedule scraping jobs for all products in the configured price range
    ///
    /// This method:
    /// 1. Queries products within the price range
    /// 2. Enqueues scraping jobs for each product across all stable stores
    /// 3. Returns the total number of jobs created
    ///
    /// # Returns
    /// Total number of jobs enqueued
    pub async fn schedule_all_products(&self) -> Result<usize> {
        info!(
            "Starting scheduled scraping for products in price range {}-{} RUB",
            self.config.min_price / 100,
            self.config.max_price / 100
        );

        // Get products in price range
        let products = self
            .db
            .get_products_in_price_range(self.config.min_price, self.config.max_price)
            .await
            .context("Failed to fetch products in price range")?;

        if products.is_empty() {
            warn!("No products found in price range");
            return Ok(0);
        }

        info!("Found {} products to scrape", products.len());

        // Enqueue jobs for each product
        let mut total_jobs = 0;
        for product in &products {
            match self
                .queue
                .enqueue_all_stores(product.id, Some(self.config.priority))
                .await
            {
                Ok(job_ids) => {
                    total_jobs += job_ids.len();
                    info!(
                        "Enqueued {} jobs for product '{}' (id={})",
                        job_ids.len(),
                        product.name,
                        product.id
                    );
                }
                Err(e) => {
                    warn!(
                        "Failed to enqueue jobs for product '{}' (id={}): {}",
                        product.name, product.id, e
                    );
                }
            }
        }

        info!(
            "Scheduled {} total scraping jobs for {} products",
            total_jobs,
            products.len()
        );

        Ok(total_jobs)
    }

    /// Schedule scraping jobs for a specific product
    ///
    /// # Arguments
    /// * `product_id` - Product to schedule scraping for
    ///
    /// # Returns
    /// Number of jobs created (one per store)
    pub async fn schedule_product(&self, product_id: i64) -> Result<usize> {
        let product = self
            .db
            .get_product(product_id)
            .await
            .context("Failed to fetch product")?
            .ok_or_else(|| anyhow::anyhow!("Product {} not found", product_id))?;

        let job_ids = self
            .queue
            .enqueue_all_stores(product_id, Some(self.config.priority))
            .await
            .context("Failed to enqueue jobs")?;

        info!(
            "Scheduled {} scraping jobs for product '{}' (id={})",
            job_ids.len(),
            product.name,
            product_id
        );

        Ok(job_ids.len())
    }

    /// Get scheduler configuration
    pub fn config(&self) -> &SchedulerConfig {
        &self.config
    }

    /// Update scheduler configuration
    pub fn set_config(&mut self, config: SchedulerConfig) {
        self.config = config;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = SchedulerConfig::default();
        assert_eq!(config.min_price, 500_000);
        assert_eq!(config.max_price, 1_500_000);
        assert_eq!(config.priority, 5);
        assert!(!config.include_unstable);
    }

    #[test]
    fn test_config_price_conversion() {
        let config = SchedulerConfig::default();
        // Verify kopecks to rubles conversion
        assert_eq!(config.min_price / 100, 5_000);
        assert_eq!(config.max_price / 100, 15_000);
    }
}
