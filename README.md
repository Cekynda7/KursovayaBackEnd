## Bookstore Backend (Microservices, FastAPI, RabbitMQ, PostgreSQL)

Монорепозиторий курсового проекта: backend онлайн-магазина книг на микросервисной архитектуре.

### Сервисы
- **auth-service**: регистрация, логин, JWT, роли (user/admin).
- **catalog-service**: каталог книг, CRUD, поиск, импорт по ISBN из внешнего API.
- **order-service**: корзина, заказы, публикация событий в RabbitMQ.
- **analytics-service**: подписка на события и запись статистики.

### Быстрый старт
1. **Скопировать env-шаблон**
   ```bash
   cp env.example .env
   ```
   При необходимости скорректировать переменные (секреты, URL БД и т.д.).

2. **Запуск всего стека**
   ```bash
   docker compose up --build
   ```

3. **Порты сервисов**
- auth-service: `http://localhost:8001`
- catalog-service: `http://localhost:8002`
- order-service: `http://localhost:8003`
- analytics-service: `http://localhost:8004`
- RabbitMQ management UI: `http://localhost:15672` (guest/guest)

4. **OpenAPI/Swagger**
- auth: `http://localhost:8001/docs`
- catalog: `http://localhost:8002/docs`
- order: `http://localhost:8003/docs`
- analytics: `http://localhost:8004/docs`

5. **Примеры curl (кратко)**
- Регистрация:
  ```bash
  curl -X POST http://localhost:8001/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"string"}'
  ```
- Логин:
  ```bash
  curl -X POST http://localhost:8001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"string"}'
  ```
- Получение профиля:
  ```bash
  curl http://localhost:8001/auth/me \
    -H "Authorization: Bearer <ACCESS_TOKEN>"
  ```

Подробные примеры для catalog и order будут в описаниях соответствующих сервисов и в OpenAPI.


