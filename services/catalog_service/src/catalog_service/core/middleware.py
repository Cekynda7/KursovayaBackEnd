from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware, добавляющий/прокидывающий Correlation-Id в запросы и логи."""

    header_name = "X-Correlation-Id"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
            bind_contextvars(correlation_id=correlation_id, path=str(request.url.path))
            response = await call_next(request)
            response.headers[self.header_name] = correlation_id
            return response
        finally:
            clear_contextvars()


