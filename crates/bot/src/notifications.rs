//! Notification Service for Price Scout Bot
//!
//! Sends automated analytics notifications to users after scraping batches complete.

use anyhow::Result;
use price_scout_db::Database;
use price_scout_models::{PriceChangeWithProduct, ScrapingBatch};
use std::time::Duration;
use teloxide::prelude::*;
use teloxide::types::ParseMode;
use tracing::{error, info, warn};

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

    /// Send batch completion notification to all users
    pub async fn notify_batch_complete(
        &self,
        batch: &ScrapingBatch,
        price_changes: &[PriceChangeWithProduct],
        arbitrage_count: i32,
    ) -> Result<()> {
        let recipients = self.db.get_notification_recipients().await?;

        if recipients.is_empty() {
            info!("No notification recipients found");
            return Ok(());
        }

        let message = self.format_batch_notification(batch, price_changes, arbitrage_count);

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

    /// Format batch completion notification message
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
