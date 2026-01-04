//! Test database connection example
//!
//! Run with: cargo run --example test_connection

use price_scout_db::Database;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // Load .env file
    dotenv::dotenv().ok();

    // Get database URL from environment
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://postgres@192.168.0.10:5432/price_scout".to_string());

    println!("==================================================");
    println!("Price Scout - Database Connection Test");
    println!("==================================================");
    println!();
    println!("Database URL: {}", database_url);
    println!();

    // Connect to database
    println!("[1/5] Connecting to database...");
    let db = Database::connect(&database_url).await?;
    println!("[+] Connected successfully");
    println!();

    // Test ping
    println!("[2/5] Testing database connection...");
    db.ping().await?;
    println!("[+] Ping successful");
    println!();

    // Get stores
    println!("[3/5] Fetching stores...");
    let stores = db.get_stores().await?;
    println!("[+] Found {} stores:", stores.len());
    for store in &stores {
        let status = if store.unstable {
            "[UNSTABLE]"
        } else {
            "[STABLE]"
        };
        println!(
            "  - {} ({}) {} - {}",
            store.name, store.id, status, store.method
        );
    }
    println!();

    // Get stable stores only
    println!("[4/5] Fetching stable stores...");
    let stable_stores = db.get_stable_stores().await?;
    println!("[+] Found {} stable stores", stable_stores.len());
    println!();

    // Test search (should return empty for now)
    println!("[5/5] Testing product search...");
    let products = db.search_products("MacBook").await?;
    println!("[+] Found {} products matching 'MacBook'", products.len());
    if products.is_empty() {
        println!("  (Expected: database is empty, no products yet)");
    }
    println!();

    println!("==================================================");
    println!("Database Connection Test: SUCCESS");
    println!("==================================================");
    println!();
    println!("Summary:");
    println!("  - Connection: OK");
    println!("  - Tables accessible: OK");
    println!("  - Stores: {} total ({} stable)", stores.len(), stable_stores.len());
    println!("  - Ready for scraper integration");
    println!();

    // Close connection
    db.close().await;

    Ok(())
}
