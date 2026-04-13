# -*- coding: utf-8 -*-
"""Centralized application exceptions and FastAPI exception handlers."""
from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from middleware.request_context import get_request_id

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception with stable payload fields."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        self.error_code = error_code
        super().__init__(self.message)


class KnowledgeBaseError(AppException):
    """Knowledge base is not available."""

    def __init__(self, message: str = '知识库服务不可用'):
        super().__init__(message, status_code=503, error_code='knowledge_base_unavailable')


class SessionNotFoundError(AppException):
    """Session lookup failed."""

    def __init__(self, session_id: str):
        super().__init__(
            f'会话不存在: {session_id}',
            status_code=404,
            error_code='session_not_found',
        )


class QueryProcessingError(AppException):
    """User-facing query processing failure."""

    def __init__(
        self,
        message: str = '处理查询时发生错误',
        *,
        detail: Optional[str] = None,
        error_code: str = 'query_processing_failed',
    ):
        super().__init__(message, status_code=500, detail=detail, error_code=error_code)


class RateLimitError(AppException):
    """Rate limit reached."""

    def __init__(self, message: str = '请求过于频繁，请稍后再试'):
        super().__init__(message, status_code=429, error_code='rate_limited')


def _error_payload(request: Request, message: str, detail: Optional[str], error_code: Optional[str]) -> dict:
    request_id = getattr(request.state, 'request_id', None) or get_request_id() or ''
    payload = {
        'status': 'error',
        'message': message,
        'detail': detail or message,
        'timestamp': datetime.now().isoformat(),
        'path': str(request.url.path),
        'request_id': request_id,
    }
    if error_code:
        payload['error_code'] = error_code
    return payload


def register_exception_handlers(app: FastAPI):
    """Register global exception handlers."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, 'request_id', None) or get_request_id() or ''
        logger.warning(
            'app_exception request_id=%s status=%s path=%s error_code=%s message=%s',
            request_id,
            exc.status_code,
            request.url.path,
            exc.error_code or '',
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, exc.message, exc.detail, exc.error_code),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        message = str(exc.detail)
        request_id = getattr(request.state, 'request_id', None) or get_request_id() or ''
        logger.warning(
            'http_exception request_id=%s status=%s path=%s message=%s',
            request_id,
            exc.status_code,
            request.url.path,
            message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, message, message, None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', None) or get_request_id() or ''
        logger.error(
            'unhandled_exception request_id=%s type=%s path=%s error=%s\n%s',
            request_id,
            type(exc).__name__,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload(request, '服务器内部错误', '服务器内部错误', 'internal_server_error'),
        )
