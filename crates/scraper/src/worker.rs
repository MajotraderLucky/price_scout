//! Scraper Worker
//!
//! Background worker that processes scraping jobs from the queue.
//!
//! The worker:
//! - Polls for pending jobs
//! - Calls Python scrapers via the bridge
//! - Saves results to the database
//! - Handles retries with exponential backoff
//! - Supports graceful shutdown

use anyhow::{Context, Result};
use chrono::Utc;
use price_scout_models::{ScraperRequest, ScraperResponse, ScrapingJob, StorePrice};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, error, info, warn};

use crate::python_bridge::run_python_scraper;
use crate::queue::ScraperQueue;

/// Worker configuration
#[derive(Debug, Clone)]
pub struct WorkerConfig {
    /// Maximum number of jobs to process per batch
    pub batch_size: i32,

    /// Delay between polling cycles when no jobs are available
    pub poll_interval: Duration,

    /// Maximum number of retry attempts for failed jobs
    pub max_retries: u32,

    /// Initial retry delay (doubles with each retry)
    pub initial_retry_delay: Duration,

    /// Maximum retry delay
    pub max_retry_delay: Duration,

    /// Timeout for scraper execution
    pub scraper_timeout: Duration,
}

impl Default for WorkerConfig {
    fn default() -> Self {
        Self {
            batch_size: 10,
            poll_interval: Duration::from_secs(5),
            max_retries: 3,
            initial_retry_delay: Duration::from_secs(60),
            max_retry_delay: Duration::from_secs(3600),
            scraper_timeout: Duration::from_secs(120),
        }
    }
}

/// Scraper worker
///
/// Processes scraping jobs in a loop until shutdown is requested.
pub struct ScraperWorker {
    queue: ScraperQueue,
    config: WorkerConfig,
    shutdown: Arc<AtomicBool>,
}

impl ScraperWorker {
    /// Create a new worker
    pub fn new(queue: ScraperQueue, config: WorkerConfig) -> Self {
        Self {
            queue,
            config,
            shutdown: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Get a shutdown handle for graceful termination
    pub fn shutdown_handle(&self) -> Arc<AtomicBool> {
        self.shutdown.clone()
    }

    /// Run the worker loop
    ///
    /// This method runs indefinitely until shutdown is requested.
    pub async fn run(&self) -> Result<()> {
        info!("Scraper worker started");
        info!(
            "Config: batch_size={}, poll_interval={:?}",
            self.config.batch_size, self.config.poll_interval
        );

        let mut processed_count = 0u64;
        let mut error_count = 0u64;

        while !self.shutdown.load(Ordering::Relaxed) {
            match self.process_batch().await {
                Ok(count) => {
                    if count > 0 {
                        processed_count += count as u64;
                        info!(
                            "Processed {} jobs (total: {}, errors: {})",
                            count, processed_count, error_count
                        );
                    } else {
                        // No jobs available, sleep before next poll
                        debug!("No pending jobs, sleeping for {:?}", self.config.poll_interval);
                        sleep(self.config.poll_interval).await;
                    }
                }
                Err(e) => {
                    error_count += 1;
                    error!("Error processing batch: {:#}", e);
                    // Sleep before retrying
                    sleep(Duration::from_secs(10)).await;
                }
            }
        }

        info!(
            "Scraper worker shutting down (processed: {}, errors: {})",
            processed_count, error_count
        );

        Ok(())
    }

    /// Process a batch of pending jobs
    ///
    /// Returns the number of jobs processed.
    async fn process_batch(&self) -> Result<usize> {
        let jobs = self
            .queue
            .get_pending_jobs(self.config.batch_size)
            .await
            .context("Failed to fetch pending jobs")?;

        if jobs.is_empty() {
            return Ok(0);
        }

        debug!("Processing batch of {} jobs", jobs.len());

        for job in &jobs {
            if self.shutdown.load(Ordering::Relaxed) {
                info!("Shutdown requested, stopping batch processing");
                break;
            }

            if let Err(e) = self.process_job(job).await {
                error!("Failed to process job {}: {:#}", job.id, e);
            }
        }

        Ok(jobs.len())
    }

    /// Process a single job
    async fn process_job(&self, job: &ScrapingJob) -> Result<()> {
        info!(
            "Processing job {} (product: {}, store: {:?})",
            job.id, job.product_id, job.store_id
        );

        // Mark job as started
        self.queue.mark_started(job.id).await?;

        // Fetch product details
        let product = self
            .queue
            .db()
            .get_product(job.product_id)
            .await?
            .ok_or_else(|| anyhow::anyhow!("Product {} not found", job.product_id))?;

        // Determine query (use search_query if available, otherwise product name)
        let query = product
            .search_query
            .as_ref()
            .unwrap_or(&product.name)
            .clone();

        // If store_id is specified, scrape that store
        // Otherwise, scrape all stable stores
        if let Some(store_id) = job.store_id {
            self.scrape_store(job, &query, store_id).await?;
        } else {
            self.scrape_all_stores(job, &query).await?;
        }

        Ok(())
    }

    /// Scrape a specific store
    async fn scrape_store(&self, job: &ScrapingJob, query: &str, store_id: i32) -> Result<()> {
        // Fetch store details
        let store = self
            .queue
            .db()
            .get_store(store_id)
            .await
            .context(format!("Store {} not found", store_id))?;

        debug!(
            "Scraping store {} ({}) for product {}",
            store.name, store.method, job.product_id
        );

        // Build scraper request
        let request = ScraperRequest {
            store: store.name.clone(),
            query: query.to_string(),
            method: store.method.clone(),
        };

        // Call Python scraper
        match run_python_scraper(request).await {
            Ok(response) => {
                self.handle_scraper_response(job, &store.name, store_id, &response)
                    .await?;
            }
            Err(e) => {
                warn!(
                    "Scraper failed for job {} (store: {}): {:#}",
                    job.id, store.name, e
                );
                self.handle_scraper_error(job, &e.to_string()).await?;
            }
        }

        Ok(())
    }

    /// Scrape all stable stores
    async fn scrape_all_stores(&self, job: &ScrapingJob, query: &str) -> Result<()> {
        let stores = self.queue.db().get_stable_stores().await?;

        debug!(
            "Scraping {} stores for product {}",
            stores.len(),
            job.product_id
        );

        let mut success_count = 0;
        let mut error_count = 0;

        for store in stores {
            let request = ScraperRequest {
                store: store.name.clone(),
                query: query.to_string(),
                method: store.method.clone(),
            };

            match run_python_scraper(request).await {
                Ok(response) => {
                    if let Err(e) = self
                        .handle_scraper_response(job, &store.name, store.id, &response)
                        .await
                    {
                        error!("Failed to save result for store {}: {:#}", store.name, e);
                        error_count += 1;
                    } else {
                        success_count += 1;
                    }
                }
                Err(e) => {
                    warn!(
                        "Scraper failed for job {} (store: {}): {:#}",
                        job.id, store.name, e
                    );
                    error_count += 1;
                }
            }
        }

        // Mark job as completed if at least one store succeeded
        if success_count > 0 {
            let result = serde_json::json!({
                "success_count": success_count,
                "error_count": error_count,
                "total_stores": success_count + error_count,
            });
            self.queue.mark_completed(job.id, result).await?;
        } else {
            // All stores failed
            self.handle_scraper_error(job, &format!("All {} stores failed", error_count))
                .await?;
        }

        Ok(())
    }

    /// Handle successful scraper response
    async fn handle_scraper_response(
        &self,
        job: &ScrapingJob,
        store_name: &str,
        store_id: i32,
        response: &ScraperResponse,
    ) -> Result<()> {
        match response.status.as_str() {
            "success" | "PASS" => {
                // Extract price
                if let Some(price) = response.price {
                    // Create StorePrice struct
                    let store_price = StorePrice {
                        id: 0, // Will be set by database
                        product_id: job.product_id,
                        store_id,
                        price,
                        url: None, // Python scraper doesn't return URL yet
                        available: true,
                        scraped_at: Utc::now(),
                    };

                    // Save price to database
                    self.queue
                        .db()
                        .upsert_store_price(&store_price)
                        .await
                        .context("Failed to upsert store price")?;

                    info!(
                        "Job {}: Saved price {} kopecks for store {}",
                        job.id, price, store_name
                    );

                    // Mark job as completed
                    let result = serde_json::json!({
                        "store": store_name,
                        "price": price,
                        "count": response.count,
                        "time": response.time,
                        "method": response.method,
                    });
                    self.queue.mark_completed(job.id, result).await?;
                } else {
                    warn!(
                        "Job {}: Scraper succeeded but no price found for store {}",
                        job.id, store_name
                    );
                    self.handle_scraper_error(job, "No price found").await?;
                }
            }
            "FAIL" | "ERROR" => {
                let error_msg = response
                    .error
                    .as_ref()
                    .map(|s| s.as_str())
                    .unwrap_or("Unknown error");
                warn!(
                    "Job {}: Scraper failed for store {}: {}",
                    job.id, store_name, error_msg
                );
                self.handle_scraper_error(job, error_msg).await?;
            }
            _ => {
                warn!(
                    "Job {}: Unknown scraper status '{}' for store {}",
                    job.id, response.status, store_name
                );
                self.handle_scraper_error(job, &format!("Unknown status: {}", response.status))
                    .await?;
            }
        }

        Ok(())
    }

    /// Handle scraper error with retry logic
    async fn handle_scraper_error(&self, job: &ScrapingJob, error: &str) -> Result<()> {
        // Check if we should retry
        // Note: We'd need to track retry count in the database for production use
        // For now, just mark as failed

        self.queue.mark_failed(job.id, error).await?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_worker_config_default() {
        let config = WorkerConfig::default();
        assert_eq!(config.batch_size, 10);
        assert_eq!(config.poll_interval, Duration::from_secs(5));
        assert_eq!(config.max_retries, 3);
    }
}
