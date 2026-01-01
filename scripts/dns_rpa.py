#!/usr/bin/env python3
"""
DNS-Shop RPA Parser
Управление реальным браузером через PyAutoGUI

Принцип: запускаем настоящий браузер, делаем скриншоты,
симулируем человеческий ввод - Qrator не может это детектить.
"""

import subprocess
import time
import sys
import os
import re
from pathlib import Path

import pyautogui
from PIL import Image

# Настройки
SCREENSHOT_DIR = Path("/tmp/dns_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# PyAutoGUI настройки безопасности
pyautogui.FAILSAFE = True  # Мышь в угол = аварийный выход
pyautogui.PAUSE = 0.5  # Пауза между действиями


def take_screenshot(name: str) -> Path:
    """Сделать скриншот экрана"""
    path = SCREENSHOT_DIR / f"{name}_{int(time.time())}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(path)
    print(f"[*] Screenshot: {path}")
    return path


def human_type(text: str, interval: float = 0.05):
    """Печать как человек - с небольшими паузами"""
    for char in text:
        pyautogui.write(char, interval=interval)
        time.sleep(0.02)


def launch_browser(url: str) -> subprocess.Popen:
    """Запуск реального Firefox"""
    print(f"[*] Запуск Firefox: {url}")

    # Пробуем разные браузеры
    browsers = [
        ["firefox", "--new-window", url],
        ["google-chrome", url],
        ["chromium", url],
    ]

    for cmd in browsers:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[+] Запущен: {cmd[0]}")
            return proc
        except FileNotFoundError:
            continue

    raise RuntimeError("Не найден браузер (firefox/chrome/chromium)")


def wait_for_page_load(seconds: int = 10):
    """Ждём загрузки страницы"""
    print(f"[*] Ожидание загрузки ({seconds}s)...")
    for i in range(seconds):
        time.sleep(1)
        print(f"  {i+1}/{seconds}")


def find_search_box():
    """
    Попытка найти поисковую строку на странице.
    В реальном приложении здесь был бы AI-анализ скриншота.
    Пока используем фиксированные координаты или поиск по изображению.
    """
    # Для DNS-Shop поисковая строка обычно вверху по центру
    # На экране 1920x1080 примерно в районе (960, 100)

    screen_width, screen_height = pyautogui.size()
    print(f"[*] Размер экрана: {screen_width}x{screen_height}")

    # Центр верхней части - типичное расположение поиска
    search_x = screen_width // 2
    search_y = 150  # Примерно 150px от верха

    return search_x, search_y


def click_search_box(x: int, y: int):
    """Клик по поисковой строке"""
    print(f"[*] Клик по ({x}, {y})")

    # Плавное движение мыши как у человека
    pyautogui.moveTo(x, y, duration=0.5)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(0.3)


def search_product(query: str):
    """Ввод поискового запроса"""
    print(f"[*] Ввод запроса: {query}")

    # Очищаем поле (Ctrl+A, Delete)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)

    # Печатаем запрос
    # PyAutoGUI не поддерживает кириллицу напрямую, используем clipboard
    import pyperclip
    pyperclip.copy(query)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

    # Enter для поиска
    pyautogui.press('enter')


def analyze_screenshot_for_prices(image_path: Path) -> list:
    """
    Анализ скриншота для извлечения цен.

    В production здесь был бы:
    1. OCR (Tesseract) для распознавания текста
    2. Или Claude Vision API для анализа изображения

    Пока возвращаем placeholder.
    """
    print(f"[*] Анализ скриншота: {image_path}")

    # Проверяем что файл существует
    if not image_path.exists():
        return []

    img = Image.open(image_path)
    print(f"[*] Размер изображения: {img.size}")

    # TODO: Интеграция с OCR или Claude Vision
    # Пример с pytesseract:
    # import pytesseract
    # text = pytesseract.image_to_string(img, lang='rus')
    # prices = re.findall(r'(\d{1,3}[\s\xa0]?\d{3})\s*[₽руб]', text)

    return []


def check_for_captcha(image_path: Path) -> bool:
    """
    Проверка наличия CAPTCHA на скриншоте.

    В production: AI-анализ или поиск характерных элементов.
    """
    # TODO: Реализовать детекцию CAPTCHA
    # Можно искать характерные паттерны:
    # - "Я не робот"
    # - reCAPTCHA логотип
    # - Характерные checkbox элементы

    return False


def run_rpa_parser(query: str = "MacBook Pro 16"):
    """Основной RPA процесс"""

    print("=" * 60)
    print("DNS-SHOP RPA PARSER")
    print("=" * 60)
    print()
    print("[!] ВНИМАНИЕ: Не двигайте мышь во время работы!")
    print("[!] Для аварийной остановки - мышь в левый верхний угол")
    print()

    browser = None

    try:
        # 1. Запуск браузера
        browser = launch_browser("https://www.dns-shop.ru/")

        # 2. Ждём загрузки
        wait_for_page_load(8)

        # 3. Скриншот главной
        screenshot1 = take_screenshot("01_main_page")

        # 4. Проверка на CAPTCHA
        if check_for_captcha(screenshot1):
            print("[!] Обнаружена CAPTCHA!")
            print("[*] Требуется ручное решение...")
            input("Нажмите Enter после решения CAPTCHA...")

        # 5. Находим поисковую строку
        search_x, search_y = find_search_box()

        # 6. Кликаем по поиску
        click_search_box(search_x, search_y)

        # 7. Вводим запрос
        search_product(query)

        # 8. Ждём результатов
        wait_for_page_load(5)

        # 9. Скриншот результатов
        screenshot2 = take_screenshot("02_search_results")

        # 10. Анализ результатов
        prices = analyze_screenshot_for_prices(screenshot2)

        if prices:
            print(f"\n[+] Найдено цен: {len(prices)}")
            for i, p in enumerate(prices[:10], 1):
                print(f"  {i}. {p}")
        else:
            print("\n[*] Автоматическое извлечение цен не реализовано")
            print(f"[*] Скриншоты сохранены в: {SCREENSHOT_DIR}")
            print("[*] Для полной реализации нужен OCR или Claude Vision")

        return prices

    except pyautogui.FailSafeException:
        print("\n[!] Аварийная остановка (мышь в углу)")
        return []

    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        return []

    finally:
        # Даём время посмотреть результат
        print("\n[*] Браузер остаётся открытым для проверки")
        print("[*] Закройте его вручную когда закончите")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"

    print("Этот скрипт управляет реальным браузером.")
    print("Убедитесь что:")
    print("  1. Вы на Linux с графическим окружением")
    print("  2. Firefox или Chrome установлен")
    print("  3. Экран свободен от других окон")
    print()

    confirm = input("Продолжить? (y/n): ")
    if confirm.lower() == 'y':
        run_rpa_parser(query)
    else:
        print("Отменено")
