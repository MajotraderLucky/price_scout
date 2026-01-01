#!/bin/bash
#
# DNS-Shop через Firefox + xdotool
#

# Аргумент: прямой URL каталога или "search:запрос"
ARG="${1:-catalog}"
OUTPUT_DIR="/tmp/dns_qute"
OUTPUT_FILE="$OUTPUT_DIR/page.html"

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_FILE"

# Прямые URL каталогов
declare -A CATALOGS=(
    ["macbook-pro"]="https://www.dns-shop.ru/catalog/recipe/b70b01357dbede01/apple-macbook-pro/"
    ["macbook"]="https://www.dns-shop.ru/catalog/recipe/8ddf1df79c19c23d/macbook/"
    ["notebooks"]="https://www.dns-shop.ru/catalog/17a892f816404e77/noutbuki/"
    ["iphone"]="https://www.dns-shop.ru/catalog/recipe/4c7e3a7f7ef9a70e/apple-iphone/"
)

if [[ "$ARG" == search:* ]]; then
    QUERY="${ARG#search:}"
    URL="https://www.dns-shop.ru/search/?q=$(echo "$QUERY" | sed 's/ /+/g')"
    TITLE="Поиск: $QUERY"
elif [[ -n "${CATALOGS[$ARG]}" ]]; then
    URL="${CATALOGS[$ARG]}"
    TITLE="Каталог: $ARG"
elif [[ "$ARG" == http* ]]; then
    URL="$ARG"
    TITLE="URL: $ARG"
else
    # По умолчанию - MacBook Pro
    URL="${CATALOGS[macbook-pro]}"
    TITLE="Каталог: MacBook Pro (default)"
fi

echo "========================================"
echo "DNS-SHOP AUTO (Firefox)"
echo "========================================"
echo "$TITLE"
echo "URL: $URL"
echo ""

# 1. Запускаем Firefox
echo "[1] Запуск Firefox..."
firefox --new-window "$URL" &
FIREFOX_PID=$!
sleep 5

# 2. Ждём загрузки
echo "[2] Ожидание загрузки (20 сек)..."
sleep 20

# 3. Фокусируем окно Firefox
echo "[3] Фокус на Firefox..."
WINDOW_ID=$(xdotool search --pid $FIREFOX_PID 2>/dev/null | head -1)

if [ -z "$WINDOW_ID" ]; then
    WINDOW_ID=$(xdotool search --name "Firefox" 2>/dev/null | head -1)
fi

if [ -z "$WINDOW_ID" ]; then
    WINDOW_ID=$(xdotool search --name "DNS" 2>/dev/null | head -1)
fi

if [ -n "$WINDOW_ID" ]; then
    echo "    Window ID: $WINDOW_ID"
    xdotool windowactivate --sync "$WINDOW_ID"
    sleep 1
else
    echo "[!] Окно Firefox не найдено"
    exit 1
fi

# 4. Сохраняем страницу через Ctrl+S
echo "[4] Ctrl+S для сохранения..."
xdotool key ctrl+s
sleep 2

# 5. В диалоге сохранения вводим путь
echo "[5] Ввод пути: $OUTPUT_FILE"

# Очищаем поле имени файла
xdotool key ctrl+a
sleep 0.2
xdotool type "$OUTPUT_FILE"
sleep 0.5

# Нажимаем Enter для сохранения
xdotool key Return
sleep 3

# 6. Проверяем результат
echo "[6] Проверка..."
if [ -f "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null)
    echo "[+] Сохранено: $OUTPUT_FILE ($SIZE bytes)"

    if [ "$SIZE" -gt 1000 ]; then
        echo ""
        echo "=== Цены на DNS-Shop ==="
        # Пробуем несколько паттернов для извлечения цен
        echo "[Метод 1: data-product-price]"
        grep -oP 'data-product-price="\K\d+' "$OUTPUT_FILE" 2>/dev/null | sort -n | uniq | while read price; do
            if [ "$price" -gt 10000 ]; then
                printf "  %'d ₽\n" "$price"
            fi
        done

        echo "[Метод 2: product-buy__price]"
        grep -oP 'product-buy__price[^>]*>\s*\K[\d\s]+' "$OUTPUT_FILE" 2>/dev/null | tr -d ' ' | sort -n | uniq | while read price; do
            if [ "$price" -gt 10000 ]; then
                printf "  %'d ₽\n" "$price"
            fi
        done

        echo "[Метод 3: lowPrice/highPrice в JSON-LD]"
        grep -oP '"(lowPrice|highPrice)":\s*\K\d+' "$OUTPUT_FILE" 2>/dev/null | sort -n | uniq | while read price; do
            if [ "$price" -gt 10000 ]; then
                printf "  %'d ₽\n" "$price"
            fi
        done
    else
        echo "[!] Файл слишком маленький"
    fi
else
    # Проверяем в Downloads
    echo "[*] Проверяю Downloads..."
    LATEST=$(ls -t ~/Downloads/*.html ~/Загрузки/*.html 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "[+] Найден: $LATEST"
        cp "$LATEST" "$OUTPUT_FILE"
    else
        echo "[!] Файл не создан"
    fi
fi

echo ""
echo "[7] Закрытие Firefox..."
pkill -f "firefox.*dns-shop" 2>/dev/null || true
sleep 1

echo ""
echo "Готово!"
