//! Python Bridge
//!
//! Communication with Python scrapers via subprocess + JSON.
//!
//! This module provides the bridge between Rust and Python scrapers.
//! Python scrapers are called via subprocess with --json flag, and results
//! are parsed from stdout.

use anyhow::{Context, Result};
use price_scout_models::{ScraperRequest, ScraperResponse};
use serde_json;
use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;
use tokio::io::AsyncReadExt;
use tokio::process::Command;
use tokio::time::timeout;
use tracing::{debug, info, warn};

/// Default timeout for scraper subprocess
const DEFAULT_TIMEOUT_SECS: u64 = 120; // 2 minutes

/// Get path to test_scrapers.py script
fn get_scraper_script_path() -> Result<PathBuf> {
    // Try to find test_scrapers.py in project structure
    let current_dir = std::env::current_dir()?;

    // Common paths to check
    let paths = vec![
        current_dir.join("scripts/test_scrapers.py"),
        current_dir.join("../scripts/test_scrapers.py"),
        current_dir.join("../../scripts/test_scrapers.py"),
    ];

    for path in &paths {
        if path.exists() {
            debug!("Found scraper script: {}", path.display());
            return Ok(path.clone());
        }
    }

    anyhow::bail!(
        "Could not find test_scrapers.py. Searched: {:?}",
        paths
            .iter()
            .map(|p| p.display().to_string())
            .collect::<Vec<_>>()
    )
}

/// Run Python scraper and return result
///
/// # Arguments
/// * `request` - Scraper request containing store name, query, and method
///
/// # Returns
/// * `ScraperResponse` - Parsed response from Python scraper
///
/// # Errors
/// * If Python script cannot be found
/// * If subprocess fails to execute
/// * If JSON parsing fails
/// * If timeout is exceeded
///
/// # Example
/// ```no_run
/// use price_scout_models::ScraperRequest;
/// use price_scout_scraper::run_python_scraper;
///
/// #[tokio::main]
/// async fn main() -> anyhow::Result<()> {
///     let request = ScraperRequest {
///         store: "dns".to_string(),
///         query: "MacBook Pro 16".to_string(),
///         method: "firefox".to_string(),
///     };
///
///     let response = run_python_scraper(request).await?;
///     println!("Price: {:?}", response.price);
///     Ok(())
/// }
/// ```
pub async fn run_python_scraper(request: ScraperRequest) -> Result<ScraperResponse> {
    info!(
        "Running Python scraper: store={}, method={}",
        request.store, request.method
    );

    // Get script path
    let script_path = get_scraper_script_path()?;

    // Build command
    let mut cmd = Command::new("python3");
    cmd.arg(&script_path)
        .arg("--json")
        .arg(format!("--store={}", request.store))
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    debug!("Executing command: {:?}", cmd);

    // Spawn subprocess
    let mut child = cmd
        .spawn()
        .context("Failed to spawn Python subprocess")?;

    // Wait for completion with timeout
    let timeout_duration = Duration::from_secs(DEFAULT_TIMEOUT_SECS);

    let result = timeout(timeout_duration, async {
        let status = child
            .wait()
            .await
            .context("Failed to wait for subprocess")?;

        if !status.success() {
            // Read stderr for error details
            let mut stderr = Vec::new();
            if let Some(mut stderr_handle) = child.stderr.take() {
                stderr_handle
                    .read_to_end(&mut stderr)
                    .await
                    .context("Failed to read stderr")?;
            }

            let error_msg = String::from_utf8_lossy(&stderr);
            warn!("Python scraper failed: {}", error_msg);

            anyhow::bail!(
                "Python scraper exited with code {:?}: {}",
                status.code(),
                error_msg
            );
        }

        // Read stdout
        let mut stdout = Vec::new();
        if let Some(mut stdout_handle) = child.stdout.take() {
            stdout_handle
                .read_to_end(&mut stdout)
                .await
                .context("Failed to read stdout")?;
        } else {
            anyhow::bail!("Could not capture stdout from Python subprocess");
        }

        Ok::<Vec<u8>, anyhow::Error>(stdout)
    })
    .await
    .context("Python scraper timeout")?;

    let stdout = result?;
    let stdout_str =
        String::from_utf8(stdout).context("Python output is not valid UTF-8")?;

    debug!("Python scraper output: {}", stdout_str);

    // Parse JSON response
    let response: ScraperResponse = serde_json::from_str(&stdout_str)
        .context(format!("Failed to parse JSON response: {}", stdout_str))?;

    info!(
        "Python scraper completed: status={}, price={:?}",
        response.status, response.price
    );

    Ok(response)
}

/// Run Python scraper with custom timeout
pub async fn run_python_scraper_with_timeout(
    request: ScraperRequest,
    timeout_secs: u64,
) -> Result<ScraperResponse> {
    let timeout_duration = Duration::from_secs(timeout_secs);

    timeout(timeout_duration, run_python_scraper(request))
        .await
        .context("Scraper timeout")?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // Requires Python environment
    async fn test_python_bridge_basic() {
        let request = ScraperRequest {
            store: "i-ray".to_string(), // Fast store
            query: "test".to_string(),
            method: "playwright_direct".to_string(),
        };

        let result = run_python_scraper(request).await;
        assert!(result.is_ok(), "Python bridge should work");
    }
}
