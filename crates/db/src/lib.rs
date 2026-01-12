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

    /// Get enabled stores (enabled=true)
    pub async fn get_enabled_stores(&self) -> Result<Vec<Store>> {
        let stores = sqlx::query_as::<_, Store>(
            "SELECT * FROM stores WHERE enabled = true ORDER BY priority DESC, id",
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch enabled stores")?;

        Ok(stores)
    }

    /// Find store by domain (partial match)
    pub async fn find_store_by_domain(&self, domain: &str) -> Result<Option<Store>> {
        let store = sqlx::query_as::<_, Store>(
            "SELECT * FROM stores WHERE base_url ILIKE '%' || $1 || '%' LIMIT 1",
        )
        .bind(domain)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to find store by domain")?;

        Ok(store)
    }

    /// Create new store
    pub async fn create_store(&self, store: &NewStore) -> Result<i32> {
        let id = sqlx::query_scalar::<_, i32>(
            r#"
            INSERT INTO stores (name, base_url, method, parser, unstable, source, priority)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            "#,
        )
        .bind(&store.name)
        .bind(&store.base_url)
        .bind(&store.method)
        .bind(&store.parser)
        .bind(store.unstable)
        .bind(&store.source)
        .bind(store.priority)
        .fetch_one(&self.pool)
        .await
        .context("Failed to create store")?;

        Ok(id)
    }

    /// Update store
    pub async fn update_store(&self, id: i32, update: &UpdateStore) -> Result<()> {
        let mut query = String::from("UPDATE stores SET updated_at = NOW()");
        let mut param_count = 0;

        if update.name.is_some() {
            param_count += 1;
            query.push_str(&format!(", name = ${}", param_count));
        }
        if update.base_url.is_some() {
            param_count += 1;
            query.push_str(&format!(", base_url = ${}", param_count));
        }
        if update.method.is_some() {
            param_count += 1;
            query.push_str(&format!(", method = ${}", param_count));
        }
        if update.parser.is_some() {
            param_count += 1;
            query.push_str(&format!(", parser = ${}", param_count));
        }
        if update.unstable.is_some() {
            param_count += 1;
            query.push_str(&format!(", unstable = ${}", param_count));
        }
        if update.enabled.is_some() {
            param_count += 1;
            query.push_str(&format!(", enabled = ${}", param_count));
        }
        if update.priority.is_some() {
            param_count += 1;
            query.push_str(&format!(", priority = ${}", param_count));
        }

        param_count += 1;
        query.push_str(&format!(" WHERE id = ${}", param_count));

        let mut q = sqlx::query(&query);

        if let Some(ref name) = update.name {
            q = q.bind(name);
        }
        if let Some(ref base_url) = update.base_url {
            q = q.bind(base_url);
        }
        if let Some(ref method) = update.method {
            q = q.bind(method);
        }
        if let Some(ref parser) = update.parser {
            q = q.bind(parser);
        }
        if let Some(unstable) = update.unstable {
            q = q.bind(unstable);
        }
        if let Some(enabled) = update.enabled {
            q = q.bind(enabled);
        }
        if let Some(priority) = update.priority {
            q = q.bind(priority);
        }

        q.bind(id)
            .execute(&self.pool)
            .await
            .context("Failed to update store")?;

        Ok(())
    }

    /// Update store health after scraping attempt
    pub async fn update_store_health(&self, id: i32, success: bool) -> Result<()> {
        if success {
            sqlx::query(
                r#"
                UPDATE stores
                SET last_success_at = NOW(),
                    failure_count = 0,
                    updated_at = NOW()
                WHERE id = $1
                "#,
            )
            .bind(id)
            .execute(&self.pool)
            .await
            .context("Failed to update store health (success)")?;
        } else {
            sqlx::query(
                r#"
                UPDATE stores
                SET last_failure_at = NOW(),
                    failure_count = failure_count + 1,
                    updated_at = NOW()
                WHERE id = $1
                "#,
            )
            .bind(id)
            .execute(&self.pool)
            .await
            .context("Failed to update store health (failure)")?;
        }

        Ok(())
    }

    /// Disable store (soft delete)
    pub async fn disable_store(&self, id: i32) -> Result<()> {
        sqlx::query("UPDATE stores SET enabled = false, updated_at = NOW() WHERE id = $1")
            .bind(id)
            .execute(&self.pool)
            .await
            .context("Failed to disable store")?;

        Ok(())
    }

    /// Delete store (hard delete)
    pub async fn delete_store(&self, id: i32) -> Result<()> {
        sqlx::query("DELETE FROM stores WHERE id = $1")
            .bind(id)
            .execute(&self.pool)
            .await
            .context("Failed to delete store")?;

        Ok(())
    }

    /// Get store health statistics
    pub async fn get_store_health_stats(&self) -> Result<StoreHealthStats> {
        let stats = sqlx::query_as::<_, StoreHealthStats>(
            "SELECT * FROM get_store_health_stats()",
        )
        .fetch_one(&self.pool)
        .await
        .context("Failed to get store health stats")?;

        Ok(stats)
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

    /// Create product from web search result (PS-53)
    ///
    /// Creates a product and optionally adds initial price from the web search.
    /// Used when user clicks "Track" button on web search results.
    pub async fn create_product_from_web(
        &self,
        name: &str,
        url: &str,
        price: Option<i32>,  // in kopecks (already converted from rubles)
        store_name: &str,
    ) -> Result<i64> {
        // 1. Create product
        let product_id = self.create_product(
            name,
            None,  // category unknown from web
            &serde_json::json!({"source": "web_search", "url": url}),
            Some(name),  // use name as search_query for future lookups
        ).await?;

        // 2. Find or create store by name/domain
        let store_id = if let Some(store) = self.find_store_by_domain(store_name).await? {
            store.id
        } else if let Some(store) = self.get_store_by_name(store_name).await? {
            store.id
        } else {
            // Create new store
            self.create_store(&NewStore {
                name: store_name.to_string(),
                base_url: url.split('/').take(3).collect::<Vec<_>>().join("/"),
                method: "generic_http".to_string(),  // valid: firefox, playwright_*, generic_*
                parser: "none".to_string(),
                unstable: true,  // web-discovered stores are unstable
                source: "manual".to_string(),        // valid: migration, manual, auto_import
                priority: 100,   // low priority
            }).await?
        };

        // 3. Add initial price if provided
        if let Some(price_kopecks) = price {
            let store_price = StorePrice {
                id: 0,  // will be assigned by DB
                product_id,
                store_id,
                price: price_kopecks,
                url: Some(url.to_string()),
                available: true,
                scraped_at: chrono::Utc::now(),
            };
            if let Err(e) = self.upsert_store_price(&store_price).await {
                // Log but don't fail - product was created
                tracing::warn!("Failed to add initial price for web product: {}", e);
            }
        }

        Ok(product_id)
    }

    /// Get product by ID
    pub async fn get_product(&self, id: i64) -> Result<Option<Product>> {
        let product = sqlx::query_as::<_, Product>("SELECT * FROM products WHERE id = $1")
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .context("Failed to fetch product")?;

        Ok(product)
    }

    /// Search products by name or search_query (article)
    ///
    /// Handles various query formats:
    /// - Simple: "MacBook Pro"
    /// - With article: "Рогатка Centershot Артикул: WAL001-1"
    /// - Multi-line with article on separate line
    pub async fn search_products(&self, query: &str) -> Result<Vec<Product>> {
        // Extract article if present (format: "Артикул: XXX" or "Артикул XXX")
        let article = if query.contains("Артикул") {
            // Extract text after "Артикул:" or "Артикул"
            query.split("Артикул")
                .nth(1)
                .and_then(|s| s.trim_start_matches(':').split_whitespace().next())
                .map(|s| s.to_string())
        } else {
            None
        };

        // Extract product name (text before "Артикул" or full query)
        let name_part = if query.contains("Артикул") {
            query.split("Артикул").next().unwrap_or(query).trim()
        } else {
            query.trim()
        };

        let name_pattern = format!("%{}%", name_part);

        let products = sqlx::query_as::<_, Product>(
            "SELECT * FROM products
             WHERE name ILIKE $1
                OR search_query ILIKE $2
                OR search_query = $3
             ORDER BY updated_at DESC LIMIT 50",
        )
        .bind(&name_pattern)
        .bind(article.as_ref().map(|a| format!("%{}%", a)).unwrap_or_else(|| name_pattern.clone()))
        .bind(article.as_deref().unwrap_or(""))
        .fetch_all(&self.pool)
        .await
        .context("Failed to search products")?;

        Ok(products)
    }

    /// Get products within a price range
    ///
    /// Finds products with at least one available price in the specified range.
    /// Used by the scheduler to select products for periodic scraping.
    ///
    /// # Arguments
    /// * `min_price` - Minimum price in kopecks
    /// * `max_price` - Maximum price in kopecks
    ///
    /// # Returns
    /// Vector of products with prices in the range
    pub async fn get_products_in_price_range(
        &self,
        min_price: i32,
        max_price: i32,
    ) -> Result<Vec<Product>> {
        let products = sqlx::query_as::<_, Product>(
            r#"
            SELECT DISTINCT p.*
            FROM products p
            JOIN store_prices sp ON p.id = sp.product_id
            WHERE sp.price >= $1 AND sp.price <= $2
              AND sp.available = true
            ORDER BY p.updated_at DESC
            "#,
        )
        .bind(min_price)
        .bind(max_price)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch products in price range")?;

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

    // ========================================================================
    // CURRENCY RATES
    // ========================================================================

    /// Save currency exchange rate to database
    ///
    /// # Arguments
    /// * `currency_code` - Currency code ('USD' or 'EUR')
    /// * `rate_to_rub` - Exchange rate to Russian Ruble
    /// * `source` - Data source ('cbr_ru' or 'open_er')
    ///
    /// # Returns
    /// ID of the created currency_rate record
    pub async fn save_currency_rate(
        &self,
        currency_code: &str,
        rate_to_rub: f64,
        source: &str,
    ) -> Result<i64> {
        let rate_id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO currency_rates (currency_code, rate_to_rub, source)
            VALUES ($1, $2, $3)
            RETURNING id
            "#,
        )
        .bind(currency_code)
        .bind(rate_to_rub)
        .bind(source)
        .fetch_one(&self.pool)
        .await
        .context("Failed to save currency rate")?;

        Ok(rate_id)
    }

    /// Get latest currency rate for a specific currency and source
    ///
    /// # Arguments
    /// * `currency_code` - Currency code ('USD' or 'EUR')
    /// * `source` - Data source ('cbr_ru' or 'open_er')
    ///
    /// # Returns
    /// Latest exchange rate, or None if not found
    pub async fn get_latest_rate(
        &self,
        currency_code: &str,
        source: &str,
    ) -> Result<Option<f64>> {
        let rate = sqlx::query_scalar::<_, Option<f64>>(
            r#"
            SELECT rate_to_rub
            FROM currency_rates
            WHERE currency_code = $1 AND source = $2
            ORDER BY recorded_at DESC
            LIMIT 1
            "#,
        )
        .bind(currency_code)
        .bind(source)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch latest rate")?;

        Ok(rate.flatten())
    }

    /// Get all currency rates for a specific date range
    ///
    /// # Arguments
    /// * `currency_code` - Currency code ('USD' or 'EUR')
    /// * `days` - Number of days to look back
    ///
    /// # Returns
    /// Vector of (source, rate, timestamp) tuples
    pub async fn get_currency_rates_history(
        &self,
        currency_code: &str,
        days: i32,
    ) -> Result<Vec<(String, f64, chrono::DateTime<chrono::Utc>)>> {
        let rates = sqlx::query_as::<_, (String, f64, chrono::DateTime<chrono::Utc>)>(
            r#"
            SELECT source, rate_to_rub, recorded_at
            FROM currency_rates
            WHERE currency_code = $1
              AND recorded_at >= NOW() - INTERVAL '$2 days'
            ORDER BY recorded_at DESC
            "#,
        )
        .bind(currency_code)
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch currency rates history")?;

        Ok(rates)
    }

    // ========================================================================
    // ANALYTICS
    // ========================================================================

    /// Get price trends for a product over time
    ///
    /// Returns daily statistics: avg, min, max prices and volatility (stddev)
    ///
    /// # Arguments
    /// * `product_id` - Product to analyze
    /// * `days` - Number of days to look back
    ///
    /// # Returns
    /// Vector of (date, avg_price, min_price, max_price, volatility) tuples
    pub async fn get_price_trends(
        &self,
        product_id: i64,
        days: i32,
    ) -> Result<Vec<(chrono::NaiveDate, f64, i32, i32, Option<f64>)>> {
        let trends = sqlx::query_as::<_, (chrono::NaiveDate, f64, i32, i32, Option<f64>)>(
            r#"
            SELECT
                DATE(scraped_at) as date,
                AVG(price)::float8 as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                STDDEV(price)::float8 as volatility
            FROM store_prices
            WHERE product_id = $1
              AND scraped_at >= NOW() - INTERVAL '1 day' * $2
              AND available = true
            GROUP BY DATE(scraped_at)
            ORDER BY date DESC
            "#,
        )
        .bind(product_id)
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch price trends")?;

        Ok(trends)
    }

    /// Calculate price-currency correlation
    ///
    /// Computes Pearson correlation between product prices and currency rates.
    /// Returns correlation coefficient (-1 to 1).
    ///
    /// # Arguments
    /// * `product_id` - Product to analyze
    /// * `currency_code` - Currency to correlate with ('USD' or 'EUR')
    /// * `days` - Number of days to analyze
    ///
    /// # Returns
    /// Correlation coefficient (None if insufficient data)
    pub async fn calculate_price_currency_correlation(
        &self,
        product_id: i64,
        currency_code: &str,
        days: i32,
    ) -> Result<Option<f64>> {
        let correlation = sqlx::query_scalar::<_, Option<f64>>(
            r#"
            WITH price_changes AS (
                SELECT DATE(scraped_at) as date,
                       AVG(price)::float8 as avg_price
                FROM store_prices
                WHERE product_id = $1
                  AND scraped_at >= NOW() - INTERVAL '1 day' * $3
                  AND available = true
                GROUP BY DATE(scraped_at)
            ),
            rate_changes AS (
                SELECT DATE(recorded_at) as date,
                       AVG(rate_to_rub)::float8 as avg_rate
                FROM currency_rates
                WHERE currency_code = $2
                  AND recorded_at >= NOW() - INTERVAL '1 day' * $3
                GROUP BY DATE(recorded_at)
            )
            SELECT CORR(p.avg_price, r.avg_rate)
            FROM price_changes p
            JOIN rate_changes r ON p.date = r.date
            "#,
        )
        .bind(product_id)
        .bind(currency_code)
        .bind(days)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to calculate correlation")?;

        Ok(correlation.flatten())
    }

    /// Get store comparison statistics
    ///
    /// Returns average price, update frequency, and availability for each store.
    ///
    /// # Arguments
    /// * `product_id` - Product to compare across stores
    /// * `days` - Number of days to analyze
    ///
    /// # Returns
    /// Vector of (store_name, avg_price, num_updates, availability_percent) tuples
    pub async fn get_store_comparison(
        &self,
        product_id: i64,
        days: i32,
    ) -> Result<Vec<(String, f64, i64, f64)>> {
        let stats = sqlx::query_as::<_, (String, f64, i64, f64)>(
            r#"
            SELECT
                s.name as store_name,
                AVG(sp.price)::float8 as avg_price,
                COUNT(*) as num_updates,
                (COUNT(*) FILTER (WHERE sp.available = true)::float8 / COUNT(*)::float8 * 100) as availability_percent
            FROM store_prices sp
            JOIN stores s ON sp.store_id = s.id
            WHERE sp.product_id = $1
              AND sp.scraped_at >= NOW() - INTERVAL '1 day' * $2
            GROUP BY s.id, s.name
            ORDER BY avg_price ASC
            "#,
        )
        .bind(product_id)
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch store comparison")?;

        Ok(stats)
    }

    /// Get market overview for a category in price range
    ///
    /// Returns aggregate statistics for products in the specified range.
    ///
    /// # Arguments
    /// * `min_price` - Minimum price in kopecks
    /// * `max_price` - Maximum price in kopecks
    /// * `days` - Number of days to analyze
    ///
    /// # Returns
    /// (total_products, avg_price, min_price, max_price, total_updates) tuple
    pub async fn get_market_overview(
        &self,
        min_price: i32,
        max_price: i32,
        days: i32,
    ) -> Result<(i64, f64, i32, i32, i64)> {
        let overview = sqlx::query_as::<_, (i64, f64, i32, i32, i64)>(
            r#"
            SELECT
                COUNT(DISTINCT sp.product_id) as total_products,
                AVG(sp.price)::float8 as avg_price,
                MIN(sp.price) as min_price,
                MAX(sp.price) as max_price,
                COUNT(*) as total_updates
            FROM store_prices sp
            WHERE sp.price >= $1 AND sp.price <= $2
              AND sp.scraped_at >= NOW() - INTERVAL '1 day' * $3
              AND sp.available = true
            "#,
        )
        .bind(min_price)
        .bind(max_price)
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch market overview")?;

        Ok(overview)
    }

    /// Find arbitrage opportunities (price differences across stores)
    ///
    /// Identifies products with significant price differences between stores,
    /// sorted by profit percentage (descending).
    ///
    /// # Arguments
    /// * `min_profit_percent` - Minimum profit percentage to include (e.g., 10.0 for 10%)
    ///
    /// # Returns
    /// Vec of tuples: (product_id, product_name, category, buy_store_id, buy_store_name,
    /// buy_price, sell_store_id, sell_store_name, sell_price, profit_kopecks, profit_percent)
    pub async fn find_arbitrage_opportunities(
        &self,
        min_profit_percent: f64,
    ) -> Result<
        Vec<(
            i64,    // product_id
            String, // product_name
            String, // category
            i64,    // buy_store_id
            String, // buy_store_name
            i32,    // buy_price
            i64,    // sell_store_id
            String, // sell_store_name
            i32,    // sell_price
            i32,    // profit_kopecks
            f64,    // profit_percent
        )>,
    > {
        let opportunities = sqlx::query_as::<_, (i64, String, String, i64, String, i32, i64, String, i32, i32, f64)>(
            r#"
            WITH price_pairs AS (
                SELECT
                    p.id as product_id,
                    p.name as product_name,
                    p.category,
                    sp1.store_id as buy_store_id,
                    sp1.price as buy_price,
                    sp2.store_id as sell_store_id,
                    sp2.price as sell_price,
                    (sp2.price - sp1.price) as profit,
                    ((sp2.price - sp1.price)::float / sp1.price::float * 100) as profit_percent
                FROM products p
                JOIN store_prices sp1 ON p.id = sp1.product_id
                JOIN store_prices sp2 ON p.id = sp2.product_id
                WHERE sp1.available = true
                  AND sp2.available = true
                  AND sp1.store_id != sp2.store_id
                  AND sp2.price > sp1.price
                  AND ((sp2.price - sp1.price)::float / sp1.price::float * 100) >= $1
            )
            SELECT
                pp.product_id,
                pp.product_name,
                pp.category,
                pp.buy_store_id,
                s1.name as buy_store_name,
                pp.buy_price,
                pp.sell_store_id,
                s2.name as sell_store_name,
                pp.sell_price,
                pp.profit,
                pp.profit_percent
            FROM price_pairs pp
            JOIN stores s1 ON pp.buy_store_id = s1.id
            JOIN stores s2 ON pp.sell_store_id = s2.id
            ORDER BY pp.profit_percent DESC
            LIMIT 100
            "#,
        )
        .bind(min_profit_percent)
        .fetch_all(&self.pool)
        .await
        .context("Failed to find arbitrage opportunities")?;

        Ok(opportunities)
    }

    // ========================================================================
    // MARKET RESEARCH
    // ========================================================================

    /// Record or update a search query for market research
    ///
    /// Uses upsert to increment search_count if query already exists.
    ///
    /// # Arguments
    /// * `query` - The search query text
    /// * `source` - Source of query ('telegram_bot', 'web_discovery', 'catalog_parse', 'manual')
    /// * `category` - Optional category classification
    ///
    /// # Returns
    /// ID of the search query record
    pub async fn record_search_query(
        &self,
        query: &str,
        source: &str,
        category: Option<&str>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO search_queries (query, source, category, search_count, last_searched_at)
            VALUES ($1, $2, $3, 1, NOW())
            ON CONFLICT (LOWER(query), source)
            DO UPDATE SET
                search_count = search_queries.search_count + 1,
                last_searched_at = NOW(),
                category = COALESCE(EXCLUDED.category, search_queries.category)
            RETURNING id
            "#,
        )
        .bind(query)
        .bind(source)
        .bind(category)
        .fetch_one(&self.pool)
        .await
        .context("Failed to record search query")?;

        Ok(id)
    }

    /// Get most popular search queries
    ///
    /// Returns queries ordered by search count and recency.
    ///
    /// # Arguments
    /// * `limit` - Maximum number of queries to return
    ///
    /// # Returns
    /// Vector of SearchQuery objects
    pub async fn get_popular_search_queries(&self, limit: i32) -> Result<Vec<SearchQuery>> {
        let queries = sqlx::query_as::<_, SearchQuery>(
            r#"
            SELECT id, query, source, category, search_count, last_searched_at, created_at
            FROM search_queries
            ORDER BY search_count DESC, last_searched_at DESC
            LIMIT $1
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch popular search queries")?;

        Ok(queries)
    }

    /// Get search queries by category
    ///
    /// # Arguments
    /// * `category` - Category to filter by
    /// * `limit` - Maximum number of queries to return
    ///
    /// # Returns
    /// Vector of SearchQuery objects in the specified category
    pub async fn get_search_queries_by_category(
        &self,
        category: &str,
        limit: i32,
    ) -> Result<Vec<SearchQuery>> {
        let queries = sqlx::query_as::<_, SearchQuery>(
            r#"
            SELECT id, query, source, category, search_count, last_searched_at, created_at
            FROM search_queries
            WHERE category = $1
            ORDER BY search_count DESC, last_searched_at DESC
            LIMIT $2
            "#,
        )
        .bind(category)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch search queries by category")?;

        Ok(queries)
    }

    /// Create a discovery job
    ///
    /// # Arguments
    /// * `source` - Discovery source ('duckduckgo', 'ozon_catalog', 'dns_catalog', 'yandex_market_catalog')
    /// * `category` - Optional category to search
    /// * `query` - Optional search query
    ///
    /// # Returns
    /// ID of the created discovery job
    pub async fn create_discovery_job(
        &self,
        source: &str,
        category: Option<&str>,
        query: Option<&str>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO discovery_jobs (source, category, query, status, scheduled_at)
            VALUES ($1, $2, $3, 'pending', NOW())
            RETURNING id
            "#,
        )
        .bind(source)
        .bind(category)
        .bind(query)
        .fetch_one(&self.pool)
        .await
        .context("Failed to create discovery job")?;

        Ok(id)
    }

    /// Get pending discovery jobs
    ///
    /// # Arguments
    /// * `limit` - Maximum number of jobs to return
    ///
    /// # Returns
    /// Vector of pending DiscoveryJob objects
    pub async fn get_pending_discovery_jobs(&self, limit: i32) -> Result<Vec<DiscoveryJob>> {
        let jobs = sqlx::query_as::<_, DiscoveryJob>(
            r#"
            SELECT id, source, category, query, status, products_found, products_new,
                   scheduled_at, started_at, completed_at, error
            FROM discovery_jobs
            WHERE status = 'pending'
            ORDER BY scheduled_at ASC
            LIMIT $1
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch pending discovery jobs")?;

        Ok(jobs)
    }

    /// Update discovery job status
    ///
    /// # Arguments
    /// * `job_id` - ID of the job to update
    /// * `status` - New status ('running', 'completed', 'failed')
    /// * `products_found` - Number of products found (optional)
    /// * `products_new` - Number of new products added (optional)
    /// * `error` - Error message if failed (optional)
    pub async fn update_discovery_job_status(
        &self,
        job_id: i64,
        status: &str,
        products_found: Option<i32>,
        products_new: Option<i32>,
        error: Option<&str>,
    ) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE discovery_jobs
            SET status = $2,
                products_found = COALESCE($3, products_found),
                products_new = COALESCE($4, products_new),
                error = $5,
                started_at = CASE WHEN $2 = 'running' THEN NOW() ELSE started_at END,
                completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE NULL END
            WHERE id = $1
            "#,
        )
        .bind(job_id)
        .bind(status)
        .bind(products_found)
        .bind(products_new)
        .bind(error)
        .execute(&self.pool)
        .await
        .context("Failed to update discovery job status")?;

        Ok(())
    }

    /// Get top products by popularity score
    ///
    /// Returns products from the materialized view, ordered by combined popularity score.
    ///
    /// # Arguments
    /// * `limit` - Maximum number of products to return (max 100)
    ///
    /// # Returns
    /// Vector of ProductPopularity objects
    pub async fn get_top_products(&self, limit: i32) -> Result<Vec<ProductPopularity>> {
        let limit = limit.min(100);
        let products = sqlx::query_as::<_, ProductPopularity>(
            r#"
            SELECT
                product_id,
                name,
                category,
                tracking_score,
                volatility_score,
                availability_score,
                arbitrage_score,
                tracking_count,
                min_price,
                max_price,
                store_count,
                calculated_at
            FROM mv_product_popularity
            ORDER BY (tracking_score + volatility_score + availability_score + arbitrage_score) DESC
            LIMIT $1
            "#,
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch top products")?;

        Ok(products)
    }

    /// Get popularity metrics for a specific product
    ///
    /// # Arguments
    /// * `product_id` - Product ID to look up
    ///
    /// # Returns
    /// ProductPopularity if found, None otherwise
    pub async fn get_product_popularity(&self, product_id: i64) -> Result<Option<ProductPopularity>> {
        let popularity = sqlx::query_as::<_, ProductPopularity>(
            r#"
            SELECT
                product_id,
                name,
                category,
                tracking_score,
                volatility_score,
                availability_score,
                arbitrage_score,
                tracking_count,
                min_price,
                max_price,
                store_count,
                calculated_at
            FROM mv_product_popularity
            WHERE product_id = $1
            "#,
        )
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch product popularity")?;

        Ok(popularity)
    }

    /// Refresh the product popularity materialized view
    ///
    /// This should be called hourly by the discovery scheduler.
    pub async fn refresh_popularity_metrics(&self) -> Result<()> {
        sqlx::query("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_popularity")
            .execute(&self.pool)
            .await
            .context("Failed to refresh popularity metrics")?;

        Ok(())
    }

    /// Get distinct product categories
    ///
    /// # Returns
    /// Vector of category names
    pub async fn get_product_categories(&self) -> Result<Vec<String>> {
        let categories = sqlx::query_scalar::<_, String>(
            r#"
            SELECT DISTINCT category
            FROM products
            WHERE category IS NOT NULL
            ORDER BY category
            "#,
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch product categories")?;

        Ok(categories)
    }

    /// Get products by category
    ///
    /// # Arguments
    /// * `category` - Category to filter by
    /// * `limit` - Maximum number of products to return
    ///
    /// # Returns
    /// Vector of Product objects in the specified category
    pub async fn get_products_by_category(&self, category: &str, limit: i32) -> Result<Vec<Product>> {
        let products = sqlx::query_as::<_, Product>(
            r#"
            SELECT * FROM products
            WHERE category = $1
            ORDER BY updated_at DESC
            LIMIT $2
            "#,
        )
        .bind(category)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch products by category")?;

        Ok(products)
    }

    // ========================================================================
    // NOTIFICATION OPERATIONS
    // ========================================================================

    /// Update user's chat_id for notifications
    pub async fn update_user_chat_id(&self, telegram_id: i64, chat_id: i64) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE users
            SET chat_id = $2
            WHERE telegram_id = $1
            "#,
        )
        .bind(telegram_id)
        .bind(chat_id)
        .execute(&self.pool)
        .await
        .context("Failed to update user chat_id")?;

        Ok(())
    }

    /// Get all users with notifications enabled
    pub async fn get_notification_recipients(&self) -> Result<Vec<UserNotification>> {
        let users = sqlx::query_as::<_, UserNotification>(
            r#"
            SELECT id, telegram_id, chat_id, username, notifications_enabled
            FROM users
            WHERE notifications_enabled = true AND chat_id IS NOT NULL
            "#,
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch notification recipients")?;

        Ok(users)
    }

    /// Create a new scraping batch
    pub async fn create_scraping_batch(&self) -> Result<i64> {
        let batch_id = sqlx::query_scalar::<_, i64>(
            "INSERT INTO scraping_batches (started_at) VALUES (NOW()) RETURNING id",
        )
        .fetch_one(&self.pool)
        .await
        .context("Failed to create scraping batch")?;

        Ok(batch_id)
    }

    /// Update scraping batch statistics
    pub async fn update_scraping_batch(
        &self,
        batch_id: i64,
        jobs_total: i32,
        jobs_success: i32,
        jobs_failed: i32,
        price_changes: i32,
    ) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE scraping_batches
            SET completed_at = NOW(),
                jobs_total = $2,
                jobs_success = $3,
                jobs_failed = $4,
                price_changes = $5
            WHERE id = $1
            "#,
        )
        .bind(batch_id)
        .bind(jobs_total)
        .bind(jobs_success)
        .bind(jobs_failed)
        .bind(price_changes)
        .execute(&self.pool)
        .await
        .context("Failed to update scraping batch")?;

        Ok(())
    }

    /// Get unnotified completed batches
    pub async fn get_unnotified_batches(&self) -> Result<Vec<ScrapingBatch>> {
        let batches = sqlx::query_as::<_, ScrapingBatch>(
            r#"
            SELECT * FROM scraping_batches
            WHERE notification_sent = false AND completed_at IS NOT NULL
            ORDER BY completed_at ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch unnotified batches")?;

        Ok(batches)
    }

    /// Mark batch as notified
    pub async fn mark_batch_notified(&self, batch_id: i64) -> Result<()> {
        sqlx::query("UPDATE scraping_batches SET notification_sent = true WHERE id = $1")
            .bind(batch_id)
            .execute(&self.pool)
            .await
            .context("Failed to mark batch as notified")?;

        Ok(())
    }

    /// Record price change event
    pub async fn record_price_change(
        &self,
        batch_id: i64,
        product_id: i64,
        store_id: i32,
        old_price: i32,
        new_price: i32,
        change_percent: f64,
    ) -> Result<i64> {
        let event_id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO price_change_events
                (batch_id, product_id, store_id, old_price, new_price, change_percent)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            "#,
        )
        .bind(batch_id)
        .bind(product_id)
        .bind(store_id)
        .bind(old_price)
        .bind(new_price)
        .bind(change_percent)
        .fetch_one(&self.pool)
        .await
        .context("Failed to record price change")?;

        Ok(event_id)
    }

    /// Get price changes for a batch with product/store names
    pub async fn get_batch_price_changes(&self, batch_id: i64) -> Result<Vec<PriceChangeWithProduct>> {
        let changes = sqlx::query_as::<_, PriceChangeWithProduct>(
            r#"
            SELECT
                e.product_id,
                p.name as product_name,
                s.name as store_name,
                e.old_price,
                e.new_price,
                e.change_percent
            FROM price_change_events e
            JOIN products p ON e.product_id = p.id
            JOIN stores s ON e.store_id = s.id
            WHERE e.batch_id = $1
            ORDER BY ABS(e.change_percent) DESC
            LIMIT 10
            "#,
        )
        .bind(batch_id)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch batch price changes")?;

        Ok(changes)
    }

    /// Get current price for product/store (for change detection)
    pub async fn get_current_price(&self, product_id: i64, store_id: i32) -> Result<Option<i32>> {
        let price = sqlx::query_scalar::<_, i32>(
            r#"
            SELECT price FROM store_prices
            WHERE product_id = $1 AND store_id = $2
            "#,
        )
        .bind(product_id)
        .bind(store_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch current price")?;

        Ok(price)
    }

    /// Log notification sent
    pub async fn log_notification(
        &self,
        user_id: i64,
        batch_id: Option<i64>,
        notification_type: &str,
    ) -> Result<i64> {
        let log_id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO notification_log (user_id, batch_id, notification_type)
            VALUES ($1, $2, $3)
            RETURNING id
            "#,
        )
        .bind(user_id)
        .bind(batch_id)
        .bind(notification_type)
        .fetch_one(&self.pool)
        .await
        .context("Failed to log notification")?;

        Ok(log_id)
    }
}

// ============================================================================
// BOT STATISTICS OPERATIONS
// ============================================================================

impl Database {
    /// Log command execution
    pub async fn log_command(
        &self,
        user_id: Option<i64>,
        command: &str,
        args: Option<&str>,
    ) -> Result<i64> {
        let log_id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO command_log (user_id, command, args)
            VALUES ($1, $2, $3)
            RETURNING id
            "#,
        )
        .bind(user_id)
        .bind(command)
        .bind(args)
        .fetch_one(&self.pool)
        .await
        .context("Failed to log command")?;

        Ok(log_id)
    }

    /// Get command usage statistics for a period
    pub async fn get_command_usage(&self, days: i32) -> Result<Vec<CommandUsage>> {
        let usage = sqlx::query_as::<_, CommandUsage>(
            r#"
            SELECT command, COUNT(*) as count
            FROM command_log
            WHERE executed_at >= NOW() - INTERVAL '1 day' * $1
            GROUP BY command
            ORDER BY count DESC
            LIMIT 10
            "#,
        )
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch command usage")?;

        Ok(usage)
    }

    /// Get system statistics for a period
    pub async fn get_system_stats(&self, days: i32) -> Result<SystemStats> {
        // Get batch statistics
        let batch_stats = sqlx::query_as::<_, (i64, i64, i64, Option<chrono::DateTime<chrono::Utc>>)>(
            r#"
            SELECT
                COUNT(*) as batches_total,
                COALESCE(SUM(jobs_success), 0) as jobs_success,
                COALESCE(SUM(jobs_failed), 0) as jobs_failed,
                MAX(completed_at) as last_batch_at
            FROM scraping_batches
            WHERE started_at >= NOW() - INTERVAL '1 day' * $1
            "#,
        )
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch batch stats")?;

        // Get store counts
        let store_counts = sqlx::query_as::<_, (i64, i64)>(
            r#"
            SELECT
                COUNT(*) FILTER (WHERE NOT unstable) as active,
                COUNT(*) as total
            FROM stores
            "#,
        )
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch store counts")?;

        let total_jobs = batch_stats.1 + batch_stats.2;
        let success_rate = if total_jobs > 0 {
            batch_stats.1 as f64 / total_jobs as f64 * 100.0
        } else {
            0.0
        };

        Ok(SystemStats {
            batches_total: batch_stats.0,
            jobs_success: batch_stats.1,
            jobs_failed: batch_stats.2,
            success_rate,
            stores_active: store_counts.0 as i32,
            stores_total: store_counts.1 as i32,
            last_batch_at: batch_stats.3,
        })
    }

    /// Get user statistics for a period
    pub async fn get_user_stats(&self, days: i32) -> Result<UserStats> {
        let user_stats = sqlx::query_as::<_, (i64, i64, i64)>(
            r#"
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE notifications_enabled = true) as with_notifications,
                COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '1 day' * $1) as active_users
            FROM users
            "#,
        )
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch user stats")?;

        // Get command count for period
        let commands_count = sqlx::query_scalar::<_, i64>(
            r#"
            SELECT COUNT(*) FROM command_log
            WHERE executed_at >= NOW() - INTERVAL '1 day' * $1
            "#,
        )
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .unwrap_or(0);

        Ok(UserStats {
            total: user_stats.0,
            with_notifications: user_stats.1,
            commands_count,
            active_users: user_stats.2,
        })
    }

    /// Get market statistics for a period
    pub async fn get_market_stats(&self, days: i32) -> Result<MarketStats> {
        let market_stats = sqlx::query_as::<_, (i64, i64, Option<i32>, Option<i32>)>(
            r#"
            SELECT
                COUNT(DISTINCT product_id) as products,
                COUNT(*) as prices_collected,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM store_prices
            WHERE scraped_at >= NOW() - INTERVAL '1 day' * $1
              AND available = true
            "#,
        )
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch market stats")?;

        // Get price changes count
        let price_changes = sqlx::query_scalar::<_, i64>(
            r#"
            SELECT COUNT(*) FROM price_change_events
            WHERE detected_at >= NOW() - INTERVAL '1 day' * $1
            "#,
        )
        .bind(days)
        .fetch_one(&self.pool)
        .await
        .unwrap_or(0);

        // Get arbitrage count
        let arbitrage = self.find_arbitrage_opportunities(5.0).await.unwrap_or_default();

        Ok(MarketStats {
            products: market_stats.0,
            prices_collected: market_stats.1,
            price_changes,
            arbitrage_opportunities: arbitrage.len() as i64,
            min_price: market_stats.2,
            max_price: market_stats.3,
        })
    }

    /// Get store rankings by average price
    pub async fn get_store_rankings(&self) -> Result<Vec<StoreRanking>> {
        let rankings = sqlx::query_as::<_, (String, f64, i64)>(
            r#"
            SELECT
                s.name,
                AVG(sp.price)::float8 as avg_price,
                COUNT(*) as prices_count
            FROM stores s
            LEFT JOIN store_prices sp ON s.id = sp.store_id AND sp.available = true
            WHERE NOT s.unstable
            GROUP BY s.id, s.name
            HAVING COUNT(*) > 0
            ORDER BY avg_price ASC
            "#,
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch store rankings")?;

        let min_avg = rankings.first().map(|r| r.1).unwrap_or(0.0);

        Ok(rankings
            .into_iter()
            .enumerate()
            .map(|(i, (name, avg, count))| StoreRanking {
                rank: (i + 1) as i32,
                store_name: name,
                avg_price: avg as i32,
                prices_count: count,
                success_rate: 100.0, // TODO: calculate from jobs
                is_cheapest: (avg - min_avg).abs() < 1.0,
            })
            .collect())
    }

    /// Get comprehensive bot statistics
    pub async fn get_comprehensive_stats(&self, days: i32) -> Result<BotStats> {
        let system = self.get_system_stats(days).await?;
        let users = self.get_user_stats(days).await?;
        let market = self.get_market_stats(days).await?;
        let stores = self.get_store_rankings().await?;
        let top_commands = self.get_command_usage(days).await?;

        Ok(BotStats {
            period_days: days,
            system,
            users,
            market,
            stores,
            top_commands,
        })
    }
}

// ============================================================================
// ARBITRAGE ANALYTICS OPERATIONS (PS-46 Phase 3)
// ============================================================================

impl Database {
    /// Record arbitrage snapshot (calls SQL function)
    ///
    /// Takes a snapshot of current arbitrage opportunities for historical tracking.
    /// Should be called periodically (e.g., hourly) by a scheduler.
    ///
    /// # Arguments
    /// * `min_profit_percent` - Minimum profit percentage to record (default: 5.0)
    ///
    /// # Returns
    /// Number of opportunities recorded
    pub async fn record_arbitrage_snapshot(&self, min_profit_percent: f64) -> Result<i32> {
        let count = sqlx::query_scalar::<_, i32>(
            "SELECT record_arbitrage_snapshot($1)",
        )
        .bind(min_profit_percent)
        .fetch_one(&self.pool)
        .await
        .context("Failed to record arbitrage snapshot")?;

        Ok(count)
    }

    /// Get arbitrage history for a specific product
    ///
    /// Returns daily aggregated arbitrage data for trend analysis.
    ///
    /// # Arguments
    /// * `product_id` - Product to analyze
    /// * `days` - Number of days to look back
    ///
    /// # Returns
    /// Vector of daily arbitrage history records
    pub async fn get_arbitrage_history(
        &self,
        product_id: i64,
        days: i32,
    ) -> Result<Vec<ArbitrageHistoryDaily>> {
        let history = sqlx::query_as::<_, ArbitrageHistoryDaily>(
            "SELECT * FROM get_arbitrage_history($1, $2)",
        )
        .bind(product_id)
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch arbitrage history")?;

        Ok(history)
    }

    /// Get market-wide arbitrage trends
    ///
    /// Returns daily aggregated statistics for all arbitrage opportunities.
    ///
    /// # Arguments
    /// * `days` - Number of days to analyze
    ///
    /// # Returns
    /// Vector of daily trend data
    pub async fn get_arbitrage_trends(&self, days: i32) -> Result<Vec<ArbitrageTrend>> {
        let trends = sqlx::query_as::<_, ArbitrageTrend>(
            "SELECT * FROM get_arbitrage_trends($1)",
        )
        .bind(days)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch arbitrage trends")?;

        Ok(trends)
    }

    /// Get best products for arbitrage
    ///
    /// Returns products with the most frequent arbitrage opportunities.
    ///
    /// # Arguments
    /// * `days` - Number of days to analyze
    /// * `limit` - Maximum number of products to return
    ///
    /// # Returns
    /// Vector of best arbitrage products
    pub async fn get_best_arbitrage_products(
        &self,
        days: i32,
        limit: i32,
    ) -> Result<Vec<BestArbitrageProduct>> {
        let products = sqlx::query_as::<_, BestArbitrageProduct>(
            "SELECT * FROM get_best_arbitrage_products($1, $2)",
        )
        .bind(days)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch best arbitrage products")?;

        Ok(products)
    }

    /// Get high-margin alerts (>20% profit)
    ///
    /// Returns current arbitrage opportunities with high profit margins.
    ///
    /// # Returns
    /// Vector of high-margin alert entries
    pub async fn get_high_margin_alerts(&self) -> Result<Vec<ArbitrageAlertView>> {
        let alerts = sqlx::query_as::<_, ArbitrageAlertView>(
            "SELECT * FROM v_arbitrage_alerts ORDER BY profit_percent DESC LIMIT 50",
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch high-margin alerts")?;

        Ok(alerts)
    }

    /// Get store pair arbitrage performance
    ///
    /// Returns statistics on which store pairs have the best arbitrage potential.
    ///
    /// # Returns
    /// Vector of store pair performance data
    pub async fn get_store_pair_arbitrage(&self) -> Result<Vec<StorePairArbitrage>> {
        let pairs = sqlx::query_as::<_, StorePairArbitrage>(
            "SELECT * FROM v_store_pair_arbitrage ORDER BY avg_profit_percent DESC LIMIT 20",
        )
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch store pair arbitrage")?;

        Ok(pairs)
    }

    /// Add product to user's arbitrage watchlist
    ///
    /// # Arguments
    /// * `user_id` - User's database ID
    /// * `product_id` - Product to watch
    /// * `min_profit_percent` - Minimum profit threshold for notifications
    ///
    /// # Returns
    /// Watchlist entry ID
    pub async fn add_to_arbitrage_watchlist(
        &self,
        user_id: i64,
        product_id: i64,
        min_profit_percent: f64,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO arbitrage_watchlist (user_id, product_id, min_profit_percent)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, product_id)
            DO UPDATE SET min_profit_percent = EXCLUDED.min_profit_percent
            RETURNING id
            "#,
        )
        .bind(user_id)
        .bind(product_id)
        .bind(min_profit_percent)
        .fetch_one(&self.pool)
        .await
        .context("Failed to add to arbitrage watchlist")?;

        Ok(id)
    }

    /// Remove product from user's arbitrage watchlist
    pub async fn remove_from_arbitrage_watchlist(
        &self,
        user_id: i64,
        product_id: i64,
    ) -> Result<bool> {
        let result = sqlx::query(
            "DELETE FROM arbitrage_watchlist WHERE user_id = $1 AND product_id = $2",
        )
        .bind(user_id)
        .bind(product_id)
        .execute(&self.pool)
        .await
        .context("Failed to remove from arbitrage watchlist")?;

        Ok(result.rows_affected() > 0)
    }

    /// Get user's arbitrage watchlist
    pub async fn get_user_arbitrage_watchlist(
        &self,
        user_id: i64,
    ) -> Result<Vec<ArbitrageWatchlist>> {
        let watchlist = sqlx::query_as::<_, ArbitrageWatchlist>(
            "SELECT * FROM arbitrage_watchlist WHERE user_id = $1 ORDER BY created_at DESC",
        )
        .bind(user_id)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch arbitrage watchlist")?;

        Ok(watchlist)
    }

    /// Set user's arbitrage alert threshold
    ///
    /// # Arguments
    /// * `user_id` - User's database ID
    /// * `min_profit_percent` - Minimum profit percentage for alerts
    /// * `product_id` - Optional product filter (None = all products)
    /// * `category` - Optional category filter
    ///
    /// # Returns
    /// Alert configuration ID
    pub async fn set_arbitrage_alert(
        &self,
        user_id: i64,
        min_profit_percent: f64,
        product_id: Option<i64>,
        category: Option<&str>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            r#"
            INSERT INTO arbitrage_alerts (user_id, min_profit_percent, product_id, category)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, product_id)
            DO UPDATE SET
                min_profit_percent = EXCLUDED.min_profit_percent,
                category = EXCLUDED.category,
                updated_at = NOW()
            RETURNING id
            "#,
        )
        .bind(user_id)
        .bind(min_profit_percent)
        .bind(product_id)
        .bind(category)
        .fetch_one(&self.pool)
        .await
        .context("Failed to set arbitrage alert")?;

        Ok(id)
    }

    /// Get user's arbitrage alert configurations
    pub async fn get_user_arbitrage_alerts(&self, user_id: i64) -> Result<Vec<ArbitrageAlert>> {
        let alerts = sqlx::query_as::<_, ArbitrageAlert>(
            "SELECT * FROM arbitrage_alerts WHERE user_id = $1 AND enabled = true ORDER BY created_at DESC",
        )
        .bind(user_id)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch arbitrage alerts")?;

        Ok(alerts)
    }

    /// Delete user's arbitrage alert
    pub async fn delete_arbitrage_alert(&self, user_id: i64, alert_id: i64) -> Result<bool> {
        let result = sqlx::query(
            "DELETE FROM arbitrage_alerts WHERE id = $1 AND user_id = $2",
        )
        .bind(alert_id)
        .bind(user_id)
        .execute(&self.pool)
        .await
        .context("Failed to delete arbitrage alert")?;

        Ok(result.rows_affected() > 0)
    }
}

// ============================================================================
// PRICE ALERT OPERATIONS (PS-47)
// ============================================================================

impl Database {
    /// Subscribe user to price alerts for a product
    ///
    /// Uses SQL function to capture baseline price and currency rates.
    /// Automatically re-enables if already subscribed but disabled.
    ///
    /// # Arguments
    /// * `user_id` - User's database ID
    /// * `product_id` - Product to track
    /// * `source` - Source of subscription ('search', 'price', 'trends', 'compare', 'manual')
    /// * `alert_type` - Type of alert ('any_drop', 'target_price', 'percent_drop')
    /// * `target_price` - Target price for 'target_price' type (optional)
    /// * `min_drop_percent` - Minimum drop percentage to trigger alert
    ///
    /// # Returns
    /// Alert subscription ID
    pub async fn subscribe_to_price_alert(
        &self,
        user_id: i64,
        product_id: i64,
        source: &str,
        alert_type: Option<&str>,
        target_price: Option<i32>,
        min_drop_percent: Option<f64>,
    ) -> Result<i64> {
        let alert_type = alert_type.unwrap_or("any_drop");
        let min_drop_percent = min_drop_percent.unwrap_or(5.0);

        let id = sqlx::query_scalar::<_, i64>(
            "SELECT subscribe_to_price_alert($1, $2, $3, $4, $5, $6)",
        )
        .bind(user_id)
        .bind(product_id)
        .bind(source)
        .bind(alert_type)
        .bind(target_price)
        .bind(min_drop_percent)
        .fetch_one(&self.pool)
        .await
        .context("Failed to subscribe to price alert")?;

        Ok(id)
    }

    /// Unsubscribe user from price alerts for a product
    ///
    /// Sets enabled=false instead of deleting to preserve history.
    ///
    /// # Returns
    /// true if alert was found and disabled
    pub async fn unsubscribe_from_price_alert(
        &self,
        user_id: i64,
        product_id: i64,
    ) -> Result<bool> {
        let result = sqlx::query(
            r#"
            UPDATE user_price_alerts
            SET enabled = false, updated_at = NOW()
            WHERE user_id = $1 AND product_id = $2
            "#,
        )
        .bind(user_id)
        .bind(product_id)
        .execute(&self.pool)
        .await
        .context("Failed to unsubscribe from price alert")?;

        Ok(result.rows_affected() > 0)
    }

    /// Get all active alerts that need checking
    ///
    /// Returns alerts that are enabled, not recently alerted,
    /// and belong to users with notifications enabled.
    ///
    /// # Arguments
    /// * `min_interval_hours` - Minimum hours between alerts for same product
    ///
    /// # Returns
    /// Vector of alerts to check
    pub async fn get_alerts_to_check(
        &self,
        min_interval_hours: i32,
    ) -> Result<Vec<AlertToCheck>> {
        let alerts = sqlx::query_as::<_, AlertToCheck>(
            "SELECT * FROM get_alerts_to_check($1)",
        )
        .bind(min_interval_hours)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch alerts to check")?;

        Ok(alerts)
    }

    /// Get current minimum price for a product
    pub async fn get_product_min_price(&self, product_id: i64) -> Result<Option<i32>> {
        let price = sqlx::query_scalar::<_, i32>(
            "SELECT get_product_min_price($1)",
        )
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to get product min price")?;

        Ok(price)
    }

    /// Analyze price change cause using currency correlation
    ///
    /// # Returns
    /// PriceChangeAnalysis with cause determination
    pub async fn analyze_price_change(
        &self,
        old_price: i32,
        new_price: i32,
        old_usd: Option<f64>,
        new_usd: Option<f64>,
        old_eur: Option<f64>,
        new_eur: Option<f64>,
    ) -> Result<PriceChangeAnalysis> {
        // Calculate price change
        let change_percent = if old_price > 0 {
            ((new_price as f64 - old_price as f64) / old_price as f64) * 100.0
        } else {
            0.0
        };

        // Get cause from SQL function
        let likely_cause: String = sqlx::query_scalar(
            "SELECT analyze_price_change_cause($1, $2, $3, $4, $5, $6)",
        )
        .bind(old_price)
        .bind(new_price)
        .bind(old_usd)
        .bind(new_usd)
        .bind(old_eur)
        .bind(new_eur)
        .fetch_one(&self.pool)
        .await
        .context("Failed to analyze price change cause")?;

        // Calculate currency changes
        let currency_usd_change = match (old_usd, new_usd) {
            (Some(old), Some(new)) if old > 0.0 => Some(((new - old) / old) * 100.0),
            _ => None,
        };

        let currency_eur_change = match (old_eur, new_eur) {
            (Some(old), Some(new)) if old > 0.0 => Some(((new - old) / old) * 100.0),
            _ => None,
        };

        Ok(PriceChangeAnalysis {
            old_price,
            new_price,
            change_percent,
            currency_usd_change,
            currency_eur_change,
            likely_cause,
        })
    }

    /// Get current currency rates
    pub async fn get_current_currency_rates(&self) -> Result<(Option<f64>, Option<f64>)> {
        let usd = sqlx::query_scalar::<_, f64>(
            r#"
            SELECT rate_to_rub FROM currency_rates
            WHERE currency_code = 'USD'
            ORDER BY recorded_at DESC LIMIT 1
            "#,
        )
        .fetch_optional(&self.pool)
        .await
        .context("Failed to get USD rate")?;

        let eur = sqlx::query_scalar::<_, f64>(
            r#"
            SELECT rate_to_rub FROM currency_rates
            WHERE currency_code = 'EUR'
            ORDER BY recorded_at DESC LIMIT 1
            "#,
        )
        .fetch_optional(&self.pool)
        .await
        .context("Failed to get EUR rate")?;

        Ok((usd, eur))
    }

    /// Record sent price alert
    ///
    /// Updates alert record and logs to history.
    pub async fn record_price_alert_sent(
        &self,
        alert_id: i64,
        old_price: i32,
        new_price: i32,
        likely_cause: &str,
    ) -> Result<()> {
        sqlx::query("SELECT record_price_alert_sent($1, $2, $3, $4)")
            .bind(alert_id)
            .bind(old_price)
            .bind(new_price)
            .bind(likely_cause)
            .execute(&self.pool)
            .await
            .context("Failed to record price alert sent")?;

        Ok(())
    }

    /// Get user's price alert subscriptions
    pub async fn get_user_price_alerts(&self, user_id: i64) -> Result<Vec<UserPriceAlert>> {
        let alerts = sqlx::query_as::<_, UserPriceAlert>(
            r#"
            SELECT * FROM user_price_alerts
            WHERE user_id = $1
            ORDER BY created_at DESC
            "#,
        )
        .bind(user_id)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch user price alerts")?;

        Ok(alerts)
    }

    /// Get price alert history for a user
    pub async fn get_price_alert_history(
        &self,
        user_id: i64,
        limit: i32,
    ) -> Result<Vec<PriceAlertLog>> {
        let history = sqlx::query_as::<_, PriceAlertLog>(
            r#"
            SELECT * FROM price_alert_log
            WHERE user_id = $1
            ORDER BY sent_at DESC
            LIMIT $2
            "#,
        )
        .bind(user_id)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch price alert history")?;

        Ok(history)
    }

    /// Get product name by ID
    pub async fn get_product_name(&self, product_id: i64) -> Result<Option<String>> {
        let name = sqlx::query_scalar::<_, String>(
            "SELECT name FROM products WHERE id = $1",
        )
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to get product name")?;

        Ok(name)
    }

    /// Get store name for the cheapest price of a product
    pub async fn get_cheapest_store_for_product(
        &self,
        product_id: i64,
    ) -> Result<Option<(String, i32)>> {
        let result = sqlx::query_as::<_, (String, i32)>(
            r#"
            SELECT s.name, sp.price
            FROM store_prices sp
            JOIN stores s ON sp.store_id = s.id
            WHERE sp.product_id = $1 AND sp.available = true
            ORDER BY sp.price ASC
            LIMIT 1
            "#,
        )
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to get cheapest store")?;

        Ok(result)
    }
}

// ============================================================================
// WISHLIST OPERATIONS (PS-50)
// ============================================================================

impl Database {
    /// Add product to user's wishlist
    ///
    /// If target_price is set, automatically creates a price alert.
    ///
    /// # Arguments
    /// * `user_id` - User's database ID
    /// * `product_id` - Product to add
    /// * `priority` - 1=high, 2=medium, 3=low
    /// * `target_price` - Optional target price in kopecks
    /// * `notes` - Optional user notes
    ///
    /// # Returns
    /// Wishlist item ID
    pub async fn add_to_wishlist(
        &self,
        user_id: i64,
        product_id: i64,
        priority: i16,
        target_price: Option<i32>,
        notes: Option<&str>,
    ) -> Result<i64> {
        let id = sqlx::query_scalar::<_, i64>(
            "SELECT add_to_wishlist($1, $2, $3, $4, $5)",
        )
        .bind(user_id)
        .bind(product_id)
        .bind(priority)
        .bind(target_price)
        .bind(notes)
        .fetch_one(&self.pool)
        .await
        .context("Failed to add to wishlist")?;

        Ok(id)
    }

    /// Remove product from user's wishlist
    ///
    /// Also disables any associated price alert.
    pub async fn remove_from_wishlist(
        &self,
        user_id: i64,
        product_id: i64,
    ) -> Result<bool> {
        // First, disable associated alert
        sqlx::query(
            r#"
            UPDATE user_price_alerts
            SET enabled = false, updated_at = NOW()
            WHERE user_id = $1 AND product_id = $2 AND source = 'wishlist'
            "#,
        )
        .bind(user_id)
        .bind(product_id)
        .execute(&self.pool)
        .await
        .context("Failed to disable wishlist alert")?;

        // Then remove from wishlist
        let result = sqlx::query(
            "DELETE FROM user_wishlist WHERE user_id = $1 AND product_id = $2",
        )
        .bind(user_id)
        .bind(product_id)
        .execute(&self.pool)
        .await
        .context("Failed to remove from wishlist")?;

        Ok(result.rows_affected() > 0)
    }

    /// Get user's wishlist with filtering and sorting
    ///
    /// # Arguments
    /// * `user_id` - User's database ID
    /// * `include_purchased` - Include purchased items
    /// * `priority_filter` - Optional priority filter (1, 2, or 3)
    ///
    /// # Returns
    /// Wishlist items sorted by priority (high first), then by created_at
    pub async fn get_user_wishlist(
        &self,
        user_id: i64,
        include_purchased: bool,
        priority_filter: Option<i16>,
    ) -> Result<Vec<WishlistItemWithProduct>> {
        let items = if let Some(priority) = priority_filter {
            sqlx::query_as::<_, WishlistItemWithProduct>(
                r#"
                SELECT * FROM v_user_wishlist
                WHERE user_id = $1
                  AND ($2 OR purchased = false)
                  AND priority = $3
                ORDER BY priority ASC, created_at DESC
                "#,
            )
            .bind(user_id)
            .bind(include_purchased)
            .bind(priority)
            .fetch_all(&self.pool)
            .await
        } else {
            sqlx::query_as::<_, WishlistItemWithProduct>(
                r#"
                SELECT * FROM v_user_wishlist
                WHERE user_id = $1
                  AND ($2 OR purchased = false)
                ORDER BY priority ASC, created_at DESC
                "#,
            )
            .bind(user_id)
            .bind(include_purchased)
            .fetch_all(&self.pool)
            .await
        };

        items.context("Failed to fetch user wishlist")
    }

    /// Get single wishlist item by ID
    pub async fn get_wishlist_item(
        &self,
        wishlist_id: i64,
    ) -> Result<Option<WishlistItemWithProduct>> {
        let item = sqlx::query_as::<_, WishlistItemWithProduct>(
            "SELECT * FROM v_user_wishlist WHERE wishlist_id = $1",
        )
        .bind(wishlist_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch wishlist item")?;

        Ok(item)
    }

    /// Get wishlist item by user and product
    pub async fn get_wishlist_by_product(
        &self,
        user_id: i64,
        product_id: i64,
    ) -> Result<Option<WishlistItemWithProduct>> {
        let item = sqlx::query_as::<_, WishlistItemWithProduct>(
            "SELECT * FROM v_user_wishlist WHERE user_id = $1 AND product_id = $2",
        )
        .bind(user_id)
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .context("Failed to fetch wishlist item by product")?;

        Ok(item)
    }

    /// Update wishlist item priority
    pub async fn update_wishlist_priority(
        &self,
        wishlist_id: i64,
        priority: i16,
    ) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE user_wishlist
            SET priority = $2, updated_at = NOW()
            WHERE id = $1
            "#,
        )
        .bind(wishlist_id)
        .bind(priority)
        .execute(&self.pool)
        .await
        .context("Failed to update wishlist priority")?;

        Ok(())
    }

    /// Set target price for wishlist item
    ///
    /// Uses database function that handles alert creation/update.
    pub async fn set_wishlist_target_price(
        &self,
        user_id: i64,
        wishlist_id: i64,
        target_price: Option<i32>,
    ) -> Result<()> {
        sqlx::query("SELECT set_wishlist_target_price($1, $2, $3)")
            .bind(user_id)
            .bind(wishlist_id)
            .bind(target_price)
            .execute(&self.pool)
            .await
            .context("Failed to set wishlist target price")?;

        Ok(())
    }

    /// Mark wishlist item as purchased
    pub async fn mark_wishlist_purchased(
        &self,
        wishlist_id: i64,
        price: i32,
        store: &str,
    ) -> Result<()> {
        sqlx::query("SELECT mark_wishlist_purchased($1, $2, $3)")
            .bind(wishlist_id)
            .bind(price)
            .bind(store)
            .execute(&self.pool)
            .await
            .context("Failed to mark as purchased")?;

        Ok(())
    }

    /// Get wishlist statistics for user
    pub async fn get_wishlist_stats(&self, user_id: i64) -> Result<WishlistStats> {
        let stats = sqlx::query_as::<_, WishlistStats>(
            "SELECT * FROM get_wishlist_stats($1)",
        )
        .bind(user_id)
        .fetch_one(&self.pool)
        .await
        .context("Failed to fetch wishlist stats")?;

        Ok(stats)
    }

    /// Check if product is in user's wishlist
    pub async fn is_in_wishlist(
        &self,
        user_id: i64,
        product_id: i64,
    ) -> Result<bool> {
        let exists = sqlx::query_scalar::<_, bool>(
            r#"
            SELECT EXISTS(
                SELECT 1 FROM user_wishlist
                WHERE user_id = $1 AND product_id = $2 AND NOT purchased
            )
            "#,
        )
        .bind(user_id)
        .bind(product_id)
        .fetch_one(&self.pool)
        .await
        .context("Failed to check wishlist")?;

        Ok(exists)
    }

    /// Get purchase history (bought items)
    pub async fn get_purchase_history(
        &self,
        user_id: i64,
        limit: i32,
    ) -> Result<Vec<WishlistItemWithProduct>> {
        let items = sqlx::query_as::<_, WishlistItemWithProduct>(
            r#"
            SELECT * FROM v_user_wishlist
            WHERE user_id = $1 AND purchased = true
            ORDER BY purchased_at DESC
            LIMIT $2
            "#,
        )
        .bind(user_id)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .context("Failed to fetch purchase history")?;

        Ok(items)
    }

    /// Check if price alert is from wishlist source
    pub async fn is_wishlist_alert(&self, alert_id: i64) -> Result<bool> {
        let is_wishlist = sqlx::query_scalar::<_, bool>(
            r#"
            SELECT EXISTS(
                SELECT 1 FROM user_price_alerts
                WHERE id = $1 AND source = 'wishlist'
            )
            "#,
        )
        .bind(alert_id)
        .fetch_one(&self.pool)
        .await
        .context("Failed to check if wishlist alert")?;

        Ok(is_wishlist)
    }
}
