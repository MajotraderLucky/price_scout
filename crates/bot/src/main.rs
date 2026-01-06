//! Price Scout Telegram Bot
//!
//! Interactive Telegram bot for price tracking and analytics.
//!
//! Features:
//! - Product search
//! - Price comparison across stores
//! - Price trend analysis
//! - ML-based price predictions
//! - Arbitrage opportunities
//! - Price tracking alerts (future)
//!
//! Commands:
//! - /start - Welcome message
//! - /help - Show available commands
//! - /search <query> - Search for products
//! - /price <product_id> - Get current prices for product
//! - /trends <product_id> - Show price trends (7 days)
//! - /predict <product_id> - Get ML price prediction
//! - /arbitrage - Find arbitrage opportunities
//! - /track <product_id> <target_price> - Track product (future)

use anyhow::{Context, Result};
use price_scout_db::Database;
use price_scout_models::{Product, StorePrice, Store};
use serde::{Deserialize, Serialize};
use teloxide::{
    dispatching::{Dispatcher, UpdateFilterExt},
    dptree,
    prelude::*,
    types::{ParseMode, Update},
    utils::command::BotCommands,
};
use tracing::{error, info};

/// Price prediction response from ML model
#[derive(Debug, Serialize, Deserialize)]
struct PricePredictionResponse {
    product_id: i64,
    current_price: Option<i32>,
    predicted_price: i32,
    prediction_horizon_days: i32,
    lower_bound: i32,
    upper_bound: i32,
    confidence: String,
    model_accuracy: ModelAccuracy,
    predicted_at: String,
    model_trained_at: String,
}

/// ML model accuracy metrics
#[derive(Debug, Serialize, Deserialize)]
struct ModelAccuracy {
    r2_score: f64,
    mae_kopecks: f64,
    mae_rub: f64,
}

/// Bot commands
#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "Supported commands:")]
enum Command {
    #[command(description = "Start the bot")]
    Start,
    #[command(description = "Show this help message")]
    Help,
    #[command(description = "Search products: /search <query>")]
    Search(String),
    #[command(description = "Get prices: /price <product_id>")]
    Price(String),
    #[command(description = "Show trends: /trends <product_id> [days]")]
    Trends(String),
    #[command(description = "Predict price: /predict <product_id>")]
    Predict(String),
    #[command(description = "Find arbitrage: /arbitrage [min_profit]")]
    Arbitrage(String),
    #[command(description = "Compare stores: /compare <product_id>")]
    Compare(String),
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt::init();

    // Load environment variables
    dotenv::dotenv().ok();

    info!("🤖 Price Scout Telegram Bot (Standalone Mode)");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Get bot token
    let bot_token = std::env::var("TELOXIDE_TOKEN")
        .or_else(|_| std::env::var("TELEGRAM_BOT_TOKEN"))
        .context("TELEGRAM_BOT_TOKEN environment variable not set")?;

    // Get database URL
    let database_url = std::env::var("DATABASE_URL")
        .context("DATABASE_URL environment variable not set")?;

    info!("📊 Database URL: {}", database_url);

    // Connect to database
    let db = Database::connect(&database_url).await?;

    // Test database connection
    db.ping().await?;
    info!("✅ Database connection OK");

    // Create bot
    let bot = Bot::new(bot_token);

    info!("✅ Bot initialized");
    info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    info!("🚀 Bot is running...");

    // Set up handler with commands and text messages
    let handler = dptree::entry()
        .branch(
            Update::filter_message()
                .filter_command::<Command>()
                .endpoint(handle_command),
        )
        .branch(
            Update::filter_message()
                .endpoint(handle_text_message),
        );

    Dispatcher::builder(bot, handler)
        .dependencies(dptree::deps![db])
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;

    Ok(())
}

/// Handle bot commands (wrapper for Dispatcher)
async fn handle_command(bot: Bot, msg: Message, cmd: Command, db: Database) -> ResponseResult<()> {
    answer(bot, msg, cmd, db).await
}

/// Handle plain text messages (smart search)
async fn handle_text_message(bot: Bot, msg: Message, db: Database) -> ResponseResult<()> {
    let text = match msg.text() {
        Some(t) => t.trim(),
        None => return Ok(()),
    };

    // Ignore short messages and commands
    if text.len() < 3 || text.starts_with('/') {
        return Ok(());
    }

    let chat_id = msg.chat.id;
    info!("Text message received: '{}'", text);

    bot.send_message(chat_id, format!("🔍 Ищу: {}...", text)).await?;

    match db.search_products(text).await {
        Ok(products) => {
            match products.len() {
                0 => {
                    bot.send_message(chat_id, "😕 Товар не найден. Попробуйте другой запрос.")
                        .await?;
                }
                1 => {
                    // Found exactly one product - show full info
                    let product = &products[0];
                    show_full_product_info(&bot, chat_id, product, &db).await?;
                }
                _ => {
                    // Multiple products - show list
                    let response = format_search_results(&products);
                    bot.send_message(chat_id, response)
                        .parse_mode(ParseMode::Html)
                        .await?;
                }
            }
        }
        Err(e) => {
            error!("Database error in text search: {:#}", e);
            bot.send_message(chat_id, "❌ Ошибка поиска. Попробуйте позже.")
                .await?;
        }
    }

    Ok(())
}

/// Show full product information: prices + trends + ML prediction
async fn show_full_product_info(
    bot: &Bot,
    chat_id: ChatId,
    product: &Product,
    db: &Database,
) -> ResponseResult<()> {
    // 1. Get and show prices
    match db.get_best_prices(product.id, 10).await {
        Ok(prices) => {
            let mut price_data = Vec::new();
            for price in prices {
                if let Ok(store) = db.get_store(price.store_id).await {
                    price_data.push((price, store));
                }
            }
            let price_msg = format_price_data(product, &price_data);
            bot.send_message(chat_id, price_msg)
                .parse_mode(ParseMode::Html)
                .await?;
        }
        Err(e) => {
            error!("Failed to get prices: {:#}", e);
            bot.send_message(chat_id, format!("📦 <b>{}</b>\n\n😕 Цены не найдены", product.name))
                .parse_mode(ParseMode::Html)
                .await?;
        }
    }

    // 2. Show price trends (7 days)
    if let Ok(trends) = db.get_price_trends(product.id, 7).await {
        if !trends.is_empty() {
            let trend_msg = format_price_trends(product.id, &trends);
            bot.send_message(chat_id, trend_msg)
                .parse_mode(ParseMode::Html)
                .await?;
        }
    }

    // 3. Show ML prediction
    match call_ml_predictor(product.id).await {
        Ok(prediction) => {
            let pred_msg = format_price_prediction(&prediction);
            bot.send_message(chat_id, pred_msg)
                .parse_mode(ParseMode::Html)
                .await?;
        }
        Err(_) => {
            // ML prediction not available - that's OK, skip silently
        }
    }

    Ok(())
}

/// Call ML predictor Python script
async fn call_ml_predictor(product_id: i64) -> Result<PricePredictionResponse> {
    use tokio::process::Command;

    let output = Command::new("python3")
        .arg("scripts/ml_predictor.py")
        .arg("predict")
        .arg("--product-id")
        .arg(product_id.to_string())
        .arg("--output")
        .arg("json")
        .output()
        .await
        .context("Failed to execute ml_predictor.py")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ML predictor failed: {}", stderr);
    }

    let prediction: PricePredictionResponse = serde_json::from_slice(&output.stdout)
        .context("Failed to parse ML predictor output")?;

    Ok(prediction)
}

/// Handle bot commands
async fn answer(bot: Bot, msg: Message, cmd: Command, db: Database) -> ResponseResult<()> {
    let chat_id = msg.chat.id;

    match cmd {
        Command::Start => {
            bot.send_message(chat_id, format_start_message())
                .parse_mode(ParseMode::Html)
                .await?;
        }

        Command::Help => {
            bot.send_message(chat_id, format_help_message())
                .parse_mode(ParseMode::Html)
                .await?;
        }

        Command::Search(query) => {
            info!("Search command received - query length: {}, query: '{}'", query.len(), query);

            if query.trim().is_empty() {
                bot.send_message(chat_id, "❌ Please provide a search query.\n\nExample: /search MacBook Pro 16")
                    .await?;
                return Ok(());
            }

            bot.send_message(chat_id, format!("🔍 Searching for: {}...", query))
                .await?;

            match db.search_products(&query).await {
                Ok(products) => {
                    if products.is_empty() {
                        bot.send_message(chat_id, format!("😕 No products found for: {}", query))
                            .await?;
                    } else {
                        let response = format_search_results(&products);
                        bot.send_message(chat_id, response)
                            .parse_mode(ParseMode::Html)
                            .await?;
                    }
                }
                Err(e) => {
                    error!("Database error in search: {:#}", e);
                    bot.send_message(chat_id, "❌ Search failed. Please try again.")
                        .await?;
                }
            }
        }

        Command::Price(product_id_str) => {
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("💰 Getting prices for product {}...", product_id))
                        .await?;

                    match db.get_product(product_id).await {
                        Ok(Some(product)) => {
                            match db.get_best_prices(product_id, 10).await {
                                Ok(prices) => {
                                    // Fetch store names for each price
                                    let mut price_data = Vec::new();
                                    for price in prices {
                                        match db.get_store(price.store_id).await {
                                            Ok(store) => {
                                                price_data.push((price, store));
                                            }
                                            Err(e) => {
                                                error!("Failed to fetch store {}: {:#}", price.store_id, e);
                                            }
                                        }
                                    }

                                    let response = format_price_data(&product, &price_data);
                                    bot.send_message(chat_id, response)
                                        .parse_mode(ParseMode::Html)
                                        .await?;
                                }
                                Err(e) => {
                                    error!("Database error getting prices: {:#}", e);
                                    bot.send_message(chat_id, "❌ Failed to get prices. Please try again.")
                                        .await?;
                                }
                            }
                        }
                        Ok(None) => {
                            bot.send_message(chat_id, "❌ Product not found.")
                                .await?;
                        }
                        Err(e) => {
                            error!("Database error: {:#}", e);
                            bot.send_message(chat_id, "❌ Failed to get product. Please try again.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Invalid product ID. Must be a number.\n\nExample: /price 1")
                        .await?;
                }
            }
        }

        Command::Trends(args) => {
            let parts: Vec<&str> = args.trim().split_whitespace().collect();
            if parts.is_empty() {
                bot.send_message(chat_id, "❌ Please provide a product ID.\n\nExample: /trends 1 30")
                    .await?;
                return Ok(());
            }

            match parts[0].parse::<i64>() {
                Ok(product_id) => {
                    let days = parts.get(1)
                        .and_then(|s| s.parse::<i32>().ok())
                        .unwrap_or(7);

                    bot.send_message(chat_id, format!("📈 Getting price trends for product {} ({} days)...", product_id, days))
                        .await?;

                    match db.get_price_trends(product_id, days).await {
                        Ok(trends) => {
                            if trends.is_empty() {
                                bot.send_message(chat_id, format!("😕 No price history found for product {}", product_id))
                                    .await?;
                            } else {
                                let response = format_price_trends(product_id, &trends);
                                bot.send_message(chat_id, response)
                                    .parse_mode(ParseMode::Html)
                                    .await?;
                            }
                        }
                        Err(e) => {
                            error!("Database error getting trends: {:#}", e);
                            bot.send_message(chat_id, "❌ Failed to get trends. Please try again.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Invalid product ID. Must be a number.\n\nExample: /trends 1 30")
                        .await?;
                }
            }
        }

        Command::Predict(product_id_str) => {
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("🔮 Predicting price for product {}...", product_id))
                        .await?;

                    match call_ml_predictor(product_id).await {
                        Ok(prediction) => {
                            let response = format_price_prediction(&prediction);
                            bot.send_message(chat_id, response)
                                .parse_mode(ParseMode::Html)
                                .await?;
                        }
                        Err(e) => {
                            error!("ML prediction failed: {:#}", e);
                            bot.send_message(chat_id, "❌ Prediction failed. ML model needs training first.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Invalid product ID. Must be a number.\n\nExample: /predict 1")
                        .await?;
                }
            }
        }

        Command::Arbitrage(min_profit_str) => {
            let min_profit = min_profit_str.trim()
                .parse::<f64>()
                .unwrap_or(10.0);

            bot.send_message(chat_id, format!("💸 Finding arbitrage opportunities (min {}% profit)...", min_profit))
                .await?;

            match db.find_arbitrage_opportunities(min_profit).await {
                Ok(opportunities) => {
                    if opportunities.is_empty() {
                        bot.send_message(chat_id, format!("😕 No arbitrage opportunities found with {}% min profit", min_profit))
                            .await?;
                    } else {
                        let response = format_arbitrage(&opportunities);
                        bot.send_message(chat_id, response)
                            .parse_mode(ParseMode::Html)
                            .await?;
                    }
                }
                Err(e) => {
                    error!("Database error finding arbitrage: {:#}", e);
                    bot.send_message(chat_id, "❌ Failed to find arbitrage. Please try again.")
                        .await?;
                }
            }
        }

        Command::Compare(product_id_str) => {
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("🏪 Comparing stores for product {}...", product_id))
                        .await?;

                    match db.get_store_comparison(product_id, 30).await {
                        Ok(stores) => {
                            if stores.is_empty() {
                                bot.send_message(chat_id, format!("😕 No store data found for product {}", product_id))
                                    .await?;
                            } else {
                                let response = format_store_comparison(product_id, &stores);
                                bot.send_message(chat_id, response)
                                    .parse_mode(ParseMode::Html)
                                    .await?;
                            }
                        }
                        Err(e) => {
                            error!("Database error comparing stores: {:#}", e);
                            bot.send_message(chat_id, "❌ Failed to compare stores. Please try again.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Invalid product ID. Must be a number.\n\nExample: /compare 1")
                        .await?;
                }
            }
        }
    }

    Ok(())
}

// Message formatting functions

fn format_start_message() -> String {
    r#"👋 <b>Welcome to Price Scout Bot!</b>

I help you track electronics prices across Russian marketplaces and find the best deals.

<b>What I can do:</b>
🔍 Search products
💰 Compare prices across stores
📈 Show price trends and predictions
💸 Find arbitrage opportunities
🏪 Compare store ratings

<b>Quick Start:</b>
Try: /search MacBook Pro 16

Use /help to see all commands.

<b>Powered by</b> Price Scout Analytics Platform
"#.to_string()
}

fn format_help_message() -> String {
    r#"<b>Available Commands:</b>

<b>Basic:</b>
/search &lt;query&gt; - Search for products
/price &lt;id&gt; - Get current prices

<b>Analytics:</b>
/trends &lt;id&gt; [days] - Price trends (default: 7 days)
/predict &lt;id&gt; - ML price prediction (7 days ahead)
/compare &lt;id&gt; - Compare stores by price/availability
/arbitrage [profit%] - Find price differences (default: 10%)

<b>Examples:</b>
/search MacBook Pro 16
/price 1
/trends 1 30
/predict 1
/compare 1
/arbitrage 15

<b>Coming Soon:</b>
/track &lt;id&gt; &lt;price&gt; - Set price alert
/untrack &lt;id&gt; - Remove price alert
/mytracking - View your tracked products
"#.to_string()
}

fn format_search_results(products: &[Product]) -> String {
    let mut response = format!("<b>🔍 Found {} products:</b>\n\n", products.len());

    for product in products.iter().take(10) {
        let category = product.category.as_deref().unwrap_or("Unknown");
        response.push_str(&format!(
            "<b>ID {}:</b> {}\n<i>Category: {}</i>\n\n",
            product.id,
            product.name,
            category
        ));
    }

    if products.len() > 10 {
        response.push_str(&format!("\n<i>... and {} more results</i>\n", products.len() - 10));
    }

    response.push_str("\n💡 <i>Use /price &lt;id&gt; to see prices</i>");

    response
}

fn format_price_data(product: &Product, price_data: &[(StorePrice, Store)]) -> String {
    let mut response = format!(
        "<b>💰 Prices for: {}</b>\n\n",
        product.name
    );

    if price_data.is_empty() {
        response.push_str("😕 No prices found\n");
        return response;
    }

    for (price, store) in price_data {
        let price_rub = price.price as f64 / 100.0;
        let available = if price.available { "[+]" } else { "[X]" };

        response.push_str(&format!(
            "{} <b>{}</b>: {:.0} ₽\n",
            available,
            store.name,
            price_rub
        ));
    }

    // Calculate best price
    if let Some((best_price, best_store)) = price_data.first() {
        let best_price_rub = best_price.price as f64 / 100.0;
        response.push_str(&format!(
            "\n[+] <b>Best price:</b> {:.0} ₽ at {}\n",
            best_price_rub,
            best_store.name
        ));
    }

    response.push_str(&format!("\n💡 <i>Use /trends {} to see price history</i>", product.id));

    response
}

fn format_price_trends(product_id: i64, trends: &[(chrono::NaiveDate, f64, i32, i32, Option<f64>)]) -> String {
    let mut response = format!("<b>📈 Price Trends (Product ID: {})</b>\n\n", product_id);

    if trends.is_empty() {
        response.push_str("😕 No trend data available yet.\n");
        response.push_str("\n<i>Trends require historical data collection.</i>");
        return response;
    }

    for (i, (date, avg_price_kopecks, min_kopecks, max_kopecks, _volatility)) in trends.iter().take(7).enumerate() {
        let avg_price = avg_price_kopecks / 100.0;
        let min_price = *min_kopecks as f64 / 100.0;
        let max_price = *max_kopecks as f64 / 100.0;

        response.push_str(&format!(
            "<b>{}</b>: {:.0} ₽ (range: {:.0}-{:.0})\n",
            date,
            avg_price,
            min_price,
            max_price
        ));

        if i == 0 && trends.len() > 1 {
            // Calculate trend direction
            let prev_price = trends[1].1 / 100.0;
            let change = avg_price - prev_price;
            let change_pct = (change / prev_price) * 100.0;

            let trend_icon = if change > 0.0 { "[^]" } else if change < 0.0 { "[v]" } else { "[-]" };

            response.push_str(&format!(
                "{} <i>{:+.1}% vs yesterday</i>\n",
                trend_icon,
                change_pct
            ));
        }
    }

    response.push_str(&format!("\n💡 <i>Use /predict {} for ML forecast</i>", product_id));

    response
}

fn format_price_prediction(pred: &PricePredictionResponse) -> String {
    let current = pred.current_price.unwrap_or(0) as f64 / 100.0;
    let predicted = pred.predicted_price as f64 / 100.0;
    let lower = pred.lower_bound as f64 / 100.0;
    let upper = pred.upper_bound as f64 / 100.0;

    let change = predicted - current;
    let change_pct = if current > 0.0 {
        (change / current) * 100.0
    } else {
        0.0
    };

    let trend_icon = if change > 0.0 { "[^]" } else if change < 0.0 { "[v]" } else { "[-]" };
    let confidence_icon = match pred.confidence.as_str() {
        "high" => "[+++]",
        "medium" => "[++]",
        _ => "[+]",
    };

    format!(
        r#"<b>[P] Price Prediction (Product ID: {})</b>

<b>Current Price:</b> {:.0} ₽
<b>Predicted (7 days):</b> {:.0} ₽

{} <b>Change:</b> {:+.0} ₽ ({:+.1}%)
{} <b>Confidence:</b> {}

<b>Price Range:</b>
  Low: {:.0} ₽
  High: {:.0} ₽

<b>Model Accuracy:</b>
  R² Score: {:.3}
  MAE: {:.0} ₽

<i>Prediction made: {}</i>
<i>Model trained: {}</i>
"#,
        pred.product_id,
        current,
        predicted,
        trend_icon,
        change,
        change_pct,
        confidence_icon,
        pred.confidence,
        lower,
        upper,
        pred.model_accuracy.r2_score,
        pred.model_accuracy.mae_rub,
        pred.predicted_at,
        pred.model_trained_at,
    )
}

fn format_arbitrage(opportunities: &[(i64, String, String, i64, String, i32, i64, String, i32, i32, f64)]) -> String {
    let mut response = format!("<b>💸 Arbitrage Opportunities</b>\n\n");

    if opportunities.is_empty() {
        response.push_str("😕 No arbitrage opportunities found.\n");
        response.push_str("\n<i>Try lowering the profit threshold: /arbitrage 5</i>");
        return response;
    }

    response.push_str(&format!("<b>Found {} opportunities:</b>\n\n", opportunities.len()));

    for (i, opp) in opportunities.iter().take(5).enumerate() {
        let (_product_id, name, _category, _buy_store_id, buy_store_name, buy_price_kopecks,
             _sell_store_id, sell_store_name, sell_price_kopecks, profit_kopecks, profit_percent) = opp;

        let buy_price = *buy_price_kopecks as f64 / 100.0;
        let sell_price = *sell_price_kopecks as f64 / 100.0;
        let profit = *profit_kopecks as f64 / 100.0;

        response.push_str(&format!(
            "<b>{}. {}</b>\n",
            i + 1,
            name
        ));
        response.push_str(&format!(
            "[<] Buy at <b>{}</b>: {:.0} ₽\n",
            buy_store_name,
            buy_price
        ));
        response.push_str(&format!(
            "[>] Sell at <b>{}</b>: {:.0} ₽\n",
            sell_store_name,
            sell_price
        ));
        response.push_str(&format!(
            "[$$] <b>Profit:</b> {:.0} ₽ ({:.1}%)\n\n",
            profit,
            profit_percent
        ));
    }

    if opportunities.len() > 5 {
        response.push_str(&format!("\n<i>... and {} more opportunities</i>", opportunities.len() - 5));
    }

    response
}

fn format_store_comparison(product_id: i64, stores: &[(String, f64, i64, f64)]) -> String {
    let mut response = format!("<b>🏪 Store Comparison (Product ID: {})</b>\n\n", product_id);

    if stores.is_empty() {
        response.push_str("😕 No store data available.\n");
        return response;
    }

    for (i, (store_name, avg_price_kopecks, update_count, availability_rate)) in stores.iter().enumerate() {
        let avg_price = avg_price_kopecks / 100.0;
        let availability = (availability_rate * 100.0) as i32;

        response.push_str(&format!(
            "{}. <b>{}</b>\n",
            i + 1,
            store_name
        ));
        response.push_str(&format!(
            "   [$] Avg: {:.0} ₽ | [#] Updates: {} | [+] Available: {}%\n\n",
            avg_price,
            update_count,
            availability
        ));
    }

    response.push_str("\n💡 <i>Lower average = better price</i>");
    response.push_str("\n💡 <i>Higher availability = more reliable</i>");

    response
}
