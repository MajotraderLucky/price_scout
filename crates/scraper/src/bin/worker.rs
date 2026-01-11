//! Price Scout Scraper Worker Binary
//!
//! Continuously processes scraping jobs from the queue.
//!
//! Usage:
//!   cargo run --bin price-scout-worker
//!   ./target/release/price-scout-worker

use anyhow::{Context, Result};
use price_scout_db::Database;
use price_scout_scraper::{ScraperQueue, ScraperWorker, WorkerConfig};
use std::env;
use std::time::Duration;
use tokio::signal;
use tracing::{error, info};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,price_scout=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("🚀 Price Scout Scraper Worker");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Get database URL
    let database_url = env::var("DATABASE_URL")
        .context("DATABASE_URL environment variable not set")?;

    // Connect to database
    info!("📡 Connecting to database...");
    let db = Database::connect(&database_url)
        .await
        .context("Failed to connect to database")?;

    // Test connection
    db.ping().await.context("Database ping failed")?;
    info!("✅ Database connected");

    // Initialize queue
    let queue = ScraperQueue::new(db.clone());
    info!("✅ Scraper queue initialized");

    // Create worker with configuration
    let config = WorkerConfig::default();
    info!(
        "⚙️  Worker configuration:\n\
         - Batch size: {}\n\
         - Poll interval: {}s\n\
         - Max retries: {}\n\
         - Scraper timeout: {}s",
        config.batch_size,
        config.poll_interval.as_secs(),
        config.max_retries,
        config.scraper_timeout.as_secs()
    );

    let worker = ScraperWorker::new(queue, config);
    let shutdown_handle = worker.shutdown_handle();

    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("✅ Worker ready - polling for jobs every 10 minutes");
    info!("✅ Materialized view refresh: every 1 hour");
    info!("Press Ctrl+C to stop");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Spawn worker task
    let worker_handle = tokio::spawn(async move {
        if let Err(e) = worker.run().await {
            error!("Worker error: {}", e);
        }
    });

    // Spawn materialized view refresh task (every hour)
    let db_refresh = db.clone();
    let refresh_handle = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(3600)); // 1 hour
        loop {
            interval.tick().await;
            info!("🔄 Refreshing materialized views...");
            match db_refresh.refresh_popularity_metrics().await {
                Ok(()) => info!("✅ mv_product_popularity refreshed"),
                Err(e) => error!("Failed to refresh mv_product_popularity: {}", e),
            }
        }
    });

    // Wait for shutdown signal
    signal::ctrl_c()
        .await
        .context("Failed to listen for Ctrl+C")?;

    info!("📡 Shutdown signal received, stopping worker...");
    shutdown_handle.store(true, std::sync::atomic::Ordering::Relaxed);

    // Abort refresh task
    refresh_handle.abort();
    info!("✅ Materialized view refresh task stopped");

    // Wait for worker to finish (with timeout)
    match tokio::time::timeout(Duration::from_secs(30), worker_handle).await {
        Ok(Ok(())) => info!("✅ Worker stopped gracefully"),
        Ok(Err(e)) => error!("Worker panicked: {}", e),
        Err(_) => error!("Worker shutdown timeout"),
    }

    // Close database connection
    db.close().await;
    info!("✅ Database connection closed");
    info!("👋 Goodbye!");

    Ok(())
}
