# -*- coding: utf-8 -*-
"""
混合检索器
结合 ChromaDB 向量检索和 TF-IDF 关键词检索
"""
from typing import List, Dict, Optional
import logging

from config import USE_CHROMADB, USE_HYBRID_SEARCH, VECTOR_SEARCH_WEIGHT, KEYWORD_SEARCH_WEIGHT
from chroma_knowledge_base import chroma_knowledge_base
from knowledge_base import knowledge_base as tfidf_kb

logger = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器"""

    def __init__(
        self,
        vector_weight: float = None,
        keyword_weight: float = None
    ):
        self.vector_weight = vector_weight if vector_weight is not None else VECTOR_SEARCH_WEIGHT
        self.keyword_weight = keyword_weight if keyword_weight is not None else KEYWORD_SEARCH_WEIGHT

        self.use_chroma = USE_CHROMADB and chroma_knowledge_base is not None
        self.use_tfidf = tfidf_kb is not None and tfidf_kb.is_loaded()

        logger.info(f"混合检索器初始化: 向量权重={self.vector_weight}, 关键词权重={self.keyword_weight}")
        logger.info(f"  - ChromaDB: {'启用' if self.use_chroma else '禁用'}")
        logger.info(f"  - TF-IDF: {'启用' if self.use_tfidf else '禁用'}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_vector: bool = None,
        use_keyword: bool = None
    ) -> List[Dict]:
        """
        混合搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_vector: 是否使用向量检索（None 表示根据配置）
            use_keyword: 是否使用关键词检索（None 表示根据配置）

        Returns:
            融合后的搜索结果
        """
        # 确定使用哪种检索方式
        if use_vector is None:
            use_vector = self.use_chroma
        if use_keyword is None:
            use_keyword = self.use_tfidf

        results = {}

        # 向量检索
        if use_vector and self.use_chroma:
            try:
                vector_results = chroma_knowledge_base.search(query, top_k=top_k * 2)
                for i, result in enumerate(vector_results):
                    doc_id = result['id']
                    if doc_id not in results:
                        results[doc_id] = {
                            'id': doc_id,
                            'text': result['text'],
                            'metadata': result.get('metadata', {}),
                            'scores': {}
                        }
                    results[doc_id]['scores']['vector'] = {
                        'value': result['similarity'],
                        'normalized': 1 - (i / len(vector_results)) if len(vector_results) > 0 else 0
                    }
            except Exception as e:
                logger.error(f"向量检索失败: {e}")

        # 关键词检索
        if use_keyword and self.use_tfidf:
            try:
                keyword_results = tfidf_kb.search(query, top_k=top_k * 2)
                for i, result in enumerate(keyword_results):
                    doc_id = result['id']
                    if doc_id not in results:
                        results[doc_id] = {
                            'id': doc_id,
                            'text': result['text'],
                            'metadata': {},
                            'scores': {}
                        }
                    results[doc_id]['scores']['keyword'] = {
                        'value': result['similarity'],
                        'normalized': 1 - (i / len(keyword_results)) if len(keyword_results) > 0 else 0
                    }
            except Exception as e:
                logger.error(f"关键词检索失败: {e}")

        # 融合分数
        for doc_id, doc_data in results.items():
            vector_score = doc_data['scores'].get('vector', {}).get('normalized', 0)
            keyword_score = doc_data['scores'].get('keyword', {}).get('normalized', 0)

            # 归一化权重
            total_weight = self.vector_weight + self.keyword_weight
            if total_weight > 0:
                doc_data['final_score'] = (
                    (vector_score * self.vector_weight + keyword_score * self.keyword_weight) / total_weight
                )
            else:
                doc_data['final_score'] = 0

        # 排序并返回 Top-K
        sorted_results = sorted(
            results.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )

        return sorted_results[:top_k]

    def get_statistics(self) -> Dict:
        """获取检索器统计信息"""
        stats = {
            'use_chroma': self.use_chroma,
            'use_tfidf': self.use_tfidf,
            'vector_weight': self.vector_weight,
            'keyword_weight': self.keyword_weight
        }

        if self.use_chroma and chroma_knowledge_base:
            stats['chroma_stats'] = chroma_knowledge_base.get_statistics()

        if self.use_tfidf and tfidf_kb:
            stats['tfidf_stats'] = tfidf_kb.get_statistics()

        return stats


# 全局实例
hybrid_retriever = HybridRetriever() if USE_HYBRID_SEARCH else None

if USE_HYBRID_SEARCH and hybrid_retriever:
    logger.info("混合检索器已启用")
else:
    logger.info("混合检索器未启用")