# -*- coding: utf-8 -*-
"""
Adaptive-RAG 查询路由器

基于 arXiv:2403.14403 (Adaptive-RAG) 思路:
按查询复杂度自动选择最高效的检索策略,
避免简单问题浪费完整管线（HyDE+CRAG+多路检索）资源。

三级路由:
- simple   → 仅 keyword/vector 单路检索, 跳过 HyDE/CRAG
- standard → 混合检索 + Rerank, 跳过 HyDE
- complex  → 完整管线: HyDE + 多路 + CRAG + 父子扩展
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── 路由常量 ──────────────────────────────────────────────
ROUTE_SIMPLE = 'simple'
ROUTE_STANDARD = 'standard'
ROUTE_COMPLEX = 'complex'

# ── 复杂查询特征词 ─────────────────────────────────────────
_COMPARE_HINTS = frozenset({
    '比较', '区别', '关系', '异同', '优缺点', '对比', '以及', '还有',
    '和…的区别', '分析', '评价', '如何看待', '为什么',
})

_MULTI_HOP_HINTS = frozenset({
    '先修课程', '后续课程', '课程链', '学习路径', '课程衔接',
    '课程关系', '课程顺序', '跨', '覆盖', '重叠', '断层',
    '一致性', '衔接', '体系',
})

_SIMPLE_PATTERNS = [
    re.compile(r'^.{0,2}(什么是|是什么|定义|概念).{0,15}$'),
    re.compile(r'^.{2,8}(几学分|多少学分|学分数)'),
    re.compile(r'^.{2,8}(在第几学期|哪个学期|开课学期)'),
    re.compile(r'^.{2,6}(有哪些课|课程有哪些|包含哪些课)'),
    re.compile(r'^(你好|你是谁|介绍一下)'),
]


class AdaptiveRouter:
    """基于规则的查询复杂度分类器。"""

    def classify(
        self,
        query: str,
        query_analysis: Dict[str, Any],
    ) -> str:
        """
        对查询进行复杂度分类, 返回路由级别。

        Parameters
        ----------
        query : str
            用户原始查询
        query_analysis : dict
            来自 agent_v2._analyze_query() 的分析结果,
            包含 complexity, intents, keywords 等字段

        Returns
        -------
        str
            'simple' | 'standard' | 'complex'
        """
        complexity = query_analysis.get('complexity', 3)
        intents = query_analysis.get('intents', [])
        keywords = query_analysis.get('keywords', [])
        query_len = len(query)

        # ── 简单查询快速通道 ──
        if complexity <= 1 and query_len <= 12:
            route = ROUTE_SIMPLE
        elif any(p.search(query) for p in _SIMPLE_PATTERNS):
            route = ROUTE_SIMPLE
        # ── 复杂查询完整管线 ──
        elif complexity >= 4:
            route = ROUTE_COMPLEX
        elif len(intents) >= 2:
            route = ROUTE_COMPLEX
        elif any(h in query for h in _MULTI_HOP_HINTS):
            route = ROUTE_COMPLEX
        elif any(h in query for h in _COMPARE_HINTS) and query_len >= 15:
            route = ROUTE_COMPLEX
        # ── 中等查询标准管线 ──
        else:
            route = ROUTE_STANDARD

        logger.info(
            "AdaptiveRouter: query=%r complexity=%d intents=%s → route=%s",
            query[:40], complexity, intents, route,
        )
        return route


# 模块级单例
adaptive_router = AdaptiveRouter()
