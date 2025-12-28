## Troubleshooting: типовые проблемы и быстрые решения

Этот файл можно использовать прямо на защите, если что-то «упало» во время демо.

---

### 1. RabbitMQ: сервисы не обрабатывают/не публикуют события

**Симптомы:**
- В RabbitMQ UI нет exchange `bookstore.events`.
- В аналитике (`GET /events`) не появляются новые события после создания заказа.

**Проверки:**
1. Контейнер RabbitMQ:
   ```bash
   docker compose ps rabbitmq
   docker compose logs rabbitmq
   ```
2. В UI `http://localhost:15672` (guest/guest):
   - Есть ли exchange `bookstore.events`?
   - Есть ли очереди, привязанные к нужным routing keys?

**Решения:**
- Перезапустить только RabbitMQ и зависящие сервисы:
  ```bash
  docker compose restart rabbitmq auth-service catalog-service order-service analytics-service
  ```
- Убедиться, что `RABBITMQ_URL` и `RABBITMQ_EXCHANGE` совпадают с `docker-compose.yml`:
  - URL: `amqp://guest:guest@rabbitmq:5672/`
  - exchange: `bookstore.events`.

---

### 2. Миграции БД: таблицы не создались / ошибки при доступе к БД

**Симптомы:**
- При запросах 500/503 или ошибки в логах «relation ... does not exist».
- В Postgres отсутствуют таблицы `users`, `books`, `orders`, `events` и т.д.

**Проверки:**
1. Логи postgres:
   ```bash
   docker compose logs postgres
   ```
2. Подключиться к БД (например, через `psql` или Adminer) и проверить наличие баз:
   - `auth_db`, `catalog_db`, `order_db`, `analytics_db`.

**Решения:**
- Пересоздать БД (только для учебного запуска):
  ```bash
  docker compose down -v
  docker compose up --build
  ```
- При необходимости прогнать Alembic миграции внутри контейнеров (опционально), например:
  ```bash
  docker compose exec auth-service alembic upgrade head
  docker compose exec catalog-service alembic upgrade head
  docker compose exec order-service alembic upgrade head
  docker compose exec analytics-service alembic upgrade head
  ```

---

### 3. JWT: 401/403 при корректных запросах

**Симптомы:**
- Swagger/curl возвращает `401 Unauthorized` или `403 Forbidden`, хотя логин прошёл успешно.

**Проверки:**
1. Проверить, что токен передаётся:
   - Заголовок: `Authorization: Bearer <access_token>`.
2. Убедиться, что используете **access_token** именно из ответа `/auth/login`, а не из другого окружения.
3. Для admin‑операций:
   - убедиться, что используемый пользователь действительно имеет роль `admin` (можно проверить через БД в таблице `users`).

**Решения:**
- Повторно залогиниться и обновить переменную `TOKEN`/`ADMIN_TOKEN` в окружении.
- В случае admin — вручную обновить роль в БД:
  ```sql
  UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
  ```

---

### 4. CORS / доступ из браузера

**Симптомы:**
- С фронтенда или Swagger‑UI браузер жалуется на CORS (blocked by CORS policy).

**Проверки:**
- В текущем курсовом бэкенде CORS не акцентирован, но для фронта может понадобиться.

**Решения (при необходимости):**
- Добавить `CORSMiddleware` в каждый FastAPI‑сервис:
  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- Пересобрать контейнер и перезапустить сервис.

---

### 5. Неожиданные 500/503 и формат ошибок

**Симптомы:**
- Клиент получает 500/503 или некрасивый HTML/traceback вместо JSON.

**Проверки:**
1. Посмотреть логи конкретного сервиса:
   ```bash
   docker compose logs auth-service
   docker compose logs catalog-service
   docker compose logs order-service
   docker compose logs analytics-service
   ```
2. Убедиться, что ответ всё равно приходит в едином формате:
   ```json
   {
     "error_code": "INTERNAL_ERROR",
     "message": "Service temporarily unavailable",
     "details": null
   }
   ```

**Решения:**
- Если ошибка связана с недоступностью БД или RabbitMQ:
  - проверить соответствующие контейнеры и окружение (`DB_URL`, `RABBITMQ_URL`);
  - перезапустить проблемный сервис.
- Если ошибка при валидации/бизнес‑логике:
  - проверить входные данные и предусмотреть обработку edge case (например, qty > 0, существующий book_id).

---

### 6. Проблемы с env и портами

**Симптомы:**
- Сервисы не стартуют или не могут подключиться к БД/брокеру.

**Проверки:**
1. Файл `.env`:
   - должен быть создан из `env.example`.
   - значения URL‑ов должны совпадать с `docker-compose.yml` (имя хоста `postgres`, `rabbitmq`).
2. Порты:
   - 8001–8004 не заняты другими процессами.

**Решения:**
- Пересоздать `.env`:
  ```bash
  cp env.example .env
  ```
- Остановить все старые контейнеры/процессы, мешающие портам:
  ```bash
  docker ps
  docker stop <id>
  ```

---

### 7. Swagger /docs не открывается

**Симптомы:**
- При переходе на `http://localhost:8001/docs` (или 8002/8003/8004) ничего не открывается.

**Проверки:**
1. Сервис запущен:
   ```bash
   docker compose ps auth-service
   docker compose logs auth-service
   ```
2. `GET /health` возвращает `{"status":"ok"}`.

**Решения:**
- Проверить, что порты проброшены в `docker-compose.yml`:
  - `8001:8000` для auth и т.д.
- При необходимости сделать `docker compose restart <service>`.

---

### 8. Нет событий в analytics-service

**Симптомы:**
- `GET /events` возвращает пустой список даже после создания заказов.

**Проверки:**
1. Логи analytics‑сервиса:
   ```bash
   docker compose logs analytics-service
   ```
   - Должно быть сообщение `analytics_consumer_started`.
2. Убедиться, что consumer стартует на событие `startup` приложения.

**Решения:**
- Перезапустить analytics‑service:
  ```bash
  docker compose restart analytics-service
  ```
- Убедиться, что `RABBITMQ_URL` и `RABBITMQ_EXCHANGE` в `.env` корректны.




