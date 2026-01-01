#!/usr/bin/env python3
"""
DNS-Shop parser с undetected-chromedriver
Использует подход из github.com/kireev20000/DNS-Shop-Parser
"""

import time
import sys

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("[!] Install: pip install undetected-chromedriver selenium")
    sys.exit(1)


def test_dns_shop(query: str = "MacBook Pro 16"):
    """Тест DNS-Shop с undetected-chromedriver"""

    print("=" * 60)
    print("DNS-SHOP TEST (undetected-chromedriver)")
    print("=" * 60)

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ru-RU")

    # Headless mode для сервера
    options.add_argument("--headless=new")

    print("[*] Запуск Chrome...")

    try:
        # version_main должен соответствовать установленному Chromium
        # browser_executable_path для использования системного Chromium
        driver = uc.Chrome(
            options=options,
            version_main=136,
            browser_executable_path="/usr/bin/chromium"
        )
        driver.set_page_load_timeout(30)

        # Сначала главная страница для cookies
        print("[*] Загрузка главной страницы...")
        driver.get("https://www.dns-shop.ru/")
        time.sleep(3)

        # Проверка на блокировку
        page_source = driver.page_source
        current_url = driver.current_url

        print(f"[*] URL: {current_url}")
        print(f"[*] Title: {driver.title}")
        print(f"[*] Page length: {len(page_source)}")

        # Проверка на CAPTCHA/блокировку
        if "showcaptcha" in current_url.lower():
            print("[X] CAPTCHA redirect!")
            return False

        if "access denied" in page_source.lower() or "403" in driver.title:
            print("[X] Access Denied!")
            return False

        # Поиск товара
        print(f"\n[*] Поиск: {query}")
        search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(5)

        print(f"[*] Search URL: {driver.current_url}")
        print(f"[*] Search Title: {driver.title}")

        page_source = driver.page_source
        print(f"[*] Page length: {len(page_source)}")

        # Ищем товары
        try:
            # Ждём загрузки карточек товаров
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-id='product']"))
            )

            products = driver.find_elements(By.CSS_SELECTOR, "[data-id='product']")
            print(f"\n[+] Найдено товаров: {len(products)}")

            for i, product in enumerate(products[:5], 1):
                try:
                    name = product.find_element(By.CSS_SELECTOR, "a.catalog-product__name").text
                    price_elem = product.find_element(By.CSS_SELECTOR, "[data-product-price]")
                    price = price_elem.get_attribute("data-product-price")

                    print(f"\n{i}. {name[:60]}...")
                    print(f"   Цена: {price} RUB")
                except Exception as e:
                    print(f"{i}. [Ошибка парсинга: {e}]")

            return True

        except Exception as e:
            print(f"[!] Товары не найдены: {e}")

            # Сохраним HTML для анализа
            with open("/tmp/dns_page.html", "w") as f:
                f.write(page_source)
            print("[*] HTML сохранён в /tmp/dns_page.html")

            # Проверим наличие каких-либо цен
            import re
            prices = re.findall(r'data-product-price="(\d+)"', page_source)
            if prices:
                print(f"\n[+] Найдены цены в HTML: {prices[:5]}")

            return False

    except Exception as e:
        print(f"[!] Ошибка: {e}")
        return False

    finally:
        try:
            driver.quit()
        except:
            pass


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"
    test_dns_shop(query)
