# -*- coding: utf-8 -*-
"""
轻量级 Prometheus 风格性能指标收集
不依赖外部 Prometheus 库，直接输出 Prometheus text format
"""
import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsCollector:
    """线程安全的指标收集器"""

    def __init__(self):
        self._lock = Lock()
        self._request_count: Dict[str, int] = defaultdict(int)
        self._request_latency_sum: Dict[str, float] = defaultdict(float)
        self._request_latency_count: Dict[str, int] = defaultdict(int)
        self._error_count: Dict[str, int] = defaultdict(int)
        self._active_requests = 0
        self._start_time = time.time()

    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """记录一次请求"""
        with self._lock:
            key = f'{method}:{path}'
            self._request_count[key] += 1
            self._request_latency_sum[key] += duration
            self._request_latency_count[key] += 1
            if status_code >= 400:
                err_key = f'{method}:{path}:{status_code}'
                self._error_count[err_key] += 1

    def inc_active(self):
        with self._lock:
            self._active_requests += 1

    def dec_active(self):
        with self._lock:
            self._active_requests -= 1

    def format_prometheus(self) -> str:
        """输出 Prometheus text exposition format"""
        lines = []
        lines.append("# HELP app_uptime_seconds Application uptime in seconds")
        lines.append("# TYPE app_uptime_seconds gauge")
        lines.append(f"app_uptime_seconds {time.time() - self._start_time:.1f}")

        lines.append("# HELP app_active_requests Current active requests")
        lines.append("# TYPE app_active_requests gauge")
        lines.append(f"app_active_requests {self._active_requests}")

        lines.append("# HELP app_http_requests_total Total HTTP requests")
        lines.append("# TYPE app_http_requests_total counter")
        with self._lock:
            for key, count in self._request_count.items():
                method, path = key.split(":", 1)
                lines.append(
                    f'app_http_requests_total{{method="{method}",path="{path}"}} {count}'
                )

        lines.append("# HELP app_http_request_duration_seconds HTTP request latency sum")
        lines.append("# TYPE app_http_request_duration_seconds summary")
        with self._lock:
            for key in self._request_latency_sum:
                method, path = key.split(":", 1)
                s = self._request_latency_sum[key]
                c = self._request_latency_count[key]
                avg = s / c if c else 0
                lines.append(
                    f'app_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {s:.4f}'
                )
                lines.append(
                    f'app_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {c}'
                )
                lines.append(
                    f'app_http_request_duration_seconds_avg{{method="{method}",path="{path}"}} {avg:.4f}'
                )

        lines.append("# HELP app_http_errors_total Total HTTP errors (4xx/5xx)")
        lines.append("# TYPE app_http_errors_total counter")
        with self._lock:
            for key, count in self._error_count.items():
                parts = key.split(":", 2)
                method, path, code = parts[0], parts[1], parts[2]
                lines.append(
                    f'app_http_errors_total{{method="{method}",path="{path}",status="{code}"}} {count}'
                )

        return "\n".join(lines) + "\n"


# 全局单例
metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """请求指标采集中间件"""

    # 不采集指标端点自身，避免递归
    SKIP_PATHS = {"/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        metrics.inc_active()
        start = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start
            # 归一化路径：将带 ID 的路径统一
            path = self._normalize_path(request.url.path)
            metrics.record_request(request.method, path, response.status_code, duration)
            return response
        except Exception:
            duration = time.time() - start
            path = self._normalize_path(request.url.path)
            metrics.record_request(request.method, path, 500, duration)
            raise
        finally:
            metrics.dec_active()

    @staticmethod
    def _normalize_path(path: str) -> str:
        """归一化路径，将 UUID/ID 参数替换为占位符"""
        parts = path.strip("/").split("/")
        normalized = []
        for part in parts:
            if len(part) > 20 or (len(part) > 8 and "-" in part):
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized)
