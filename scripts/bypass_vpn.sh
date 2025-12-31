#!/bin/bash
#
# Добавление маршрутов для обхода VPN к магазинам
# Запуск: sudo ./bypass_vpn.sh add
# Откат: sudo ./bypass_vpn.sh remove
#

# Конфигурация
GATEWAY="192.168.0.1"  # Домашний роутер
INTERFACE="wlo1"       # WiFi интерфейс

# IP-адреса магазинов (можно добавить больше)
declare -a SHOP_DOMAINS=(
    "www.citilink.ru"
    "www.dns-shop.ru"
    "cdn.citilink.ru"
)

get_ips() {
    local domain=$1
    dig +short "$domain" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'
}

add_routes() {
    echo "Добавление маршрутов для обхода VPN..."
    echo "Gateway: $GATEWAY"
    echo "Interface: $INTERFACE"
    echo ""

    for domain in "${SHOP_DOMAINS[@]}"; do
        echo "[$domain]"
        ips=$(get_ips "$domain")

        for ip in $ips; do
            if ip route add "$ip" via "$GATEWAY" dev "$INTERFACE" 2>/dev/null; then
                echo "  [+] $ip"
            else
                echo "  [!] $ip (уже существует или ошибка)"
            fi
        done
    done

    echo ""
    echo "Готово! Проверьте: ip route get 178.248.234.66"
}

remove_routes() {
    echo "Удаление маршрутов..."

    for domain in "${SHOP_DOMAINS[@]}"; do
        echo "[$domain]"
        ips=$(get_ips "$domain")

        for ip in $ips; do
            if ip route del "$ip" via "$GATEWAY" dev "$INTERFACE" 2>/dev/null; then
                echo "  [-] $ip"
            else
                echo "  [!] $ip (не найден или ошибка)"
            fi
        done
    done

    echo ""
    echo "Готово!"
}

show_status() {
    echo "Текущие маршруты к магазинам:"
    echo ""

    for domain in "${SHOP_DOMAINS[@]}"; do
        echo "[$domain]"
        ips=$(get_ips "$domain")

        for ip in $ips; do
            route=$(ip route get "$ip" 2>/dev/null | head -1)
            if echo "$route" | grep -q "tun"; then
                echo "  $ip -> VPN (tun)"
            elif echo "$route" | grep -q "$INTERFACE"; then
                echo "  $ip -> LOCAL ($INTERFACE)"
            else
                echo "  $ip -> $route"
            fi
        done
    done
}

case "$1" in
    add)
        add_routes
        ;;
    remove)
        remove_routes
        ;;
    status)
        show_status
        ;;
    *)
        echo "Использование: $0 {add|remove|status}"
        echo ""
        echo "  add    - Добавить маршруты (обход VPN)"
        echo "  remove - Удалить маршруты (вернуть VPN)"
        echo "  status - Показать текущие маршруты"
        exit 1
        ;;
esac
