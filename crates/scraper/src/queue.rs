//! Scraping Job Queue
//!
//! This module provides job queue management for scraping operations.
//! Jobs are stored in PostgreSQL and processed by workers.

use anyhow::{Context, Result};
use chrono::Utc;
use price_scout_db::Database;
use price_scout_models::ScrapingJob;
use sqlx::Row;
use tracing::{debug, info, warn};

/// Scraper job queue manager
///
/// Provides high-level operations for managing scraping jobs in the database.
#[derive(Clone)]
pub struct ScraperQueue {
    db: Database,
}

impl ScraperQueue {
    /// Create a new scraper queue
    pub fn new(db: Database) -> Self {
        Self { db }
    }

    /// Enqueue a scraping job for a product
    ///
    /// # Arguments
    /// * `product_id` - Product to scrape
    /// * `store_id` - Optional specific store (None = all stores)
    /// * `priority` - Job priority (1-10, default 5)
    ///
    /// # Returns
    /// Job ID of the created job
    pub async fn enqueue(
        &self,
        product_id: i64,
        store_id: Option<i32>,
        priority: Option<i32>,
    ) -> Result<i64> {
        let priority = priority.unwrap_or(5);

        let job_id = sqlx::query_scalar::<_, i64>(
            "INSERT INTO scraping_jobs (product_id, store_id, status, priority, scheduled_at)
             VALUES ($1, $2, 'pending', $3, NOW())
             RETURNING id",
        )
        .bind(product_id)
        .bind(store_id)
        .bind(priority)
        .fetch_one(self.db.pool())
        .await
        .context("Failed to enqueue scraping job")?;

        info!(
            "Enqueued scraping job {} for product {} (store: {:?}, priority: {})",
            job_id, product_id, store_id, priority
        );

        Ok(job_id)
    }

    /// Enqueue scraping jobs for a product across all stores
    ///
    /// Creates one job per store for the given product.
    ///
    /// # Arguments
    /// * `product_id` - Product to scrape
    /// * `priority` - Job priority (default 5)
    ///
    /// # Returns
    /// Vector of created job IDs
    pub async fn enqueue_all_stores(
        &self,
        product_id: i64,
        priority: Option<i32>,
    ) -> Result<Vec<i64>> {
        let stores = self.db.get_stable_stores().await?;
        let mut job_ids = Vec::new();

        for store in stores {
            let job_id = self.enqueue(product_id, Some(store.id), priority).await?;
            job_ids.push(job_id);
        }

        info!(
            "Enqueued {} scraping jobs for product {} across all stores",
            job_ids.len(),
            product_id
        );

        Ok(job_ids)
    }

    /// Fetch pending jobs
    ///
    /// Retrieves jobs with 'pending' status, ordered by priority (descending) and scheduled_at.
    ///
    /// # Arguments
    /// * `limit` - Maximum number of jobs to fetch
    ///
    /// # Returns
    /// Vector of pending jobs
    pub async fn get_pending_jobs(&self, limit: i32) -> Result<Vec<ScrapingJob>> {
        let jobs = sqlx::query_as::<_, ScrapingJob>(
            "SELECT * FROM scraping_jobs
             WHERE status = 'pending'
             ORDER BY priority DESC, scheduled_at ASC
             LIMIT $1",
        )
        .bind(limit)
        .fetch_all(self.db.pool())
        .await
        .context("Failed to fetch pending jobs")?;

        debug!("Fetched {} pending jobs", jobs.len());

        Ok(jobs)
    }

    /// Mark a job as started
    ///
    /// Updates job status to 'running' and sets started_at timestamp.
    pub async fn mark_started(&self, job_id: i64) -> Result<()> {
        let rows_affected = sqlx::query(
            "UPDATE scraping_jobs
             SET status = 'running', started_at = NOW()
             WHERE id = $1 AND status = 'pending'",
        )
        .bind(job_id)
        .execute(self.db.pool())
        .await
        .context("Failed to mark job as started")?
        .rows_affected();

        if rows_affected == 0 {
            warn!("Job {} was not in pending state", job_id);
        } else {
            debug!("Job {} marked as started", job_id);
        }

        Ok(())
    }

    /// Mark a job as completed successfully
    ///
    /// Updates job status to 'completed', sets completed_at timestamp, and stores result.
    pub async fn mark_completed(&self, job_id: i64, result: serde_json::Value) -> Result<()> {
        sqlx::query(
            "UPDATE scraping_jobs
             SET status = 'completed', completed_at = NOW(), result = $2
             WHERE id = $1",
        )
        .bind(job_id)
        .bind(result)
        .execute(self.db.pool())
        .await
        .context("Failed to mark job as completed")?;

        info!("Job {} completed successfully", job_id);

        Ok(())
    }

    /// Mark a job as failed
    ///
    /// Updates job status to 'failed', sets completed_at timestamp, and stores error message.
    pub async fn mark_failed(&self, job_id: i64, error: &str) -> Result<()> {
        sqlx::query(
            "UPDATE scraping_jobs
             SET status = 'failed', completed_at = NOW(), error = $2
             WHERE id = $1",
        )
        .bind(job_id)
        .bind(error)
        .execute(self.db.pool())
        .await
        .context("Failed to mark job as failed")?;

        warn!("Job {} failed: {}", job_id, error);

        Ok(())
    }

    /// Retry a failed job
    ///
    /// Resets job status to 'pending' and increments scheduled_at by delay.
    ///
    /// # Arguments
    /// * `job_id` - Job to retry
    /// * `delay_secs` - Delay before retrying (seconds)
    pub async fn retry_job(&self, job_id: i64, delay_secs: i64) -> Result<()> {
        sqlx::query(
            "UPDATE scraping_jobs
             SET status = 'pending',
                 scheduled_at = NOW() + INTERVAL '1 second' * $2,
                 error = NULL
             WHERE id = $1",
        )
        .bind(job_id)
        .bind(delay_secs)
        .execute(self.db.pool())
        .await
        .context("Failed to retry job")?;

        info!("Job {} scheduled for retry in {}s", job_id, delay_secs);

        Ok(())
    }

    /// Get job statistics
    ///
    /// Returns counts of jobs by status.
    pub async fn get_stats(&self) -> Result<JobStats> {
        let row = sqlx::query(
            r#"
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'running') as running,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM scraping_jobs
            "#,
        )
        .fetch_one(self.db.pool())
        .await
        .context("Failed to fetch job stats")?;

        Ok(JobStats {
            pending: row.try_get("pending")?,
            running: row.try_get("running")?,
            completed: row.try_get("completed")?,
            failed: row.try_get("failed")?,
        })
    }

    /// Clean up old completed jobs
    ///
    /// Deletes completed jobs older than the specified number of days.
    ///
    /// # Arguments
    /// * `days` - Jobs older than this will be deleted
    ///
    /// # Returns
    /// Number of jobs deleted
    pub async fn cleanup_old_jobs(&self, days: i32) -> Result<u64> {
        let rows_deleted = sqlx::query(
            "DELETE FROM scraping_jobs
             WHERE status = 'completed'
             AND completed_at < NOW() - INTERVAL '1 day' * $1",
        )
        .bind(days)
        .execute(self.db.pool())
        .await
        .context("Failed to clean up old jobs")?
        .rows_affected();

        if rows_deleted > 0 {
            info!("Cleaned up {} old completed jobs", rows_deleted);
        }

        Ok(rows_deleted)
    }

    /// Get a specific job by ID
    pub async fn get_job(&self, job_id: i64) -> Result<Option<ScrapingJob>> {
        let job = sqlx::query_as::<_, ScrapingJob>("SELECT * FROM scraping_jobs WHERE id = $1")
            .bind(job_id)
            .fetch_optional(self.db.pool())
            .await
            .context("Failed to fetch job")?;

        Ok(job)
    }

    /// Get database reference
    pub fn db(&self) -> &Database {
        &self.db
    }
}

/// Job queue statistics
#[derive(Debug, Clone)]
pub struct JobStats {
    pub pending: i64,
    pub running: i64,
    pub completed: i64,
    pub failed: i64,
}

impl JobStats {
    pub fn total(&self) -> i64 {
        self.pending + self.running + self.completed + self.failed
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Note: These tests require a database connection
    // Run with: cargo test --package price-scout-scraper -- --ignored

    #[tokio::test]
    #[ignore]
    async fn test_enqueue_and_fetch() {
        dotenv::dotenv().ok();
        let db_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");
        let db = Database::connect(&db_url).await.expect("Failed to connect");
        let queue = ScraperQueue::new(db);

        // Enqueue a job
        let job_id = queue
            .enqueue(1, Some(1), Some(5))
            .await
            .expect("Failed to enqueue");
        assert!(job_id > 0);

        // Fetch pending jobs
        let jobs = queue.get_pending_jobs(10).await.expect("Failed to fetch");
        assert!(!jobs.is_empty());

        // Clean up
        sqlx::query("DELETE FROM scraping_jobs WHERE id = $1")
            .bind(job_id)
            .execute(queue.db().pool())
            .await
            .expect("Failed to clean up");
    }
}
