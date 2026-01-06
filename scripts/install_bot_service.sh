#!/bin/bash
#
# Install Price Scout Telegram Bot systemd service
#
# Usage: ./install_bot_service.sh
#

set -e

echo "========================================="
echo "Price Scout Bot Service Installation"
echo "========================================="
echo ""

# Check if service file exists
if [ ! -f "/home/sergey/price_scout/config/price-scout-bot.service" ]; then
    echo "Error: Service file not found"
    exit 1
fi

# Check if binary exists
if [ ! -f "/home/sergey/price_scout/target/release/price-scout-bot" ]; then
    echo "Error: Bot binary not found"
    exit 1
fi

echo "Step 1: Copying service file to systemd..."
sudo cp /home/sergey/price_scout/config/price-scout-bot.service /etc/systemd/system/
echo "[+] Service file installed"

echo ""
echo "Step 2: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "[+] Systemd reloaded"

echo ""
echo "Step 3: Enabling service (auto-start on boot)..."
sudo systemctl enable price-scout-bot.service
echo "[+] Service enabled"

echo ""
echo "Step 4: Starting service..."
sudo systemctl start price-scout-bot.service
echo "[+] Service started"

echo ""
echo "Step 5: Checking service status..."
sudo systemctl status price-scout-bot.service --no-pager || true

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Commands:"
echo "  Check status: sudo systemctl status price-scout-bot.service"
echo "  View logs:    sudo journalctl -u price-scout-bot.service -f"
echo "  Restart:      sudo systemctl restart price-scout-bot.service"
echo "  Stop:         sudo systemctl stop price-scout-bot.service"
echo ""
