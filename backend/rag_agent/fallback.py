"""
降级策略处理器
实现多级降级机制，确保系统在各种故障场景下都能提供服务
"""

from typing import List, Dict, Optional, Callable
from enum import Enum
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FallbackLevel(Enum):
    """降级级别"""
    PRIMARY = "primary"           # 主要方法（向量检索）
    SECONDARY = "secondary"       # 次要方法（TF-IDF）
    TERTIARY = "tertiary"         # 第三级（内存检索）
    EMERGENCY = "emergency"       # 紧急降级（友好错误）


@dataclass
class FallbackResult:
    """降级结果"""
    success: bool
    level: FallbackLevel
    results: List[Dict]
    error: Optional[str] = None
    fallback_reason: Optional[str] = None


class FallbackStrategy:
    """
    降级策略处理器
    
    实现多级降级机制：
    1. PRIMARY: 向量检索（ChromaDB）
    2. SECONDARY: TF-IDF关键词检索
    3. TERTIARY: 内存中的简单匹配
    4. EMERGENCY: 返回友好的错误消息和建议
    """
    
    def __init__(self,
                 vector_kb=None,
                 keyword_kb=None,
                 enable_memory_fallback: bool = True):
        """
        初始化降级策略
        
        Args:
            vector_kb: 向量知识库
            keyword_kb: 关键词知识库
            enable_memory_fallback: 是否启用内存降级
        """
        self.vector_kb = vector_kb
        self.keyword_kb = keyword_kb
        self.enable_memory_fallback = enable_memory_fallback
        
        # 统计信息
        self.fallback_stats = {
            FallbackLevel.PRIMARY: 0,
            FallbackLevel.SECONDARY: 0,
            FallbackLevel.TERTIARY: 0,
            FallbackLevel.EMERGENCY: 0
        }
        
        logger.info(
            f"[Fallback] 初始化降级策略: "
            f"向量={vector_kb is not None}, "
            f"关键词={keyword_kb is not None}, "
            f"内存降级={enable_memory_fallback}"
        )
    
    def search_with_fallback(self, 
                            query: str, 
                            top_k: int = 5,
                            min_results: int = 1) -> FallbackResult:
        """
        带降级的检索
        
        按优先级尝试各级检索方法，直到成功或全部失败
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_results: 最少结果数（低于此数量触发降级）
            
        Returns:
            降级结果
        """
        logger.info(f"[Fallback] 开始检索: {query}, top_k={top_k}")
        
        # 1. PRIMARY: 向量检索
        result = self._try_vector_search(query, top_k, min_results)
        if result.success:
            self.fallback_stats[FallbackLevel.PRIMARY] += 1
            return result
        
        logger.warning(f"[Fallback] PRIMARY失败: {result.error}, 降级到SECONDARY")
        
        # 2. SECONDARY: TF-IDF检索
        result = self._try_keyword_search(query, top_k, min_results)
        if result.success:
            self.fallback_stats[FallbackLevel.SECONDARY] += 1
            return result
        
        logger.warning(f"[Fallback] SECONDARY失败: {result.error}, 降级到TERTIARY")
        
        # 3. TERTIARY: 内存检索
        if self.enable_memory_fallback:
            result = self._try_memory_search(query, top_k, min_results)
            if result.success:
                self.fallback_stats[FallbackLevel.TERTIARY] += 1
                return result
            
            logger.warning(f"[Fallback] TERTIARY失败: {result.error}, 降级到EMERGENCY")
        
        # 4. EMERGENCY: 友好错误
        result = self._emergency_response(query)
        self.fallback_stats[FallbackLevel.EMERGENCY] += 1
        return result
    
    def _try_vector_search(self, 
                          query: str, 
                          top_k: int,
                          min_results: int) -> FallbackResult:
        """
        尝试向量检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_results: 最少结果数
            
        Returns:
            降级结果
        """
        if not self.vector_kb:
            return FallbackResult(
                success=False,
                level=FallbackLevel.PRIMARY,
                results=[],
                error="向量知识库未初始化"
            )
        
        try:
            if not hasattr(self.vector_kb, 'search'):
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.PRIMARY,
                    results=[],
                    error="向量知识库不支持search方法"
                )
            
            results = self.vector_kb.search(query, top_k=top_k)
            
            if len(results) < min_results:
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.PRIMARY,
                    results=results,
                    error=f"结果数量不足: {len(results)} < {min_results}"
                )
            
            logger.info(f"[Fallback] PRIMARY成功: 返回{len(results)}个结果")
            return FallbackResult(
                success=True,
                level=FallbackLevel.PRIMARY,
                results=results
            )
            
        except Exception as e:
            logger.error(f"[Fallback] PRIMARY异常: {str(e)}", exc_info=True)
            return FallbackResult(
                success=False,
                level=FallbackLevel.PRIMARY,
                results=[],
                error=str(e)
            )
    
    def _try_keyword_search(self, 
                           query: str, 
                           top_k: int,
                           min_results: int) -> FallbackResult:
        """
        尝试关键词检索（TF-IDF）
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_results: 最少结果数
            
        Returns:
            降级结果
        """
        if not self.keyword_kb:
            return FallbackResult(
                success=False,
                level=FallbackLevel.SECONDARY,
                results=[],
                error="关键词知识库未初始化"
            )
        
        try:
            if not hasattr(self.keyword_kb, 'search'):
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.SECONDARY,
                    results=[],
                    error="关键词知识库不支持search方法"
                )
            
            results = self.keyword_kb.search(query, top_k=top_k)
            
            if len(results) < min_results:
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.SECONDARY,
                    results=results,
                    error=f"结果数量不足: {len(results)} < {min_results}",
                    fallback_reason="PRIMARY失败"
                )
            
            logger.info(f"[Fallback] SECONDARY成功: 返回{len(results)}个结果")
            return FallbackResult(
                success=True,
                level=FallbackLevel.SECONDARY,
                results=results,
                fallback_reason="PRIMARY失败"
            )
            
        except Exception as e:
            logger.error(f"[Fallback] SECONDARY异常: {str(e)}", exc_info=True)
            return FallbackResult(
                success=False,
                level=FallbackLevel.SECONDARY,
                results=[],
                error=str(e),
                fallback_reason="PRIMARY失败"
            )
    
    def _try_memory_search(self, 
                          query: str, 
                          top_k: int,
                          min_results: int) -> FallbackResult:
        """
        尝试内存检索（简单字符串匹配）
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_results: 最少结果数
            
        Returns:
            降级结果
        """
        try:
            # 尝试从关键词知识库获取所有文档
            all_docs = []
            if self.keyword_kb:
                if hasattr(self.keyword_kb, 'chunks'):
                    all_docs = self.keyword_kb.chunks
                elif hasattr(self.keyword_kb, 'get_all_documents'):
                    all_docs = self.keyword_kb.get_all_documents()
            
            if not all_docs:
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.TERTIARY,
                    results=[],
                    error="无法获取文档进行内存检索",
                    fallback_reason="PRIMARY和SECONDARY失败"
                )
            
            # 简单的字符串包含匹配
            import jieba
            query_tokens = set(jieba.cut(query.lower()))
            
            matched_docs = []
            for doc in all_docs:
                content = doc.get('content', '').lower()
                doc_tokens = set(jieba.cut(content))
                
                # 计算交集
                overlap = query_tokens & doc_tokens
                if overlap:
                    score = len(overlap) / len(query_tokens) if query_tokens else 0
                    matched_docs.append({
                        **doc,
                        'similarity': score,
                        'match_type': 'memory'
                    })
            
            # 排序并返回top_k
            matched_docs.sort(key=lambda x: x['similarity'], reverse=True)
            results = matched_docs[:top_k]
            
            if len(results) < min_results:
                return FallbackResult(
                    success=False,
                    level=FallbackLevel.TERTIARY,
                    results=results,
                    error=f"结果数量不足: {len(results)} < {min_results}",
                    fallback_reason="PRIMARY和SECONDARY失败"
                )
            
            logger.info(f"[Fallback] TERTIARY成功: 返回{len(results)}个结果")
            return FallbackResult(
                success=True,
                level=FallbackLevel.TERTIARY,
                results=results,
                fallback_reason="PRIMARY和SECONDARY失败"
            )
            
        except Exception as e:
            logger.error(f"[Fallback] TERTIARY异常: {str(e)}", exc_info=True)
            return FallbackResult(
                success=False,
                level=FallbackLevel.TERTIARY,
                results=[],
                error=str(e),
                fallback_reason="PRIMARY和SECONDARY失败"
            )
    
    def _emergency_response(self, query: str) -> FallbackResult:
        """
        紧急响应（所有检索方法都失败）
        
        返回友好的错误消息和建议
        
        Args:
            query: 查询文本
            
        Returns:
            降级结果
        """
        logger.error(f"[Fallback] EMERGENCY: 所有检索方法都失败，查询={query}")
        
        # 生成友好的错误消息
        error_message = {
            'type': 'system_error',
            'message': '抱歉，系统暂时无法检索相关信息',
            'suggestions': [
                '请稍后重试',
                '尝试使用不同的关键词重新提问',
                '简化您的问题，使用更具体的术语',
                '如果问题持续存在，请联系系统管理员'
            ],
            'query': query,
            'timestamp': None
        }
        
        # 添加时间戳
        from datetime import datetime
        error_message['timestamp'] = datetime.now().isoformat()
        
        return FallbackResult(
            success=False,
            level=FallbackLevel.EMERGENCY,
            results=[],
            error="所有检索方法都失败",
            fallback_reason="PRIMARY、SECONDARY和TERTIARY全部失败"
        )
    
    def get_stats(self) -> Dict[str, any]:
        """
        获取降级统计信息
        
        Returns:
            统计信息字典
        """
        total = sum(self.fallback_stats.values())
        
        stats = {
            'total_requests': total,
            'by_level': {}
        }
        
        for level, count in self.fallback_stats.items():
            stats['by_level'][level.value] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0
            }
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        for level in FallbackLevel:
            self.fallback_stats[level] = 0
        logger.info("[Fallback] 统计信息已重置")
