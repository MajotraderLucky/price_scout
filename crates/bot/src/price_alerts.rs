//! Price Alert Service
//!
//! PS-47: Smart Price Alerts with Currency Correlation Analysis
//!
//! Features:
//! - Automatic subscription when user shows interest in a product
//! - Background alert checker loop (every 30 minutes)
//! - Currency correlation analysis to explain price changes
//! - Inline keyboard for unsubscribe

use anyhow::Result;
use price_scout_db::Database;
use price_scout_models::{AlertToCheck, PriceChangeAnalysis};
use teloxide::{
    prelude::*,
    types::{InlineKeyboardButton, InlineKeyboardMarkup, ParseMode},
};
use tracing::{error, info, warn};

/// Minimum interval between alerts for same product (hours)
const ALERT_MIN_INTERVAL_HOURS: i32 = 6;

/// Check interval (30 minutes)
const CHECK_INTERVAL_SECS: u64 = 30 * 60;

/// Minimum price drop percentage to trigger alert
const MIN_DROP_PERCENT: f64 = 5.0;

/// Price alert checker service
pub struct PriceAlertService {
    bot: Bot,
    db: Database,
}

impl PriceAlertService {
    pub fn new(bot: Bot, db: Database) -> Self {
        Self { bot, db }
    }

    /// Main alert checker loop
    /// Runs every 30 minutes, checks all active alerts
    pub async fn run_loop(&self) {
        info!("[ALERTS] Price alert checker started (interval: {}s)", CHECK_INTERVAL_SECS);

        loop {
            match self.check_all_alerts().await {
                Ok(sent) => {
                    if sent > 0 {
                        info!("[ALERTS] Sent {} price alerts", sent);
                    }
                }
                Err(e) => {
                    error!("[ALERTS] Error checking alerts: {:#}", e);
                }
            }

            tokio::time::sleep(tokio::time::Duration::from_secs(CHECK_INTERVAL_SECS)).await;
        }
    }

    /// Check all active alerts and send notifications
    async fn check_all_alerts(&self) -> Result<i32> {
        let alerts = self.db.get_alerts_to_check(ALERT_MIN_INTERVAL_HOURS).await?;

        if alerts.is_empty() {
            return Ok(0);
        }

        info!("[ALERTS] Checking {} alerts", alerts.len());

        let mut sent_count = 0;

        // Get current currency rates once
        let (current_usd, current_eur) = self.db.get_current_currency_rates().await?;

        for alert in alerts {
            match self.check_single_alert(&alert, current_usd, current_eur).await {
                Ok(true) => sent_count += 1,
                Ok(false) => {} // No alert needed
                Err(e) => {
                    warn!("[ALERTS] Error checking alert {}: {:#}", alert.alert_id, e);
                }
            }
        }

        Ok(sent_count)
    }

    /// Check single alert and send if needed
    /// Returns true if alert was sent
    async fn check_single_alert(
        &self,
        alert: &AlertToCheck,
        current_usd: Option<f64>,
        current_eur: Option<f64>,
    ) -> Result<bool> {
        // Get current minimum price
        let current_price = match self.db.get_product_min_price(alert.product_id).await? {
            Some(p) => p,
            None => return Ok(false), // No price data
        };

        // Check if price dropped enough
        let baseline = alert.baseline_price;
        if current_price >= baseline {
            return Ok(false); // Price not dropped
        }

        let drop_percent = ((baseline - current_price) as f64 / baseline as f64) * 100.0;

        // Check minimum drop threshold
        let threshold = alert.min_drop_percent.unwrap_or(MIN_DROP_PERCENT);
        if drop_percent < threshold {
            return Ok(false); // Drop too small
        }

        // Check target price (if set)
        if let Some(target) = alert.target_price {
            if current_price > target {
                return Ok(false); // Not reached target yet
            }
        }

        // Analyze price change cause
        let analysis = self.db.analyze_price_change(
            baseline,
            current_price,
            alert.baseline_currency_usd,
            current_usd,
            alert.baseline_currency_eur,
            current_eur,
        ).await?;

        // Get product and store info
        let product_name = self.db.get_product_name(alert.product_id).await?
            .unwrap_or_else(|| format!("Товар #{}", alert.product_id));

        let store_info = self.db.get_cheapest_store_for_product(alert.product_id).await?;

        // Send alert
        self.send_price_alert(
            alert.chat_id,
            alert.product_id,
            &product_name,
            store_info.as_ref(),
            baseline,
            current_price,
            &analysis,
        ).await?;

        // Record alert sent
        self.db.record_price_alert_sent(
            alert.alert_id,
            baseline,
            current_price,
            &analysis.likely_cause,
        ).await?;

        Ok(true)
    }

    /// Send price alert message to user
    async fn send_price_alert(
        &self,
        chat_id: i64,
        product_id: i64,
        product_name: &str,
        store_info: Option<&(String, i32)>,
        old_price: i32,
        new_price: i32,
        analysis: &PriceChangeAnalysis,
    ) -> Result<()> {
        let old_rub = old_price as f64 / 100.0;
        let new_rub = new_price as f64 / 100.0;

        // Format store info
        let store_line = match store_info {
            Some((name, _)) => format!("{}: ", name),
            None => String::new(),
        };

        // Format cause analysis
        let cause_text = analysis.cause_description_ru();
        let cause_emoji = match analysis.likely_cause.as_str() {
            "currency" => "[~]", // Currency-driven
            "market" => "[!]",   // Real market drop
            "mixed" => "[?]",    // Mixed factors
            _ => "[?]",
        };

        // Currency change info
        let currency_info = format_currency_changes(analysis);

        let msg = format!(
            r#"<b>[!] Цена снизилась!</b>

<b>{}</b>
{}{:.0} ₽ → <b>{:.0} ₽</b> ({:.1}%)

<b>Анализ причины:</b>
{} {}
{}

💡 <i>/price {} - посмотреть все цены</i>"#,
            product_name,
            store_line,
            old_rub,
            new_rub,
            analysis.change_percent,
            cause_emoji,
            cause_text,
            currency_info,
            product_id,
        );

        // Create keyboard with actions
        let keyboard = InlineKeyboardMarkup::new(vec![
            vec![
                InlineKeyboardButton::callback(
                    "Посмотреть цены",
                    format!("price_{}", product_id),
                ),
                InlineKeyboardButton::callback(
                    "Отписаться",
                    format!("unsub_{}", product_id),
                ),
            ],
        ]);

        self.bot
            .send_message(ChatId(chat_id), msg)
            .parse_mode(ParseMode::Html)
            .reply_markup(keyboard)
            .await?;

        Ok(())
    }
}

/// Format currency change information
fn format_currency_changes(analysis: &PriceChangeAnalysis) -> String {
    let mut lines = Vec::new();

    if let Some(usd_change) = analysis.currency_usd_change {
        if usd_change.abs() > 0.5 {
            let direction = if usd_change > 0.0 { "вырос" } else { "упал" };
            lines.push(format!("[o] USD {} на {:.1}%", direction, usd_change.abs()));
        }
    }

    if let Some(eur_change) = analysis.currency_eur_change {
        if eur_change.abs() > 0.5 {
            let direction = if eur_change > 0.0 { "вырос" } else { "упал" };
            lines.push(format!("[o] EUR {} на {:.1}%", direction, eur_change.abs()));
        }
    }

    if lines.is_empty() {
        String::new()
    } else {
        lines.join("\n")
    }
}

/// Subscribe user to price alerts for a product
/// Called from command handlers when user shows interest
pub async fn auto_subscribe(
    db: &Database,
    user_id: i64,
    product_id: i64,
    source: &str,
) -> Result<()> {
    match db.subscribe_to_price_alert(
        user_id,
        product_id,
        source,
        Some("any_drop"),
        None,
        Some(5.0),
    ).await {
        Ok(alert_id) => {
            info!(
                "[ALERTS] Auto-subscribed user {} to product {} (alert_id: {}, source: {})",
                user_id, product_id, alert_id, source
            );
            Ok(())
        }
        Err(e) => {
            // Log but don't fail - auto-subscribe is optional
            warn!(
                "[ALERTS] Failed to auto-subscribe user {} to product {}: {}",
                user_id, product_id, e
            );
            Ok(())
        }
    }
}

/// Unsubscribe user from price alerts
/// Called from callback handler
pub async fn unsubscribe(
    db: &Database,
    user_id: i64,
    product_id: i64,
) -> Result<bool> {
    let result = db.unsubscribe_from_price_alert(user_id, product_id).await?;

    if result {
        info!(
            "[ALERTS] User {} unsubscribed from product {}",
            user_id, product_id
        );
    } else {
        warn!(
            "[ALERTS] No subscription found for user {} and product {}",
            user_id, product_id
        );
    }

    Ok(result)
}

/// Start the price alert checker loop
pub async fn price_alert_loop(bot: Bot, db: Database) {
    let service = PriceAlertService::new(bot, db);
    service.run_loop().await;
}
