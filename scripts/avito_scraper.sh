#!/bin/bash
#
# Avito Scraper
# Firefox + xdotool метод для обхода rate limiting
#

set -e

# Конфигурация
QUERY="${1:-macbook-pro-16}"
OUTPUT_DIR="${2:-/tmp/avito_scraper}"
TIMEOUT_LOAD=30
TIMEOUT_SAVE=5

# Каталоги Avito
declare -A CATALOGS=(
    ["macbook-pro-16"]="https://www.avito.ru/rossiya/noutbuki?q=MacBook+Pro+16"
    ["macbook-air"]="https://www.avito.ru/rossiya/noutbuki?q=MacBook+Air"
    ["iphone"]="https://www.avito.ru/rossiya/telefony?q=iPhone"
)

# Функция очистки
cleanup() {
    echo "[*] Cleanup: закрытие всех процессов..."
    pkill -f "firefox" 2>/dev/null || true
    pkill -f "i3" 2>/dev/null || true
    sleep 1
    pkill -9 -f "firefox" 2>/dev/null || true
    pkill -9 -f "i3" 2>/dev/null || true
    echo "[+] Cleanup завершён"
}

trap cleanup EXIT

# Проверка доступа к X-серверу
if [ -z "$XVFB_RUNNING" ]; then
    USE_XVFB=0
    if [ -z "$DISPLAY" ]; then
        USE_XVFB=1
    fi

    if [ "$USE_XVFB" = "1" ]; then
        if command -v xvfb-run >/dev/null 2>&1; then
            echo "[*] Запуск через Xvfb..."
            export XVFB_RUNNING=1
            exec xvfb-run -a --server-args="-screen 0 1920x1080x24" "$0" "$@"
        else
            echo "[!] Xvfb не установлен и нет доступа к дисплею"
            exit 1
        fi
    fi
fi
echo "[*] DISPLAY=$DISPLAY"

# Если в Xvfb - запускаем легковесный WM
if [ -n "$XVFB_RUNNING" ]; then
    if command -v i3 >/dev/null 2>&1; then
        echo "[*] Запуск i3 window manager..."
        i3 &
        sleep 2
    fi
fi

# Получаем URL
if [[ -n "${CATALOGS[$QUERY]}" ]]; then
    URL="${CATALOGS[$QUERY]}"
elif [[ "$QUERY" == http* ]]; then
    URL="$QUERY"
else
    echo "[!] Неизвестный запрос: $QUERY"
    echo "Доступные: ${!CATALOGS[*]}"
    exit 1
fi

# Подготовка
mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_QUERY=$(echo "$QUERY" | tr '/' '_' | tr ' ' '_')
OUTPUT_FILE="$OUTPUT_DIR/${SAFE_QUERY}_${TIMESTAMP}.html"
JSON_FILE="$OUTPUT_DIR/${SAFE_QUERY}_${TIMESTAMP}.json"

echo "========================================"
echo "  Avito Scraper"
echo "========================================"
echo "Запрос: $QUERY"
echo "URL: $URL"
echo "Output: $OUTPUT_FILE"
echo ""

# Закрываем старые экземпляры Firefox
echo "[0] Проверка старых процессов Firefox..."
if pgrep -c firefox >/dev/null 2>&1; then
    echo "    Найдены старые процессы, закрываю..."
    pkill -f "firefox" 2>/dev/null || true
    sleep 2
fi

# Запуск Firefox
echo "[1] Запуск Firefox..."
firefox --new-window "$URL" &
FIREFOX_PID=$!
sleep 3

# Ожидание загрузки
echo "[2] Ожидание загрузки ($TIMEOUT_LOAD сек)..."
sleep $TIMEOUT_LOAD

# Поиск окна
echo "[3] Поиск окна Firefox..."
WINDOW_ID=""
for pattern in "Avito" "AVITO" "Авито" "MacBook" "Firefox"; do
    WINDOW_ID=$(xdotool search --name "$pattern" 2>/dev/null | head -1)
    if [ -n "$WINDOW_ID" ]; then
        echo "    Найдено окно: $WINDOW_ID (паттерн: $pattern)"
        break
    fi
done

if [ -z "$WINDOW_ID" ]; then
    echo "[!] Окно не найдено"
    exit 1
fi

# Активация и сохранение
echo "[4] Извлечение HTML..."
xdotool windowactivate --sync "$WINDOW_ID"
sleep 1

# Прокрутка страницы для загрузки lazy content
echo "    Прокрутка страницы..."
xdotool key Page_Down
sleep 1
xdotool key Page_Down
sleep 1
xdotool key Home
sleep 1

# View Source (Ctrl+U) + Copy
xdotool key ctrl+u
sleep 2

# Select All + Copy (Ctrl+A, Ctrl+C)
xdotool key ctrl+a
sleep 0.3
xdotool key ctrl+c
sleep 0.5

# Сохранение из буфера
xclip -selection clipboard -o > "$OUTPUT_FILE" 2>/dev/null || true

# Проверка
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE")
    echo "[+] Сохранено: $OUTPUT_FILE ($SIZE bytes)"

    # Извлечение данных
    TITLE=$(grep -oP '<title>\K[^<]+' "$OUTPUT_FILE" | head -1)
    echo "    Страница: ${TITLE:0:60}"

    # Парсинг Avito
    echo "[5] Парсинг данных..."
    python3 - "$OUTPUT_FILE" "$JSON_FILE" << 'PYTHON_SCRIPT'
import sys
import re
import json
from pathlib import Path
from datetime import datetime

html_file = sys.argv[1]
json_file = sys.argv[2]

html = Path(html_file).read_text(encoding='utf-8', errors='ignore')

result = {
    'source': 'avito',
    'products': [],
    'timestamp': datetime.now().isoformat()
}

# Method 1: itemProp/itemprop="price" (case-insensitive)
for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
    price = int(match)
    if 50000 < price < 500000:
        result['products'].append({
            'price': price,
            'available': True
        })

# Method 2: data-marker="item-price" with meta tag
if not result['products']:
    for match in re.findall(r'data-marker="item-price"[^<]*<meta[^>]+content="(\d+)"', html, re.IGNORECASE):
        price = int(match)
        if 50000 < price < 500000:
            result['products'].append({
                'price': price,
                'available': True
            })

# Fallback: JSON-LD
if not result['products']:
    for match in re.findall(r'"price":\s*"?(\d+)"?', html):
        price = int(match)
        if 50000 < price < 500000:
            result['products'].append({
                'price': price,
                'available': True
            })

# Уникальные цены
seen = set()
unique_products = []
for p in result['products']:
    if p['price'] not in seen:
        seen.add(p['price'])
        unique_products.append(p)
result['products'] = unique_products

# Сохраняем JSON
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Вывод сводки
if result['products']:
    prices = [p['price'] for p in result['products']]
    print(f"    Найдено товаров: {len(result['products'])}")
    print(f"    Цены: {min(prices):,} - {max(prices):,} RUB")
else:
    print("    [!] Товары не найдены")
PYTHON_SCRIPT

    echo "[+] JSON: $JSON_FILE"
else
    echo "[!] Файл пустой или не создан"
    exit 1
fi

echo ""
echo "========================================"
echo "  Готово!"
echo "========================================"
