## Runbook: запуск и эксплуатация онлайн‑магазина книг

### 1. Зависимости

- Docker и Docker Compose.
- Порт 5432 (PostgreSQL) и порты 8001–8004 (микросервисы) должны быть свободны.

### 2. Переменные окружения

Базовый шаблон лежит в файле `env.example` в корне репозитория.

Основные переменные:

- **Общие**
  - `PYTHON_VERSION=3.11`
  - `JWT_SECRET` — секрет для подписи JWT (обязательно заменить для production).
  - `JWT_ALGORITHM=HS256`
  - `ACCESS_TOKEN_EXPIRE_MINUTES=30`
  - `RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/`
  - `RABBITMQ_EXCHANGE=bookstore.events`
- **БД**
  - `AUTH_DB_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/auth_db`
  - `CATALOG_DB_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/catalog_db`
  - `ORDER_DB_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/order_db`
  - `ANALYTICS_DB_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/analytics_db`

Перед первым запуском:

```bash
cp env.example .env   # Windows: copy env.example .env
```

### 3. Запуск всего стека

Из корня проекта:

```bash
docker compose up --build
```

Команда поднимет:

- PostgreSQL с БД:
  - `auth_db`, `catalog_db`, `order_db`, `analytics_db`
- RabbitMQ (порт `5672`, UI на `15672`).
- Сервисы:
  - auth-service — `http://localhost:8001`
  - catalog-service — `http://localhost:8002`
  - order-service — `http://localhost:8003`
  - analytics-service — `http://localhost:8004`

### 4. Healthcheck и диагностика

Каждый сервис предоставляет:

- `GET /health` — простой healthcheck, без авторизации:
  ```json
  { "status": "ok" }
  ```
- `GET /docs` и `GET /openapi.json` — Swagger UI и JSON‑схема API.

При проверке состояния:

1. Убедитесь, что контейнеры запущены:
   ```bash
   docker compose ps
   ```
2. Проверьте, что `http://localhost:<порт>/health` возвращает `{"status":"ok"}`.
3. Зайдите в RabbitMQ UI: `http://localhost:15672` (логин/пароль: guest/guest).

### 5. Типовой сценарий проверки функционала

1. **Регистрация и логин** (auth-service):
   - `POST http://localhost:8001/auth/register`
   - `POST http://localhost:8001/auth/login` → получить `access_token`.
2. **Создание admin‑пользователя**:
   - В учебных целях роль admin можно выдать вручную (через SQL `UPDATE users SET role='admin' WHERE email='...'`).
3. **Работа с каталогом** (catalog-service, под admin‑токеном):
   - `POST /books` — создать книгу.
   - `GET /books` — проверить, что книга видна в списке.
4. **Корзина и заказы** (order-service, под user‑токеном):
   - `POST /cart/items` — добавить книгу.
   - `GET /cart` — проверить корзину.
   - `POST /orders` — создать заказ.
5. **Проверка событий**:
   - В RabbitMQ UI убедиться в наличии сообщений по exchange `bookstore.events`.
   - В analytics-service: `GET http://localhost:8004/events` — увидеть события `order.created`, `stock.reserve.*`.

### 6. Типовые проблемы и решения

- **Проблема**: сервисы не могут подключиться к PostgreSQL.
  - **Проверить**:
    - Контейнер `postgres` запущен: `docker compose ps`.
    - Логи Postgres: `docker compose logs postgres`.
    - Соответствие URL в `.env` и `docker-compose.yml`.

- **Проблема**: не работает RabbitMQ или события.
  - **Проверить**:
    - Контейнер `rabbitmq` запущен.
    - В UI RabbitMQ exchange `bookstore.events` существует.
    - Логи order-service и catalog-service на наличие ошибок подключения.

- **Проблема**: много ответов `503 Service Unavailable`.
  - **Причина**: глобальный обработчик перехватывает непредвиденные исключения.
  - **Действия**:
    - Посмотреть логи соответствующего сервиса — в JSON‑логе будет событие `unhandled_exception`.
    - Проверить соединения с БД/RabbitMQ и корректность переменных окружения.

- **Проблема**: Swagger `/docs` не открывается.
  - **Проверить**:
    - Что контейнер сервиса запущен и слушает нужный порт.
    - Что прокси/фаервол не блокирует доступ.

### 7. Остановка и очистка

- Остановить сервисы:
  ```bash
  docker compose down
  ```
- Остановить и удалить данные (включая volume с БД):
  ```bash
  docker compose down -v
  ```

Использовать удаление volume аккуратно — оно удаляет все тестовые и продакшн‑данные PostgreSQL.


