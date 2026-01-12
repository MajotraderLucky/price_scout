//! Wishlist Module for Price Scout Bot
//!
//! PS-50: Wishlist (Delayed Purchases) Feature
//!
//! Provides:
//! - /wishlist command to view wishlist
//! - /wish add/remove/bought subcommands
//! - Inline keyboard management
//! - Integration with price alerts

use anyhow::Result;
use price_scout_db::Database;
use price_scout_models::{WishlistItemWithProduct, WishlistPriority, WishlistStats};
use teloxide::{
    prelude::*,
    types::{ChatId, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode},
};
use tracing::info;

// ============================================================================
// INLINE KEYBOARDS
// ============================================================================

/// Main wishlist keyboard with filters
pub fn wishlist_main_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![
        vec![
            InlineKeyboardButton::callback("Все", "wl_filter_all"),
            InlineKeyboardButton::callback("[!!!]", "wl_filter_1"),
            InlineKeyboardButton::callback("[!!]", "wl_filter_2"),
            InlineKeyboardButton::callback("[!]", "wl_filter_3"),
        ],
        vec![
            InlineKeyboardButton::callback("Актуальные", "wl_active"),
            InlineKeyboardButton::callback("Купленные", "wl_purchased"),
        ],
    ])
}

/// Wishlist item action keyboard
pub fn wishlist_item_keyboard(wishlist_id: i64, product_id: i64) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![
        vec![
            InlineKeyboardButton::callback("Цены", format!("price_{}", product_id)),
            InlineKeyboardButton::callback("Тренды", format!("trends_{}", product_id)),
        ],
        vec![
            InlineKeyboardButton::callback("[!!!]", format!("wl_pri_{}_{}", wishlist_id, 1)),
            InlineKeyboardButton::callback("[!!]", format!("wl_pri_{}_{}", wishlist_id, 2)),
            InlineKeyboardButton::callback("[!]", format!("wl_pri_{}_{}", wishlist_id, 3)),
        ],
        vec![
            InlineKeyboardButton::callback("Цель", format!("wl_target_{}", wishlist_id)),
            InlineKeyboardButton::callback("Купил", format!("wl_bought_{}", wishlist_id)),
        ],
        vec![
            InlineKeyboardButton::callback("Удалить", format!("wl_remove_{}", wishlist_id)),
            InlineKeyboardButton::callback("Назад", "wl_back"),
        ],
    ])
}

/// Add to wishlist keyboard (shown in search results/price view)
pub fn add_to_wishlist_keyboard(product_id: i64) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![vec![InlineKeyboardButton::callback(
        "[+] В wishlist",
        format!("wl_add_{}", product_id),
    )]])
}

/// Priority selection keyboard
#[allow(dead_code)]
pub fn priority_keyboard(wishlist_id: i64) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup::new(vec![vec![
        InlineKeyboardButton::callback("[!!!] Высокий", format!("wl_setpri_{}_{}", wishlist_id, 1)),
        InlineKeyboardButton::callback("[!!] Средний", format!("wl_setpri_{}_{}", wishlist_id, 2)),
        InlineKeyboardButton::callback("[!] Низкий", format!("wl_setpri_{}_{}", wishlist_id, 3)),
    ]])
}

/// Confirm purchase keyboard (select store)
pub fn bought_confirm_keyboard(wishlist_id: i64, stores: &[(String, i32)]) -> InlineKeyboardMarkup {
    let mut rows: Vec<Vec<InlineKeyboardButton>> = stores
        .iter()
        .take(5)
        .map(|(store, price)| {
            let price_rub = *price as f64 / 100.0;
            vec![InlineKeyboardButton::callback(
                format!("{}: {:.0} RUB", store, price_rub),
                format!("wl_confirm_{}_{}_{}", wishlist_id, price, store),
            )]
        })
        .collect();

    rows.push(vec![InlineKeyboardButton::callback("Отмена", "wl_back")]);

    InlineKeyboardMarkup::new(rows)
}

// ============================================================================
// MESSAGE FORMATTING
// ============================================================================

/// Format wishlist for display
pub fn format_wishlist(
    items: &[WishlistItemWithProduct],
    stats: &WishlistStats,
    filter: Option<&str>,
) -> String {
    let filter_label = match filter {
        Some("1") => " (Высокий)",
        Some("2") => " (Средний)",
        Some("3") => " (Низкий)",
        Some("purchased") => " (Купленные)",
        _ => "",
    };

    let mut msg = format!("<b>[*] Список желаний{}</b>\n", filter_label);
    msg.push_str("━━━━━━━━━━━━━━━━━━━━━━━━\n\n");

    if items.is_empty() {
        msg.push_str("Список пуст.\n\n");
        msg.push_str("Добавить: /wish add &lt;id&gt; [цена]\n");
        msg.push_str("Или нажмите [+] В wishlist в результатах поиска\n");
    } else {
        for (i, item) in items.iter().take(10).enumerate() {
            let priority = WishlistPriority::from_i16(item.priority);
            let name = truncate_name(&item.product_name, 25);

            // Status line
            if item.purchased {
                msg.push_str(&format!("{}. <s>{}</s>\n", i + 1, name));
                if let (Some(price), Some(store)) = (&item.purchased_price, &item.purchased_store) {
                    let price_rub = *price as f64 / 100.0;
                    msg.push_str(&format!("   [$] Куплено: {:.0} RUB в {}\n", price_rub, store));
                }
            } else {
                msg.push_str(&format!(
                    "{}. {} <b>{}</b> (ID:{})\n",
                    i + 1,
                    priority.symbol(),
                    name,
                    item.product_id
                ));

                // Current price
                if let Some(current) = item.current_price {
                    let current_rub = current as f64 / 100.0;
                    msg.push_str(&format!("   Сейчас: {:.0} RUB", current_rub));

                    // Target price comparison
                    if let Some(target) = item.target_price {
                        let target_rub = target as f64 / 100.0;
                        if current <= target {
                            msg.push_str(&format!(" [+] (цель: {:.0})", target_rub));
                        } else {
                            msg.push_str(&format!(" (цель: {:.0})", target_rub));
                        }
                    }
                    msg.push('\n');
                }
            }
            msg.push('\n');
        }

        if items.len() > 10 {
            msg.push_str(&format!("<i>... и ещё {}</i>\n\n", items.len() - 10));
        }
    }

    // Stats footer
    msg.push_str("━━━━━━━━━━━━━━━━━━━━━━━━\n");
    msg.push_str(&format!(
        "[i] {} в списке | {} куплено\n",
        stats.active_items, stats.purchased_items
    ));
    if stats.total_spent > 0 {
        let spent_rub = stats.total_spent as f64 / 100.0;
        msg.push_str(&format!("[$] Потрачено: {:.0} RUB\n", spent_rub));
    }

    msg
}

/// Format single wishlist item details
pub fn format_wishlist_item(item: &WishlistItemWithProduct) -> String {
    let priority = WishlistPriority::from_i16(item.priority);

    let mut msg = format!("<b>{} {}</b>\n\n", priority.symbol(), item.product_name);

    if let Some(category) = &item.category {
        msg.push_str(&format!("Категория: {}\n", category));
    }

    msg.push_str(&format!("Приоритет: {}\n", priority.label_ru()));

    if let Some(current) = item.current_price {
        let current_rub = current as f64 / 100.0;
        msg.push_str(&format!("Текущая цена: {:.0} RUB\n", current_rub));
    }

    if let Some(target) = item.target_price {
        let target_rub = target as f64 / 100.0;
        msg.push_str(&format!("Целевая цена: {:.0} RUB\n", target_rub));

        if let Some(current) = item.current_price {
            if current > target {
                let diff = current - target;
                let diff_rub = diff as f64 / 100.0;
                let percent = (diff as f64 / current as f64) * 100.0;
                msg.push_str(&format!("До цели: {:.0} RUB ({:.1}%)\n", diff_rub, percent));
            } else {
                msg.push_str("[+] Цель достигнута!\n");
            }
        }
    }

    if let Some(notes) = &item.notes {
        msg.push_str(&format!("\nЗаметки: {}\n", notes));
    }

    msg.push_str(&format!(
        "\nДобавлено: {}\n",
        item.created_at.format("%Y-%m-%d")
    ));

    msg
}

/// Truncate product name
fn truncate_name(name: &str, max_len: usize) -> String {
    if name.chars().count() <= max_len {
        name.to_string()
    } else {
        format!(
            "{}...",
            name.chars().take(max_len - 3).collect::<String>()
        )
    }
}

// ============================================================================
// COMMAND HANDLERS
// ============================================================================

/// Handle /wishlist command
pub async fn handle_wishlist_command(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
) -> Result<()> {
    let items = db.get_user_wishlist(user_id, false, None).await?;
    let stats = db.get_wishlist_stats(user_id).await?;

    let msg = format_wishlist(&items, &stats, None);

    bot.send_message(chat_id, msg)
        .parse_mode(ParseMode::Html)
        .reply_markup(wishlist_main_keyboard())
        .await?;

    Ok(())
}

/// Handle /wish add <id> [price] command
pub async fn handle_wish_add(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
    product_id: i64,
    target_price: Option<i32>,
) -> Result<()> {
    // Verify product exists
    let product = match db.get_product(product_id).await? {
        Some(p) => p,
        None => {
            bot.send_message(chat_id, "[X] Товар не найден").await?;
            return Ok(());
        }
    };

    // Add to wishlist with medium priority
    let wishlist_id = db
        .add_to_wishlist(
            user_id,
            product_id,
            2, // medium priority
            target_price,
            None,
        )
        .await?;

    let price_msg = target_price
        .map(|p| {
            let p_rub = p as f64 / 100.0;
            format!(" с целевой ценой {:.0} RUB", p_rub)
        })
        .unwrap_or_default();

    let msg = format!(
        "[+] <b>{}</b> добавлен в список желаний{}\n\n/wishlist - посмотреть список",
        product.name, price_msg
    );

    bot.send_message(chat_id, msg)
        .parse_mode(ParseMode::Html)
        .await?;

    info!(
        "[WISHLIST] User {} added product {} to wishlist (id: {})",
        user_id, product_id, wishlist_id
    );

    Ok(())
}

/// Handle /wish remove <id> command
pub async fn handle_wish_remove(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
    product_id: i64,
) -> Result<()> {
    let removed = db.remove_from_wishlist(user_id, product_id).await?;

    let msg = if removed {
        "[+] Товар удален из списка желаний"
    } else {
        "[i] Товар не найден в списке желаний"
    };

    bot.send_message(chat_id, msg).await?;

    Ok(())
}

/// Handle /wish bought <id> command (mark as purchased)
pub async fn handle_wish_bought(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
    product_id: i64,
) -> Result<()> {
    // Find wishlist item
    let item = match db.get_wishlist_by_product(user_id, product_id).await? {
        Some(i) => i,
        None => {
            bot.send_message(chat_id, "[X] Товар не найден в списке желаний")
                .await?;
            return Ok(());
        }
    };

    // Get current prices to show store options
    let prices = db.get_best_prices(product_id, 5).await?;

    if prices.is_empty() {
        // No prices - ask for manual input
        bot.send_message(
            chat_id,
            "Цены не найдены. Введите данные покупки:\n/wish bought_confirm &lt;цена&gt; &lt;магазин&gt;",
        )
        .parse_mode(ParseMode::Html)
        .await?;
    } else {
        // Show store selection
        let mut stores = Vec::new();
        for price in &prices {
            if let Ok(store) = db.get_store(price.store_id).await {
                stores.push((store.name, price.price));
            }
        }

        let msg = format!("Где купили <b>{}</b>?", item.product_name);

        bot.send_message(chat_id, msg)
            .parse_mode(ParseMode::Html)
            .reply_markup(bought_confirm_keyboard(item.wishlist_id, &stores))
            .await?;
    }

    Ok(())
}

// ============================================================================
// CALLBACK HANDLERS
// ============================================================================

/// Handle wishlist-related callbacks
/// Returns true if callback was handled
pub async fn handle_wishlist_callback(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
    data: &str,
) -> Result<bool> {
    match data {
        // Filter callbacks
        "wl_filter_all" | "wl_active" => {
            let items = db.get_user_wishlist(user_id, false, None).await?;
            let stats = db.get_wishlist_stats(user_id).await?;
            let msg = format_wishlist(&items, &stats, None);

            bot.send_message(chat_id, msg)
                .parse_mode(ParseMode::Html)
                .reply_markup(wishlist_main_keyboard())
                .await?;
            return Ok(true);
        }
        "wl_purchased" => {
            let items = db.get_purchase_history(user_id, 20).await?;
            let stats = db.get_wishlist_stats(user_id).await?;
            let msg = format_wishlist(&items, &stats, Some("purchased"));

            bot.send_message(chat_id, msg)
                .parse_mode(ParseMode::Html)
                .reply_markup(wishlist_main_keyboard())
                .await?;
            return Ok(true);
        }
        "wl_back" => {
            let items = db.get_user_wishlist(user_id, false, None).await?;
            let stats = db.get_wishlist_stats(user_id).await?;
            let msg = format_wishlist(&items, &stats, None);

            bot.send_message(chat_id, msg)
                .parse_mode(ParseMode::Html)
                .reply_markup(wishlist_main_keyboard())
                .await?;
            return Ok(true);
        }
        _ => {}
    }

    // Priority filter
    if data.starts_with("wl_filter_") {
        if let Ok(priority) = data[10..].parse::<i16>() {
            let items = db
                .get_user_wishlist(user_id, false, Some(priority))
                .await?;
            let stats = db.get_wishlist_stats(user_id).await?;
            let msg = format_wishlist(&items, &stats, Some(&priority.to_string()));

            bot.send_message(chat_id, msg)
                .parse_mode(ParseMode::Html)
                .reply_markup(wishlist_main_keyboard())
                .await?;
            return Ok(true);
        }
    }

    // Add to wishlist from product view
    if data.starts_with("wl_add_") {
        if let Ok(product_id) = data[7..].parse::<i64>() {
            handle_wish_add(bot, chat_id, db, user_id, product_id, None).await?;
            return Ok(true);
        }
    }

    // Set priority
    if data.starts_with("wl_pri_") {
        let parts: Vec<&str> = data[7..].split('_').collect();
        if parts.len() == 2 {
            if let (Ok(wishlist_id), Ok(priority)) =
                (parts[0].parse::<i64>(), parts[1].parse::<i16>())
            {
                db.update_wishlist_priority(wishlist_id, priority).await?;

                let priority_enum = WishlistPriority::from_i16(priority);
                bot.send_message(
                    chat_id,
                    format!("[+] Приоритет изменён на: {}", priority_enum.label_ru()),
                )
                .await?;
                return Ok(true);
            }
        }
    }

    // Remove from wishlist
    if data.starts_with("wl_remove_") {
        if let Ok(wishlist_id) = data[10..].parse::<i64>() {
            if let Some(item) = db.get_wishlist_item(wishlist_id).await? {
                db.remove_from_wishlist(user_id, item.product_id).await?;
                bot.send_message(chat_id, "[+] Удалено из списка желаний")
                    .await?;

                // Refresh list
                let items = db.get_user_wishlist(user_id, false, None).await?;
                let stats = db.get_wishlist_stats(user_id).await?;
                let msg = format_wishlist(&items, &stats, None);

                bot.send_message(chat_id, msg)
                    .parse_mode(ParseMode::Html)
                    .reply_markup(wishlist_main_keyboard())
                    .await?;
            }
            return Ok(true);
        }
    }

    // Show bought confirmation (select store)
    if data.starts_with("wl_bought_") {
        if let Ok(wishlist_id) = data[10..].parse::<i64>() {
            if let Some(item) = db.get_wishlist_item(wishlist_id).await? {
                let prices = db.get_best_prices(item.product_id, 5).await?;
                let mut stores = Vec::new();
                for price in &prices {
                    if let Ok(store) = db.get_store(price.store_id).await {
                        stores.push((store.name, price.price));
                    }
                }

                if stores.is_empty() {
                    bot.send_message(
                        chat_id,
                        "Введите данные покупки:\n/wish bought_confirm &lt;цена&gt; &lt;магазин&gt;",
                    )
                    .parse_mode(ParseMode::Html)
                    .await?;
                } else {
                    let msg = format!("Где купили <b>{}</b>?", item.product_name);
                    bot.send_message(chat_id, msg)
                        .parse_mode(ParseMode::Html)
                        .reply_markup(bought_confirm_keyboard(wishlist_id, &stores))
                        .await?;
                }
            }
            return Ok(true);
        }
    }

    // Confirm purchase with selected store/price
    // Format: wl_confirm_{wishlist_id}_{price}_{store}
    if data.starts_with("wl_confirm_") {
        let rest = &data[11..];
        // Find first underscore to get wishlist_id
        if let Some(pos1) = rest.find('_') {
            let wishlist_id_str = &rest[..pos1];
            let after_id = &rest[pos1 + 1..];
            // Find second underscore to get price
            if let Some(pos2) = after_id.find('_') {
                let price_str = &after_id[..pos2];
                let store = &after_id[pos2 + 1..];

                if let (Ok(wishlist_id), Ok(price)) =
                    (wishlist_id_str.parse::<i64>(), price_str.parse::<i32>())
                {
                    if let Some(item) = db.get_wishlist_item(wishlist_id).await? {
                        db.mark_wishlist_purchased(wishlist_id, price, store)
                            .await?;

                        let price_rub = price as f64 / 100.0;
                        let msg = format!(
                            "[+] <b>{}</b> отмечен как купленный!\n\nЦена: {:.0} RUB\nМагазин: {}",
                            item.product_name, price_rub, store
                        );

                        bot.send_message(chat_id, msg)
                            .parse_mode(ParseMode::Html)
                            .await?;

                        info!(
                            "[WISHLIST] User {} marked product {} as purchased for {} in {}",
                            user_id, item.product_id, price, store
                        );
                    }
                    return Ok(true);
                }
            }
        }
    }

    // Target price setting - requires text input
    if data.starts_with("wl_target_") {
        if let Ok(wishlist_id) = data[10..].parse::<i64>() {
            bot.send_message(
                chat_id,
                format!(
                    "Введите целевую цену в рублях:\n<code>/wish target {} &lt;цена&gt;</code>",
                    wishlist_id
                ),
            )
            .parse_mode(ParseMode::Html)
            .await?;
            return Ok(true);
        }
    }

    // Show item details
    if data.starts_with("wl_item_") {
        if let Ok(wishlist_id) = data[8..].parse::<i64>() {
            if let Some(item) = db.get_wishlist_item(wishlist_id).await? {
                let msg = format_wishlist_item(&item);
                bot.send_message(chat_id, msg)
                    .parse_mode(ParseMode::Html)
                    .reply_markup(wishlist_item_keyboard(wishlist_id, item.product_id))
                    .await?;
                return Ok(true);
            }
        }
    }

    Ok(false)
}

/// Auto-add to wishlist when viewing product (optional feature)
/// Can be called from price/trends handlers
#[allow(dead_code)]
pub async fn auto_suggest_wishlist(
    bot: &Bot,
    chat_id: ChatId,
    db: &Database,
    user_id: i64,
    product_id: i64,
) -> Result<()> {
    // Check if already in wishlist
    if !db.is_in_wishlist(user_id, product_id).await? {
        // Show add button
        bot.send_message(chat_id, "")
            .reply_markup(add_to_wishlist_keyboard(product_id))
            .await?;
    }
    Ok(())
}
