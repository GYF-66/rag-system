"""
重试机制
实现智能重试装饰器，支持指数退避和异常处理
"""

import time
import logging
from typing import Callable, Type, Tuple, Optional, Any
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    exceptions: Tuple[Type[Exception], ...] = (Exception,)


def exponential_backoff(attempt: int, 
                       initial_delay: float = 1.0,
                       exponential_base: float = 2.0,
                       max_delay: float = 60.0) -> float:
    """
    计算指数退避延迟
    
    Args:
        attempt: 当前尝试次数（从0开始）
        initial_delay: 初始延迟（秒）
        exponential_base: 指数基数
        max_delay: 最大延迟（秒）
        
    Returns:
        延迟时间（秒）
    """
    delay = initial_delay * (exponential_base ** attempt)
    return min(delay, max_delay)


def retry_with_backoff(max_attempts: int = 3,
                      initial_delay: float = 1.0,
                      max_delay: float = 60.0,
                      exponential_base: float = 2.0,
                      exceptions: Tuple[Type[Exception], ...] = (Exception,),
                      fallback: Optional[Callable] = None):
    """
    重试装饰器（支持指数退避）
    
    Args:
        max_attempts: 最大尝试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        exceptions: 需要重试的异常类型
        fallback: 失败后的降级函数
        
    Example:
        @retry_with_backoff(
            max_attempts=3,
            exceptions=(TimeoutError, ConnectionError),
            fallback=lambda *args, **kwargs: []
        )
        def fetch_data():
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # 成功后记录（如果之前有重试）
                    if attempt > 0:
                        logger.info(
                            f"[Retry] {func.__name__} 在第 {attempt + 1} 次尝试成功"
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # 如果是最后一次尝试，不再重试
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"[Retry] {func.__name__} 失败，已达最大重试次数 {max_attempts}"
                        )
                        break
                    
                    # 计算延迟
                    delay = exponential_backoff(
                        attempt,
                        initial_delay,
                        exponential_base,
                        max_delay
                    )
                    
                    logger.warning(
                        f"[Retry] {func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): "
                        f"{type(e).__name__}: {str(e)}, "
                        f"{delay:.1f}秒后重试"
                    )
                    
                    # 等待后重试
                    time.sleep(delay)
            
            # 所有尝试都失败
            if fallback:
                logger.info(f"[Retry] {func.__name__} 使用降级函数")
                try:
                    return fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"[Retry] 降级函数也失败: {str(fallback_error)}"
                    )
            
            # 抛出最后一次的异常
            raise last_exception
        
        return wrapper
    return decorator


class RetryableOperation:
    """
    可重试操作的上下文管理器
    
    Example:
        with RetryableOperation(max_attempts=3) as retry:
            result = retry.execute(risky_function, arg1, arg2)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 不抑制异常
        return False
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行可重试操作
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数返回值
        """
        for attempt in range(self.config.max_attempts):
            self.attempt = attempt
            
            try:
                return func(*args, **kwargs)
                
            except self.config.exceptions as e:
                self.last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    logger.error(
                        f"[RetryableOperation] 操作失败，已达最大重试次数"
                    )
                    raise
                
                delay = exponential_backoff(
                    attempt,
                    self.config.initial_delay,
                    self.config.exponential_base,
                    self.config.max_delay
                )
                
                logger.warning(
                    f"[RetryableOperation] 尝试 {attempt + 1}/{self.config.max_attempts} 失败，"
                    f"{delay:.1f}秒后重试"
                )
                
                time.sleep(delay)
        
        # 不应该到达这里
        raise self.last_exception
