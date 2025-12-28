## Demo script: сценарий демонстрации (curl)

Ниже — пошаговый сценарий демо, который можно прогнать прямо на защите.  
Используются переменные окружения:

```bash
export AUTH_URL=http://localhost:8001
export CATALOG_URL=http://localhost:8002
export ORDER_URL=http://localhost:8003
export ANALYTICS_URL=http://localhost:8004
```

Для Windows PowerShell:

```powershell
$env:AUTH_URL="http://localhost:8001"
$env:CATALOG_URL="http://localhost:8002"
$env:ORDER_URL="http://localhost:8003"
$env:ANALYTICS_URL="http://localhost:8004"
```

---

### Шаг 0. Запуск инфраструктуры

```bash
docker compose up --build
```

Проверить health:

```bash
curl $AUTH_URL/health
curl $CATALOG_URL/health
curl $ORDER_URL/health
curl $ANALYTICS_URL/health
```

Ожидается: `{"status":"ok"}`.

---

### Шаг 1. Регистрация и логин обычного пользователя

```bash
curl -X POST $AUTH_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

Если пользователь уже есть, будет `409 Conflict` — это нормально.

```bash
USER_LOGIN_RESPONSE=$(curl -s -X POST $AUTH_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}')
echo $USER_LOGIN_RESPONSE
export USER_TOKEN=$(echo $USER_LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "USER_TOKEN=$USER_TOKEN"
```

Проверяем `/auth/me`:

```bash
curl -s $AUTH_URL/auth/me \
  -H "Authorization: Bearer $USER_TOKEN" | jq
```

---

### Шаг 2. Подготовка admin‑пользователя (упрощённо)

В учебных условиях проще всего:

1. Либо заранее создать admin‑запись в БД (через SQL или миграцию).
2. Либо продемонстрировать смену роли в БД и затем залогиниться под этим аккаунтом.

Далее предполагается, что есть `admin@example.com` с паролем `password123` и ролью `admin`.

```bash
ADMIN_LOGIN_RESPONSE=$(curl -s -X POST $AUTH_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}')
echo $ADMIN_LOGIN_RESPONSE
export ADMIN_TOKEN=$(echo $ADMIN_LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "ADMIN_TOKEN=$ADMIN_TOKEN"
```

---

### Шаг 3. Проверка защиты эндпоинтов (401/403)

1. Без токена:

```bash
curl -i $ORDER_URL/orders
```

Ожидается: `401 Unauthorized` и JSON ошибки.

2. User пытается вызвать admin‑endpoint:

```bash
curl -i -X POST $CATALOG_URL/books \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"title":"X","description":"Y","isbn":"111","price":10.5,"author_name":"A","category_names":["C"],"stock_quantity":1}'
```

Ожидается: `403 Forbidden` и JSON в формате `{error_code, message, details}`.

---

### Шаг 4. Создание книги (admin)

```bash
CREATE_BOOK_RESPONSE=$(curl -s -X POST $CATALOG_URL/books \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
        "title":"Demo Book",
        "description":"Book from demo_script",
        "isbn":"9999999999999",
        "price":15.5,
        "author_name":"Demo Author",
        "category_names":["Demo Category"],
        "stock_quantity":5
      }')
echo $CREATE_BOOK_RESPONSE | jq
export BOOK_ID=$(echo $CREATE_BOOK_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "BOOK_ID=$BOOK_ID"
```

Проверяем, что книга появилась:

```bash
curl -s "$CATALOG_URL/books?query=Demo" | jq
curl -s $CATALOG_URL/books/$BOOK_ID | jq
```

---

### Шаг 5. Импорт книги по ISBN (опционально в демо)

```bash
curl -s -X POST "$CATALOG_URL/books/import/by-isbn?isbn=9780140328721" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

Проверить через `GET /books`, что импортированная книга добавлена.

---

### Шаг 6. Добавление книги в корзину (user)

```bash
curl -s -X POST $ORDER_URL/cart/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d "{\"book_id\": $BOOK_ID, \"qty\": 2}" | jq
```

Проверяем корзину:

```bash
curl -s $ORDER_URL/cart \
  -H "Authorization: Bearer $USER_TOKEN" | jq
```

---

### Шаг 7. Создание заказа

```bash
CREATE_ORDER_RESPONSE=$(curl -s -X POST $ORDER_URL/orders \
  -H "Authorization: Bearer $USER_TOKEN")
echo $CREATE_ORDER_RESPONSE | jq
export ORDER_ID=$(echo $CREATE_ORDER_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "ORDER_ID=$ORDER_ID"
```

Проверка заказов:

```bash
curl -s $ORDER_URL/orders \
  -H "Authorization: Bearer $USER_TOKEN" | jq

curl -s $ORDER_URL/orders/$ORDER_ID \
  -H "Authorization: Bearer $USER_TOKEN" | jq
```

Ожидается: статус заказа `created` (дальнейшее изменение статуса зависит от обработки событий stock.reserve.*).

---

### Шаг 8. Проверка событий в RabbitMQ и аналитике

1. Открыть RabbitMQ UI: `http://localhost:15672` (guest/guest).
   - Показать exchange `bookstore.events`.
   - Показать появившиеся сообщения/счётчики по routing keys:
     - `order.created`
     - `stock.reserve.request`
     - `stock.reserve.succeeded` или `stock.reserve.failed`

2. Проверить аналитический сервис:

```bash
curl -s $ANALYTICS_URL/events | jq
```

Ожидается: массив `items` с событиями, где `routing_key` — `order.created` и/или `stock.reserve.*`.

---

### Шаг 9. Демонстрация обработки ошибок (невалидные данные)

Пример 1: отрицательное количество в корзине.

```bash
curl -i -X POST $ORDER_URL/cart/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d "{\"book_id\": $BOOK_ID, \"qty\": -1}"
```

Ожидается:
- Код 4xx (`400` или `422`).
- Ответ в формате:
  ```json
  {
    "error_code": "VALIDATION_ERROR" или "HTTP_ERROR",
    "message": "...",
    "details": { ... }
  }
  ```

Пример 2: несуществующий `book_id`.

```bash
curl -i -X POST $ORDER_URL/cart/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"book_id": 999999, "qty": 1}'
```

Затем `POST /orders`:

```bash
curl -i -X POST $ORDER_URL/orders \
  -H "Authorization: Bearer $USER_TOKEN"
```

Ожидается: 4xx и структурированный JSON‑ответ ошибки.

---

### Шаг 10. Проверка логирования и correlation-id

1. Выполнить любой запрос, например:

```bash
curl -s $AUTH_URL/auth/me \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "X-Correlation-Id: DEMO-CORR-ID" | jq
```

2. В другом окне:

```bash
docker compose logs auth-service
```

Показать, что в JSON‑логах присутствует `correlation_id: "DEMO-CORR-ID"` и событие, соответствующее запросу. 




