# -*- coding: utf-8 -*-
"""
语义缓存单元测试
测试缓存存储、检索、过期、LRU淘汰
"""
import pytest
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from utils.cache import SemanticCache, CacheEntry
from datetime import datetime, timedelta


class TestCacheEntry:
    """缓存条目测试"""
    
    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(
            key="test_key",
            query="测试查询",
            query_vector=[0.1, 0.2, 0.3],
            result={"data": "test"},
            timestamp=datetime.now(),
            ttl=3600
        )
        assert entry.key == "test_key"
        assert entry.query == "测试查询"
        assert entry.ttl == 3600
        assert entry.hit_count == 0
    
    def test_is_expired(self):
        """测试过期判断"""
        # 未过期
        entry = CacheEntry(
            key="test",
            query="test",
            query_vector=None,
            result={},
            timestamp=datetime.now(),
            ttl=3600
        )
        assert not entry.is_expired()
        
        # 已过期
        old_entry = CacheEntry(
            key="test",
            query="test",
            query_vector=None,
            result={},
            timestamp=datetime.now() - timedelta(seconds=7200),
            ttl=3600
        )
        assert old_entry.is_expired()
        
        # 永不过期
        no_ttl_entry = CacheEntry(
            key="test",
            query="test",
            query_vector=None,
            result={},
            timestamp=datetime.now(),
            ttl=0
        )
        assert not no_ttl_entry.is_expired()


class TestSemanticCache:
    """语义缓存测试"""
    
    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return SemanticCache(
            max_size=10,
            default_ttl=60,
            similarity_threshold=0.95
        )
    
    def test_cache_initialization(self, cache):
        """测试缓存初始化"""
        assert cache.max_size == 10
        assert cache.default_ttl == 60
        assert cache.similarity_threshold == 0.95
    
    def test_set_and_get(self, cache):
        """测试设置和获取"""
        cache.set("测试查询", {"result": "data"})
        result = cache.get("测试查询")
        assert result == {"result": "data"}
    
    def test_get_nonexistent(self, cache):
        """测试获取不存在的键"""
        result = cache.get("不存在的查询")
        assert result is None
    
    def test_exact_match(self, cache):
        """测试精确匹配"""
        cache.set("学费缴纳政策", {"answer": "详细说明"})
        result = cache.get("学费缴纳政策")
        assert result == {"answer": "详细说明"}
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = SemanticCache(max_size=10, default_ttl=1)
        cache.set("测试", {"data": "test"})
        
        # 立即获取应该成功
        assert cache.get("测试") is not None
        
        # 等待过期
        time.sleep(1.5)
        assert cache.get("测试") is None
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = SemanticCache(max_size=3, default_ttl=3600)
        
        # 填满缓存
        cache.set("query1", {"data": 1})
        cache.set("query2", {"data": 2})
        cache.set("query3", {"data": 3})
        
        # 访问query1，使其成为最近使用
        cache.get("query1")
        
        # 添加新条目，应该淘汰query2
        cache.set("query4", {"data": 4})
        
        assert cache.get("query1") is not None
        assert cache.get("query2") is None
        assert cache.get("query3") is not None
        assert cache.get("query4") is not None
    
    def test_clear(self, cache):
        """测试清空缓存"""
        cache.set("query1", {"data": 1})
        cache.set("query2", {"data": 2})
        
        cache.clear()
        
        assert cache.get("query1") is None
        assert cache.get("query2") is None
        assert len(cache._cache) == 0
    
    def test_cleanup_expired(self):
        """测试清理过期条目"""
        cache = SemanticCache(max_size=10, default_ttl=1)
        
        cache.set("query1", {"data": 1})
        cache.set("query2", {"data": 2}, ttl=10)
        
        time.sleep(1.5)
        
        cache.cleanup_expired()
        
        assert cache.get("query1") is None
        assert cache.get("query2") is not None
    
    def test_get_stats(self, cache):
        """测试统计信息"""
        cache.set("query1", {"data": 1})
        cache.get("query1")
        cache.get("query1")
        cache.get("nonexistent")
        
        stats = cache.get_stats()
        
        assert stats["total_entries"] == 1
        assert stats["total_hits"] >= 2
        assert stats["total_misses"] >= 1
        assert "hit_rate" in stats
    
    def test_custom_ttl(self, cache):
        """测试自定义TTL"""
        cache.set("query1", {"data": 1}, ttl=100)
        cache.set("query2", {"data": 2}, ttl=1)
        
        time.sleep(1.5)
        
        assert cache.get("query1") is not None
        assert cache.get("query2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
