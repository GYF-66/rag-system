# -*- coding: utf-8 -*-
"""
Redis 缓存模块测试
"""
import pytest
import json


@pytest.mark.unit
def test_make_cache_key():
    """测试缓存键生成"""
    from backend.cache.redis_cache import _make_cache_key

    key1 = _make_cache_key("func_a", ("arg1",), {"k": "v"})
    key2 = _make_cache_key("func_a", ("arg1",), {"k": "v"})
    key3 = _make_cache_key("func_b", ("arg1",), {"k": "v"})

    # 相同输入产生相同键
    assert key1 == key2
    # 不同函数名产生不同键
    assert key1 != key3
    # 键以 cache: 开头
    assert key1.startswith("cache:")


@pytest.mark.unit
def test_local_cache_get_set():
    """测试本地缓存读写"""
    from backend.cache.redis_cache import _local_get, _local_set, _local_cache, _local_cache_expiry

    # 清理状态
    _local_cache.clear()
    _local_cache_expiry.clear()

    # 写入
    _local_set("test_key", '{"data": 1}', ttl=60)
    assert _local_get("test_key") == '{"data": 1}'

    # 不存在的键
    assert _local_get("nonexistent") is None


@pytest.mark.unit
def test_local_cache_expiry():
    """测试本地缓存过期"""
    import time
    from backend.cache.redis_cache import _local_get, _local_set, _local_cache, _local_cache_expiry

    _local_cache.clear()
    _local_cache_expiry.clear()

    # 设置 1 秒过期
    _local_set("expire_key", '"value"', ttl=1)
    assert _local_get("expire_key") == '"value"'

    # 等待过期
    time.sleep(1.1)
    assert _local_get("expire_key") is None


@pytest.mark.unit
def test_cache_result_sync():
    """测试同步函数缓存装饰器"""
    from backend.cache.redis_cache import cache_result, _local_cache, _local_cache_expiry

    _local_cache.clear()
    _local_cache_expiry.clear()

    call_count = 0

    @cache_result(ttl=60)
    def expensive_func(x, y):
        nonlocal call_count
        call_count += 1
        return x + y

    # 第一次调用
    result1 = expensive_func(1, 2)
    assert result1 == 3
    assert call_count == 1

    # 第二次调用应命中缓存
    result2 = expensive_func(1, 2)
    assert result2 == 3
    assert call_count == 1  # 没有再次调用

    # 不同参数不命中缓存
    result3 = expensive_func(3, 4)
    assert result3 == 7
    assert call_count == 2


@pytest.mark.unit
def test_cache_result_async():
    """测试异步函数缓存装饰器"""
    import asyncio
    from backend.cache.redis_cache import cache_result, _local_cache, _local_cache_expiry

    _local_cache.clear()
    _local_cache_expiry.clear()

    call_count = 0

    @cache_result(ttl=60)
    async def async_func(x):
        nonlocal call_count
        call_count += 1
        return {"result": x * 2}

    result1 = asyncio.run(async_func(5))
    assert result1 == {"result": 10}
    assert call_count == 1

    result2 = asyncio.run(async_func(5))
    assert result2 == {"result": 10}
    assert call_count == 1


@pytest.mark.unit
def test_evict_expired():
    """测试过期缓存清理"""
    import time
    from backend.cache.redis_cache import _local_set, _evict_expired, _local_cache, _local_cache_expiry

    _local_cache.clear()
    _local_cache_expiry.clear()

    # 添加已过期的条目
    _local_cache["old1"] = '"v1"'
    _local_cache_expiry["old1"] = time.time() - 10

    _local_cache["old2"] = '"v2"'
    _local_cache_expiry["old2"] = time.time() - 5

    # 添加未过期的条目
    _local_set("fresh", '"v3"', ttl=300)

    _evict_expired()

    assert "old1" not in _local_cache
    assert "old2" not in _local_cache
    assert "fresh" in _local_cache
