//! Minimal Python Bridge Test
//!
//! Tests JSON communication with a minimal Python script (no dependencies).

use anyhow::{Context, Result};
use serde_json;
use std::path::PathBuf;
use std::process::Stdio;
use tokio::io::AsyncReadExt;
use tokio::process::Command;

#[derive(Debug, serde::Deserialize)]
struct TestResponse {
    store: String,
    status: String,
    price: Option<i32>,
    count: Option<i32>,
    time: f64,
    error: Option<String>,
    method: Option<String>,
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("\n🧪 Minimal Python Bridge Test\n");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    // Find test script
    let current_dir = std::env::current_dir()?;
    let script_path = current_dir.join("scripts/test_bridge_minimal.py");

    if !script_path.exists() {
        anyhow::bail!("Script not found: {}", script_path.display());
    }

    println!("📂 Script: {}", script_path.display());
    println!("⏳ Executing Python subprocess...\n");

    // Execute Python script
    let mut child = Command::new("python3")
        .arg(&script_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .context("Failed to spawn Python subprocess")?;

    // Wait for completion
    let status = child.wait().await.context("Failed to wait for subprocess")?;

    if !status.success() {
        let mut stderr = Vec::new();
        if let Some(mut stderr_handle) = child.stderr.take() {
            stderr_handle.read_to_end(&mut stderr).await?;
        }
        let error_msg = String::from_utf8_lossy(&stderr);
        anyhow::bail!("Python script failed: {}", error_msg);
    }

    // Read stdout
    let mut stdout = Vec::new();
    if let Some(mut stdout_handle) = child.stdout.take() {
        stdout_handle.read_to_end(&mut stdout).await?;
    }

    let stdout_str = String::from_utf8(stdout).context("Output is not valid UTF-8")?;

    println!("📄 Raw JSON output:");
    println!("{}", stdout_str);
    println!();

    // Parse JSON
    let response: TestResponse =
        serde_json::from_str(&stdout_str).context("Failed to parse JSON")?;

    println!("✅ JSON parsed successfully!\n");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    println!("📊 Parsed data:");
    println!("   Store: {}", response.store);
    println!("   Status: {}", response.status);
    println!("   Price: {} kopecks", response.price.unwrap_or(0));
    println!("   Count: {}", response.count.unwrap_or(0));
    println!("   Time: {:.2}s", response.time);
    println!("   Method: {}", response.method.as_deref().unwrap_or("unknown"));
    println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("\n🎉 Python Bridge: WORKING!");
    println!("✅ Subprocess spawn: OK");
    println!("✅ JSON output: OK");
    println!("✅ JSON parsing: OK");
    println!("✅ Data extraction: OK");
    println!("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    Ok(())
}
