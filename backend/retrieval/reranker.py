# -*- coding: utf-8 -*-
"""
Rerank（重排序）模块
对向量检索结果进行精排，提升相关性
"""
import re
import time
from typing import List, Dict, Optional
from collections import Counter

import jieba

from config import (
    RERANKER_USE_CROSS_ENCODER,
    RERANKER_CROSS_ENCODER_MODEL,
    RERANKER_BATCH_SIZE,
    RERANKER_MAX_LENGTH,
)


class Reranker:
    """重排序器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.use_cross_encoder = self.config.get('use_cross_encoder', RERANKER_USE_CROSS_ENCODER)
        self.cross_encoder_model = self.config.get('cross_encoder_model', RERANKER_CROSS_ENCODER_MODEL)
        self.batch_size = RERANKER_BATCH_SIZE
        self.max_length = RERANKER_MAX_LENGTH

        # 初始化交叉编码器（如果启用）
        self.cross_encoder = None
        if self.use_cross_encoder:
            self._init_cross_encoder()

    def _init_cross_encoder(self):
        """初始化交叉编码器（GPU加速）"""
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder(
                self.cross_encoder_model or 'BAAI/bge-reranker-base',
                device=device
            )
            print(f"[OK] CrossEncoder 初始化成功 @ {device}")
        except ImportError:
            print("[WARN] sentence-transformers 未安装，将使用基于规则的重排序")
            self.use_cross_encoder = False
        except Exception as e:
            print(f"[WARN] CrossEncoder 初始化失败: {e}，将使用基于规则的重排序")
            self.use_cross_encoder = False

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        重排序文档

        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            top_k: 返回的文档数量

        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []

        # 记录原始相似度
        for doc in documents:
            if 'original_similarity' not in doc:
                doc['original_similarity'] = doc.get('similarity', 0)

        # 使用交叉编码器重排序
        if self.use_cross_encoder and self.cross_encoder:
            return self._rerank_with_cross_encoder(query, documents, top_k)

        # 使用基于规则的重排序
        return self._rerank_with_rules(query, documents, top_k)

    def _rerank_with_cross_encoder(
        self,
        query: str,
        documents: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """使用交叉编码器进行重排序"""
        try:
            # 准备输入对
            pairs = [[query, doc['text']] for doc in documents]

            # 计算分数
            scores = self.cross_encoder.predict(pairs)

            # 更新重排序分数
            for i, doc in enumerate(documents):
                doc['rerank_score'] = float(scores[i])

            # 按分数排序
            reranked = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)

            return reranked[:top_k]

        except Exception as e:
            print(f"[WARN] 交叉编码器重排序失败: {e}，降级到规则重排序")
            return self._rerank_with_rules(query, documents, top_k)

    def _rerank_with_rules(
        self,
        query: str,
        documents: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """使用基于规则的重排序"""
        query_keywords = set(jieba.cut(query))

        scored_docs = []
        for doc in documents:
            text = doc.get('text', '')

            # 计算多个特征
            features = self._extract_features(query, text, query_keywords)

            # 计算综合分数
            rerank_score = self._calculate_score(features, doc.get('similarity', 0))

            doc['rerank_score'] = rerank_score
            doc['features'] = features

            scored_docs.append(doc)

        # 按重排序分数排序
        reranked = sorted(scored_docs, key=lambda x: x['rerank_score'], reverse=True)

        return reranked[:top_k]

    def _extract_features(
        self,
        query: str,
        text: str,
        query_keywords: set
    ) -> Dict:
        """提取特征用于重排序"""
        # 关键词匹配
        text_keywords = set(jieba.cut(text))
        keyword_overlap = len(query_keywords & text_keywords) / len(query_keywords) if query_keywords else 0

        # 精确短语匹配
        exact_match_score = 0
        if query in text:
            exact_match_score = 1.0

        # 部分短语匹配（2-gram）
        query_bigrams = [query[i:i+2] for i in range(len(query)-1)]
        phrase_match = sum(1 for bigram in query_bigrams if bigram in text) / len(query_bigrams) if query_bigrams else 0

        # 文本长度惩罚（过短或过长的文档降权）
        length = len(text)
        optimal_length = 300
        length_penalty = 1.0 - min(abs(length - optimal_length) / optimal_length, 0.5)

        # 章节相关性（包含章节标题的文档提权）
        section_score = 0
        if self._has_section_title(text):
            section_score = 0.2

        # 句子完整性（以句号结尾的完整句子提权）
        sentence_completeness = 0
        if text.rstrip().endswith(('。', '！', '？', '\n')):
            sentence_completeness = 0.1

        # 重复内容惩罚
        unique_chars = len(set(text))
        uniqueness = unique_chars / length if length > 0 else 0

        return {
            'keyword_overlap': keyword_overlap,
            'exact_match': exact_match_score,
            'phrase_match': phrase_match,
            'length_penalty': length_penalty,
            'section_score': section_score,
            'sentence_completeness': sentence_completeness,
            'uniqueness': uniqueness
        }

    def _calculate_score(self, features: Dict, vector_similarity: float) -> float:
        """计算综合重排序分数"""
        # 权重配置
        weights = {
            'vector_similarity': 0.4,      # 向量相似度权重
            'keyword_overlap': 0.25,       # 关键词重叠权重
            'exact_match': 0.15,           # 精确匹配权重
            'phrase_match': 0.10,          # 短语匹配权重
            'length_penalty': 0.05,        # 长度惩罚权重
            'section_score': 0.03,         # 章节相关性权重
            'sentence_completeness': 0.01, # 句子完整性权重
            'uniqueness': 0.01             # 唯一性权重
        }

        # 计算加权分数
        score = (
            vector_similarity * weights['vector_similarity'] +
            features['keyword_overlap'] * weights['keyword_overlap'] +
            features['exact_match'] * weights['exact_match'] +
            features['phrase_match'] * weights['phrase_match'] +
            features['length_penalty'] * weights['length_penalty'] +
            features['section_score'] * weights['section_score'] +
            features['sentence_completeness'] * weights['sentence_completeness'] +
            features['uniqueness'] * weights['uniqueness']
        )

        return score

    def _has_section_title(self, text: str) -> bool:
        """判断文本是否包含章节标题"""
        patterns = [
            r'第[一二三四五六七八九十]+[编章节]',
            r'第\d+[编章节]',
            r'安徽信息工程学院[^\n]+（实施）办法',
            r'安徽信息工程学院[^\n]+管理[办法细则条例]',
        ]

        for pattern in patterns:
            if re.search(pattern, text):
                return True

        return False

    def get_statistics(self) -> Dict:
        """获取重排序器统计信息"""
        return {
            'use_cross_encoder': self.use_cross_encoder,
            'cross_encoder_model': self.cross_encoder_model,
            'method': 'cross_encoder' if self.use_cross_encoder else 'rule_based'
        }


# 全局重排序器实例
reranker = Reranker()