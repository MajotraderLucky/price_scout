//! Price Scout Scheduler Binary
//!
//! One-shot job enqueuing for periodic scraping.
//! Designed to be run by systemd timer every 10 minutes.
//!
//! Usage:
//!   cargo run --bin price-scout-scheduler
//!   ./target/release/price-scout-scheduler

use anyhow::{Context, Result};
use price_scout_db::Database;
use price_scout_scraper::{Scheduler, SchedulerConfig, ScraperQueue};
use std::env;
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

    info!("📅 Price Scout Scheduler");
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

    // Initialize queue and scheduler
    let queue = ScraperQueue::new(db.clone());
    let config = SchedulerConfig::default();
    let scheduler = Scheduler::new(db.clone(), queue, config.clone());

    info!(
        "⚙️  Scheduler configuration:\n\
         - Price range: {} - {} RUB\n\
         - Priority: {}\n\
         - Include unstable: {}",
        config.min_price / 100,
        config.max_price / 100,
        config.priority,
        config.include_unstable
    );

    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("🔄 Scheduling scraping jobs...");

    // Schedule all products
    match scheduler.schedule_all_products().await {
        Ok(total_jobs) => {
            info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            info!("✅ Scheduling completed successfully");
            info!("📊 Total jobs enqueued: {}", total_jobs);
            info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        }
        Err(e) => {
            error!("❌ Scheduling failed: {}", e);
            return Err(e);
        }
    }

    // Close database connection
    db.close().await;

    Ok(())
}
