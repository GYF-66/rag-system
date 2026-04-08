# -*- coding: utf-8 -*-
"""
GraphRAG 检索器 — 图谱增强的检索后端

实现 HybridRetriever 的 backend 接口约定（search 方法），
可作为第三个检索通道注入混合检索器。

检索策略：
1. 子图检索：从查询关键词定位种子节点，BFS 扩展获取上下文
2. 社区检索：全局性问题匹配社区摘要
3. 路径检索：课程链/学习路径类查询
4. 一致性分析：教务决策类查询
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphRetriever:
    """
    图谱检索后端 — 兼容 HybridRetriever 的 backend 接口

    接口约定：
        search(query, top_k, min_similarity) -> List[Dict]
        每个 dict 须含: text, id, section(可选), similarity/score, metadata(可选)
    """

    def __init__(self, knowledge_graph) -> None:
        self._kg = knowledge_graph
        self._cache: Dict[str, List[Dict]] = {}

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.03,
        keywords: Optional[List[str]] = None,
        query_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        图谱检索主入口

        根据查询类型选择不同检索策略：
        - 课程关系/学习路径 → 路径检索
        - 一致性/覆盖度/断层 → 一致性分析
        - 全局性问题 → 社区检索
        - 默认 → 子图检索
        """
        if not self._kg.is_built:
            return []

        start = time.perf_counter()

        # 使用传入的关键词或从查询中提取
        kws = keywords or self._extract_keywords(query)
        if not kws:
            return []

        # 缓存检查
        cache_key = f"{query}:{top_k}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        results: List[Dict[str, Any]] = []
        strategy = self._select_strategy(query, query_type)

        if strategy == 'path':
            results = self._path_search(query, kws, top_k)
        elif strategy == 'alignment':
            results = self._alignment_search(query, top_k)
        elif strategy == 'community':
            results = self._community_search(kws, top_k)
        else:
            results = self._subgraph_search(kws, top_k)

        elapsed = (time.perf_counter() - start) * 1000
        logger.debug('GraphRetriever [%s]: %d 结果, %.1fms', strategy, len(results), elapsed)

        self._cache[cache_key] = results
        return results

    def _select_strategy(self, query: str, query_type: Optional[str] = None) -> str:
        """根据查询内容选择检索策略"""
        path_hints = ('学习路径', '先修', '后续', '课程链', '先导', '前置', '衔接', '课程顺序', '学完之后', '之前学')
        alignment_hints = ('一致性', '覆盖度', '断层', '冗余', '对齐', '支撑', '培养目标', '毕业要求')
        global_hints = ('概述', '总体', '全景', '整体', '所有课程', '专业特色', '专业介绍')

        if any(h in query for h in path_hints):
            return 'path'
        if any(h in query for h in alignment_hints):
            return 'alignment'
        if any(h in query for h in global_hints):
            return 'community'
        return 'subgraph'

    def _subgraph_search(self, keywords: List[str], top_k: int) -> List[Dict[str, Any]]:
        """子图检索 — 默认策略"""
        subgraph = self._kg.search_subgraph(keywords, max_hops=2, max_nodes=25)
        if not subgraph.get('nodes'):
            return []

        results = []
        # 将子图摘要作为一个检索结果
        if subgraph.get('summary'):
            results.append({
                'id': f"graph_subgraph_{hashlib.md5(subgraph['summary'].encode()).hexdigest()[:8]}",
                'text': subgraph['summary'],
                'section': '知识图谱检索',
                'similarity': 0.85,
                'score': 0.85,
                'char_count': len(subgraph['summary']),
                'metadata': {
                    'source': 'graph_rag',
                    'strategy': 'subgraph',
                    'node_count': subgraph.get('total_nodes', 0),
                    'edge_count': subgraph.get('total_edges', 0),
                },
            })

        # 路径推理结果
        for path in subgraph.get('paths', [])[:3]:
            text = f"[知识推理路径] {path['from']} → {path['to']}\n路径：{path['path']}"
            results.append({
                'id': f"graph_path_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                'text': text,
                'section': '图谱推理路径',
                'similarity': 0.80,
                'score': 0.80,
                'char_count': len(text),
                'metadata': {
                    'source': 'graph_rag',
                    'strategy': 'path_reasoning',
                },
            })

        return results[:top_k]

    def _path_search(self, query: str, keywords: List[str], top_k: int) -> List[Dict[str, Any]]:
        """路径检索 — 课程学习路径查询"""
        results = []
        for kw in keywords:
            path_data = self._kg.get_course_learning_path(kw)
            if path_data.get('path'):
                text = path_data['description']
                results.append({
                    'id': f"graph_lpath_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                    'text': text,
                    'section': '学习路径推荐',
                    'similarity': 0.90,
                    'score': 0.90,
                    'char_count': len(text),
                    'metadata': {
                        'source': 'graph_rag',
                        'strategy': 'learning_path',
                        'path_length': len(path_data['path']),
                        'path_data': path_data['path'],
                    },
                })
                break  # 一条路径够了

        # 补充子图结果
        subgraph_results = self._subgraph_search(keywords, top_k - len(results))
        results.extend(subgraph_results)
        return results[:top_k]

    def _alignment_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """一致性分析检索 — 教务决策支持"""
        analysis = self._kg.get_alignment_analysis()
        results = []

        # 总览
        overview = (
            f"[培养方案一致性分析]\n"
            f"课程总数：{analysis['total_courses']}  "
            f"知识点总数：{analysis['total_concepts']}  "
            f"毕业要求：{analysis['total_requirements']}\n"
            f"发现断层：{analysis['gap_count']} 处  "
            f"知识冗余：{analysis['overlap_count']} 处"
        )
        results.append({
            'id': 'graph_alignment_overview',
            'text': overview,
            'section': '一致性分析总览',
            'similarity': 0.92,
            'score': 0.92,
            'char_count': len(overview),
            'metadata': {
                'source': 'graph_rag',
                'strategy': 'alignment',
                'analysis_data': {
                    'gap_count': analysis['gap_count'],
                    'overlap_count': analysis['overlap_count'],
                },
            },
        })

        # 断层详情
        for gap in analysis.get('gaps', [])[:3]:
            text = gap['suggestion']
            results.append({
                'id': f"graph_gap_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                'text': text,
                'section': '知识断层检测',
                'similarity': 0.88,
                'score': 0.88,
                'char_count': len(text),
                'metadata': {
                    'source': 'graph_rag',
                    'strategy': 'gap_detection',
                    'severity': gap.get('severity', 'medium'),
                },
            })

        # 冗余详情
        for overlap in analysis.get('overlaps', [])[:3]:
            text = overlap['suggestion']
            results.append({
                'id': f"graph_overlap_{hashlib.md5(text.encode()).hexdigest()[:8]}",
                'text': text,
                'section': '知识冗余检测',
                'similarity': 0.85,
                'score': 0.85,
                'char_count': len(text),
                'metadata': {
                    'source': 'graph_rag',
                    'strategy': 'overlap_detection',
                },
            })

        return results[:top_k]

    def _community_search(self, keywords: List[str], top_k: int) -> List[Dict[str, Any]]:
        """社区检索 — 全局性问题"""
        communities = self._kg.search_community(keywords, top_k=top_k)
        results = []
        for comm in communities:
            text = comm['summary']
            results.append({
                'id': f"graph_community_{comm['community_id']}",
                'text': text,
                'section': '知识社区',
                'similarity': min(0.70 + comm['score'] * 0.1, 0.95),
                'score': min(0.70 + comm['score'] * 0.1, 0.95),
                'char_count': len(text),
                'metadata': {
                    'source': 'graph_rag',
                    'strategy': 'community',
                    'community_id': comm['community_id'],
                    'member_count': comm['member_count'],
                },
            })
        return results[:top_k]

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """简易关键词提取"""
        import jieba
        words = list(jieba.cut(query))
        return [w for w in words if len(w) >= 2]
