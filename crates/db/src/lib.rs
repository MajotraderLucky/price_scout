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
                STDDEV(price) as volatility
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
