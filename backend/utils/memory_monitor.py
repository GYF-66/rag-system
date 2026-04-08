# -*- coding: utf-8 -*-
"""
内存监控工具
提供装饰器用于监控函数内存使用情况
"""
import psutil
import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)


def monitor_memory(threshold_mb: float = 50.0) -> Callable:
    """
    内存监控装饰器
    
    Args:
        threshold_mb: 内存增长警告阈值（MB）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            
            result = await func(*args, **kwargs)
            
            mem_after = process.memory_info().rss / 1024 / 1024
            mem_delta = mem_after - mem_before
            
            if mem_delta > threshold_mb:
                logger.warning(
                    f"[内存监控] {func.__name__} 内存增长: {mem_delta:.2f}MB "
                    f"(前: {mem_before:.2f}MB, 后: {mem_after:.2f}MB)"
                )
            else:
                logger.debug(
                    f"[内存监控] {func.__name__} 内存变化: {mem_delta:+.2f}MB"
                )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            mem_after = process.memory_info().rss / 1024 / 1024
            mem_delta = mem_after - mem_before
            
            if mem_delta > threshold_mb:
                logger.warning(
                    f"[内存监控] {func.__name__} 内存增长: {mem_delta:.2f}MB "
                    f"(前: {mem_before:.2f}MB, 后: {mem_after:.2f}MB)"
                )
            else:
                logger.debug(
                    f"[内存监控] {func.__name__} 内存变化: {mem_delta:+.2f}MB"
                )
            
            return result
        
        # 根据函数类型返回对应的wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_memory_usage() -> dict:
    """
    获取当前进程内存使用情况
    
    Returns:
        包含内存使用信息的字典
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    
    return {
        'rss_mb': mem_info.rss / 1024 / 1024,  # 物理内存
        'vms_mb': mem_info.vms / 1024 / 1024,  # 虚拟内存
        'percent': process.memory_percent(),    # 内存占用百分比
    }


def log_memory_usage(prefix: str = ""):
    """
    记录当前内存使用情况
    
    Args:
        prefix: 日志前缀
    """
    mem_usage = get_memory_usage()
    logger.info(
        f"{prefix}内存使用: RSS={mem_usage['rss_mb']:.2f}MB, "
        f"VMS={mem_usage['vms_mb']:.2f}MB, "
        f"占用={mem_usage['percent']:.2f}%"
    )
