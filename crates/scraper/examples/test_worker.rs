//! Test Worker Example
//!
//! Demonstrates the scraper worker processing jobs from the queue.
//!
//! Usage:
//! ```bash
//! # Set DATABASE_URL
//! export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
//!
//! # Run the worker
//! cargo run --example test_worker
//! ```
//!
//! The worker will:
//! 1. Connect to the database
//! 2. Create a test product
//! 3. Enqueue scraping jobs
//! 4. Process jobs (call Python scrapers)
//! 5. Save results to database
//! 6. Display statistics

use price_scout_db::Database;
use price_scout_models::ProductSpecs;
use price_scout_scraper::{ScraperQueue, ScraperWorker, WorkerConfig};
use std::time::Duration;
use tokio::time::timeout;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    println!("\n🔧 Scraper Worker Test\n");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    // Load environment
    dotenv::dotenv().ok();
    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");

    println!("📡 Connecting to database...");
    let db = Database::connect(&database_url).await?;
    println!("✅ Connected!\n");

    // Create queue
    let queue = ScraperQueue::new(db.clone());

    // Check if we have any stores
    let stores = db.get_stable_stores().await?;
    println!("📦 Available stores: {}", stores.len());
    for store in &stores {
        println!("   - {} ({})", store.name, store.method);
    }
    println!();

    // Check for existing products
    println!("🔍 Checking for existing products...");
    let existing_products = db.search_products("MacBook").await?;

    let product_id = if let Some(product) = existing_products.first() {
        println!("✅ Found existing product: {} (ID: {})", product.name, product.id);
        product.id
    } else {
        println!("📝 Creating test product...");

        // Create a test product
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

        let product_id = db
            .create_product(
                "MacBook Pro 16\" M1 Pro 32GB 512GB",
                Some("laptops"),
                &specs.to_json(),
                Some("MacBook Pro 16"),
            )
            .await?;
        println!("✅ Created product with ID: {}", product_id);
        product_id
    };

    println!();

    // Enqueue scraping jobs for all stores
    println!("📤 Enqueuing scraping jobs...");
    let job_ids = queue.enqueue_all_stores(product_id, Some(5)).await?;
    println!("✅ Enqueued {} jobs", job_ids.len());
    for (i, job_id) in job_ids.iter().enumerate() {
        println!("   Job {}: ID {}", i + 1, job_id);
    }
    println!();

    // Get initial stats
    let stats = queue.get_stats().await?;
    println!("📊 Initial Queue Statistics:");
    println!("   Pending:   {}", stats.pending);
    println!("   Running:   {}", stats.running);
    println!("   Completed: {}", stats.completed);
    println!("   Failed:    {}", stats.failed);
    println!("   Total:     {}", stats.total());
    println!();

    // Create worker configuration
    let config = WorkerConfig {
        batch_size: 3, // Process 3 jobs at a time
        poll_interval: Duration::from_secs(2),
        max_retries: 3,
        initial_retry_delay: Duration::from_secs(30),
        max_retry_delay: Duration::from_secs(600),
        scraper_timeout: Duration::from_secs(120),
    };

    // Create worker
    let worker = ScraperWorker::new(queue.clone(), config);
    let shutdown = worker.shutdown_handle();

    println!("🚀 Starting worker...");
    println!("   (Worker will process jobs for 60 seconds, then shutdown)\n");

    // Run worker with timeout
    let worker_task = tokio::spawn(async move {
        worker.run().await
    });

    // Wait for 60 seconds, then trigger shutdown
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_secs(60)).await;
        println!("\n⏰ Time's up! Requesting shutdown...");
        shutdown.store(true, std::sync::atomic::Ordering::Relaxed);
    });

    // Wait for worker to finish or timeout
    match timeout(Duration::from_secs(70), worker_task).await {
        Ok(Ok(Ok(()))) => {
            println!("✅ Worker shut down gracefully");
        }
        Ok(Ok(Err(e))) => {
            eprintln!("❌ Worker error: {:#}", e);
        }
        Ok(Err(e)) => {
            eprintln!("❌ Worker task panicked: {}", e);
        }
        Err(_) => {
            eprintln!("⏰ Worker timed out");
        }
    }

    println!();

    // Get final stats
    let final_stats = queue.get_stats().await?;
    println!("📊 Final Queue Statistics:");
    println!("   Pending:   {} ({})", final_stats.pending,
        if final_stats.pending < stats.pending { "↓" } else { "-" });
    println!("   Running:   {}", final_stats.running);
    println!("   Completed: {} ({})", final_stats.completed,
        if final_stats.completed > stats.completed { "↑" } else { "-" });
    println!("   Failed:    {} ({})", final_stats.failed,
        if final_stats.failed > stats.failed { "↑" } else { "-" });
    println!("   Total:     {}", final_stats.total());
    println!();

    // Get best prices for the product
    println!("💰 Best Prices:");
    let best_prices = db.get_best_prices(product_id, 5).await?;
    if best_prices.is_empty() {
        println!("   No prices found yet");
    } else {
        for price in best_prices {
            // Fetch store name
            let store = db.get_store(price.store_id).await?;
            let price_rub = price.price_rub();
            let available = if price.available { "✓" } else { "✗" };
            println!(
                "   {} {}: {:>10.2} RUB [{}]",
                available, store.name, price_rub, price.scraped_at.format("%H:%M:%S")
            );
        }
    }
    println!();

    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("✅ Worker test completed!");

    Ok(())
}
