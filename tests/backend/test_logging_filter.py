# -*- coding: utf-8 -*-
"""
日志敏感信息过滤器测试
"""
import pytest
import logging


@pytest.mark.unit
def test_sensitive_filter_password():
    """测试密码过滤"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg='User login with password: my_secret_123', args=(), exc_info=None
    )
    f.filter(record)
    assert "my_secret_123" not in record.msg
    assert "password: ***" in record.msg


@pytest.mark.unit
def test_sensitive_filter_token():
    """测试 Token 过滤"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg='Authorization token=eyJhbGciOiJIUzI1NiJ9.abc', args=(), exc_info=None
    )
    f.filter(record)
    assert "eyJhbGciOiJIUzI1NiJ9" not in record.msg
    assert "token: ***" in record.msg


@pytest.mark.unit
def test_sensitive_filter_api_key():
    """测试 API Key 过滤"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg='Calling LLM with api_key=sk-abc123def456', args=(), exc_info=None
    )
    f.filter(record)
    assert "sk-abc123def456" not in record.msg
    assert "api_key: ***" in record.msg


@pytest.mark.unit
def test_sensitive_filter_secret():
    """测试 Secret 过滤"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg='Config secret=very_secret_value loaded', args=(), exc_info=None
    )
    f.filter(record)
    assert "very_secret_value" not in record.msg
    assert "secret: ***" in record.msg


@pytest.mark.unit
def test_sensitive_filter_no_sensitive_data():
    """测试无敏感信息时不修改"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    original_msg = "Normal log message without sensitive data"
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg=original_msg, args=(), exc_info=None
    )
    f.filter(record)
    assert record.msg == original_msg


@pytest.mark.unit
def test_sensitive_filter_returns_true():
    """测试过滤器始终返回 True（不丢弃日志）"""
    from backend.utils.logging_filter import SensitiveDataFilter

    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg='password=secret123', args=(), exc_info=None
    )
    result = f.filter(record)
    assert result is True
