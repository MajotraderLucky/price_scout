#!/bin/bash
#
# Citilink Scraper for Server
# Firefox + xdotool метод для обхода rate limiting
#

set -e

# Конфигурация
QUERY="${1:-macbook-pro}"
OUTPUT_DIR="${2:-/tmp/citilink_scraper}"
TIMEOUT_LOAD=30
TIMEOUT_SAVE=5

# Каталоги Citilink
declare -A CATALOGS=(
    ["macbook-pro"]="https://www.citilink.ru/search/?text=MacBook+Pro+16"
    ["macbook-air"]="https://www.citilink.ru/search/?text=MacBook+Air"
    ["macbook"]="https://www.citilink.ru/search/?text=Apple+MacBook"
    ["iphone"]="https://www.citilink.ru/search/?text=iPhone"
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
echo "  Citilink Scraper"
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
for pattern in "Citilink" "CITILINK" "Ситилинк" "MacBook" "Firefox"; do
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

# Активация и сохранение через Save Page (Ctrl+S) для получения отрендеренного DOM
echo "[4] Извлечение HTML (rendered DOM)..."
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

# Save Page As (Ctrl+S) - сохраняет отрендеренный DOM
xdotool key ctrl+s
sleep 2

# Вводим имя файла в диалоге сохранения
xdotool type "$OUTPUT_FILE"
sleep 0.5
xdotool key Return
sleep 3

# Если файл не создан через диалог - пробуем через clipboard
if [ ! -f "$OUTPUT_FILE" ] || [ ! -s "$OUTPUT_FILE" ]; then
    echo "    Fallback: View Source + Clipboard..."
    # Закрываем диалог если открыт
    xdotool key Escape
    sleep 0.5

    # View Source (Ctrl+U)
    xdotool key ctrl+u
    sleep 2

    # Select All + Copy (Ctrl+A, Ctrl+C)
    xdotool key ctrl+a
    sleep 0.3
    xdotool key ctrl+c
    sleep 0.5

    # Сохранение из буфера
    xclip -selection clipboard -o > "$OUTPUT_FILE" 2>/dev/null
fi

# Проверка
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE")
    echo "[+] Сохранено: $OUTPUT_FILE ($SIZE bytes)"

    # Извлечение данных
    TITLE=$(grep -oP '<title>\K[^<]+' "$OUTPUT_FILE" | head -1)
    echo "    Страница: ${TITLE:0:60}"

    # Парсинг Citilink (Next.js __NEXT_DATA__)
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
    'source': 'citilink',
    'products': [],
    'timestamp': datetime.now().isoformat()
}

# Извлекаем __NEXT_DATA__
match = re.search(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
    html
)

if match:
    try:
        data = json.loads(match.group(1))
        props = data.get("props", {}).get("pageProps", {}).get("effectorValues", {})

        for key, value in props.items():
            if isinstance(value, dict) and "products" in value:
                for item in value["products"]:
                    product = {
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'price': item.get('price', {}).get('price', 0),
                        'old_price': item.get('price', {}).get('oldPrice'),
                        'available': item.get('isAvailable', False),
                        'rating': item.get('rating', {}).get('value'),
                        'reviews': item.get('rating', {}).get('reviewsCount'),
                        'url': f"https://www.citilink.ru/product/{item.get('slug', '')}/" if item.get('slug') else None
                    }
                    result['products'].append(product)
    except json.JSONDecodeError as e:
        print(f"    [!] JSON parse error: {e}")

# Fallback: data-meta-price
if not result['products']:
    prices = re.findall(r'data-meta-price="(\d+)"', html)
    names = re.findall(r'data-meta-name="([^"]+)"', html)

    for i, price in enumerate(prices):
        name = names[i] if i < len(names) else f"Product {i+1}"
        result['products'].append({
            'name': name,
            'price': int(price),
            'available': True
        })

# Сохраняем JSON
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Вывод сводки
if result['products']:
    prices = [p['price'] for p in result['products'] if p.get('price')]
    available = [p for p in result['products'] if p.get('available')]

    print(f"    Найдено товаров: {len(result['products'])}")
    if prices:
        print(f"    Цены: {min(prices):,} - {max(prices):,} RUB")
    print(f"    В наличии: {len(available)}")
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
