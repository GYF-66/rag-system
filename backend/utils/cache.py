"""
语义缓存
实现基于语义相似度的查询缓存，避免重复检索
"""

import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    query: str
    query_vector: Optional[List[float]]
    result: Any
    timestamp: datetime
    ttl: int  # 生存时间（秒）
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False  # 永不过期
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)


class SemanticCache:
    """
    语义缓存
    
    基于查询语义相似度的智能缓存系统
    - 支持相似查询匹配（不需要完全相同）
    - 支持TTL过期管理
    - 支持LRU淘汰策略
    """
    
    def __init__(self,
                 max_size: int = 1000,
                 default_ttl: int = 3600,
                 similarity_threshold: float = 0.95,
                 embedding_func: Optional[callable] = None):
        """
        初始化语义缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            similarity_threshold: 相似度阈值（0-1）
            embedding_func: 向量化函数（可选）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.similarity_threshold = similarity_threshold
        self.embedding_func = embedding_func
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        
        logger.info(
            f"[Cache] 初始化语义缓存: "
            f"max_size={max_size}, ttl={default_ttl}s, "
            f"threshold={similarity_threshold}"
        )
    
    def _compute_key(self, query: str) -> str:
        """
        计算查询的缓存键
        
        使用MD5哈希作为键
        """
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _compute_vector(self, query: str) -> Optional[List[float]]:
        """
        计算查询向量
        
        如果提供了embedding_func，则计算向量用于语义匹配
        """
        if self.embedding_func:
            try:
                return self.embedding_func(query)
            except Exception as e:
                logger.warning(f"[Cache] 向量计算失败: {str(e)}")
        return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            相似度（0-1）
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get(self, query: str) -> Optional[Any]:
        """
        获取缓存结果
        
        Args:
            query: 查询文本
            
        Returns:
            缓存的结果，如果未命中则返回None
        """
        key = self._compute_key(query)
        
        with self._lock:
            # 精确匹配
            if key in self._cache:
                entry = self._cache[key]
                
                # 检查是否过期
                if entry.is_expired():
                    logger.debug(f"[Cache] 缓存过期: {query[:50]}")
                    del self._cache[key]
                    return None
                
                # 命中
                entry.hit_count += 1
                logger.info(f"[Cache] 精确命中: {query[:50]}")
                return entry.result
            
            # 语义匹配（如果启用）
            if self.embedding_func:
                query_vector = self._compute_vector(query)
                if query_vector:
                    best_match = self._find_similar_entry(query_vector)
                    if best_match:
                        entry, similarity = best_match
                        entry.hit_count += 1
                        logger.info(
                            f"[Cache] 语义命中: {query[:50]} "
                            f"(相似度: {similarity:.3f})"
                        )
                        return entry.result
        
        logger.debug(f"[Cache] 未命中: {query[:50]}")
        return None
    
    def _find_similar_entry(self, 
                           query_vector: List[float]) -> Optional[Tuple[CacheEntry, float]]:
        """
        查找语义相似的缓存条目
        
        Args:
            query_vector: 查询向量
            
        Returns:
            (缓存条目, 相似度) 或 None
        """
        best_entry = None
        best_similarity = 0.0
        
        for entry in self._cache.values():
            # 跳过过期条目
            if entry.is_expired():
                continue
            
            # 跳过没有向量的条目
            if not entry.query_vector:
                continue
            
            # 计算相似度
            similarity = self._cosine_similarity(query_vector, entry.query_vector)
            
            # 更新最佳匹配
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_entry = entry
        
        if best_entry:
            return (best_entry, best_similarity)
        return None
    
    def set(self, query: str, result: Any, ttl: Optional[int] = None):
        """
        设置缓存
        
        Args:
            query: 查询文本
            result: 结果
            ttl: 生存时间（秒），None使用默认值
        """
        key = self._compute_key(query)
        ttl = ttl if ttl is not None else self.default_ttl
        
        # 计算向量
        query_vector = self._compute_vector(query)
        
        entry = CacheEntry(
            key=key,
            query=query,
            query_vector=query_vector,
            result=result,
            timestamp=datetime.now(),
            ttl=ttl
        )
        
        with self._lock:
            # 检查缓存大小
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = entry
        
        logger.debug(f"[Cache] 已缓存: {query[:50]}")
    
    def _evict_lru(self):
        """
        淘汰最少使用的条目（LRU）
        """
        if not self._cache:
            return
        
        # 找到最少使用的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hit_count, self._cache[k].timestamp)
        )
        
        del self._cache[lru_key]
        logger.debug(f"[Cache] LRU淘汰: {lru_key}")
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
        logger.info("[Cache] 缓存已清空")
    
    def cleanup_expired(self):
        """
        清理过期条目
        
        应定期调用此方法
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.info(f"[Cache] 清理了 {len(expired_keys)} 个过期条目")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_entries = len(self._cache)
            total_hits = sum(entry.hit_count for entry in self._cache.values())
            
            if self._cache:
                avg_hits = total_hits / total_entries
                max_hits = max(entry.hit_count for entry in self._cache.values())
            else:
                avg_hits = 0
                max_hits = 0
        
        return {
            'total_entries': total_entries,
            'max_size': self.max_size,
            'usage_ratio': total_entries / self.max_size if self.max_size > 0 else 0,
            'total_hits': total_hits,
            'avg_hits_per_entry': avg_hits,
            'max_hits': max_hits
        }
