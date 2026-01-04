# Price Scout - Стратегия парсинга

> Обновлено: 2026-01-04

## Текущий статус: 9 магазинов (8 стабильных + 1 нестабильный)

### Работающие магазины

| Магазин       | Метод                 | Защита           | Время   | Статус       |
|---------------|-----------------------|------------------|---------|--------------|
| DNS-Shop      | Firefox + xdotool     | Qrator (сложная) | 38.2s   | [+] PASS     |
| Ozon          | Firefox + xdotool     | Bot detection    | 52.4s   | [+] PASS     |
| i-ray.ru      | Playwright Direct     | Нет              | 4.1s    | [+] PASS     |
| Citilink      | Firefox + xdotool     | Rate Limit (429) | N/A     | [~] UNSTABLE |
| nix.ru        | Playwright Direct     | Нет              | 3.6s    | [+] PASS     |
| regard.ru     | Playwright Stealth    | Bot detection    | 7.9s    | [+] PASS     |
| kns.ru        | Playwright Direct     | Нет              | 3.5s    | [+] PASS     |
| Yandex Market | Playwright + Stealth  | SmartCaptcha     | 15.4s   | [+] PASS     |
| Avito         | Firefox + xdotool     | Rate Limit       | 46.6s   | [+] PASS     |

**Примечание:** Citilink исключен из регулярных тестов из-за агрессивного rate limiting.
Тестируется только по запросу: `--store=citilink` с интервалом 5+ минут.

### Заблокированные магазины

| Магазин       | Проблема           | Требуется        |
|---------------|--------------------|------------------|
| E-katalog.ru  | IP блокировка      | Локальный запуск |

---

## Методы парсинга

### 1. Playwright Direct

**Для:** Магазины без защиты (i-ray, nix, kns)

```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 ...",
        locale="ru-RU",
    )
    page = context.new_page()
    response = page.goto(url, wait_until="domcontentloaded")
    html = page.content()
```

**Преимущества:**
- Быстрый (3-5 сек)
- Простой
- Минимум ресурсов

### 2. Playwright Stealth

**Для:** Магазины с базовой защитой (regard, Citilink, Yandex Market)

```python
from playwright_stealth import Stealth

stealth = Stealth(
    navigator_languages_override=("ru-RU", "ru"),
    navigator_platform_override="Win32",
)
stealth.apply_stealth_sync(page)
```

**Особенности:**
- Патчит `navigator.webdriver`
- Эмулирует реальный браузер
- Добавляет случайные задержки

### 3. Firefox + xdotool (Xvfb)

**Для:** Сложная защита (DNS-Shop, Ozon)

```bash
# Запуск в виртуальном дисплее
xvfb-run -a --server-args="-screen 0 1920x1080x24" firefox "$URL" &

# Ожидание загрузки
sleep 30

# Имитация действий пользователя
xdotool key Page_Down
xdotool key ctrl+u  # View Source
xdotool key ctrl+a  # Select All
xdotool key ctrl+c  # Copy

# Сохранение из буфера
xclip -selection clipboard -o > output.html
```

**Почему работает:**
- Реальный Firefox (не headless)
- Нет признаков автоматизации
- Полная эмуляция пользователя

---

## Retry логика (Citilink)

```python
max_retries = 3
retry_delay = 30  # секунд

for attempt in range(max_retries):
    response = page.goto(url)

    if response.status == 429:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            retry_delay += 15  # Увеличиваем задержку
            continue
        else:
            return "FAIL"

    # Успех
    break
```

---

## Парсинг данных

### Schema.org / JSON-LD

```python
# itemprop="price"
match = re.search(r'itemprop="price"\s+content="(\d+)"', html)

# JSON-LD
match = re.search(r'"price":\s*(\d+)', html)
```

### Next.js (Citilink)

```python
match = re.search(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
    html
)
data = json.loads(match.group(1))
products = data["props"]["pageProps"]["effectorValues"]["..."]["products"]
```

### Yandex Market

```python
# Thin space (U+2006) в ценах
match = re.search(r'"price":\s*\{\s*"value"\s*:\s*"?(\d+)"?', html)

# Альтернатива: data-auto="price-value"
elements = page.query_selector_all('[data-auto="price-value"]')
```

### DNS-Shop JSON API

```python
# Данные в catalog JSON
with open(json_path) as f:
    data = json.load(f)

price = data["catalog"]["low_price"]
count = data["catalog"]["count"]
```

---

## Инфраструктура

### Сервера

| Сервер   | IP              | Провайдер  | Использование |
|----------|-----------------|------------|---------------|
| VPS      | 185.105.108.119 | Datacenter | CAPTCHA       |
| Archbook | 91.122.50.46    | Ростелеком | Production    |

### Почему Archbook работает

1. **Резидентный IP** (Ростелеком) - не в blacklist'ах
2. **i3 window manager** - легковесный WM для Xvfb
3. **Firefox real** - не определяется как бот
4. **xdotool** - имитация реальных действий

---

## Антибот защита

### Типы защиты и методы обхода

| Защита            | Примеры          | Решение                      |
|-------------------|------------------|------------------------------|
| Headless detect   | Ozon, DNS        | Firefox + xdotool            |
| Rate limiting     | Citilink         | Retry + задержки 30-60 сек   |
| Bot detection     | regard           | Playwright Stealth           |
| SmartCaptcha      | Yandex           | Stealth + медленная загрузка |
| IP blocking       | Avito            | Прокси (не решено)           |
| Qrator WAF        | DNS-Shop         | Firefox + резидентный IP     |

### Рекомендуемые задержки

| Магазин       | Между запросами | После загрузки |
|---------------|-----------------|----------------|
| i-ray, nix    | 2-3 сек         | 2 сек          |
| regard        | 3-5 сек         | 2-4 сек        |
| Citilink      | 8-15 сек        | 5-8 сек        |
| DNS, Ozon     | 30-45 сек       | 35 сек         |
| Yandex Market | 5-8 сек         | 5-8 сек        |

---

## Скрипты

| Скрипт                 | Метод                | Магазины                    |
|------------------------|----------------------|-----------------------------|
| test_scrapers.py       | Unified test system  | Все 8 магазинов             |
| dns_scraper.sh         | Firefox + xdotool    | DNS-Shop                    |
| ozon_scraper.sh        | Firefox + xdotool    | Ozon                        |
| stealth_scraper.py     | Playwright Stealth   | regard.ru                   |
| citilink_playwright.py | Playwright + delay   | Citilink                    |

---

## Управление нестабильными магазинами

### Citilink: Стратегия минимальной частоты

**Проблема:**
Citilink блокирует частые запросы даже с Firefox методом и увеличенными задержками.

**Решение:**
```bash
# Исключить из регулярных тестов
python test_scrapers.py --skip-unstable

# Тестировать вручную с интервалом 5-10 минут
python test_scrapers.py --store=citilink
```

**Рекомендации:**
- Минимальный интервал между запросами: 5 минут
- Не запускать в автоматических CI/CD пайплайнах
- Использовать только для ручной проверки цен
- Резидентный IP (домашний интернет) более надежен чем VPS

**Альтернативы (будущее):**
- Прокси-ротация с резидентными IP
- Использование официального API Citilink (если появится)
- Парсинг через мобильное приложение

---

## Следующие шаги

- [X] Добавить Ozon (Firefox метод)
- [X] Добавить Yandex Market (Stealth метод)
- [X] Добавить Avito (Firefox метод)
- [X] Retry логика для Citilink (429)
- [X] Исключить Citilink из регулярных тестов (PS-20)
- [ ] Прокси для нестабильных магазинов
- [ ] Локальный запуск для E-katalog
- [ ] Автоматический сбор цен по расписанию
