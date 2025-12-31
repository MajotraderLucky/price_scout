# API Endpoints - Результаты диагностики

> Дата: 2025-12-31

---

## E-katalog.ru

### Статус: НЕДОСТУПЕН

| Параметр            | Значение                                          |
|---------------------|---------------------------------------------------|
| IP адрес            | 83.222.5.34                                       |
| Ping                | 100% packet loss                                  |
| HTTP (80)           | Connection timeout                                |
| HTTPS (443)         | Connection timeout                                |
| Причина             | Блокировка серверных/облачных IP                  |

### Вывод

E-katalog.ru блокирует запросы с серверных IP-адресов. Для работы с этим источником потребуется:

1. **Локальный запуск** - парсер должен работать на домашнем ПК/ноутбуке
2. **Резидентные прокси** - использовать прокси с жилыми IP
3. **VPN** - подключение через VPN с российским IP
4. **Headless браузер** - Playwright/Puppeteer могут обходить некоторые блокировки

---

## Альтернативные источники (предварительная проверка)

| Источник          | HTTP Status | Доступность | Примечание                        |
|-------------------|-------------|-------------|-----------------------------------|
| ozon.ru           | 307         | Частично    | Редирект, требует cookies/JS      |
| wildberries.ru    | 498         | Блокируется | Кастомный код ошибки              |
| dns-shop.ru       | Не проверен | -           | -                                 |

---

## Рекомендации

### Краткосрочные (для тестирования)

1. Тестировать парсер **локально** на домашней машине
2. Использовать **Playwright** с реальным браузером
3. Добавить случайные задержки (2-5 сек между запросами)

### Долгосрочные (для production)

1. Исследовать **публичные API** маркетплейсов:
   - Ozon Seller API
   - Wildberries API
   - Yandex Market API

2. Рассмотреть **платные решения**:
   - Прокси-сервисы с резидентными IP
   - Готовые API агрегаторы цен

3. **Гибридная архитектура**:
   - Бот и API на сервере
   - Парсер на локальной машине (через очередь задач)

---

## Следующие шаги

- [ ] Протестировать e-katalog.ru локально (домашний ПК)
- [ ] Исследовать публичные API маркетплейсов
- [ ] Оценить стоимость прокси-сервисов
- [ ] Рассмотреть альтернативные агрегаторы (price.ru, sravni.com)

---

---

## Citilink

### Статус: CAPTCHA REQUIRED

| Параметр            | Значение                                          |
|---------------------|---------------------------------------------------|
| HTTP Status         | 429 (Too Many Requests)                           |
| Framework           | Next.js (React SSR)                               |
| Данные              | JSON в `__NEXT_DATA__`                            |
| Защита              | CAPTCHA + Rate Limiting                           |
| isCaptchaRequired   | true                                              |
| isBlockedByDelay    | true                                              |

### Структура данных (Next.js)

```javascript
// Продукты находятся в:
props.initialState.subcategory.productsFilter.payload.productsFilter.products

// Информация об авторизации:
props.initialState.authModule.auth.isCaptchaRequired
props.initialState.authModule.auth.isBlockedByDelay
```

### Вывод

Citilink возвращает пустой массив продуктов при активной CAPTCHA. Для обхода нужно:
1. Решить CAPTCHA (2Captcha/Anti-Captcha)
2. Использовать сессионные cookies
3. Эмулировать поведение пользователя

---

## DNS-Shop

### Статус: BLOCKED (401)

| Параметр            | Значение                                          |
|---------------------|---------------------------------------------------|
| HTTP Status         | 401 Unauthorized                                  |
| Защита              | Серверная проверка ботов                          |
| Playwright          | Не помогает                                       |

### Вывод

DNS использует продвинутую защиту, которая блокирует даже headless браузеры.

---

## Логи тестирования

### 2025-12-31 - Playwright тесты

```
$ ping -c 3 e-katalog.ru
PING e-katalog.ru (83.222.5.34) 56(84) bytes of data.
--- e-katalog.ru ping statistics ---
3 packets transmitted, 0 received, 100% packet loss

$ curl -v --connect-timeout 10 "https://e-katalog.ru/"
* Trying 83.222.5.34:443...
* Failed to connect to e-katalog.ru port 443 after 10000 ms: Timeout was reached
curl: (28) Failed to connect to e-katalog.ru port 443 after 10000 ms: Timeout was reached
```

**Окружение:** Linux server, не-российский IP
