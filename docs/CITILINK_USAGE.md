# Citilink: Руководство по использованию

## Статус: НЕСТАБИЛЬНЫЙ магазин

Citilink имеет агрессивный rate limiting и исключен из регулярных тестов.

## Быстрый старт

**Правильное использование:**

```bash
# Тестировать Citilink отдельно
python scripts/test_scrapers.py --store=citilink

# Ждать минимум 5 минут перед следующим запуском
sleep 300
python scripts/test_scrapers.py --store=citilink
```

**Тесты без Citilink:**

```bash
# Полный тест 8 стабильных магазинов
python scripts/test_scrapers.py --skip-unstable

# Результат: 8/8 PASSED (citilink SKIP)
```

## Почему Citilink нестабильный?

### Проблема

1. **Агрессивный rate limiting:**
   - HTTP 200, но `effectorValues = {}`
   - Товары не загружаются
   - Пустой массив products

2. **Блокировка на уровне API:**
   - Не решается сменой метода (Firefox, Playwright)
   - Retry с задержками помогает, но не всегда
   - Зависит от IP репутации

3. **Реальный пример:**
   ```
   [TEST] citilink (citilink_firefox)
     [FAIL] Rate limited (429) after 3 attempts
     Time: 0.0s
   ```

### Что работает

1. **Интервалы 5-10 минут между запросами**
2. **Резидентный IP** (домашний интернет > VPS datacenter IP)
3. **Ручное тестирование** по необходимости

## Использование в разных сценариях

### Сценарий 1: Разработка (частые тесты)

```bash
# Исключить Citilink
python test_scrapers.py --skip-unstable

# Результат: 8/8 PASSED
```

### Сценарий 2: Проверка всех магазинов

```bash
# День 1 - стабильные магазины
python test_scrapers.py --skip-unstable

# День 1 (через 10+ минут) - Citilink
python test_scrapers.py --store=citilink
```

### Сценарий 3: CI/CD пайплайн

```bash
# В .github/workflows/test.yml
- name: Test stable stores
  run: |
    cd scripts
    python test_scrapers.py --skip-unstable

# Citilink НЕ включаем в автоматические тесты
```

### Сценарий 4: Ручная проверка цен

```bash
# Утром проверить стабильные
python test_scrapers.py --skip-unstable

# Днем (через 5+ часов) проверить Citilink
python test_scrapers.py --store=citilink
```

## Частые ошибки

### ❌ НЕПРАВИЛЬНО

```bash
# 1. Частые запросы
for i in {1..10}; do
  python test_scrapers.py --store=citilink
done
# Результат: 9/10 - HTTP 429

# 2. Включение в регулярные тесты
cron: */5 * * * * python test_scrapers.py
# Результат: citilink FAIL каждые 5 минут

# 3. Тесты без --skip-unstable
python test_scrapers.py
# Результат: 8/9 PASSED, 1 FAIL (citilink)
```

### ✅ ПРАВИЛЬНО

```bash
# 1. Редкие запросы с интервалом
python test_scrapers.py --store=citilink
sleep 600  # 10 минут
python test_scrapers.py --store=citilink

# 2. Регулярные тесты БЕЗ Citilink
cron: */5 * * * * python test_scrapers.py --skip-unstable

# 3. Ручная проверка Citilink раз в день
cron: 0 10 * * * python test_scrapers.py --store=citilink
```

## Альтернативные решения (будущее)

1. **Прокси-ротация:**
   - Использовать резидентные прокси
   - Ротация IP между запросами
   - Стоимость: ~$50/месяц

2. **Официальный API:**
   - Если Citilink запустит партнерскую программу
   - Легальный доступ к данным

3. **Мобильное приложение:**
   - Парсинг через Android/iOS API
   - Меньше ограничений

## Техническая информация

**Конфигурация (test_scrapers.py):**

```python
StoreConfig(
    name="citilink",
    method="citilink_firefox",
    search_url="https://www.citilink.ru/search/?text=MacBook+Pro+16",
    parser="citilink_json",
    unstable=True,  # Помечен как нестабильный
)
```

**Параметры retry (test_citilink_special):**
- max_retries: 3
- retry_delay: 90s, 150s, 210s (инкремент +60s)
- initial_delay: 10-35s (зависит от попытки)
- Общее время: ~4.5 минуты максимум

**Скрипт:** `scripts/citilink_scraper.sh`
- Метод: Firefox + xdotool
- Save Page As + Clipboard fallback
- Парсинг __NEXT_DATA__ или data-meta-price

## Вопросы и ответы

**Q: Почему не использовать прокси сразу?**
A: Резидентные прокси стоят $50+/месяц. Пока не критично, используем ручное тестирование.

**Q: Можно ли вернуть Citilink в регулярные тесты?**
A: Да, если Citilink ослабит rate limiting или мы добавим прокси-ротацию.

**Q: Какие еще магазины нестабильные?**
A: Пока только Citilink. Остальные 8 магазинов стабильно работают.

**Q: Как часто можно тестировать Citilink?**
A: Рекомендуем раз в 5-10 минут. Максимум - раз в час безопасно.

## Changelog

| Дата       | Изменение                              |
|------------|----------------------------------------|
| 2026-01-04 | Исключен из регулярных тестов (PS-20)  |
| 2026-01-03 | Переход на citilink_firefox метод      |
| 2026-01-02 | Retry логика при 429                   |
| 2025-12-31 | Первая интеграция (Playwright)         |
