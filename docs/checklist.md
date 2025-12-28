## Чек‑лист ручных проверок для защиты

Ниже — список шагов, которые можно пройти в Swagger/curl/Postman во время приёма проекта. У каждого шага указано **что сделать** и **что должно быть в ответе**.

Типовые порты (сверить с `docker-compose.yml`):
- auth-service: `http://localhost:8001`
- catalog-service: `http://localhost:8002`
- order-service: `http://localhost:8003`
- analytics-service: `http://localhost:8004`

---

### 1. Старт инфраструктуры

- **Действие**: в корне проекта
  ```bash
  docker compose up --build
  ```
- **Проверка**:
  - Все контейнеры в состоянии `Up` (`docker compose ps`).
  - `GET /health`:
    - `http://localhost:8001/health`
    - `http://localhost:8002/health`
    - `http://localhost:8003/health`
    - `http://localhost:8004/health`
  - **Ожидаемый результат**: статус `200 OK`, тело:
    ```json
    { "status": "ok" }
    ```

---

### 2. Регистрация, логин и JWT (auth-service)

1. **Регистрация пользователя**:
   - **Запрос**: `POST http://localhost:8001/auth/register`
   - **Тело**:
     ```json
     {
       "email": "user@example.com",
       "password": "password123"
     }
     ```
   - **Ожидается**:
     - `201 Created` (либо `409 Conflict`, если вызывается повторно).
     - Тело содержит `id`, `email`, `role`, `is_active`, `created_at`.

2. **Логин**:
   - **Запрос**: `POST http://localhost:8001/auth/login`
   - **Тело**:
     ```json
     {
       "email": "user@example.com",
       "password": "password123"
     }
     ```
   - **Ожидается**:
     - `200 OK`.
     - Тело:
       ```json
       {
         "access_token": "<JWT>",
         "token_type": "bearer"
       }
       ```

3. **Профиль по JWT**:
   - **Запрос**: `GET /auth/me` с заголовком:
     - `Authorization: Bearer <JWT>`
   - **Ожидается**: `200 OK`, JSON пользователя.

---

### 3. Защищённые эндпоинты и роли

1. **Без JWT**:
   - **Запрос**: `POST http://localhost:8003/orders` без заголовка Authorization.
   - **Ожидается**: `401 Unauthorized` и JSON ошибки в формате:
     ```json
     {
       "error_code": "HTTP_ERROR",
       "message": "Not authenticated",
       "details": { ... }
     }
     ```

2. **Пользователь пытается вызвать admin‑endpoint**:
   - Под user‑токеном (обычный пользователь) вызвать:
     - `POST http://localhost:8002/books`
   - **Ожидается**: `403 Forbidden`, тело в едином формате ошибки.

---

### 4. Admin‑операции каталога (создание/импорт книги)

*(роль admin можно выдать вручную через SQL или заранее подготовить аккаунт)*

1. **Создание книги**:
   - **Запрос**: `POST http://localhost:8002/books`
   - **Заголовок**: `Authorization: Bearer <ADMIN_JWT>`
   - **Тело**:
     ```json
     {
       "title": "Test Book",
       "description": "Book description",
       "isbn": "1234567890123",
       "price": 10.5,
       "author_name": "Test Author",
       "category_names": ["Test Category"],
       "stock_quantity": 5
     }
     ```
   - **Ожидается**:
     - `201 Created`.
     - В ответе `stock_quantity = 5`, корректный `id`, `author`, `categories`.

2. **Импорт книги по ISBN**:
   - **Запрос**: `POST http://localhost:8002/books/import/by-isbn?isbn=<существующий ISBN>`
   - **Заголовок**: `Authorization: Bearer <ADMIN_JWT>`
   - **Ожидается**:
     - `201 Created` — книга создана на основе внешнего API.
     - В ответе заполнены хотя бы `title` и `isbn`.

---

### 5. Корзина и создание заказа (order-service)

1. **Добавление в корзину**:
   - **Запрос**: `POST http://localhost:8003/cart/items`
   - **Заголовок**: `Authorization: Bearer <USER_JWT>`
   - **Тело**:
     ```json
     {
       "book_id": 1,
       "qty": 2
     }
     ```
   - **Ожидается**:
     - `201 Created`.
     - Тело:
       ```json
       {
         "items": [
           { "book_id": 1, "quantity": 2 }
         ]
       }
       ```

2. **Просмотр корзины**:
   - **Запрос**: `GET http://localhost:8003/cart`
   - **Заголовок**: `Authorization: Bearer <USER_JWT>`
   - **Ожидается**: тот же набор items.

3. **Создание заказа**:
   - **Запрос**: `POST http://localhost:8003/orders`
   - **Заголовок**: `Authorization: Bearer <USER_JWT>`
   - **Ожидается**:
     - `201 Created`.
     - Ответ содержит:
       ```json
       {
         "id": <order_id>,
         "status": "created",
         "total_amount": ...,
         "items": [ ... ]
       }
       ```
     - Корзина после этого — пустая (`GET /cart` → `items: []`).

---

### 6. События RabbitMQ и аналитика

1. **Проверка публикации `order.created` и `stock.reserve.request`**:
   - После `POST /orders`:
     - Открыть RabbitMQ UI (`http://localhost:15672`), посмотреть сообщения/графы по exchange `bookstore.events`.
   - **Ожидается**: наличие сообщений по routing key `order.created` и `stock.reserve.request`.

2. **Проверка обработки `stock.reserve.request` в catalog-service**:
   - Для заказов с достаточным stock:
     - ожидается событие `stock.reserve.succeeded`.
   - Для заказов с недостаточным stock (например, qty > stock_quantity):
     - ожидается событие `stock.reserve.failed`.

3. **Проверка аналитики**:
   - **Запрос**: `GET http://localhost:8004/events`
   - **Ожидается**:
     - `200 OK`.
     - Тело содержит `items` со строками, где `routing_key` — `order.created`, `stock.reserve.succeeded` или `stock.reserve.failed`.

---

### 7. Проверка «не должно быть 500» и формата ошибок

1. **Неверные типы / отрицательное количество**:
   - `POST /cart/items` с телом:
     ```json
     { "book_id": 1, "qty": -1 }
     ```
   - **Ожидается**:
     - Код 4xx (`400` или `422`).
     - Тело соответствует формату:
       ```json
       {
         "error_code": "VALIDATION_ERROR" или "HTTP_ERROR",
         "message": "...",
         "details": { ... }
       }
       ```
     - Нет ответа `500 Internal Server Error`.

2. **Несуществующий `book_id` при создании заказа**:
   - Добавить в корзину книгу с несуществующим id.
   - `POST /orders`.
   - **Ожидается**: 4xx (например, `400`), стандартный JSON‑ответ ошибки.

3. **Пустые поля / сломанный JSON**:
   - Отправить пустое тело или некорректный JSON на любой POST.
   - **Ожидается**: 4xx + описанная ошибка валидации.

4. **Глобальные ошибки**:
   - При выключенной БД/брокере (для демонстрации) сервис должен вернуть `503 Service Unavailable` с JSON в едином формате, а не «сырым» 500.

---

### 8. Структура и документация

- **Swagger**:
  - Проверить, что для каждого сервиса доступен `/docs` и `/openapi.json`.
- **Документация**:
  - Папка `/docs` содержит:
    - `README_DOCS.md`, `api_contracts.md`, `event_contracts.md`, `business_requirements.md`, `defense_guide.md`, `runbook.md` и диаграммы.




