//! Price Scout Database Layer
//!
//! PostgreSQL database operations using sqlx.

use anyhow::{Context, Result};
use price_scout_models::*;
use sqlx::postgres::{PgPool, PgPoolOptions};
use tracing::info;

// ============================================================================
// DATABASE CONNECTION
// ============================================================================

#[derive(Clone)]
pub struct Database {
    pool: PgPool,
}

impl Database {
    /// Connect to PostgreSQL database
    pub async fn connect(database_url: &str) -> Result<Self> {
        info!("Connecting to database: {}", database_url);

        let pool = PgPoolOptions::new()
            .max_connections(10)
            .acquire_timeout(std::time::Duration::from_secs(5))
            .connect(database_url)
            .await
            .context("Failed to connect to database")?;

        info!("Database connection established");

        Ok(Self { pool })
    }

    /// Get reference to connection pool
    pub fn pool(&self) -> &PgPool {
        &self.pool
    }

    /// Close database connection
    pub async fn close(self) {
        self.pool.close().await;
    }

    /// Test database connection
    pub async fn ping(&self) -> Result<()> {
        sqlx::query("SELECT 1")
            .execute(&self.pool)
            .await
            .context("Failed to ping database")?;

        Ok(())
    }
}

// ============================================================================
// STORE OPERATIONS
// ============================================================================

impl Database {
    /// Get all stores
    pub async fn get_stores(&self) -> Result<Vec<Store>> {
        let stores = sqlx::query_as::<_, Store>("SELECT * FROM stores ORDER BY id")
            .fetch_all(&self.pool)
            .await
            .context("Failed to fetch stores")?;

        Ok(stores)
    }

    /// Get stable stores (unstable=false)
    pub async fn get_stable_stores(&self) -> Result<Vec<Store>> {
        let stores = sqlx::query_as::<_, Store>(
            "SELECT * FROM stores WHERE unstable = false ORDER BY id",
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch stable stores")?;

        Ok(stores)
    }

    /// Get store by name
    pub async fn get_store_by_name(&self, name: &str) -> Result<Option<Store>> {
        let store = sqlx::query_as::<_, Store>("SELECT * FROM stores WHERE name = $1")
            .bind(name)
            .fetch_optional(&self.pool)
            .await
            .context("Failed to fetch store by name")?;

        Ok(store)
    }

    /// Get store by ID
    pub async fn get_store(&self, id: i32) -> Result<Store> {
        let store = sqlx::query_as::<_, Store>("SELECT * FROM stores WHERE id = $1")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .context("Failed to fetch store")?;

        Ok(store)
    }
}

// ============================================================================
// PRODUCT OPERATIONS
// ============================================================================

impl Database {
    /// Create new product
    pub async fn create_product(
        &self,
        name: &str,
        category: Option<&str>,
        specs: &serde_json::Value,
        search_query: Option<&str>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO products (name, category, specs, search_query)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            "#,
        )
        .bind(name)
        .bind(category)
        .bind(specs)
        .bind(search_query)
        .fetch_one(&self.pool)
        .await
        .context("Failed to create product")?;

        Ok(id)
    }

    /// Get product by ID
    pub async fn get_product(&self, id: i64) -> Result<Product> {
        let product = sqlx::query_as::<_, Product>("SELECT * FROM products WHERE id = $1")
            .bind(id)
            .fetch_one(&self.pool)
            .await
            .context("Failed to fetch product")?;

        Ok(product)
    }

    /// Search products by name
    pub async fn search_products(&self, query: &str) -> Result<Vec<Product>> {
        let products = sqlx::query_as::<_, Product>(
            "SELECT * FROM products WHERE name ILIKE $1 ORDER BY updated_at DESC LIMIT 50",
        )
        .bind(format!("%{}%", query))
        .fetch_all(&self.pool)
        .await
        .context("Failed to search products")?;

        Ok(products)
    }
}

// ============================================================================
// PRICE OPERATIONS
// ============================================================================

impl Database {
    /// Upsert store price (insert or update)
    pub async fn upsert_store_price(&self, price: &StorePrice) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO store_prices (product_id, store_id, price, url, available, scraped_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (product_id, store_id)
            DO UPDATE SET
                price = EXCLUDED.price,
                url = EXCLUDED.url,
                available = EXCLUDED.available,
                scraped_at = EXCLUDED.scraped_at
            RETURNING id
            "#,
        )
        .bind(price.product_id)
        .bind(price.store_id)
        .bind(price.price)
        .bind(&price.url)
        .bind(price.available)
        .bind(price.scraped_at)
        .fetch_one(&self.pool)
        .await
        .context("Failed to upsert store price")?;

        Ok(id)
    }

    /// Get best prices for product
    pub async fn get_best_prices(&self, product_id: i64, limit: i32) -> Result<Vec<StorePrice>> {
        let prices = sqlx::query_as::<_, StorePrice>(
            r#"
            SELECT * FROM store_prices
            WHERE product_id = $1 AND available = true
            ORDER BY price ASC
            LIMIT $2
            "#,
        )
        .bind(product_id)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch best prices")?;

        Ok(prices)
    }

    /// Get prices for product by store ID
    pub async fn get_product_price_by_store(
        &self,
        product_id: i64,
        store_id: i32,
    ) -> Result<Option<StorePrice>> {
        let price = sqlx::query_as::<_, StorePrice>(
            "SELECT * FROM store_prices WHERE product_id = $1 AND store_id = $2",
        )
        .bind(product_id)
        .bind(store_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch product price by store")?;

        Ok(price)
    }
}

// ============================================================================
// USER OPERATIONS
// ============================================================================

impl Database {
    /// Create or update user
    pub async fn upsert_user(&self, telegram_id: i64, username: Option<&str>) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO users (telegram_id, username, created_at, last_active_at)
            VALUES ($1, $2, NOW(), NOW())
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                last_active_at = NOW()
            RETURNING id
            "#,
        )
        .bind(telegram_id)
        .bind(username)
        .fetch_one(&self.pool)
        .await
        .context("Failed to upsert user")?;

        Ok(id)
    }

    /// Get user by telegram ID
    pub async fn get_user_by_telegram_id(&self, telegram_id: i64) -> Result<Option<User>> {
        let user =
            sqlx::query_as::<_, User>("SELECT * FROM users WHERE telegram_id = $1")
                .bind(telegram_id)
                .fetch_optional(&self.pool)
                .await
                .context("Failed to fetch user")?;

        Ok(user)
    }
}

// ============================================================================
// TRACKING OPERATIONS
// ============================================================================

impl Database {
    /// Create tracking
    pub async fn create_tracking(
        &self,
        user_id: i64,
        product_id: i64,
        target_price: Option<i32>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO trackings (user_id, product_id, target_price)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, product_id)
            DO UPDATE SET target_price = EXCLUDED.target_price
            RETURNING id
            "#,
        )
        .bind(user_id)
        .bind(product_id)
        .bind(target_price)
        .fetch_one(&self.pool)
        .await
        .context("Failed to create tracking")?;

        Ok(id)
    }

    /// Get user trackings
    pub async fn get_user_trackings(&self, user_id: i64) -> Result<Vec<Tracking>> {
        let trackings = sqlx::query_as::<_, Tracking>(
            "SELECT * FROM trackings WHERE user_id = $1 ORDER BY created_at DESC",
        )
        .bind(user_id)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch user trackings")?;

        Ok(trackings)
    }

    /// Get tracking by ID
    pub async fn get_tracking(&self, id: i64) -> Result<Tracking> {
        let tracking =
            sqlx::query_as::<_, Tracking>("SELECT * FROM trackings WHERE id = $1")
                .bind(id)
                .fetch_one(&self.pool)
                .await
                .context("Failed to fetch tracking")?;

        Ok(tracking)
    }
}

// ============================================================================
// SCRAPING JOB OPERATIONS
// ============================================================================

impl Database {
    /// Enqueue scraping job
    pub async fn enqueue_scraping_job(
        &self,
        product_id: i64,
        store_id: Option<i32>,
        priority: i32,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO scraping_jobs (product_id, store_id, status, priority)
            VALUES ($1, $2, 'pending', $3)
            RETURNING id
            "#,
        )
        .bind(product_id)
        .bind(store_id)
        .bind(priority)
        .fetch_one(&self.pool)
        .await
        .context("Failed to enqueue scraping job")?;

        Ok(id)
    }

    /// Get pending jobs
    pub async fn get_pending_jobs(&self, limit: i32) -> Result<Vec<ScrapingJob>> {
        let jobs = sqlx::query_as::<_, ScrapingJob>(
            r#"
            SELECT * FROM scraping_jobs
            WHERE status = 'pending'
            ORDER BY priority DESC, scheduled_at ASC
            LIMIT $1
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch pending jobs")?;

        Ok(jobs)
    }

    /// Update job status
    pub async fn update_job_status(
        &self,
        job_id: i64,
        status: &str,
        error: Option<&str>,
        result: Option<&serde_json::Value>,
    ) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE scraping_jobs
            SET status = $2,
                error = $3,
                result = $4,
                completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE NULL END
            WHERE id = $1
            "#,
        )
        .bind(job_id)
        .bind(status)
        .bind(error)
        .bind(result)
        .execute(&self.pool)
        .await
        .context("Failed to update job status")?;

        Ok(())
    }
}
