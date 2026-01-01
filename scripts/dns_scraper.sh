#!/bin/bash
#
# DNS-Shop Scraper for Server
# Автоматически закрывает браузер после извлечения данных
#

set -e

# Конфигурация
CATALOG="${1:-macbook-pro}"
OUTPUT_DIR="${2:-/tmp/dns_scraper}"
TIMEOUT_LOAD=25
TIMEOUT_SAVE=5

# Каталоги DNS-Shop
declare -A CATALOGS=(
    ["macbook-pro"]="https://www.dns-shop.ru/catalog/recipe/b70b01357dbede01/apple-macbook-pro/"
    ["macbook"]="https://www.dns-shop.ru/catalog/recipe/8ddf1df79c19c23d/macbook/"
    ["iphone"]="https://www.dns-shop.ru/catalog/recipe/4c7e3a7f7ef9a70e/apple-iphone/"
    ["notebooks"]="https://www.dns-shop.ru/catalog/17a892f816404e77/noutbuki/"
)

# Функция очистки
cleanup() {
    echo "[*] Cleanup: закрытие всех процессов..."

    # Закрываем Firefox
    pkill -f "firefox" 2>/dev/null || true

    # Закрываем i3
    pkill -f "i3" 2>/dev/null || true

    sleep 1

    # Принудительное завершение если не закрылись
    pkill -9 -f "firefox" 2>/dev/null || true
    pkill -9 -f "i3" 2>/dev/null || true

    # НЕ убиваем Xvfb - xvfb-run сам это сделает
    echo "[+] Cleanup завершён"
}

# Trap для гарантированного закрытия при любом выходе
trap cleanup EXIT

# Проверка доступа к X-серверу (только если ещё не в xvfb-run)
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
if [[ -n "${CATALOGS[$CATALOG]}" ]]; then
    URL="${CATALOGS[$CATALOG]}"
elif [[ "$CATALOG" == http* ]]; then
    URL="$CATALOG"
else
    echo "[!] Неизвестный каталог: $CATALOG"
    echo "Доступные: ${!CATALOGS[*]}"
    exit 1
fi

# Подготовка
mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/${CATALOG}_${TIMESTAMP}.html"
JSON_FILE="$OUTPUT_DIR/${CATALOG}_${TIMESTAMP}.json"

echo "========================================"
echo "  DNS-Shop Scraper"
echo "========================================"
echo "Каталог: $CATALOG"
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
for pattern in "MacBook" "DNS" "Firefox"; do
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

# Активация и сохранение через View Source + Clipboard
echo "[4] Извлечение HTML..."
xdotool windowactivate --sync "$WINDOW_ID"
sleep 1

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

# Проверка
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE")
    echo "[+] Сохранено: $OUTPUT_FILE ($SIZE bytes)"

    # Извлечение данных
    TITLE=$(grep -oP '<title>\K[^<]+' "$OUTPUT_FILE" | head -1)
    echo "    Страница: ${TITLE:0:60}"

    # Извлечение JSON-LD данных
    echo "[5] Парсинг данных..."
    python3 - "$OUTPUT_FILE" "$JSON_FILE" << 'PYTHON_SCRIPT'
import sys
import re
import json
from pathlib import Path

html_file = sys.argv[1]
json_file = sys.argv[2]

html = Path(html_file).read_text(encoding='utf-8', errors='ignore')

result = {
    'catalog': {},
    'products': [],
    'timestamp': None
}

# Извлекаем JSON.stringify данные
match = re.search(r'JSON\.stringify\((\{[^}]+\}[^)]+)\)', html)
if match:
    try:
        raw = match.group(1).replace('\\/', '/')
        data = json.loads(raw)
        result['catalog'] = {
            'name': data.get('name'),
            'low_price': data.get('offers', {}).get('lowPrice'),
            'high_price': data.get('offers', {}).get('highPrice'),
            'count': data.get('offers', {}).get('offerCount'),
            'rating': data.get('aggregateRating', {}).get('ratingValue'),
            'reviews': data.get('aggregateRating', {}).get('reviewCount')
        }
    except:
        pass

# Извлекаем товары
product_pattern = re.compile(
    r'data-product="([^"]+)"[^>]*data-code="(\d+)".*?'
    r'catalog-product__name[^>]*href="([^"]+)"[^>]*><span>([^<]+)',
    re.DOTALL
)

for match in product_pattern.finditer(html):
    uuid, code, url, name = match.groups()
    short_name = name.split('[')[0].strip()

    specs = re.search(r'\[([^\]]+)\]', name)
    specs_str = specs.group(1) if specs else ''

    ram = re.search(r'RAM\s*(\d+)\s*ГБ', specs_str)
    ssd = re.search(r'SSD\s*(\d+)\s*ГБ', specs_str)

    result['products'].append({
        'code': code,
        'name': short_name,
        'ram': ram.group(1) if ram else None,
        'ssd': ssd.group(1) if ssd else None,
        'url': f"https://www.dns-shop.ru{url}"
    })

from datetime import datetime
result['timestamp'] = datetime.now().isoformat()

# Сохраняем JSON
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Вывод сводки
cat = result['catalog']
if cat.get('name'):
    print(f"    Каталог: {cat['name']}")
    print(f"    Цены: {cat.get('low_price', 0):,} - {cat.get('high_price', 0):,} RUB")
    print(f"    Моделей всего: {cat.get('count', 'N/A')}")
    print(f"    На странице: {len(result['products'])}")
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
