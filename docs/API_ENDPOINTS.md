# API Endpoints - Результаты тестирования

> Обновлено: 2026-01-03

---

## Сводка: 9/9 магазинов работают

| Магазин       | Метод                 | Цена        | Время  | Статус   |
|---------------|-----------------------|-------------|--------|----------|
| Avito         | Firefox + xdotool     | 54,900 RUB  | 41.0s  | [+] PASS |
| DNS-Shop      | Firefox + xdotool     | 62,799 RUB  | 38.2s  | [+] PASS |
| Ozon          | Firefox + xdotool     | 94,213 RUB  | 52.4s  | [+] PASS |
| i-ray.ru      | Playwright Direct     | 107,999 RUB | 4.1s   | [+] PASS |
| Citilink      | Playwright + Stealth  | 115,990 RUB | 14.5s  | [+] PASS |
| nix.ru        | Playwright Direct     | 129,563 RUB | 3.6s   | [+] PASS |
| regard.ru     | Playwright Stealth    | 144,400 RUB | 7.9s   | [+] PASS |
| kns.ru        | Playwright Direct     | 156,463 RUB | 3.5s   | [+] PASS |
| Yandex Market | Playwright + Stealth  | 295,309 RUB | 15.4s  | [+] PASS |

---

## Avito

### Статус: РАБОТАЕТ (Firefox метод)

| Параметр        | Значение                                               |
|-----------------|--------------------------------------------------------|
| URL             | https://www.avito.ru/rossiya/noutbuki?q=MacBook+Pro+16 |
| Защита          | IP блокировка на VPS, работает на резидентном IP       |
| Playwright      | [X] CAPTCHA на VPS                                     |
| Firefox+xdotool | [+] Работает на Archbook                               |
| Формат данных   | Schema.org (itemProp="price")                          |

### Как работает

```bash
# 1. Запуск Firefox в Xvfb
xvfb-run firefox "$URL" &
sleep 30

# 2. Имитация пользователя
xdotool key Page_Down && sleep 1
xdotool key ctrl+u  # View Source
xdotool key ctrl+a && xdotool key ctrl+c

# 3. Парсинг HTML
# itemProp="price" content="84990"
```

### Парсинг цен

```python
# Method 1: itemProp="price" (case-insensitive)
for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
    price = int(match)

# Method 2: data-marker="item-price" with meta tag
for match in re.findall(r'data-marker="item-price"[^<]*<meta[^>]+content="(\d+)"', html, re.IGNORECASE):
    price = int(match)
```

### Важно

- Avito блокирует VPS (datacenter IP) - показывает CAPTCHA
- На резидентном IP (Archbook) работает без проблем
- Firefox + xdotool успешно обходит защиту
- Находит 15-30 объявлений MacBook Pro 16
- Диапазон цен: 54,900 - 350,000 RUB

---

## DNS-Shop

### Статус: РАБОТАЕТ (Firefox метод)

| Параметр        | Значение                                              |
|-----------------|-------------------------------------------------------|
| URL             | https://www.dns-shop.ru/catalog/recipe/.../           |
| Защита          | Qrator WAF                                            |
| Playwright      | [X] Блокируется (401/403)                             |
| Firefox+xdotool | [+] Работает                                          |
| Формат данных   | JSON в catalog API                                    |

### Как работает

```bash
# 1. Запуск Firefox в Xvfb
xvfb-run firefox "$URL" &
sleep 35

# 2. Имитация пользователя
xdotool key Page_Down && sleep 1
xdotool key ctrl+u  # View Source
xdotool key ctrl+a && xdotool key ctrl+c

# 3. Парсинг JSON
# catalog.low_price, catalog.count
```

### Результат

```json
{
  "catalog": {
    "low_price": 62799,
    "count": 77,
    "name": "Apple MacBook Pro"
  }
}
```

---

## Ozon

### Статус: РАБОТАЕТ (Firefox метод)

| Параметр        | Значение                                              |
|-----------------|-------------------------------------------------------|
| URL             | https://www.ozon.ru/search/?text=MacBook+Pro+16       |
| Защита          | Headless browser detection                            |
| Playwright      | [X] Блокируется (403)                                 |
| Firefox+xdotool | [+] Работает                                          |
| Формат данных   | JSON ("finalPrice": N)                                |

### Парсинг цен

```python
# Method 1: finalPrice в JSON state
for match in re.findall(r'"finalPrice":\s*(\d+)', html):
    price = int(match)

# Method 2: data-widget prices
for match in re.findall(r'(\d{2,3})\s*(\d{3})\s*₽', html):
    price = int(match[0] + match[1])
```

---

## Yandex Market

### Статус: РАБОТАЕТ (Playwright Stealth)

| Параметр       | Значение                                              |
|----------------|-------------------------------------------------------|
| URL            | https://market.yandex.ru/search?text=MacBook+Pro+16   |
| Защита         | SmartCaptcha (обходится stealth)                      |
| Playwright     | [+] Работает (со stealth)                             |
| Формат данных  | JSON ("price":{"value":"N"})                          |

### Парсинг цен

```python
# Thin space (U+2006) в ценах!
match = re.search(r'"price":\s*\{\s*"value"\s*:\s*"?(\d+)"?', html)

# Селектор
elements = page.query_selector_all('[data-auto="price-value"]')
```

### Важно

- Цены содержат thin space (U+2006) - нужно очищать
- Нужна задержка 5-8 сек перед парсингом

---

## Citilink

### Статус: НЕСТАБИЛЬНЫЙ - Исключен из регулярных тестов

| Параметр               | Значение                                              |
|------------------------|-------------------------------------------------------|
| URL                    | https://www.citilink.ru/search/?text=MacBook+Pro+16   |
| Framework              | Next.js (React SSR)                                   |
| Защита                 | Агрессивный Rate Limiting (429)                       |
| Метод                  | Firefox + xdotool (citilink_scraper.sh)               |
| Стратегия              | Исключен из полных тестов, только по запросу          |
| Рекомендуемый интервал | Минимум 5-10 минут между запросами                    |
| Надежность             | 50-70% (зависит от IP и частоты)                      |

### Проблема Rate Limiting

**Симптомы:**
- HTTP 200, но `effectorValues` пустой объект `{}`
- Товары не загружаются через JavaScript
- Fallback метод (data-meta-price) находит только 1-2 цены вместо десятков
- Результат: products array пустой

**Что НЕ работает:**
- Смена метода (Firefox vs Playwright) - блокировка на API уровне
- Retry с задержками (90s, 150s, 210s) - помогает, но не всегда
- Увеличение initial delays - улучшает, но не решает проблему

**Что работает:**
- Интервалы между запросами: минимум 5-10 минут
- Резидентный IP (домашний интернет): выше надежность чем VPS
- Ручное тестирование по необходимости

### Использование

**ПРАВИЛЬНО:**
```bash
# Тестировать Citilink отдельно с интервалом 5+ минут
python test_scrapers.py --store=citilink

# Полный тест без Citilink
python test_scrapers.py --skip-unstable
```

**НЕПРАВИЛЬНО:**
```bash
# НЕ включать в частые полные тесты
python test_scrapers.py  # Будет FAIL для citilink

# НЕ запускать чаще 5 минут
for i in {1..10}; do python test_scrapers.py --store=citilink; done  # 429 ошибки
```

### Структура данных (Next.js)

```javascript
// __NEXT_DATA__ script
props.pageProps.effectorValues["..."].products[0].price.price
props.pageProps.effectorValues["..."].products[0].isAvailable
```

### Fallback

```python
# data-meta-price атрибут
prices = re.findall(r'data-meta-price="(\d+)"', html)
```

### История решения проблемы

| Дата       | Изменение                                       | Результат          |
|------------|-------------------------------------------------|--------------------|
| 2026-01-04 | Исключен из регулярных тестов (PS-20)           | [+] Стабильность   |
| 2026-01-03 | Переход на Firefox метод + увеличенные delays   | [~] 50-70%         |
| 2026-01-02 | Retry логика при 429 (90s, 150s, 210s)          | [~] Нестабильно    |
| 2025-12-31 | Playwright Stealth + delay                      | [X] CAPTCHA        |

---

## regard.ru

### Статус: РАБОТАЕТ (Playwright Stealth)

| Параметр       | Значение                                              |
|----------------|-------------------------------------------------------|
| URL            | https://www.regard.ru/catalog?search={query}          |
| Защита         | Bot detection                                         |
| Решение        | playwright-stealth + random delays                    |

### Парсинг

```python
# Schema.org
match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
```

---

## i-ray.ru

### Статус: РАБОТАЕТ (Playwright Direct)

| Параметр       | Значение                                              |
|----------------|-------------------------------------------------------|
| URL            | https://i-ray.ru/search?q={query}                     |
| Защита         | Нет                                                   |
| Метод          | Playwright Direct (без stealth)                       |

Простой магазин без защиты. Быстрый парсинг (3-4 сек).

---

## nix.ru

### Статус: РАБОТАЕТ (Playwright Direct)

| Параметр       | Значение                                              |
|----------------|-------------------------------------------------------|
| URL            | https://www.nix.ru/autocatalog/apple_notebook/...     |
| Защита         | Нет                                                   |
| URL тип        | Прямая ссылка на товар                                |

---

## kns.ru

### Статус: РАБОТАЕТ (Playwright Direct)

| Параметр       | Значение                                                |
|----------------|---------------------------------------------------------|
| URL            | https://www.kns.ru/product/noutbuk-apple-macbook-pro... |
| Защита         | Нет                                                     |
| URL тип        | Прямая ссылка на товар                                  |

---

## Заблокированные источники

### E-katalog.ru

| Параметр       | Значение                                              |
|----------------|-------------------------------------------------------|
| Проблема       | Блокировка серверных IP                               |
| Ping           | 100% packet loss                                      |
| Требуется      | Локальный запуск / VPN                                |

---

## Инфраструктура

### Сервера

| Сервер   | IP              | Провайдер  | Статус       |
|----------|-----------------|------------|--------------|
| VPS      | 185.105.108.119 | Datacenter | [X] CAPTCHA  |
| Archbook | 91.122.50.46    | Ростелеком | [+] Working  |

### Почему VPS не работает

- Datacenter IP в blacklist'ах
- Определяется как серверный трафик
- Citilink/DNS/Ozon блокируют

### Почему Archbook работает

- Резидентный IP (Ростелеком)
- Firefox real (не headless)
- xdotool имитирует пользователя

---

## Тестовый скрипт

```bash
# Запуск всех тестов
cd /home/sergey/price_scout/scripts
./venv/bin/python test_scrapers.py

# Один магазин
./venv/bin/python test_scrapers.py --store dns

# Быстрые тесты (без Firefox)
./venv/bin/python test_scrapers.py --quick
```

---

## История изменений

| Дата       | Изменение                                       |
|------------|-------------------------------------------------|
| 2026-01-03 | Avito работает! Исправлен парсер, 9/9 магазинов |
| 2026-01-02 | Ozon добавлен (Firefox метод)                   |
| 2026-01-02 | Yandex Market добавлен (Stealth метод)          |
| 2026-01-02 | Citilink: retry логика при 429                  |
| 2026-01-02 | Avito: подтверждено IP blocking                 |
| 2026-01-02 | ALL TESTS PASSED: 8/8 магазинов                 |
| 2025-12-31 | DNS-Shop: Firefox bypass для Qrator             |
| 2025-12-31 | Citilink: Playwright + delay                    |
| 2025-12-31 | regard.ru: Stealth bypass                       |
