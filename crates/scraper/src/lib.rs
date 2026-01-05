//! Price Scout Scraper Orchestration
//!
//! This crate provides:
//! - Python bridge for calling Python scrapers
//! - Job queue management for scraping tasks
//! - Background worker for processing jobs
//!
//! # Architecture
//!
//! ```text
//! ┌─────────────────────────────────────┐
//! │         Application                 │
//! │   (API / Bot / CLI)                 │
//! └──────────────┬──────────────────────┘
//!                │
//!                v
//! ┌─────────────────────────────────────┐
//! │      ScraperQueue                   │
//! │   - enqueue jobs                    │
//! │   - manage priorities               │
//! │   - track status                    │
//! └──────────────┬──────────────────────┘
//!                │
//!                v
//! ┌─────────────────────────────────────┐
//! │      ScraperWorker                  │
//! │   - poll for jobs                   │
//! │   - call Python bridge              │
//! │   - save results                    │
//! └──────────────┬──────────────────────┘
//!                │
//!                v
//! ┌─────────────────────────────────────┐
//! │      Python Bridge                  │
//! │   - subprocess spawn                │
//! │   - JSON communication              │
//! └─────────────────────────────────────┘
//! ```

pub mod python_bridge;
pub mod queue;
pub mod worker;

pub use python_bridge::*;
pub use queue::{JobStats, ScraperQueue};
pub use worker::{ScraperWorker, WorkerConfig};
