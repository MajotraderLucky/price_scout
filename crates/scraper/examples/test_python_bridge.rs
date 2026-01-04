//! Test Python Bridge Communication
//!
//! This example tests the Rust ↔ Python bridge by calling the test_scrapers.py script.
//!
//! Usage:
//! ```bash
//! cargo run --example test_python_bridge
//! ```

use price_scout_models::ScraperRequest;
use price_scout_scraper::run_python_scraper;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing for logging
    tracing_subscriber::fmt::init();

    println!("\n🧪 Testing Python Bridge Communication\n");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    // Test with i-ray.ru (fastest stable store)
    let request = ScraperRequest {
        store: "i-ray".to_string(),
        query: "MacBook Pro 16".to_string(),
        method: "playwright_direct".to_string(),
    };

    println!("📡 Sending request to Python scraper:");
    println!("   Store: {}", request.store);
    println!("   Query: {}", request.query);
    println!("   Method: {}", request.method);
    println!();

    println!("⏳ Running Python subprocess...\n");

    // Run Python scraper
    match run_python_scraper(request).await {
        Ok(response) => {
            println!("✅ Python bridge communication SUCCESS!\n");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
            println!("📊 Response:");
            println!("   Store: {}", response.store);
            println!("   Status: {}", response.status);
            println!("   Price: {}", response.price.unwrap_or(0));
            println!("   Count: {}", response.count.unwrap_or(0));
            println!("   Time: {:.2}s", response.time);
            println!("   Method: {}", response.method.as_deref().unwrap_or("unknown"));

            if let Some(error) = response.error {
                println!("   Error: {}", error);
            }

            println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!("\n✅ Test completed successfully!");

            Ok(())
        }
        Err(e) => {
            println!("❌ Python bridge communication FAILED!\n");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
            println!("Error: {:#}", e);
            println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

            Err(e)
        }
    }
}
