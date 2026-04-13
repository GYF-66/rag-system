# -*- coding: utf-8 -*-
"""Request context helpers for correlation ids and access logs."""
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = 'X-Request-ID'
_request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')


def get_request_id() -> str:
    """Return the active request id if one is bound to the current context."""
    return _request_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a per-request correlation id and expose it to handlers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        request.state.request_id = request_id
        start = time.perf_counter()
        response = None

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                'request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s',
                request_id,
                request.method,
                request.url.path,
                response.status_code if response is not None else 'error',
                duration_ms,
            )
            _request_id_ctx.reset(token)
