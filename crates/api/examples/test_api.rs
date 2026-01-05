//! Test API Client Example
//!
//! Demonstrates how to interact with the Price Scout API.
//!
//! Prerequisites:
//! - API server must be running: `cargo run --bin price-scout-api`
//! - Database must be set up with products and stores
//!
//! Usage:
//! ```bash
//! cargo run --example test_api
//! ```

use anyhow::Result;
use reqwest::Client;
use serde_json::{json, Value};

#[tokio::main]
async fn main() -> Result<()> {
    println!("\n🧪 Price Scout API Client Test\n");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    let client = Client::new();
    let base_url = "http://localhost:3000";

    println!("📡 Testing API at {}\n", base_url);

    println!("1️⃣  Health Check");
    println!("   GET /health");
    let response = client.get(format!("{}/health", base_url)).send().await?;
    println!("   Status: {}", response.status());
    println!("   Body: {}\n", response.text().await?);

    println!("2️⃣  List Stores");
    println!("   GET /api/stores");
    let response = client
        .get(format!("{}/api/stores", base_url))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let stores: Value = response.json().await?;
    println!("   Stores: {}\n", serde_json::to_string_pretty(&stores)?);

    println!("3️⃣  Search Products");
    println!("   POST /api/search");
    let response = client
        .post(format!("{}/api/search", base_url))
        .json(&json!({ "query": "MacBook" }))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let search_results: Value = response.json().await?;
    println!(
        "   Results: {}\n",
        serde_json::to_string_pretty(&search_results)?
    );

    let product_id = search_results["products"]
        .as_array()
        .and_then(|arr| arr.first())
        .and_then(|p| p["id"].as_i64())
        .unwrap_or(1);

    println!("4️⃣  Get Product Details");
    println!("   GET /api/products/{}", product_id);
    let response = client
        .get(format!("{}/api/products/{}", base_url, product_id))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let product: Value = response.json().await?;
    println!("   Product: {}\n", serde_json::to_string_pretty(&product)?);

    println!("5️⃣  Get Product Prices");
    println!("   GET /api/products/{}/prices", product_id);
    let response = client
        .get(format!("{}/api/products/{}/prices", base_url, product_id))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let prices: Value = response.json().await?;
    println!("   Prices: {}\n", serde_json::to_string_pretty(&prices)?);

    println!("6️⃣  Trigger Scraping (All Stores)");
    println!("   POST /api/products/{}/scrape", product_id);
    let response = client
        .post(format!(
            "{}/api/products/{}/scrape",
            base_url, product_id
        ))
        .json(&json!({ "priority": 8 }))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let scrape_response: Value = response.json().await?;
    println!(
        "   Response: {}\n",
        serde_json::to_string_pretty(&scrape_response)?
    );

    println!("7️⃣  Trigger Scraping (Specific Stores)");
    println!("   POST /api/products/{}/scrape", product_id);
    let response = client
        .post(format!(
            "{}/api/products/{}/scrape",
            base_url, product_id
        ))
        .json(&json!({
            "stores": ["dns", "ozon"],
            "priority": 10
        }))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let scrape_response: Value = response.json().await?;
    println!(
        "   Response: {}\n",
        serde_json::to_string_pretty(&scrape_response)?
    );

    println!("8️⃣  Get Queue Statistics");
    println!("   GET /api/queue/stats");
    let response = client
        .get(format!("{}/api/queue/stats", base_url))
        .send()
        .await?;
    println!("   Status: {}", response.status());
    let stats: Value = response.json().await?;
    println!("   Stats: {}\n", serde_json::to_string_pretty(&stats)?);

    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("✅ All API tests completed!\n");

    Ok(())
}
