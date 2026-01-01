#!/usr/bin/env python3
"""
DNS-Shop RPA Parser с OCR
Полный цикл: браузер -> скриншот -> OCR -> данные
"""

import subprocess
import time
import sys
import re
from pathlib import Path

# Отключаем MouseInfo до импорта pyautogui (не требует tkinter)
import os
os.environ['DISPLAY'] = os.environ.get('DISPLAY', ':0')

# Mock mouseinfo чтобы избежать tkinter
import sys
from unittest.mock import MagicMock
sys.modules['mouseinfo'] = MagicMock()

import pyautogui

from PIL import Image

# Попытка импорта pytesseract
try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("[!] pytesseract не установлен")
    print("[!] Для OCR: pip install pytesseract")
    print("[!] И установите tesseract-ocr: sudo apt install tesseract-ocr tesseract-ocr-rus")

SCREENSHOT_DIR = Path("/tmp/dns_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def take_screenshot(name: str) -> Path:
    """Скриншот экрана через разные методы"""
    path = SCREENSHOT_DIR / f"{name}.png"

    # Метод 1: PIL ImageGrab (если доступен)
    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        screenshot.save(path)
        print(f"[+] Screenshot (PIL): {path}")
        return path
    except Exception:
        pass

    # Метод 2: scrot
    try:
        import subprocess
        subprocess.run(["scrot", str(path)], check=True, capture_output=True)
        print(f"[+] Screenshot (scrot): {path}")
        return path
    except Exception:
        pass

    # Метод 3: gnome-screenshot
    try:
        import subprocess
        subprocess.run(["gnome-screenshot", "-f", str(path)], check=True, capture_output=True)
        print(f"[+] Screenshot (gnome): {path}")
        return path
    except Exception:
        pass

    # Метод 4: import (ImageMagick)
    try:
        import subprocess
        subprocess.run(["import", "-window", "root", str(path)], check=True, capture_output=True)
        print(f"[+] Screenshot (import): {path}")
        return path
    except Exception:
        pass

    # Метод 5: maim
    try:
        import subprocess
        subprocess.run(["maim", str(path)], check=True, capture_output=True)
        print(f"[+] Screenshot (maim): {path}")
        return path
    except Exception:
        pass

    print(f"[!] Не удалось сделать скриншот")
    print(f"[!] Установите: sudo apt install scrot или gnome-screenshot или maim")
    return path


def extract_prices_ocr(image_path: Path) -> list:
    """Извлечение цен через OCR"""
    if not HAS_OCR:
        print("[!] OCR недоступен")
        return []

    try:
        img = Image.open(image_path)

        # OCR с русским языком
        text = pytesseract.image_to_string(img, lang='rus+eng')

        # Ищем паттерны цен:
        # "123 456 ₽", "123456 руб", "123 456" рядом с "₽"
        prices = []

        # Паттерн 1: числа с пробелами + символ рубля
        pattern1 = re.findall(r'(\d{1,3}[\s\xa0]?\d{3}[\s\xa0]?\d{0,3})\s*[₽руб\.]', text)
        prices.extend(pattern1)

        # Паттерн 2: просто большие числа (вероятно цены)
        pattern2 = re.findall(r'(\d{2,3}[\s\xa0]\d{3})', text)
        prices.extend(pattern2)

        # Очищаем и конвертируем
        clean_prices = []
        for p in prices:
            # Убираем пробелы
            clean = re.sub(r'[\s\xa0]', '', str(p))
            if clean.isdigit():
                num = int(clean)
                # Фильтруем разумные цены (10к - 500к)
                if 10000 <= num <= 500000:
                    clean_prices.append(num)

        return sorted(set(clean_prices))

    except Exception as e:
        print(f"[!] OCR ошибка: {e}")
        return []


def detect_captcha_ocr(image_path: Path) -> bool:
    """Детекция CAPTCHA через OCR"""
    if not HAS_OCR:
        return False

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='rus+eng').lower()

        captcha_keywords = [
            'captcha', 'капча', 'я не робот', 'i am not a robot',
            'проверка', 'verification', 'подтвердите'
        ]

        for keyword in captcha_keywords:
            if keyword in text:
                print(f"[!] Обнаружено: '{keyword}'")
                return True

        return False

    except Exception as e:
        print(f"[!] CAPTCHA detection error: {e}")
        return False


def launch_firefox(url: str) -> subprocess.Popen:
    """Запуск Firefox"""
    cmd = ["firefox", "--new-window", url]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Firefox запущен")
        return proc
    except FileNotFoundError:
        # Fallback на chromium
        cmd = ["chromium", url]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Chromium запущен")
        return proc


def human_delay(min_sec: float = 0.5, max_sec: float = 1.5):
    """Случайная задержка как у человека"""
    import random
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def type_query(query: str):
    """Ввод запроса через clipboard (для кириллицы)"""
    import pyperclip
    pyperclip.copy(query)
    pyautogui.hotkey('ctrl', 'v')


def run_dns_rpa(query: str = "MacBook Pro 16"):
    """Основной RPA процесс"""

    print("=" * 60)
    print("DNS-SHOP RPA + OCR")
    print("=" * 60)
    print()
    print("[!] НЕ ДВИГАЙТЕ МЫШЬ во время работы!")
    print("[!] Аварийный выход: мышь в левый верхний угол")
    print()

    try:
        # 1. Запуск браузера
        browser = launch_firefox("https://www.dns-shop.ru/")
        time.sleep(8)  # Ждём загрузки

        # 2. Скриншот главной
        screen1 = take_screenshot("01_main")

        # 3. Проверка CAPTCHA
        if detect_captcha_ocr(screen1):
            print("\n[!] CAPTCHA обнаружена!")
            input("[*] Решите CAPTCHA вручную и нажмите Enter...")
            screen1 = take_screenshot("01_after_captcha")

        # 4. Клик по поисковой строке
        screen_w, screen_h = pyautogui.size()
        search_x = screen_w // 2
        search_y = 120

        print(f"[*] Клик по поиску ({search_x}, {search_y})")
        pyautogui.moveTo(search_x, search_y, duration=0.3)
        human_delay(0.2, 0.4)
        pyautogui.click()
        human_delay(0.3, 0.5)

        # 5. Ввод запроса
        print(f"[*] Ввод: {query}")
        type_query(query)
        human_delay(0.3, 0.5)
        pyautogui.press('enter')

        # 6. Ждём результатов
        print("[*] Ожидание результатов...")
        time.sleep(5)

        # 7. Скриншот результатов
        screen2 = take_screenshot("02_results")

        # 8. OCR извлечение цен
        prices = extract_prices_ocr(screen2)

        if prices:
            print(f"\n[+] Найдено {len(prices)} цен:")
            for i, p in enumerate(prices[:15], 1):
                print(f"  {i}. {p:,} RUB".replace(",", " "))

            print(f"\n  Минимум: {min(prices):,} RUB".replace(",", " "))
            print(f"  Максимум: {max(prices):,} RUB".replace(",", " "))
        else:
            print("\n[*] Цены не извлечены автоматически")
            print(f"[*] Проверьте скриншоты: {SCREENSHOT_DIR}")

        return prices

    except pyautogui.FailSafeException:
        print("\n[!] Аварийный выход")
        return []
    except Exception as e:
        print(f"\n[!] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"

    # Проверка окружения
    print("Проверка зависимостей:")
    print(f"  PyAutoGUI: OK")
    print(f"  pytesseract: {'OK' if HAS_OCR else 'НЕТ'}")

    if not HAS_OCR:
        print("\n[!] Для полной функциональности установите:")
        print("  sudo apt install tesseract-ocr tesseract-ocr-rus")

    print(f"\nЗапуск парсера для: {query}")
    confirm = input("Продолжить? (y/n): ")

    if confirm.lower() == 'y':
        run_dns_rpa(query)
