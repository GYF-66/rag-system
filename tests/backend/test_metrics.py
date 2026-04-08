# -*- coding: utf-8 -*-
"""
性能指标收集器测试
"""
import pytest


@pytest.mark.unit
def test_metrics_collector_creation():
    """测试指标收集器创建"""
    from backend.monitoring.metrics import MetricsCollector

    collector = MetricsCollector()
    assert collector._active_requests == 0
    assert len(collector._request_count) == 0


@pytest.mark.unit
def test_metrics_record_request():
    """测试记录请求"""
    from backend.monitoring.metrics import MetricsCollector

    collector = MetricsCollector()
    collector.record_request("GET", "/health", 200, 0.05)
    collector.record_request("POST", "/api/chat", 200, 1.2)
    collector.record_request("GET", "/health", 200, 0.03)

    assert collector._request_count["GET:/health"] == 2
    assert collector._request_count["POST:/api/chat"] == 1
    assert collector._request_latency_count["GET:/health"] == 2


@pytest.mark.unit
def test_metrics_record_errors():
    """测试记录错误请求"""
    from backend.monitoring.metrics import MetricsCollector

    collector = MetricsCollector()
    collector.record_request("POST", "/api/chat", 500, 0.1)
    collector.record_request("GET", "/api/missing", 404, 0.01)

    assert collector._error_count["POST:/api/chat:500"] == 1
    assert collector._error_count["GET:/api/missing:404"] == 1


@pytest.mark.unit
def test_metrics_active_requests():
    """测试活跃请求计数"""
    from backend.monitoring.metrics import MetricsCollector

    collector = MetricsCollector()
    collector.inc_active()
    collector.inc_active()
    assert collector._active_requests == 2

    collector.dec_active()
    assert collector._active_requests == 1


@pytest.mark.unit
def test_metrics_prometheus_format():
    """测试 Prometheus 格式输出"""
    from backend.monitoring.metrics import MetricsCollector

    collector = MetricsCollector()
    collector.record_request("GET", "/health", 200, 0.05)

    output = collector.format_prometheus()

    assert "app_uptime_seconds" in output
    assert "app_active_requests" in output
    assert "app_http_requests_total" in output
    assert 'method="GET"' in output
    assert 'path="/health"' in output


@pytest.mark.unit
def test_metrics_normalize_path():
    """测试路径归一化"""
    from backend.monitoring.metrics import MetricsMiddleware

    # 普通路径不变
    assert MetricsMiddleware._normalize_path("/health") == "/health"
    assert MetricsMiddleware._normalize_path("/api/chat") == "/api/chat"

    # UUID 路径被替换
    result = MetricsMiddleware._normalize_path("/api/sessions/550e8400-e29b-41d4-a716-446655440000")
    assert "{id}" in result
