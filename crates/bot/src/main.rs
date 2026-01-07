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
//! - /top [limit] - Show top popular products
//! - /track <product_id> <target_price> - Track product (future)

mod notifications;

use anyhow::{Context, Result};
use price_scout_db::Database;
use price_scout_models::{Product, ProductPopularity, StorePrice, Store};
use serde::{Deserialize, Serialize};
use teloxide::{
    dispatching::{Dispatcher, UpdateFilterExt},
    dptree,
    prelude::*,
    types::{CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update},
    utils::command::BotCommands,
};
use tracing::{error, info, warn};

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

/// Web search response from Python script
#[derive(Debug, Serialize, Deserialize)]
struct WebSearchResponse {
    query: String,
    results: Vec<WebSearchResult>,
    error: Option<String>,
}

/// Single web search result
#[derive(Debug, Serialize, Deserialize)]
struct WebSearchResult {
    title: String,
    url: String,
    domain: String,
    shop: Option<String>,
    snippet: String,
    prices: Vec<i64>,
}

/// Bot commands
#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "Доступные команды:")]
enum Command {
    #[command(description = "Запустить бота")]
    Start,
    #[command(description = "Показать справку")]
    Help,
    #[command(description = "Поиск товаров: /search <запрос>")]
    Search(String),
    #[command(description = "Цены товара: /price <id>")]
    Price(String),
    #[command(description = "Тренды цен: /trends <id> [дни]")]
    Trends(String),
    #[command(description = "Прогноз цены: /predict <id>")]
    Predict(String),
    #[command(description = "Арбитраж: /arbitrage [мин_профит]")]
    Arbitrage(String),
    #[command(description = "Сравнить магазины: /compare <id>")]
    Compare(String),
    #[command(description = "Веб-поиск: /web <запрос>")]
    Web(String),
    #[command(description = "Топ товаров: /top [лимит]")]
    Top(String),
    #[command(description = "Статистика бота: /stats [период]")]
    Stats(String),
}

// ============================================================================
// INLINE KEYBOARDS
// ============================================================================

/// Клавиатура для команды /stats (период + быстрые команды)
fn stats_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![
        vec![
            InlineKeyboardButton::callback("24 часа", "stats_1"),
            InlineKeyboardButton::callback("7 дней", "stats_7"),
            InlineKeyboardButton::callback("30 дней", "stats_30"),
        ],
        vec![
            InlineKeyboardButton::callback("📊 Цены", "cmd_price"),
            InlineKeyboardButton::callback("📈 Тренды", "cmd_trends"),
            InlineKeyboardButton::callback("💰 Арбитраж", "cmd_arb"),
            InlineKeyboardButton::callback("🏆 Топ", "cmd_top"),
        ],
    ])
}

/// Универсальная клавиатура быстрых команд
fn quick_commands_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![vec![
        InlineKeyboardButton::callback("📊 Цены", "cmd_price"),
        InlineKeyboardButton::callback("📈 Тренды", "cmd_trends"),
        InlineKeyboardButton::callback("💰 Арбитраж", "cmd_arb"),
        InlineKeyboardButton::callback("🏆 Топ", "cmd_top"),
    ]])
}

/// Клавиатура для результатов поиска товара (действия + быстрые команды)
fn product_keyboard(product_id: i64) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![
        vec![
            InlineKeyboardButton::callback("💰 Цены", format!("price_{}", product_id)),
            InlineKeyboardButton::callback("📈 Тренды", format!("trends_{}", product_id)),
            InlineKeyboardButton::callback("🔮 Прогноз", format!("predict_{}", product_id)),
        ],
        vec![
            InlineKeyboardButton::callback("💸 Арбитраж", "cmd_arb"),
            InlineKeyboardButton::callback("🏆 Топ", "cmd_top"),
            InlineKeyboardButton::callback("📊 Статистика", "cmd_stats"),
        ],
    ])
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

    // Start notification poller in background
    let bot_for_notifier = bot.clone();
    let db_for_notifier = db.clone();
    tokio::spawn(async move {
        notifications::notification_poller(bot_for_notifier, db_for_notifier).await;
    });
    info!("✅ Notification poller started");

    // Start daily report scheduler in background
    let bot_for_daily = bot.clone();
    let db_for_daily = db.clone();
    tokio::spawn(async move {
        notifications::daily_report_scheduler(bot_for_daily, db_for_daily).await;
    });
    info!("✅ Daily report scheduler started (09:00 MSK)");

    info!("🚀 Bot is running...");

    // Set up handler with commands, text messages, and callback queries
    let handler = dptree::entry()
        .branch(
            Update::filter_message()
                .filter_command::<Command>()
                .endpoint(handle_command),
        )
        .branch(
            Update::filter_message()
                .endpoint(handle_text_message),
        )
        .branch(
            Update::filter_callback_query()
                .endpoint(handle_callback),
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

/// Handle callback queries from inline keyboard buttons
async fn handle_callback(bot: Bot, q: CallbackQuery, db: Database) -> ResponseResult<()> {
    let data = match &q.data {
        Some(d) => d.as_str(),
        None => {
            bot.answer_callback_query(&q.id).await?;
            return Ok(());
        }
    };

    let chat_id = match q.message.as_ref() {
        Some(msg) => msg.chat().id,
        None => {
            bot.answer_callback_query(&q.id).await?;
            return Ok(());
        }
    };

    // Get user for logging (optional - don't block if it fails)
    let telegram_id = q.from.id.0 as i64;
    let user = db.get_user_by_telegram_id(telegram_id).await.ok().flatten();
    let user_id = user.as_ref().map(|u| u.id);

    match data {
        // Stats period buttons
        "stats_1" => {
            log_command_async(&db, user_id, "stats", Some("1")).await;
            let stats = db.get_comprehensive_stats(1).await;
            match stats {
                Ok(s) => {
                    let msg = format_stats_message(&s);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(stats_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        "stats_7" => {
            log_command_async(&db, user_id, "stats", Some("7")).await;
            let stats = db.get_comprehensive_stats(7).await;
            match stats {
                Ok(s) => {
                    let msg = format_stats_message(&s);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(stats_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        "stats_30" => {
            log_command_async(&db, user_id, "stats", Some("30")).await;
            let stats = db.get_comprehensive_stats(30).await;
            match stats {
                Ok(s) => {
                    let msg = format_stats_message(&s);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(stats_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        // Quick command buttons
        "cmd_price" => {
            bot.send_message(chat_id, "<b>💰 Цены</b>\n\nИспользуйте: /price &lt;id товара&gt;\n\nНапример: /price 1")
                .parse_mode(ParseMode::Html)
                .await?;
        }
        "cmd_trends" => {
            bot.send_message(chat_id, "<b>📈 Тренды</b>\n\nИспользуйте: /trends &lt;id товара&gt;\n\nНапример: /trends 1")
                .parse_mode(ParseMode::Html)
                .await?;
        }
        "cmd_arb" => {
            log_command_async(&db, user_id, "arbitrage", None).await;
            // Execute arbitrage command
            let results = db.find_arbitrage_opportunities(10.0).await;
            match results {
                Ok(opps) if !opps.is_empty() => {
                    let msg = format_arbitrage(&opps);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(quick_commands_keyboard())
                        .await?;
                }
                Ok(_) => {
                    bot.send_message(chat_id, "[i] Арбитражных возможностей не найдено")
                        .reply_markup(quick_commands_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        "cmd_top" => {
            log_command_async(&db, user_id, "top", None).await;
            let products = db.get_top_products(10).await;
            match products {
                Ok(prods) => {
                    let msg = format_top_products(&prods);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(quick_commands_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        "cmd_stats" => {
            log_command_async(&db, user_id, "stats", Some("7")).await;
            let stats = db.get_comprehensive_stats(7).await;
            match stats {
                Ok(s) => {
                    let msg = format_stats_message(&s);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(stats_keyboard())
                        .await?;
                }
                Err(e) => {
                    bot.send_message(chat_id, format!("[X] Ошибка: {}", e)).await?;
                }
            }
        }
        // Product-specific buttons - show command hints
        _ if data.starts_with("price_") => {
            if let Ok(product_id) = data[6..].parse::<i64>() {
                bot.send_message(chat_id, format!("<b>💰 Цены товара #{}</b>\n\nВведите: /price {}", product_id, product_id))
                    .parse_mode(ParseMode::Html)
                    .await?;
            }
        }
        _ if data.starts_with("trends_") => {
            if let Ok(product_id) = data[7..].parse::<i64>() {
                bot.send_message(chat_id, format!("<b>📈 Тренды товара #{}</b>\n\nВведите: /trends {}", product_id, product_id))
                    .parse_mode(ParseMode::Html)
                    .await?;
            }
        }
        _ if data.starts_with("predict_") => {
            if let Ok(product_id) = data[8..].parse::<i64>() {
                bot.send_message(chat_id, format!("<b>🔮 Прогноз товара #{}</b>\n\nВведите: /predict {}", product_id, product_id))
                    .parse_mode(ParseMode::Html)
                    .await?;
            }
        }
        _ => {
            warn!("Unknown callback data: {}", data);
        }
    }

    // Answer callback to remove loading indicator
    bot.answer_callback_query(&q.id).await?;
    Ok(())
}

/// Clean search query from common prefixes and noise
fn clean_search_query(text: &str) -> String {
    let mut result = text.trim().to_string();

    // Remove common emoji prefixes
    let emoji_prefixes = ["🔍", "🌐", "💰", "📈", "😕", "❌"];
    for emoji in emoji_prefixes {
        if result.starts_with(emoji) {
            result = result[emoji.len()..].trim_start().to_string();
        }
    }

    // Remove common text prefixes (case-insensitive) - may need multiple passes
    let prefixes = ["ищу:", "ищу", "найти:", "найти", "поиск:", "поиск", "купить:", "купить"];
    for _ in 0..2 {  // Two passes to handle "🔍 Ищу: Ищу:"
        for prefix in &prefixes {
            if result.to_lowercase().starts_with(prefix) {
                result = result[prefix.len()..].trim_start().to_string();
            }
        }
        // Also check emoji again after text removal
        for emoji in &emoji_prefixes {
            if result.starts_with(*emoji) {
                result = result[emoji.len()..].trim_start().to_string();
            }
        }
    }

    // Remove trailing dots
    result = result.trim_end_matches('.').trim().to_string();

    result
}

/// Handle plain text messages (smart search)
async fn handle_text_message(bot: Bot, msg: Message, db: Database) -> ResponseResult<()> {
    let raw_text = match msg.text() {
        Some(t) => t.trim(),
        None => return Ok(()),
    };

    // Clean the search query
    let text = clean_search_query(raw_text);

    // Ignore short messages and commands
    if text.len() < 3 || raw_text.starts_with('/') {
        return Ok(());
    }

    let chat_id = msg.chat.id;
    info!("Text message received: '{}' -> cleaned: '{}'", raw_text, text);

    bot.send_message(chat_id, format!("🔍 Ищу: {}...", text)).await?;

    match db.search_products(&text).await {
        Ok(products) => {
            match products.len() {
                0 => {
                    // Product not found in DB - try web search
                    bot.send_message(chat_id, "😕 Товар не найден в БД. Ищу в интернете...")
                        .await?;

                    match call_web_search(&text, 15).await {
                        Ok(results) => {
                            let response = format_web_search_results(&results);
                            bot.send_message(chat_id, response)
                                .parse_mode(ParseMode::Html)
                                .await?;
                        }
                        Err(e) => {
                            error!("Web search fallback failed: {:#}", e);
                            bot.send_message(chat_id, "😕 Ничего не найдено.")
                                .await?;
                        }
                    }
                }
                1 => {
                    // Found exactly one product - show full info from DB
                    let product = &products[0];
                    show_full_product_info(&bot, chat_id, product, &db).await?;

                    // Also run web search to find better prices
                    bot.send_message(chat_id, "🌐 Ищу лучшие цены в интернете...")
                        .await?;

                    match call_web_search(&text, 15).await {
                        Ok(results) => {
                            let response = format_web_search_results(&results);
                            bot.send_message(chat_id, response)
                                .parse_mode(ParseMode::Html)
                                .await?;
                        }
                        Err(e) => {
                            error!("Web search failed: {:#}", e);
                            // Silent fail - DB results already shown
                        }
                    }
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

/// Call web search Python script
async fn call_web_search(query: &str, max_results: i32) -> Result<WebSearchResponse> {
    use tokio::process::Command;

    // Use venv Python for duckduckgo-search dependency
    let output = Command::new("venv/bin/python")
        .arg("scripts/web_search.py")
        .arg("search")
        .arg("--query")
        .arg(query)
        .arg("--max-results")
        .arg(max_results.to_string())
        .output()
        .await
        .context("Failed to execute web_search.py")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("Web search failed: {}", stderr);
    }

    let response: WebSearchResponse = serde_json::from_slice(&output.stdout)
        .context("Failed to parse web search output")?;

    Ok(response)
}

/// Log command execution (fire-and-forget)
async fn log_command_async(db: &Database, user_id: Option<i64>, command: &str, args: Option<&str>) {
    if let Err(e) = db.log_command(user_id, command, args).await {
        warn!("Failed to log command: {}", e);
    }
}

/// Handle bot commands
async fn answer(bot: Bot, msg: Message, cmd: Command, db: Database) -> ResponseResult<()> {
    let chat_id = msg.chat.id;
    let user_id = msg.from.as_ref().map(|u| u.id.0 as i64);

    match cmd {
        Command::Start => {
            log_command_async(&db, user_id, "start", None).await;
            // Save user's chat_id for notifications
            if let Some(user) = &msg.from {
                let telegram_id = user.id.0 as i64;
                let username = user.username.as_deref();

                // Upsert user
                if let Err(e) = db.upsert_user(telegram_id, username).await {
                    warn!("Failed to upsert user: {}", e);
                }

                // Update chat_id for notifications
                if let Err(e) = db.update_user_chat_id(telegram_id, chat_id.0).await {
                    warn!("Failed to update chat_id: {}", e);
                } else {
                    info!("Saved chat_id {} for user {}", chat_id.0, telegram_id);
                }
            }

            bot.send_message(chat_id, format_start_message())
                .parse_mode(ParseMode::Html)
                .reply_markup(quick_commands_keyboard())
                .await?;
        }

        Command::Help => {
            log_command_async(&db, user_id, "help", None).await;
            bot.send_message(chat_id, format_help_message())
                .parse_mode(ParseMode::Html)
                .reply_markup(quick_commands_keyboard())
                .await?;
        }

        Command::Search(query) => {
            log_command_async(&db, user_id, "search", Some(&query)).await;
            info!("Search command received - query length: {}, query: '{}'", query.len(), query);

            if query.trim().is_empty() {
                bot.send_message(chat_id, "❌ Укажите поисковый запрос.\n\nПример: /search MacBook Pro 16")
                    .await?;
                return Ok(());
            }

            bot.send_message(chat_id, format!("🔍 Ищу: {}...", query))
                .await?;

            match db.search_products(&query).await {
                Ok(products) => {
                    if products.is_empty() {
                        bot.send_message(chat_id, format!("😕 Ничего не найдено по запросу: {}", query))
                            .await?;
                    } else {
                        let response = format_search_results(&products);
                        bot.send_message(chat_id, response)
                            .parse_mode(ParseMode::Html)
                            .reply_markup(quick_commands_keyboard())
                            .await?;
                    }
                }
                Err(e) => {
                    error!("Database error in search: {:#}", e);
                    bot.send_message(chat_id, "❌ Ошибка поиска. Попробуйте позже.")
                        .await?;
                }
            }
        }

        Command::Price(product_id_str) => {
            log_command_async(&db, user_id, "price", Some(&product_id_str)).await;
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("💰 Получаю цены для товара {}...", product_id))
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
                                        .reply_markup(product_keyboard(product_id))
                                        .await?;
                                }
                                Err(e) => {
                                    error!("Database error getting prices: {:#}", e);
                                    bot.send_message(chat_id, "❌ Не удалось получить цены. Попробуйте позже.")
                                        .await?;
                                }
                            }
                        }
                        Ok(None) => {
                            bot.send_message(chat_id, "❌ Товар не найден.")
                                .await?;
                        }
                        Err(e) => {
                            error!("Database error: {:#}", e);
                            bot.send_message(chat_id, "❌ Ошибка загрузки товара. Попробуйте позже.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Неверный ID товара. Укажите число.\n\nПример: /price 1")
                        .await?;
                }
            }
        }

        Command::Trends(args) => {
            log_command_async(&db, user_id, "trends", Some(&args)).await;
            let parts: Vec<&str> = args.split_whitespace().collect();
            if parts.is_empty() {
                bot.send_message(chat_id, "❌ Укажите ID товара.\n\nПример: /trends 1 30")
                    .await?;
                return Ok(());
            }

            match parts[0].parse::<i64>() {
                Ok(product_id) => {
                    let days = parts.get(1)
                        .and_then(|s| s.parse::<i32>().ok())
                        .unwrap_or(7);

                    bot.send_message(chat_id, format!("📈 Загружаю тренды цен для товара {} ({} дней)...", product_id, days))
                        .await?;

                    match db.get_price_trends(product_id, days).await {
                        Ok(trends) => {
                            if trends.is_empty() {
                                bot.send_message(chat_id, format!("😕 История цен не найдена для товара {}", product_id))
                                    .await?;
                            } else {
                                let response = format_price_trends(product_id, &trends);
                                bot.send_message(chat_id, response)
                                    .parse_mode(ParseMode::Html)
                                    .reply_markup(product_keyboard(product_id))
                                    .await?;
                            }
                        }
                        Err(e) => {
                            error!("Database error getting trends: {:#}", e);
                            bot.send_message(chat_id, "❌ Ошибка загрузки трендов. Попробуйте позже.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Неверный ID товара. Укажите число.\n\nПример: /trends 1 30")
                        .await?;
                }
            }
        }

        Command::Predict(product_id_str) => {
            log_command_async(&db, user_id, "predict", Some(&product_id_str)).await;
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("🔮 Прогнозирую цену для товара {}...", product_id))
                        .await?;

                    match call_ml_predictor(product_id).await {
                        Ok(prediction) => {
                            let response = format_price_prediction(&prediction);
                            bot.send_message(chat_id, response)
                                .parse_mode(ParseMode::Html)
                                .reply_markup(product_keyboard(product_id))
                                .await?;
                        }
                        Err(e) => {
                            error!("ML prediction failed: {:#}", e);
                            bot.send_message(chat_id, "❌ Ошибка прогноза. ML модель требует обучения.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Неверный ID товара. Укажите число.\n\nПример: /predict 1")
                        .await?;
                }
            }
        }

        Command::Arbitrage(min_profit_str) => {
            log_command_async(&db, user_id, "arbitrage", Some(&min_profit_str)).await;
            let min_profit = min_profit_str.trim()
                .parse::<f64>()
                .unwrap_or(10.0);

            bot.send_message(chat_id, format!("💸 Ищу арбитражные возможности (мин. {}% профит)...", min_profit))
                .await?;

            match db.find_arbitrage_opportunities(min_profit).await {
                Ok(opportunities) => {
                    if opportunities.is_empty() {
                        bot.send_message(chat_id, format!("😕 Арбитражные возможности с профитом {}% не найдены", min_profit))
                            .await?;
                    } else {
                        let response = format_arbitrage(&opportunities);
                        bot.send_message(chat_id, response)
                            .parse_mode(ParseMode::Html)
                            .reply_markup(quick_commands_keyboard())
                            .await?;
                    }
                }
                Err(e) => {
                    error!("Database error finding arbitrage: {:#}", e);
                    bot.send_message(chat_id, "❌ Ошибка поиска арбитража. Попробуйте позже.")
                        .await?;
                }
            }
        }

        Command::Compare(product_id_str) => {
            log_command_async(&db, user_id, "compare", Some(&product_id_str)).await;
            match product_id_str.trim().parse::<i64>() {
                Ok(product_id) => {
                    bot.send_message(chat_id, format!("🏪 Сравниваю магазины для товара {}...", product_id))
                        .await?;

                    match db.get_store_comparison(product_id, 30).await {
                        Ok(stores) => {
                            if stores.is_empty() {
                                bot.send_message(chat_id, format!("😕 Данные о магазинах не найдены для товара {}", product_id))
                                    .await?;
                            } else {
                                let response = format_store_comparison(product_id, &stores);
                                bot.send_message(chat_id, response)
                                    .parse_mode(ParseMode::Html)
                                    .reply_markup(product_keyboard(product_id))
                                    .await?;
                            }
                        }
                        Err(e) => {
                            error!("Database error comparing stores: {:#}", e);
                            bot.send_message(chat_id, "❌ Ошибка сравнения магазинов. Попробуйте позже.")
                                .await?;
                        }
                    }
                }
                Err(_) => {
                    bot.send_message(chat_id, "❌ Неверный ID товара. Укажите число.\n\nПример: /compare 1")
                        .await?;
                }
            }
        }

        Command::Web(query) => {
            log_command_async(&db, user_id, "web", Some(&query)).await;
            if query.trim().is_empty() {
                bot.send_message(chat_id, "❌ Укажите запрос.\n\nПример: /web рогатка centershot")
                    .await?;
                return Ok(());
            }

            bot.send_message(chat_id, format!("🌐 Ищу в интернете: {}...", query))
                .await?;

            match call_web_search(&query, 15).await {
                Ok(results) => {
                    let response = format_web_search_results(&results);
                    bot.send_message(chat_id, response)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(quick_commands_keyboard())
                        .await?;
                }
                Err(e) => {
                    error!("Web search failed: {:#}", e);
                    bot.send_message(chat_id, "❌ Ошибка веб-поиска. Попробуйте позже.")
                        .await?;
                }
            }
        }

        Command::Top(limit_str) => {
            log_command_async(&db, user_id, "top", Some(&limit_str)).await;
            let limit = limit_str.trim()
                .parse::<i32>()
                .unwrap_or(10)
                .min(100);

            bot.send_message(chat_id, format!("📊 Загружаю Top {} товаров...", limit))
                .await?;

            match db.get_top_products(limit).await {
                Ok(products) => {
                    if products.is_empty() {
                        bot.send_message(
                            chat_id,
                            "😕 Рейтинг товаров пока не сформирован.\n\n<i>Данные появятся после накопления статистики.</i>"
                        )
                        .parse_mode(ParseMode::Html)
                        .await?;
                    } else {
                        let response = format_top_products(&products);
                        bot.send_message(chat_id, response)
                            .parse_mode(ParseMode::Html)
                            .reply_markup(quick_commands_keyboard())
                            .await?;
                    }
                }
                Err(e) => {
                    error!("Failed to get top products: {:#}", e);
                    bot.send_message(chat_id, "❌ Ошибка загрузки рейтинга. Попробуйте позже.")
                        .await?;
                }
            }
        }

        Command::Stats(period_str) => {
            log_command_async(&db, user_id, "stats", Some(&period_str)).await;
            // Parse period: "7d", "24h", "30d" or just number of days
            let days = parse_period(&period_str).unwrap_or(7);

            bot.send_message(chat_id, format!("[i] Собираю статистику за {} дней...", days))
                .await?;

            match db.get_comprehensive_stats(days).await {
                Ok(stats) => {
                    let response = format_stats_message(&stats);
                    bot.send_message(chat_id, response)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(stats_keyboard())
                        .await?;
                }
                Err(e) => {
                    error!("Failed to get stats: {:#}", e);
                    bot.send_message(chat_id, "[X] Ошибка загрузки статистики. Попробуйте позже.")
                        .await?;
                }
            }
        }
    }

    Ok(())
}

// Message formatting functions

/// Generate compact command hints footer for all messages
fn format_command_hints_footer() -> &'static str {
    "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
     <b>Команды:</b>\n\
     /start /help /search /price /trends\n\
     /predict /arbitrage /compare /web /top"
}

fn format_start_message() -> String {
    format!(r#"👋 <b>Добро пожаловать в Price Scout!</b>

Я помогаю отслеживать цены на электронику в российских магазинах и находить лучшие предложения.

<b>Что я умею:</b>
🔍 Искать товары
💰 Сравнивать цены в магазинах
📈 Показывать тренды и прогнозы цен
💸 Находить арбитражные возможности
🏪 Сравнивать рейтинги магазинов

<b>Быстрый старт:</b>
Попробуйте: /search MacBook Pro 16

Или просто напишите название товара!

<b>Powered by</b> Price Scout Analytics
{}"#,
        format_command_hints_footer()
    )
}

fn format_help_message() -> String {
    format!(r#"<b>Доступные команды:</b>

<b>Основные:</b>
/search &lt;запрос&gt; - Поиск товаров
/price &lt;id&gt; - Цены товара
/web &lt;запрос&gt; - Веб-поиск (DuckDuckGo)

<b>Аналитика:</b>
/trends &lt;id&gt; [дни] - Тренды цен (по умолчанию: 7 дней)
/predict &lt;id&gt; - ML прогноз цены (на 7 дней)
/compare &lt;id&gt; - Сравнение магазинов
/arbitrage [профит%] - Арбитражные возможности (по умолчанию: 10%)
/top [лимит] - Топ популярных товаров (по умолчанию: 10)

<b>Умный поиск:</b>
Просто напишите название товара - бот найдёт в БД и интернете!

<b>Примеры:</b>
/search MacBook Pro 16
/price 1
/web фонарь Fenix
/trends 1 30
/predict 1
/top 20

<b>Скоро:</b>
/track &lt;id&gt; &lt;цена&gt; - Отслеживание цены
{}"#,
        format_command_hints_footer()
    )
}

fn format_search_results(products: &[Product]) -> String {
    let mut response = format!("<b>🔍 Найдено товаров: {}</b>\n\n", products.len());

    for product in products.iter().take(10) {
        let category = product.category.as_deref().unwrap_or("Без категории");
        response.push_str(&format!(
            "<b>ID {}:</b> {}\n<i>Категория: {}</i>\n\n",
            product.id,
            product.name,
            category
        ));
    }

    if products.len() > 10 {
        response.push_str(&format!("\n<i>... и ещё {} результатов</i>\n", products.len() - 10));
    }

    response.push_str("\n💡 <i>/price &lt;id&gt; - посмотреть цены</i>");
    response.push_str(format_command_hints_footer());

    response
}

fn format_price_data(product: &Product, price_data: &[(StorePrice, Store)]) -> String {
    let mut response = format!(
        "<b>💰 Цены на: {}</b>\n\n",
        product.name
    );

    if price_data.is_empty() {
        response.push_str("😕 Цены не найдены\n");
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
            "\n[+] <b>Лучшая цена:</b> {:.0} ₽ в {}\n",
            best_price_rub,
            best_store.name
        ));
    }

    response.push_str(&format!("\n💡 <i>/trends {} - история цен</i>", product.id));
    response.push_str(format_command_hints_footer());

    response
}

fn format_price_trends(product_id: i64, trends: &[(chrono::NaiveDate, f64, i32, i32, Option<f64>)]) -> String {
    let mut response = format!("<b>📈 Тренды цен (Товар ID: {})</b>\n\n", product_id);

    if trends.is_empty() {
        response.push_str("😕 Нет данных о трендах.\n");
        response.push_str("\n<i>Тренды появятся после накопления данных.</i>");
        return response;
    }

    for (i, (date, avg_price_kopecks, min_kopecks, max_kopecks, _volatility)) in trends.iter().take(7).enumerate() {
        let avg_price = avg_price_kopecks / 100.0;
        let min_price = *min_kopecks as f64 / 100.0;
        let max_price = *max_kopecks as f64 / 100.0;

        response.push_str(&format!(
            "<b>{}</b>: {:.0} ₽ (диапазон: {:.0}-{:.0})\n",
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
                "{} <i>{:+.1}% за день</i>\n",
                trend_icon,
                change_pct
            ));
        }
    }

    response.push_str(&format!("\n💡 <i>/predict {} - ML прогноз</i>", product_id));
    response.push_str(format_command_hints_footer());

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
    let confidence_ru = match pred.confidence.as_str() {
        "high" => "высокая",
        "medium" => "средняя",
        _ => "низкая",
    };
    let confidence_icon = match pred.confidence.as_str() {
        "high" => "[+++]",
        "medium" => "[++]",
        _ => "[+]",
    };

    format!(
        r#"<b>🔮 Прогноз цены (Товар ID: {})</b>

<b>Текущая цена:</b> {:.0} ₽
<b>Прогноз (7 дней):</b> {:.0} ₽

{} <b>Изменение:</b> {:+.0} ₽ ({:+.1}%)
{} <b>Уверенность:</b> {}

<b>Диапазон цен:</b>
  Мин: {:.0} ₽
  Макс: {:.0} ₽

<b>Точность модели:</b>
  R² Score: {:.3}
  MAE: {:.0} ₽

<i>Прогноз сделан: {}</i>
<i>Модель обучена: {}</i>
{}"#,
        pred.product_id,
        current,
        predicted,
        trend_icon,
        change,
        change_pct,
        confidence_icon,
        confidence_ru,
        lower,
        upper,
        pred.model_accuracy.r2_score,
        pred.model_accuracy.mae_rub,
        pred.predicted_at,
        pred.model_trained_at,
        format_command_hints_footer(),
    )
}

#[allow(clippy::type_complexity)]
fn format_arbitrage(opportunities: &[(i64, String, String, i64, String, i32, i64, String, i32, i32, f64)]) -> String {
    let mut response = "<b>💸 Арбитражные возможности</b>\n\n".to_string();

    if opportunities.is_empty() {
        response.push_str("😕 Арбитражные возможности не найдены.\n");
        response.push_str("\n<i>Попробуйте снизить порог: /arbitrage 5</i>");
        return response;
    }

    response.push_str(&format!("<b>Найдено {} возможностей:</b>\n\n", opportunities.len()));

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
            "[<] Купить в <b>{}</b>: {:.0} ₽\n",
            buy_store_name,
            buy_price
        ));
        response.push_str(&format!(
            "[>] Продать в <b>{}</b>: {:.0} ₽\n",
            sell_store_name,
            sell_price
        ));
        response.push_str(&format!(
            "[$$] <b>Профит:</b> {:.0} ₽ ({:.1}%)\n\n",
            profit,
            profit_percent
        ));
    }

    if opportunities.len() > 5 {
        response.push_str(&format!("\n<i>... и ещё {} возможностей</i>", opportunities.len() - 5));
    }

    response.push_str(format_command_hints_footer());
    response
}

fn format_store_comparison(product_id: i64, stores: &[(String, f64, i64, f64)]) -> String {
    let mut response = format!("<b>🏪 Сравнение магазинов (Товар ID: {})</b>\n\n", product_id);

    if stores.is_empty() {
        response.push_str("😕 Нет данных о магазинах.\n");
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
            "   [$] Сред: {:.0} ₽ | [#] Обновлений: {} | [+] Наличие: {}%\n\n",
            avg_price,
            update_count,
            availability
        ));
    }

    response.push_str("\n💡 <i>Ниже средняя = лучше цена</i>");
    response.push_str("\n💡 <i>Выше наличие = надёжнее</i>");
    response.push_str(format_command_hints_footer());

    response
}

fn format_web_search_results(response: &WebSearchResponse) -> String {
    let mut msg = format!("<b>🌐 Веб-поиск: {}</b>\n\n", response.query);

    if let Some(err) = &response.error {
        msg.push_str(&format!("❌ Ошибка: {}\n", err));
        return msg;
    }

    // Filter results with prices
    let with_prices: Vec<_> = response.results.iter()
        .filter(|r| !r.prices.is_empty())
        .collect();

    if with_prices.is_empty() {
        msg.push_str("😕 Цены не найдены в результатах поиска.\n\n");

        // Show first few results without prices (with links)
        let other_results: Vec<_> = response.results.iter().take(3).collect();
        if !other_results.is_empty() {
            msg.push_str("<b>Найденные ссылки:</b>\n");
            for (i, result) in other_results.iter().enumerate() {
                let shop = result.shop.as_deref().unwrap_or(&result.domain);
                msg.push_str(&format!(
                    "{}. <a href=\"{}\">{}</a>\n",
                    i + 1,
                    result.url,
                    shop
                ));
            }
        }
    } else {
        msg.push_str(&format!("<b>Найдено {} результатов с ценами:</b>\n\n", with_prices.len()));

        for (i, result) in with_prices.iter().take(5).enumerate() {
            let shop = result.shop.as_deref().unwrap_or(&result.domain);
            let min_price = result.prices.iter().min().unwrap_or(&0);

            msg.push_str(&format!(
                "{}. <b>{}</b>\n   💰 от {} ₽\n   🔗 <a href=\"{}\">{}</a>\n\n",
                i + 1,
                shop,
                min_price,
                result.url,
                result.domain
            ));
        }

        if with_prices.len() > 5 {
            msg.push_str(&format!("<i>... и ещё {} результатов</i>\n", with_prices.len() - 5));
        }
    }

    msg.push_str(format_command_hints_footer());
    msg
}

fn format_top_products(products: &[ProductPopularity]) -> String {
    let mut msg = format!("<b>📊 Top {} популярных товаров</b>\n", products.len());
    msg.push_str("<i>(диапазон 1,000 - 15,000 ₽)</i>\n\n");

    for (i, p) in products.iter().take(10).enumerate() {
        let score = p.popularity_score();
        let category = p.category.as_deref().unwrap_or("—");

        // Price range
        let price_range = match (p.min_price, p.max_price) {
            (Some(min), Some(max)) => format!("{} - {} ₽", min / 100, max / 100),
            (Some(min), None) => format!("от {} ₽", min / 100),
            _ => "—".to_string(),
        };

        // Score breakdown
        let stores = p.store_count.unwrap_or(0);

        msg.push_str(&format!(
            "<b>{}. {}</b>\n",
            i + 1,
            truncate_name(&p.name, 40)
        ));
        msg.push_str(&format!(
            "   📈 Рейтинг: <b>{}</b>/100 | 🏪 {}\n",
            score,
            stores
        ));
        msg.push_str(&format!(
            "   💰 {} | 📁 {}\n",
            price_range,
            category
        ));
        msg.push_str(&format!(
            "   <i>T:{} V:{} A:{} R:{}</i>\n\n",
            p.tracking_score,
            p.volatility_score,
            p.availability_score,
            p.arbitrage_score
        ));
    }

    if products.len() > 10 {
        msg.push_str(&format!("<i>... и ещё {} товаров</i>\n\n", products.len() - 10));
    }

    msg.push_str("<b>Расшифровка баллов:</b>\n");
    msg.push_str("T=отслеживания, V=волатильность,\n");
    msg.push_str("A=наличие, R=арбитраж\n\n");
    msg.push_str("💡 <i>/price &lt;id&gt; для просмотра цен</i>");
    msg.push_str(format_command_hints_footer());

    msg
}

/// Truncate product name to fit in message
fn truncate_name(name: &str, max_len: usize) -> String {
    if name.chars().count() <= max_len {
        name.to_string()
    } else {
        let truncated: String = name.chars().take(max_len - 3).collect();
        format!("{}...", truncated)
    }
}

/// Parse period string like "7d", "24h", "30d" into days
fn parse_period(period: &str) -> Option<i32> {
    let period = period.trim().to_lowercase();

    if period.is_empty() {
        return None;
    }

    // Check for "24h" format
    if period.ends_with('h') {
        let hours: i32 = period.trim_end_matches('h').parse().ok()?;
        return Some((hours + 23) / 24); // Round up to days
    }

    // Check for "7d" format
    if period.ends_with('d') {
        return period.trim_end_matches('d').parse().ok();
    }

    // Try plain number
    period.parse().ok()
}

/// Format comprehensive bot statistics message
fn format_stats_message(stats: &price_scout_models::BotStats) -> String {
    let mut msg = format!(
        "<b>[i] Price Scout - Статистика ({}д)</b>\n",
        stats.period_days
    );
    msg.push_str("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n");

    // System health
    msg.push_str("<b>[SYS] Здоровье системы:</b>\n");
    msg.push_str(&format!(
        "  Скрейпинг: {}/{} ({:.0}%)\n",
        stats.system.jobs_success,
        stats.system.jobs_success + stats.system.jobs_failed,
        stats.system.success_rate
    ));
    msg.push_str(&format!(
        "  Магазины: {}/{} активных\n",
        stats.system.stores_active,
        stats.system.stores_total
    ));
    msg.push_str(&format!("  Батчей: {}\n", stats.system.batches_total));

    if let Some(last) = &stats.system.last_batch_at {
        let time_str = last.format("%H:%M").to_string();
        msg.push_str(&format!("  Последний: {}\n", time_str));
    }

    // Users
    msg.push_str("\n<b>[USR] Пользователи:</b>\n");
    msg.push_str(&format!("  Всего: {}\n", stats.users.total));
    msg.push_str(&format!("  С уведомлениями: {}\n", stats.users.with_notifications));
    msg.push_str(&format!("  Команд за {}д: {}\n", stats.period_days, stats.users.commands_count));

    // Top commands
    if !stats.top_commands.is_empty() {
        let top_cmds: Vec<String> = stats.top_commands.iter()
            .take(3)
            .map(|c| format!("/{} ({})", c.command, c.count))
            .collect();
        msg.push_str(&format!("  Популярные: {}\n", top_cmds.join(", ")));
    }

    // Market
    msg.push_str("\n<b>[MKT] Рынок:</b>\n");
    msg.push_str(&format!("  Товаров: {}\n", stats.market.products));
    msg.push_str(&format!("  Цен собрано: {}\n", stats.market.prices_collected));
    msg.push_str(&format!("  Изменений цен: {}\n", stats.market.price_changes));
    msg.push_str(&format!("  Арбитраж: {} возможностей\n", stats.market.arbitrage_opportunities));

    // Store rankings
    if !stats.stores.is_empty() {
        msg.push_str("\n<b>[TOP] Топ магазинов:</b>\n");
        for store in stats.stores.iter().take(3) {
            let price_k = store.avg_price / 1000;
            let cheapest = if store.is_cheapest { " (мин)" } else { "" };
            msg.push_str(&format!(
                "  {}. {} - {}K{}\n",
                store.rank,
                store.store_name,
                price_k,
                cheapest
            ));
        }
    }

    msg.push_str("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    msg
}
