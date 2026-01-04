//! Price Scout Scraper Orchestration
//!
//! Manages Python scrapers and job queue.
//! Python bridge to be implemented in PS-23.

pub mod python_bridge;

pub use python_bridge::*;
