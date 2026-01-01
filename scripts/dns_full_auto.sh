#!/bin/bash
#
# DNS-Shop полная автоматизация
# Запуск: ./dns_full_auto.sh "MacBook Pro 16"
#

QUERY="${1:-MacBook Pro 16}"
OUTPUT_DIR="/tmp/dns_qute"
OUTPUT_FILE="$OUTPUT_DIR/page.html"

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_FILE"

URL="https://www.dns-shop.ru/search/?q=$(echo "$QUERY" | sed 's/ /+/g')"

echo "========================================"
echo "DNS-SHOP AUTO"
echo "========================================"
echo "Запрос: $QUERY"
echo "URL: $URL"
echo ""

# 1. Запускаем qutebrowser
echo "[1] Запуск qutebrowser..."
qutebrowser "$URL" &
QUTE_PID=$!
sleep 3

# 2. Ждём загрузки страницы
echo "[2] Ожидание загрузки (20 сек)..."
sleep 20

# 3. Находим окно и фокусируем
echo "[3] Фокус на qutebrowser..."
WINDOW_ID=$(xdotool search --pid $QUTE_PID 2>/dev/null | head -1)

if [ -z "$WINDOW_ID" ]; then
    # Пробуем по классу
    WINDOW_ID=$(xdotool search --class "qutebrowser" 2>/dev/null | head -1)
fi

if [ -z "$WINDOW_ID" ]; then
    echo "[!] Окно не найдено, пробую по имени..."
    WINDOW_ID=$(xdotool search --name "DNS" 2>/dev/null | head -1)
fi

if [ -n "$WINDOW_ID" ]; then
    echo "    Window ID: $WINDOW_ID"
    xdotool windowactivate --sync "$WINDOW_ID"
    sleep 1
else
    echo "[!] Окно qutebrowser не найдено"
    echo "[*] Кликни на окно qutebrowser вручную и запусти скрипт снова"
    exit 1
fi

# 4. Сохраняем через Greasemonkey скрипт (Ctrl+Shift+S)
echo "[4] Нажимаем Ctrl+Shift+S (greasemonkey save)..."
xdotool key ctrl+shift+s
sleep 3

# 4b. Проверяем Downloads на новые файлы
echo "[4b] Поиск сохранённого файла..."
LATEST_FILE=$(ls -t ~/Downloads/dns_page_*.html ~/Загрузки/dns_page_*.html 2>/dev/null | head -1)

if [ -n "$LATEST_FILE" ] && [ -f "$LATEST_FILE" ]; then
    cp "$LATEST_FILE" "$OUTPUT_FILE"
    echo "[+] Скопирован: $LATEST_FILE -> $OUTPUT_FILE"
else
    echo "[!] Файл не найден в Downloads"

    # Fallback: пробуем стандартное сохранение через Ctrl+S
    echo "[4c] Fallback: Ctrl+S..."
    xdotool key ctrl+s
    sleep 2

    # Вводим путь
    xdotool type "$OUTPUT_FILE"
    sleep 0.3
    xdotool key Return
    sleep 3
fi

# 5. Проверяем результат
echo "[5] Проверка файла..."
if [ -f "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE")
    echo "[+] Сохранено: $OUTPUT_FILE ($SIZE bytes)"

    # Парсим цены
    echo ""
    echo "Цены:"
    grep -oP 'data-product-price="\K\d+' "$OUTPUT_FILE" | sort -n | uniq | head -15 | while read price; do
        printf "  %'d RUB\n" "$price"
    done
else
    echo "[!] Файл не создан"
fi

echo ""
echo "Готово!"
