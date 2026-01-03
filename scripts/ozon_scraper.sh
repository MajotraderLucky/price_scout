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

# Method 1: Search in JSON state
# Ozon stores data in __NUXT__ or similar
for match in re.findall(r'"finalPrice":\s*(\d+)', html):
    price = int(match)
    if 50000 < price < 500000:
        result['products'].append({'price': price, 'available': True})

# Method 2: data-widget prices
if not result['products']:
    for match in re.findall(r'(\d{2,3})\s*(\d{3})\s*₽', html):
        price = int(match[0] + match[1])
        if 50000 < price < 500000:
            result['products'].append({'price': price, 'available': True})

# Method 3: price in meta
if not result['products']:
    for match in re.findall(r'"price":\s*"?(\d+)"?', html):
        price = int(match)
        if 50000 < price < 500000:
            result['products'].append({'price': price, 'available': True})

# Dedupe
seen = set()
unique = []
for p in result['products']:
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
