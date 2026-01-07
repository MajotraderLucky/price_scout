//! Notification Service for Price Scout Bot
//!
//! Sends automated analytics notifications to users after scraping batches complete.

use anyhow::Result;
use chrono::{Datelike, TimeZone, Utc};
use price_scout_db::Database;
use price_scout_models::{BotStats, PriceChangeWithProduct, ScrapingBatch};
use std::time::Duration;
use teloxide::prelude::*;
use teloxide::types::ParseMode;
use tracing::{error, info, warn};

/// Arbitrage opportunity for display
#[derive(Debug)]
pub struct ArbitrageInfo {
    pub product_name: String,
    pub buy_store: String,
    pub buy_price: i32,
    pub sell_store: String,
    pub sell_price: i32,
    pub profit_percent: f64,
}

/// Market statistics for notification
#[derive(Debug, Default)]
#[allow(dead_code)]
pub struct MarketStats {
    pub total_products: i64,
    pub total_prices: i64,
    pub min_price: i32,
    pub max_price: i32,
    pub stores_working: i32,  // TODO: populate in get_market_stats
    pub stores_failed: i32,   // TODO: populate in get_market_stats
}

/// Notification service for sending analytics updates
pub struct NotificationService {
    bot: Bot,
    db: Database,
}

impl NotificationService {
    /// Create new notification service
    pub fn new(bot: Bot, db: Database) -> Self {
        Self { bot, db }
    }

    /// Get market statistics
    async fn get_market_stats(&self) -> MarketStats {
        // Get overview from last 24 hours
        match self.db.get_market_overview(0, i32::MAX, 1).await {
            Ok((products, _avg, min, max, total)) => MarketStats {
                total_products: products,
                total_prices: total,
                min_price: min,
                max_price: max,
                ..Default::default()
            },
            Err(_) => MarketStats::default(),
        }
    }

    /// Get top arbitrage opportunities
    async fn get_top_arbitrage(&self, limit: usize) -> Vec<ArbitrageInfo> {
        match self.db.find_arbitrage_opportunities(5.0).await {
            Ok(opps) => opps
                .into_iter()
                .take(limit)
                .map(|(_, name, _, _, buy_store, buy_price, _, sell_store, sell_price, _, profit_pct)| {
                    ArbitrageInfo {
                        product_name: name,
                        buy_store,
                        buy_price,
                        sell_store,
                        sell_price,
                        profit_percent: profit_pct,
                    }
                })
                .collect(),
            Err(_) => vec![],
        }
    }

    /// Send batch completion notification to all users
    pub async fn notify_batch_complete(
        &self,
        batch: &ScrapingBatch,
        price_changes: &[PriceChangeWithProduct],
        _arbitrage_count: i32,
    ) -> Result<()> {
        let recipients = self.db.get_notification_recipients().await?;

        if recipients.is_empty() {
            info!("No notification recipients found");
            return Ok(());
        }

        // Gather additional statistics
        let market_stats = self.get_market_stats().await;
        let top_arbitrage = self.get_top_arbitrage(3).await;

        let message = self.format_batch_notification_v2(batch, price_changes, &market_stats, &top_arbitrage);

        info!(
            "Sending notification to {} users for batch {}",
            recipients.len(),
            batch.id
        );

        let mut success_count = 0;
        let mut fail_count = 0;

        for user in &recipients {
            if let Some(chat_id) = user.chat_id {
                match self
                    .bot
                    .send_message(ChatId(chat_id), &message)
                    .parse_mode(ParseMode::Html)
                    .await
                {
                    Ok(_) => {
                        success_count += 1;
                        // Log notification
                        if let Err(e) = self
                            .db
                            .log_notification(user.id, Some(batch.id), "batch_complete")
                            .await
                        {
                            warn!("Failed to log notification: {}", e);
                        }
                    }
                    Err(e) => {
                        fail_count += 1;
                        warn!(
                            "Failed to send notification to user {} (chat_id: {}): {}",
                            user.telegram_id, chat_id, e
                        );
                    }
                }

                // Rate limiting - 30 messages per second max for Telegram
                tokio::time::sleep(Duration::from_millis(50)).await;
            }
        }

        info!(
            "Notification sent: {} success, {} failed",
            success_count, fail_count
        );

        Ok(())
    }

    /// Format batch completion notification message (v2 - detailed)
    fn format_batch_notification_v2(
        &self,
        batch: &ScrapingBatch,
        price_changes: &[PriceChangeWithProduct],
        stats: &MarketStats,
        arbitrage: &[ArbitrageInfo],
    ) -> String {
        let mut msg = String::from("<b>[!] Price Scout - Отчёт</b>\n\n");

        // Scraping results
        let total_jobs = batch.jobs_success + batch.jobs_failed;
        let success_rate = if total_jobs > 0 {
            (batch.jobs_success as f64 / total_jobs as f64 * 100.0) as i32
        } else {
            0
        };

        msg.push_str("<b>Сбор данных:</b>\n");
        msg.push_str(&format!(
            "  [+] Успешно: {}/{} ({}%)\n",
            batch.jobs_success, total_jobs, success_rate
        ));
        if batch.jobs_failed > 0 {
            msg.push_str(&format!("  [X] Ошибок: {}\n", batch.jobs_failed));
        }

        // Market overview
        if stats.total_products > 0 {
            msg.push_str("\n<b>Рынок:</b>\n");
            msg.push_str(&format!("  Товаров: {}\n", stats.total_products));
            msg.push_str(&format!("  Цен: {}\n", stats.total_prices));
            if stats.min_price > 0 && stats.max_price > 0 {
                msg.push_str(&format!(
                    "  Диапазон: {} - {} руб\n",
                    format_price_short(stats.min_price),
                    format_price_short(stats.max_price)
                ));
            }
        }

        // Price changes section
        if !price_changes.is_empty() {
            msg.push_str(&format!(
                "\n<b>Изменения цен ({}):</b>\n",
                price_changes.len()
            ));

            for (i, change) in price_changes.iter().take(3).enumerate() {
                let icon = if change.change_percent < 0.0 { "[v]" } else { "[^]" };
                let name = truncate(&change.product_name, 20);
                msg.push_str(&format!(
                    "  {}. {} {}: {:+.1}%\n",
                    i + 1,
                    icon,
                    name,
                    change.change_percent
                ));
            }

            if price_changes.len() > 3 {
                msg.push_str(&format!(
                    "  <i>... ещё {}</i>\n",
                    price_changes.len() - 3
                ));
            }
        }

        // Arbitrage opportunities - the highlight!
        if !arbitrage.is_empty() {
            msg.push_str(&format!(
                "\n<b>[$$] Арбитраж ({}):</b>\n",
                arbitrage.len()
            ));

            for opp in arbitrage.iter().take(3) {
                let name = truncate(&opp.product_name, 18);
                msg.push_str(&format!(
                    "  <b>{}</b>\n",
                    name
                ));
                msg.push_str(&format!(
                    "    {} {} -> {} {}\n",
                    format_price_short(opp.buy_price),
                    opp.buy_store,
                    format_price_short(opp.sell_price),
                    opp.sell_store
                ));
                msg.push_str(&format!(
                    "    Профит: <b>+{:.0}%</b>\n",
                    opp.profit_percent
                ));
            }

            msg.push_str("\n/arbitrage - все возможности\n");
        } else {
            msg.push_str("\n<i>Арбитражных возможностей нет</i>\n");
        }

        // Footer with quick commands
        msg.push_str("\n━━━━━━━━━━━━━━━━━━━━━━━━\n");
        msg.push_str("/price /trends /predict /top");

        msg
    }

    /// Format batch completion notification message (legacy)
    #[allow(dead_code)]
    fn format_batch_notification(
        &self,
        batch: &ScrapingBatch,
        price_changes: &[PriceChangeWithProduct],
        arbitrage_count: i32,
    ) -> String {
        let mut msg = String::from("<b>[!] Price Scout Analytics Update</b>\n\n");

        // Summary section
        msg.push_str("<b>Summary:</b>\n");
        msg.push_str(&format!("[+] Updated: {} products\n", batch.jobs_success));
        if batch.jobs_failed > 0 {
            msg.push_str(&format!("[X] Failed: {} products\n", batch.jobs_failed));
        }

        // Price changes section
        if !price_changes.is_empty() {
            msg.push_str(&format!(
                "\n<b>Price Changes ({}):</b>\n",
                price_changes.len()
            ));

            for (i, change) in price_changes.iter().take(5).enumerate() {
                let icon = if change.change_percent < 0.0 {
                    "[v]"
                } else {
                    "[^]"
                };
                let name = truncate(&change.product_name, 25);
                msg.push_str(&format!(
                    "{}. {} {}: {:+.1}%\n",
                    i + 1,
                    icon,
                    name,
                    change.change_percent
                ));
            }

            if price_changes.len() > 5 {
                msg.push_str(&format!(
                    "<i>... and {} more</i>\n",
                    price_changes.len() - 5
                ));
            }
        }

        // Arbitrage opportunities
        if arbitrage_count > 0 {
            msg.push_str(&format!(
                "\n<b>[$$] Arbitrage:</b> {} opportunities found!\n",
                arbitrage_count
            ));
            msg.push_str("Use /arbitrage to see details\n");
        }

        // Footer with command hints
        msg.push_str(format_command_hints_footer());

        msg
    }
}

/// Format price in short form (e.g., "107K" or "1.2M")
fn format_price_short(price: i32) -> String {
    if price >= 1_000_000 {
        format!("{:.1}M", price as f64 / 1_000_000.0)
    } else if price >= 1_000 {
        format!("{}K", price / 1_000)
    } else {
        format!("{}", price)
    }
}

/// Truncate string to max length
fn truncate(s: &str, max_len: usize) -> String {
    if s.chars().count() <= max_len {
        s.to_string()
    } else {
        format!("{}...", s.chars().take(max_len - 3).collect::<String>())
    }
}

/// Command hints footer (same as in main.rs)
fn format_command_hints_footer() -> &'static str {
    "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
     <b>Commands:</b>\n\
     /start /help /search /price /trends\n\
     /predict /arbitrage /compare /web /top"
}

/// Background task for polling and sending notifications
pub async fn notification_poller(bot: Bot, db: Database) {
    let service = NotificationService::new(bot, db.clone());

    info!("Notification poller started");

    loop {
        // Check for unnotified batches
        match db.get_unnotified_batches().await {
            Ok(batches) => {
                for batch in batches {
                    info!("Processing unnotified batch {}", batch.id);

                    // Get price changes for this batch
                    let price_changes = db
                        .get_batch_price_changes(batch.id)
                        .await
                        .unwrap_or_default();

                    // Get arbitrage count
                    let arbitrage_count = db
                        .find_arbitrage_opportunities(10.0)
                        .await
                        .map(|v| v.len() as i32)
                        .unwrap_or(0);

                    // Send notifications
                    if let Err(e) = service
                        .notify_batch_complete(&batch, &price_changes, arbitrage_count)
                        .await
                    {
                        error!("Notification failed for batch {}: {}", batch.id, e);
                    }

                    // Mark batch as notified
                    if let Err(e) = db.mark_batch_notified(batch.id).await {
                        error!("Failed to mark batch {} as notified: {}", batch.id, e);
                    }
                }
            }
            Err(e) => {
                warn!("Failed to check for notifications: {}", e);
            }
        }

        // Poll every 5 minutes
        tokio::time::sleep(Duration::from_secs(300)).await;
    }
}

/// Background task for sending daily reports at 09:00 MSK (06:00 UTC)
pub async fn daily_report_scheduler(bot: Bot, db: Database) {
    info!("Daily report scheduler started (09:00 MSK)");

    loop {
        // Calculate time until next 06:00 UTC (09:00 MSK)
        let wait_duration = calculate_wait_until_target_hour(6, 0);

        info!(
            "Next daily report in {} hours {} minutes",
            wait_duration.as_secs() / 3600,
            (wait_duration.as_secs() % 3600) / 60
        );

        tokio::time::sleep(wait_duration).await;

        // Send daily report
        if let Err(e) = send_daily_report(&bot, &db).await {
            error!("Failed to send daily report: {}", e);
        }

        // Wait a bit to avoid double-triggering
        tokio::time::sleep(Duration::from_secs(60)).await;
    }
}

/// Calculate duration until target time (next occurrence)
fn calculate_wait_until_target_hour(target_hour: u32, target_minute: u32) -> Duration {
    let now = Utc::now();
    let today_target = Utc
        .with_ymd_and_hms(
            now.year(),
            now.month(),
            now.day(),
            target_hour,
            target_minute,
            0,
        )
        .unwrap();

    let target = if now < today_target {
        today_target
    } else {
        // Tomorrow
        today_target + chrono::Duration::days(1)
    };

    let diff = target - now;
    Duration::from_secs(diff.num_seconds().max(0) as u64)
}

/// Send daily report to all users with notifications enabled
async fn send_daily_report(bot: &Bot, db: &Database) -> Result<()> {
    info!("Generating daily report...");

    // Get 24-hour statistics
    let stats = db.get_comprehensive_stats(1).await?;
    let recipients = db.get_notification_recipients().await?;

    if recipients.is_empty() {
        info!("No recipients for daily report");
        return Ok(());
    }

    let message = format_daily_report(&stats);

    info!("Sending daily report to {} users", recipients.len());

    let mut success_count = 0;
    let mut fail_count = 0;

    for user in &recipients {
        if let Some(chat_id) = user.chat_id {
            match bot
                .send_message(ChatId(chat_id), &message)
                .parse_mode(ParseMode::Html)
                .await
            {
                Ok(_) => {
                    success_count += 1;
                    // Log notification
                    if let Err(e) = db.log_notification(user.id, None, "daily_report").await {
                        warn!("Failed to log notification: {}", e);
                    }
                }
                Err(e) => {
                    fail_count += 1;
                    warn!(
                        "Failed to send daily report to user {} (chat_id: {}): {}",
                        user.telegram_id, chat_id, e
                    );
                }
            }

            // Rate limiting
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
    }

    info!(
        "Daily report sent: {} success, {} failed",
        success_count, fail_count
    );

    Ok(())
}

/// Format daily report message
fn format_daily_report(stats: &BotStats) -> String {
    let now = Utc::now();
    let date_str = now.format("%Y-%m-%d").to_string();

    let mut msg = String::from("<b>[!] Price Scout - Дневной отчёт</b>\n");
    msg.push_str("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    msg.push_str(&format!("Дата: {}\n\n", date_str));

    // System stats for 24h
    msg.push_str("<b>[SYS] За 24 часа:</b>\n");
    msg.push_str(&format!("  Батчей: {}\n", stats.system.batches_total));
    msg.push_str(&format!("  Успешно: {:.0}%\n", stats.system.success_rate));
    msg.push_str(&format!(
        "  Новых цен: {}\n",
        stats.system.jobs_success
    ));

    // Market movement
    msg.push_str("\n<b>[MKT] Движение рынка:</b>\n");
    msg.push_str(&format!("  Товаров: {}\n", stats.market.products));
    msg.push_str(&format!("  Изменений цен: {}\n", stats.market.price_changes));

    // Price range
    if let (Some(min), Some(max)) = (stats.market.min_price, stats.market.max_price) {
        msg.push_str(&format!(
            "  Диапазон: {} - {} руб\n",
            format_price_short(min),
            format_price_short(max)
        ));
    }

    // Arbitrage
    if stats.market.arbitrage_opportunities > 0 {
        msg.push_str(&format!(
            "\n<b>[$$] Арбитраж дня:</b>\n  {} возможностей\n",
            stats.market.arbitrage_opportunities
        ));
        msg.push_str("  /arbitrage - подробнее\n");
    }

    // Store rankings
    if !stats.stores.is_empty() {
        msg.push_str("\n<b>[TOP] Магазины:</b>\n");
        for store in stats.stores.iter().take(3) {
            let price_k = store.avg_price / 1000;
            let cheapest = if store.is_cheapest { " [мин]" } else { "" };
            msg.push_str(&format!(
                "  {}. {} - {}K{}\n",
                store.rank, store.store_name, price_k, cheapest
            ));
        }
    }

    // Footer
    msg.push_str("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    msg.push_str("/stats | /price | /arbitrage");

    msg
}
