# -*- coding: utf-8 -*-
"""
统一错误处理装饰器
减少重复的 try-except 模式
"""
from functools import wraps
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


def handle_errors(func):
    """异步路由错误处理装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{func.__name__} 执行失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务器内部错误: {str(e)}"
            )
    return wrapper


def handle_sync_errors(func):
    """同步函数错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"{func.__name__} 执行失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务器内部错误: {str(e)}"
            )
    return wrapper
