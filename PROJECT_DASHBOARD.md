# Price Scout - Project Dashboard

> Последнее обновление: 2025-12-31

---

## Kanban Board

### Backlog

| ID   | Задача                                   | Приоритет | План                              |
|------|------------------------------------------|-----------|-----------------------------------|
| PS-5 | Создать Python прототип парсера          | Medium    | [PARSING_STRATEGY.md]             |
| PS-6 | Настроить PostgreSQL схему               | Medium    | [TECH_STACK.md]                   |
| PS-7 | Настроить Redis кэширование              | Low       | [TECH_STACK.md]                   |
| PS-8 | Реализовать Telegram бот (teloxide)      | Medium    | [ROADMAP.md]                      |

### In Progress

| ID   | Задача                                   | Приоритет | План                              |
|------|------------------------------------------|-----------|-----------------------------------|
| PS-2 | Исследовать альтернативные источники     | High      | [API_ENDPOINTS.md]                |

### Review

| ID   | Задача                                   | Приоритет | План                               |
|------|------------------------------------------|-----------|------------------------------------|
| PS-1 | Диагностика API E-katalog.ru             | High      | [API_ENDPOINTS.md] - ЗАБЛОКИРОВАНО |

### Done

| ID   | Задача                                   | Дата       | План                              |
|------|------------------------------------------|------------|-----------------------------------|
| PS-0 | Документация и планирование проекта      | 2025-12-31 | [README.md]                       |

---

## Quick Links

| Документ                   | Описание                              | Путь                              |
|----------------------------|---------------------------------------|-----------------------------------|
| README                     | Обзор проекта                         | [README.md](README.md)            |
| Roadmap                    | Фазы разработки                       | [docs/ROADMAP.md]                 |
| Tech Stack                 | Архитектура и технологии              | [docs/TECH_STACK.md]              |
| Parsing Strategy           | Стратегия парсинга                    | [docs/PARSING_STRATEGY.md]        |
| API Research               | Исследование API                      | [docs/API_RESEARCH.md]            |
| API Diagnostics            | План диагностики E-katalog            | [docs/API_DIAGNOSTICS_PLAN.md]    |
| API Endpoints              | Результаты диагностики                | [docs/API_ENDPOINTS.md]           |
| Market Research            | Анализ рынка                          | [docs/MARKET_RESEARCH.md]         |

---

## Project Stats

| Метрика                    | Значение         |
|----------------------------|------------------|
| Фаза                       | MVP (Phase 1)    |
| Статус                     | Planning         |
| Задач в Backlog            | 4                |
| Задач In Progress          | 1                |
| Задач Done                 | 1                |

---

## Current Focus

**PS-2: Исследовать альтернативные источники**

Цель: Найти доступные источники данных о ценах

**Блокер PS-1:** E-katalog.ru недоступен с серверных IP (см. [API_ENDPOINTS.md])

Шаги:
- [ ] Исследовать публичные API маркетплейсов (Ozon, WB, YM)
- [ ] Проверить альтернативные агрегаторы (price.ru, sravni.com)
- [ ] Оценить стоимость прокси-сервисов
- [ ] Протестировать локально с домашнего ПК

---

## Changelog

| Дата       | Изменение                                          |
|------------|----------------------------------------------------|
| 2025-12-31 | PS-1 заблокирован: e-katalog.ru недоступен         |
| 2025-12-31 | Создан API_ENDPOINTS.md с результатами диагностики |
| 2025-12-31 | Создан дашборд проекта                             |
| 2025-12-31 | Добавлен план диагностики API                      |
| 2025-12-31 | Начальная документация проекта                     |

[PARSING_STRATEGY.md]: docs/PARSING_STRATEGY.md
[TECH_STACK.md]: docs/TECH_STACK.md
[ROADMAP.md]: docs/ROADMAP.md
[API_DIAGNOSTICS_PLAN.md]: docs/API_DIAGNOSTICS_PLAN.md
[API_ENDPOINTS.md]: docs/API_ENDPOINTS.md
[README.md]: README.md
