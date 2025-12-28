## Контракты событий RabbitMQ

### Общие сведения

- **Exchange**: `bookstore.events`
- **Тип**: `topic`
- **Формат сообщений**: JSON
- **Routing keys**:
  - `order.created`
  - `stock.reserve.request`
  - `stock.reserve.succeeded`
  - `stock.reserve.failed`

Все события имеют общий «обёрточный» формат:

```json
{
  "event_id": "uuid",          // Уникальный идентификатор события
  "occurred_at": "ISO8601",    // Время возникновения события (UTC)
  "correlation_id": "uuid",    // Идентификатор цепочки запросов (из HTTP X-Correlation-Id)
  "idempotency_key": "uuid",   // Ключ идемпотентности для защиты от повторной обработки
  "payload": {                 // Доменные данные
    "...": "..."
  }
}
```

> Примечание: на уровне кода часть этих полей может добавляться при публикации (например, `occurred_at`, `idempotency_key`), но логический контракт именно такой.

---

## Событие `order.created`

- **Publisher**: `order-service`
- **Consumers**:
  - `analytics-service`
  - (потенциально другие сервисы)

### Назначение

Зафиксировать факт создания нового заказа пользователем.

### Payload

```json
{
  "order_id": 10,
  "user_id": 1,
  "total_amount": 31.5,
  "items": [
    { "book_id": 1, "quantity": 2 },
    { "book_id": 5, "quantity": 1 }
  ],
  "status": "created"
}
```

### Пример полного сообщения

```json
{
  "event_id": "d3a2c1e4-7c9b-4a1e-9f4c-0e5b14b7c001",
  "occurred_at": "2025-01-01T12:00:00Z",
  "correlation_id": "40f4f9a8-0c92-4d4a-9e46-b6bb4c0f0001",
  "idempotency_key": "8c4be1e2-3519-4c7a-8bfa-1af7d1d80001",
  "payload": {
    "order_id": 10,
    "user_id": 1,
    "total_amount": 31.5,
    "items": [
      { "book_id": 1, "quantity": 2 },
      { "book_id": 5, "quantity": 1 }
    ],
    "status": "created"
  }
}
```

---

## Событие `stock.reserve.request`

- **Publisher**: `order-service`
- **Consumers**:
  - `catalog-service`
  - `analytics-service`

### Назначение

Запросить резервирование товара на складе под созданный заказ.

### Payload

```json
{
  "order_id": 10,
  "user_id": 1,
  "items": [
    { "book_id": 1, "quantity": 2 },
    { "book_id": 5, "quantity": 1 }
  ]
}
```

### Пример полного сообщения

```json
{
  "event_id": "e4c2c1e4-7c9b-4a1e-9f4c-0e5b14b7c002",
  "occurred_at": "2025-01-01T12:00:01Z",
  "correlation_id": "40f4f9a8-0c92-4d4a-9e46-b6bb4c0f0001",
  "idempotency_key": "8c4be1e2-3519-4c7a-8bfa-1af7d1d80002",
  "payload": {
    "order_id": 10,
    "user_id": 1,
    "items": [
      { "book_id": 1, "quantity": 2 },
      { "book_id": 5, "quantity": 1 }
    ]
  }
}
```

---

## Событие `stock.reserve.succeeded`

- **Publisher**: `catalog-service`
- **Consumers**:
  - `order-service`
  - `analytics-service`

### Назначение

Подтвердить успешное резервирование стока под заказ.

### Payload

```json
{
  "order_id": 10,
  "items": [
    { "book_id": 1, "quantity": 2 },
    { "book_id": 5, "quantity": 1 }
  ]
}
```

### Пример полного сообщения

```json
{
  "event_id": "f5d3c1e4-7c9b-4a1e-9f4c-0e5b14b7c003",
  "occurred_at": "2025-01-01T12:00:02Z",
  "correlation_id": "40f4f9a8-0c92-4d4a-9e46-b6bb4c0f0001",
  "idempotency_key": "8c4be1e2-3519-4c7a-8bfa-1af7d1d80003",
  "payload": {
    "order_id": 10,
    "items": [
      { "book_id": 1, "quantity": 2 },
      { "book_id": 5, "quantity": 1 }
    ]
  }
}
```

---

## Событие `stock.reserve.failed`

- **Publisher**: `catalog-service`
- **Consumers**:
  - `order-service`
  - `analytics-service`

### Назначение

Сообщить о невозможности зарезервировать товар (например, нехватка на складе).

### Payload

```json
{
  "order_id": 10,
  "reason": "not_enough_stock",
  "items": [
    { "book_id": 1, "requested": 2, "available": 0 }
  ]
}
```

### Пример полного сообщения

```json
{
  "event_id": "a6e4c1e4-7c9b-4a1e-9f4c-0e5b14b7c004",
  "occurred_at": "2025-01-01T12:00:02Z",
  "correlation_id": "40f4f9a8-0c92-4d4a-9e46-b6bb4c0f0001",
  "idempotency_key": "8c4be1e2-3519-4c7a-8bfa-1af7d1d80004",
  "payload": {
    "order_id": 10,
    "reason": "not_enough_stock",
    "items": [
      { "book_id": 1, "requested": 2, "available": 0 }
    ]
  }
}
```


