# Price Scout - Стратегия парсинга

## Выбранный источник: E-katalog.ru

### Почему E-katalog

| Критерий                | E-katalog              | Прямой парсинг WB/Ozon |
|-------------------------|------------------------|------------------------|
| Количество источников   | 1 сайт                 | 5+ сайтов              |
| Охват магазинов         | Сотни                  | По 1 на каждый         |
| Сложность поддержки     | Низкая                 | Высокая                |
| Блокировки              | Умеренные              | Агрессивные            |
| История цен             | [+] Есть               | [X] Нужно собирать     |
| Стоимость               | Бесплатно              | Бесплатно              |

---

## Стратегия парсинга

### Приоритет 1: Поиск скрытого API

Перед написанием HTML-парсера необходимо исследовать сайт на наличие внутреннего API.

**Преимущества скрытого API:**
- Скорость: ~0.3 сек vs ~5 сек (HTML)
- Стабильность: не зависит от изменений верстки
- Структурированные данные: JSON/Protobuf

**Методика поиска:**

```
1. Открыть DevTools -> Network
2. Выполнить поиск на сайте
3. Фильтровать по XHR/Fetch
4. Искать запросы с JSON/Protobuf ответами
5. Проанализировать структуру запросов
```

**Признаки скрытого API:**
- Content-Type: application/json
- Content-Type: application/x-protobuf
- URL содержит /api/, /v1/, /graphql

---

### Приоритет 2: HTML парсинг (fallback)

Если скрытое API не найдено, используем Playwright для парсинга HTML.

**Технологии:**

| Компонент        | Rust                   | Python (прототип)      |
|------------------|------------------------|------------------------|
| Браузер          | chromiumoxide          | Playwright             |
| HTML парсинг     | scraper                | BeautifulSoup          |
| Антидетект       | Собственная реализация | playwright-stealth     |

---

## План исследования E-katalog

### Этап 1: Разведка (1-2 часа)

```bash
# Задачи:
1. Открыть https://e-katalog.ru в браузере
2. DevTools -> Network -> включить "Preserve log"
3. Выполнить поиск "Samsung Galaxy S24"
4. Записать все XHR/Fetch запросы
5. Проанализировать ответы на наличие JSON
```

**Чек-лист:**

- [ ] Найти endpoint поиска
- [ ] Найти endpoint получения цен
- [ ] Определить параметры запросов
- [ ] Проверить необходимость авторизации
- [ ] Проверить наличие rate limiting

### Этап 2: Прототип парсера (2-4 часа)

```python
# Python прототип для быстрой проверки концепции
from playwright.sync_api import sync_playwright

def search_ekatalog(query: str) -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
        )
        page = context.new_page()

        # Поиск
        url = f"https://e-katalog.ru/ek-list.php?search_={query}"
        page.goto(url)
        page.wait_for_load_state("networkidle")

        # Извлечение данных (селекторы уточнить!)
        products = []
        cards = page.query_selector_all(".model-short-block")

        for card in cards:
            name = card.query_selector(".model-short-title")
            price = card.query_selector(".model-price-range")

            if name and price:
                products.append({
                    "name": name.inner_text(),
                    "price": price.inner_text(),
                })

        browser.close()
        return products
```

### Этап 3: Определение CSS-селекторов

**Предполагаемая структура (требует проверки):**

| Элемент           | Предполагаемый селектор        |
|-------------------|--------------------------------|
| Карточка товара   | `.model-short-block`           |
| Название          | `.model-short-title a`         |
| Диапазон цен      | `.model-price-range`           |
| Мин. цена         | `.price-range .pr31`           |
| Ссылка на товар   | `.model-short-title a[href]`   |
| Изображение       | `.model-short-img img`         |

**Страница товара (для получения цен по магазинам):**

| Элемент           | Предполагаемый селектор        |
|-------------------|--------------------------------|
| Таблица цен       | `.where-buy-table`             |
| Магазин           | `.where-buy-shop-name`         |
| Цена              | `.where-buy-price`             |
| Ссылка            | `.where-buy-link a[href]`      |

---

## Антибот меры

### Защита E-katalog (ожидаемая)

| Мера                  | Вероятность | Решение                       |
|-----------------------|-------------|-------------------------------|
| Rate limiting         | Высокая     | Задержки 2-5 сек между зап.   |
| User-Agent проверка   | Высокая     | Реалистичный UA               |
| Cookie проверка       | Средняя     | Сохранение сессии             |
| JavaScript challenge  | Средняя     | Playwright (реальный браузер) |
| CAPTCHA               | Низкая      | Ручное решение / сервисы      |
| IP блокировка         | Низкая      | Ротация при необходимости     |

### Рекомендуемые настройки

```python
# Playwright context settings
context = browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    viewport={"width": 1920, "height": 1080},
    locale="ru-RU",
    timezone_id="Europe/Moscow",
)

# Задержки между запросами
import random
import time

def random_delay():
    time.sleep(random.uniform(2, 5))
```

---

## Кэширование

### Стратегия кэширования

| Тип данных           | TTL        | Хранилище  |
|----------------------|------------|------------|
| Результаты поиска    | 1 час      | Redis      |
| Цены на товар        | 1 час      | Redis      |
| Информация о товаре  | 24 часа    | PostgreSQL |
| История цен          | Бессрочно  | PostgreSQL |

### Redis ключи

```
search:{query_hash}           -> JSON результатов поиска
product:{product_id}:prices   -> JSON цен по магазинам
product:{product_id}:info     -> JSON информации о товаре
```

---

## Расписание проверок

### MVP (Фаза 1)

- Парсинг только по запросу пользователя
- Кэширование на 1 час

### Фаза 2 (Отслеживание)

| Категория товаров    | Частота проверки |
|----------------------|------------------|
| Отслеживаемые        | Каждые 6 часов   |
| Популярные запросы   | Каждые 12 часов  |
| Остальные            | По запросу       |

---

## Метрики и мониторинг

### Что отслеживать

| Метрика                    | Цель              |
|----------------------------|-------------------|
| Время ответа парсера       | < 10 сек          |
| Процент успешных запросов  | > 95%             |
| Cache hit rate             | > 70%             |
| Количество блокировок      | < 1% запросов     |

---

## Следующие шаги

1. [ ] Исследовать E-katalog через DevTools
2. [ ] Найти скрытое API (если есть)
3. [ ] Определить точные CSS-селекторы
4. [ ] Создать Python прототип парсера
5. [ ] Протестировать на 100 запросах
6. [ ] Портировать на Rust для production
