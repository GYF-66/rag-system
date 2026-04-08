"""
性能指标收集
收集和导出系统性能指标
"""

import time
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """单个指标"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    指标收集器
    
    收集系统运行时的各种性能指标
    """
    
    def __init__(self, window_size: int = 1000):
        """
        初始化指标收集器
        
        Args:
            window_size: 滑动窗口大小（保留最近N个数据点）
        """
        self.window_size = window_size
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._counters: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        
        logger.info(f"[Metrics] 初始化指标收集器，窗口大小: {window_size}")
    
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 标签（可选）
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        with self._lock:
            self._metrics[name].append(metric)
    
    def increment(self, name: str, delta: int = 1):
        """
        增加计数器
        
        Args:
            name: 计数器名称
            delta: 增量
        """
        with self._lock:
            self._counters[name] += delta
    
    def get_counter(self, name: str) -> int:
        """获取计数器值"""
        with self._lock:
            return self._counters.get(name, 0)
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """
        获取指标统计信息
        
        Args:
            name: 指标名称
            
        Returns:
            统计信息字典（count, mean, min, max, p50, p95, p99）
        """
        with self._lock:
            metrics = list(self._metrics.get(name, []))
        
        if not metrics:
            return {
                'count': 0,
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0
            }
        
        values = [m.value for m in metrics]
        values.sort()
        
        count = len(values)
        mean = sum(values) / count
        min_val = values[0]
        max_val = values[-1]
        
        # 计算百分位数
        p50 = self._percentile(values, 0.50)
        p95 = self._percentile(values, 0.95)
        p99 = self._percentile(values, 0.99)
        
        return {
            'count': count,
            'mean': mean,
            'min': min_val,
            'max': max_val,
            'p50': p50,
            'p95': p95,
            'p99': p99
        }
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """
        计算百分位数
        
        Args:
            sorted_values: 已排序的值列表
            percentile: 百分位（0-1）
            
        Returns:
            百分位数值
        """
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        获取所有指标的统计信息
        
        Returns:
            所有指标的统计信息
        """
        with self._lock:
            metric_names = list(self._metrics.keys())
        
        all_stats = {}
        for name in metric_names:
            all_stats[name] = self.get_stats(name)
        
        return all_stats
    
    def get_counters(self) -> Dict[str, int]:
        """获取所有计数器"""
        with self._lock:
            return dict(self._counters)
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
        logger.info("[Metrics] 指标已重置")
    
    def export_summary(self) -> Dict[str, Any]:
        """
        导出指标摘要
        
        Returns:
            包含所有指标和计数器的摘要
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.get_all_stats(),
            'counters': self.get_counters()
        }


class Timer:
    """
    计时器上下文管理器
    
    Example:
        with Timer(metrics, 'retrieval_latency'):
            results = search(query)
    """
    
    def __init__(self, 
                 collector: MetricsCollector,
                 metric_name: str,
                 tags: Optional[Dict[str, str]] = None):
        """
        初始化计时器
        
        Args:
            collector: 指标收集器
            metric_name: 指标名称
            tags: 标签（可选）
        """
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.time() - self.start_time) * 1000  # 转换为毫秒
        self.collector.record(self.metric_name, elapsed, self.tags)
        return False


# 全局指标收集器实例
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
