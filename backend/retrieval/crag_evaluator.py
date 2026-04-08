# -*- coding: utf-8 -*-
"""CRAG (Corrective Retrieval Augmented Generation) 检索质量评估与纠正。

参考 CRAG 论文（arXiv:2401.15884），引入轻量级检索评估器：
- 对检索结果质量打分
- 质量差时触发纠正策略（扩大检索范围 / 查询改写 / 拒绝回答）
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

import jieba

try:
    from config import CRAG_QUALITY_THRESHOLD_HIGH, CRAG_QUALITY_THRESHOLD_LOW
except ImportError:
    CRAG_QUALITY_THRESHOLD_HIGH = 0.6
    CRAG_QUALITY_THRESHOLD_LOW = 0.3

logger = logging.getLogger(__name__)


class RetrievalQualityEvaluator:
    """评估检索结果与查询的相关性质量。"""

    def evaluate(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        query_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """评估检索质量，返回评估结果和建议动作。

        Returns:
            {
                'quality_score': float (0-1),
                'action': 'accept' | 'refine' | 'reject',
                'details': {...},
                'correction_hints': [...]
            }
        """
        if not sources:
            return {
                'quality_score': 0.0,
                'action': 'reject',
                'details': {'reason': '无检索结果'},
                'correction_hints': ['expand_query', 'lower_threshold'],
            }

        query_keywords = set(jieba.cut(query))
        query_keywords = {w for w in query_keywords if len(w) >= 2}
        intents = query_analysis.get('intents', [])

        # 多维度评估
        scores = {
            'similarity': self._score_similarity(sources),
            'keyword_coverage': self._score_keyword_coverage(query_keywords, sources),
            'diversity': self._score_diversity(sources),
            'completeness': self._score_completeness(query, intents, sources),
        }

        # 加权综合分
        weights = {
            'similarity': 0.35,
            'keyword_coverage': 0.30,
            'diversity': 0.15,
            'completeness': 0.20,
        }
        quality_score = sum(scores[k] * weights[k] for k in scores)

        # 确定动作
        if quality_score >= CRAG_QUALITY_THRESHOLD_HIGH:
            action = 'accept'
        elif quality_score >= CRAG_QUALITY_THRESHOLD_LOW:
            action = 'refine'
        else:
            action = 'reject'

        # 纠正建议
        correction_hints = self._generate_correction_hints(scores, query_analysis)

        result = {
            'quality_score': round(quality_score, 3),
            'action': action,
            'details': {k: round(v, 3) for k, v in scores.items()},
            'correction_hints': correction_hints,
        }

        logger.info(
            'CRAG 评估: query="%s" score=%.3f action=%s hints=%s',
            query[:50], quality_score, action, correction_hints,
        )
        return result

    def _score_similarity(self, sources: List[Dict[str, Any]]) -> float:
        """评估平均相似度分数。"""
        sims = [
            max(s.get('similarity', 0.0), s.get('rerank_score', 0.0))
            for s in sources
        ]
        if not sims:
            return 0.0
        # Top-3 平均
        top_sims = sorted(sims, reverse=True)[:3]
        return min(sum(top_sims) / len(top_sims), 1.0)

    def _score_keyword_coverage(
        self, query_keywords: set, sources: List[Dict[str, Any]]
    ) -> float:
        """评估检索结果覆盖了多少查询关键词。"""
        if not query_keywords:
            return 0.5

        covered = set()
        for s in sources:
            text = str(s.get('text', ''))
            for kw in query_keywords:
                if kw in text:
                    covered.add(kw)

        return len(covered) / len(query_keywords) if query_keywords else 0.5

    def _score_diversity(self, sources: List[Dict[str, Any]]) -> float:
        """评估检索结果的章节多样性。"""
        sections = set()
        for s in sources:
            section = str(s.get('section', '')).strip()
            if section:
                sections.add(section)
        if len(sources) <= 1:
            return 0.5
        return min(len(sections) / max(len(sources), 1), 1.0)

    def _score_completeness(
        self, query: str, intents: List[str], sources: List[Dict[str, Any]]
    ) -> float:
        """评估检索结果是否足以回答问题。"""
        total_text_len = sum(len(str(s.get('text', ''))) for s in sources)

        # 基于文本总长度的粗略估计
        if total_text_len < 100:
            return 0.2
        if total_text_len < 300:
            return 0.4
        if total_text_len < 800:
            return 0.7
        return 0.9

    def _generate_correction_hints(
        self, scores: Dict[str, float], query_analysis: Dict[str, Any]
    ) -> List[str]:
        """根据评估分数生成纠正建议。"""
        hints: List[str] = []

        if scores['similarity'] < 0.3:
            hints.append('expand_top_k')
        if scores['keyword_coverage'] < 0.4:
            hints.append('rewrite_query')
        if scores['diversity'] < 0.3:
            hints.append('diversify_retrieval')
        if scores['completeness'] < 0.3:
            hints.append('lower_threshold')

        return hints


def apply_corrections(
    query: str,
    sources: List[Dict[str, Any]],
    evaluation: Dict[str, Any],
    retriever: Any = None,
    top_k: int = 6,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """根据 CRAG 评估结果应用纠正策略。

    Returns:
        (corrected_sources, correction_info)
    """
    action = evaluation.get('action', 'accept')
    hints = evaluation.get('correction_hints', [])

    if action == 'accept':
        return sources, {'corrected': False}

    correction_info: Dict[str, Any] = {'corrected': True, 'actions_taken': []}

    if action == 'refine' and retriever is not None:
        # 策略1: 扩大 top_k 重新检索
        if 'expand_top_k' in hints:
            expanded_top_k = min(top_k * 2, 20)
            try:
                expanded_sources = retriever.search(query, top_k=expanded_top_k)
                if len(expanded_sources) > len(sources):
                    sources = expanded_sources
                    correction_info['actions_taken'].append(f'expanded_top_k_to_{expanded_top_k}')
            except Exception as exc:
                logger.warning('CRAG expand_top_k 失败: %s', exc)

        # 策略2: 使用查询关键词做补充检索
        if 'rewrite_query' in hints:
            keywords = query_analysis_keywords(query)
            if keywords:
                keyword_query = ' '.join(keywords[:4])
                try:
                    extra = retriever.search(keyword_query, top_k=max(top_k // 2, 3))
                    existing_ids = {s.get('id') for s in sources}
                    for e in extra:
                        if e.get('id') not in existing_ids:
                            sources.append(e)
                    correction_info['actions_taken'].append('keyword_supplement')
                except Exception as exc:
                    logger.warning('CRAG rewrite_query 补充失败: %s', exc)

    if action == 'reject':
        correction_info['actions_taken'].append('quality_too_low')

    logger.info('CRAG 纠正完成: actions=%s', correction_info.get('actions_taken'))
    return sources, correction_info


def query_analysis_keywords(query: str) -> List[str]:
    """提取查询关键词。"""
    stopwords = {'什么', '如何', '怎么', '是否', '可以', '请问', '哪些', '关于', '需要'}
    tokens = []
    for token in jieba.cut(query):
        cleaned = token.strip()
        if len(cleaned) >= 2 and cleaned not in stopwords:
            tokens.append(cleaned)
    return tokens[:6]


# 全局实例
quality_evaluator = RetrievalQualityEvaluator()
