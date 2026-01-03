#!/bin/bash
#
# Ozon Scraper
# Firefox + xdotool метод для обхода bot detection
#

set -e

QUERY="${1:-macbook-pro-16}"
OUTPUT_DIR="${2:-/tmp/ozon_scraper}"
TIMEOUT_LOAD=35

declare -A CATALOGS=(
    ["macbook-pro-16"]="https://www.ozon.ru/search/?text=MacBook+Pro+16&from_global=true"
    ["macbook-air"]="https://www.ozon.ru/search/?text=MacBook+Air&from_global=true"
    ["iphone"]="https://www.ozon.ru/search/?text=iPhone&from_global=true"
)

cleanup() {
    echo "[*] Cleanup..."
    pkill -f "firefox" 2>/dev/null || true
    pkill -f "i3" 2>/dev/null || true
    sleep 1
    pkill -9 -f "firefox" 2>/dev/null || true
    pkill -9 -f "i3" 2>/dev/null || true
}

trap cleanup EXIT

# Xvfb check
if [ -z "$XVFB_RUNNING" ]; then
    if [ -z "$DISPLAY" ]; then
        if command -v xvfb-run >/dev/null 2>&1; then
            echo "[*] Starting via Xvfb..."
            export XVFB_RUNNING=1
            exec xvfb-run -a --server-args="-screen 0 1920x1080x24" "$0" "$@"
        else
            echo "[!] Xvfb not installed"
            exit 1
        fi
    fi
fi
echo "[*] DISPLAY=$DISPLAY"

# WM for Xvfb
if [ -n "$XVFB_RUNNING" ]; then
    if command -v i3 >/dev/null 2>&1; then
        echo "[*] Starting i3..."
        i3 &
        sleep 2
    fi
fi

# Get URL
if [[ -n "${CATALOGS[$QUERY]}" ]]; then
    URL="${CATALOGS[$QUERY]}"
elif [[ "$QUERY" == http* ]]; then
    URL="$QUERY"
else
    echo "[!] Unknown query: $QUERY"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_QUERY=$(echo "$QUERY" | tr '/' '_' | tr ' ' '_')
OUTPUT_FILE="$OUTPUT_DIR/${SAFE_QUERY}_${TIMESTAMP}.html"
JSON_FILE="$OUTPUT_DIR/${SAFE_QUERY}_${TIMESTAMP}.json"

echo "========================================"
echo "  Ozon Scraper (Firefox + xdotool)"
echo "========================================"
echo "URL: $URL"
echo ""

# Kill old Firefox
if pgrep -c firefox >/dev/null 2>&1; then
    echo "[0] Killing old Firefox..."
    pkill -f "firefox" 2>/dev/null || true
    sleep 2
fi

# Start Firefox
echo "[1] Starting Firefox..."
firefox --new-window "$URL" &
FIREFOX_PID=$!
sleep 3

# Wait for page load
echo "[2] Waiting for page load ($TIMEOUT_LOAD sec)..."
sleep $TIMEOUT_LOAD

# Find window
echo "[3] Finding Firefox window..."
WINDOW_ID=""
for pattern in "OZON" "Ozon" "ozon" "MacBook" "Firefox"; do
    WINDOW_ID=$(xdotool search --name "$pattern" 2>/dev/null | head -1)
    if [ -n "$WINDOW_ID" ]; then
        echo "    Found: $WINDOW_ID (pattern: $pattern)"
        break
    fi
done

if [ -z "$WINDOW_ID" ]; then
    echo "[!] Window not found"
    exit 1
fi

# Activate and scroll
echo "[4] Extracting HTML..."
xdotool windowactivate --sync "$WINDOW_ID"
sleep 1

# Scroll for lazy loading
echo "    Scrolling..."
for i in {1..3}; do
    xdotool key Page_Down
    sleep 1
done
xdotool key Home
sleep 1

# View Source + Copy
xdotool key ctrl+u
sleep 2
xdotool key ctrl+a
sleep 0.3
xdotool key ctrl+c
sleep 0.5

# Save from clipboard
xclip -selection clipboard -o > "$OUTPUT_FILE" 2>/dev/null || true

if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    SIZE=$(stat -c%s "$OUTPUT_FILE")
    echo "[+] Saved: $OUTPUT_FILE ($SIZE bytes)"

    TITLE=$(grep -oP '<title>\K[^<]+' "$OUTPUT_FILE" | head -1)
    echo "    Page: ${TITLE:0:60}"

    # Parse Ozon
    echo "[5] Parsing data..."
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
    'source': 'ozon',
    'products': [],
    'timestamp': datetime.now().isoformat()
}

def extract_specs(name):
    """Извлечение характеристик из названия"""
    if not name:
        return {'cpu': None, 'ram': None, 'ssd': None, 'screen': None, 'article': None}

    # Screen: "16.2", "16", "14.2"
    screen_match = re.search(r'(\d{2})(?:\.\d)?["\s]', name)
    screen = screen_match.group(1) if screen_match else None

    # CPU: "M1 Pro", "M4 Max", "M5"
    cpu_match = re.search(r'(?:Apple\s+)?(M\d+(?:\s+(?:Pro|Max|Ultra))?)', name, re.I)
    cpu = cpu_match.group(1).strip() if cpu_match else None

    # RAM: "32 ГБ", "32GB"
    ram_match = re.search(r'(?:RAM|ОЗУ|память)?\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
    if not ram_match:
        all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
        ram = int(all_gb[0]) if all_gb else None
    else:
        ram = int(ram_match.group(1))

    # SSD: "512 ГБ", "1TB"
    ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ТБ|TB)', name, re.I)
    if ssd_match:
        ssd = int(ssd_match.group(1)) * 1000
    else:
        ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
        if not ssd_match:
            all_tb = re.findall(r'(\d+)\s*(?:ТБ|TB)', name, re.I)
            if all_tb:
                ssd = int(all_tb[0]) * 1000
            else:
                all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
                ssd = int(all_gb[1]) if len(all_gb) >= 2 else None
        else:
            ssd = int(ssd_match.group(1))

    # Article: "Z14V0008D"
    article_match = re.search(r'\b([A-Z]\d{2}[A-Z0-9]{5,})\b', name)
    article = article_match.group(1) if article_match else None

    return {
        'cpu': cpu,
        'ram': ram,
        'ssd': ssd,
        'screen': screen,
        'article': article
    }

# Try to extract product data with names from JSON state
products_data = []

# Method 1: Extract from JSON state (finalPrice + name)
# Look for product objects with both name and price
json_pattern = r'"(?:name|title)":\s*"([^"]+)"[^}]*?"finalPrice":\s*(\d+)|"finalPrice":\s*(\d+)[^}]*?"(?:name|title)":\s*"([^"]+)"'
for match in re.finditer(json_pattern, html):
    name = match.group(1) or match.group(4)
    price = int(match.group(2) or match.group(3))
    if name and 50000 < price < 500000:
        products_data.append({'name': name, 'price': price, 'available': True})

# Method 2: Fallback to prices only (if names not found)
if not products_data:
    for match in re.findall(r'"finalPrice":\s*(\d+)', html):
        price = int(match)
        if 50000 < price < 500000:
            products_data.append({'price': price, 'available': True, 'name': ''})

# Method 3: Extract from product tile links (current Ozon structure)
# Product tiles have href="/product/NAME-ID/" and nearby price spans
if not products_data:
    # Find product URLs and extract names from slug
    product_links = re.findall(r'href="/product/([^/]+)-(\d+)/', html)
    for slug, product_id in product_links:
        # Convert slug to readable name: "apple-macbook-air-13" -> "Apple Macbook Air 13"
        name = slug.replace('-', ' ').title()
        products_data.append({'name': name, 'price': None, 'product_id': product_id, 'available': True})

    # Extract prices separately from price spans (format: "113 999 ₽")
    prices = []
    for match in re.findall(r'(\d{2,3})\s*(\d{3})\s*₽', html):
        price = int(match[0] + match[1])
        if 50000 < price < 500000:
            prices.append(price)

    # Match prices to products (assume same order in HTML)
    for i, product in enumerate(products_data):
        if i < len(prices):
            product['price'] = prices[i]

    # Remove products without prices
    products_data = [p for p in products_data if p.get('price')]

# Add specs to products
for p in products_data:
    p['specs'] = extract_specs(p.get('name', ''))

# Dedupe by price
seen = set()
unique = []
for p in products_data:
    if p['price'] not in seen:
        seen.add(p['price'])
        unique.append(p)

result['products'] = unique

with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

if result['products']:
    prices = [p['price'] for p in result['products']]
    print(f"    Found: {len(result['products'])} products")
    print(f"    Prices: {min(prices):,} - {max(prices):,} RUB")
else:
    print("    [!] No products found")
PYTHON_SCRIPT

    echo "[+] JSON: $JSON_FILE"
else
    echo "[!] File empty or not created"
    exit 1
fi

echo ""
echo "========================================"
echo "  Done!"
echo "========================================"
