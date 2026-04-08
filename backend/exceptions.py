# -*- coding: utf-8 -*-
"""
统一异常定义与 FastAPI 异常处理器
集中管理所有业务异常，避免在路由中重复编写 try/except
"""
import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ============ 业务异常定义 ============

class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, status_code: int = 500, detail: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


class KnowledgeBaseError(AppException):
    """知识库相关异常"""

    def __init__(self, message: str = "知识库服务不可用"):
        super().__init__(message, status_code=503)


class SessionNotFoundError(AppException):
    """会话不存在"""

    def __init__(self, session_id: str):
        super().__init__(f"会话不存在: {session_id}", status_code=404)


class QueryProcessingError(AppException):
    """查询处理异常"""

    def __init__(self, message: str = "处理查询时发生错误"):
        super().__init__(message, status_code=500)


class RateLimitError(AppException):
    """速率限制异常"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message, status_code=429)


# ============ 异常处理器注册 ============

def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(f"业务异常 [{exc.status_code}]: {exc.message} - {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "detail": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": str(exc.detail),
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"未处理异常: {type(exc).__name__}: {exc} - {request.url.path}\n"
            f"{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "服务器内部错误",
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url.path),
            },
        )
