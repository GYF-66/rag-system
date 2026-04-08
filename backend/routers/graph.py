# -*- coding: utf-8 -*-
"""
GraphRAG API 路由 — 知识图谱可视化与分析接口

提供以下端点：
  GET  /api/graph/visualization  — 完整图谱可视化数据
  GET  /api/graph/stats          — 图谱统计信息
  POST /api/graph/search         — 图谱子图检索
  POST /api/graph/learning-path  — 学习路径查询
  GET  /api/graph/alignment      — 培养方案一致性分析
  GET  /api/graph/communities    — 社区列表
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/graph', tags=['GraphRAG'])

# ── 请求/响应模型 ──────────────────────────────────────────────────────


class GraphSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_hops: int = Field(2, ge=1, le=4)
    max_nodes: int = Field(30, ge=5, le=100)


class LearningPathRequest(BaseModel):
    course_keyword: str = Field(..., min_length=1, max_length=100)


# ── 图谱实例获取 ──────────────────────────────────────────────────────

# ── 独立图谱实例（不依赖 agent 初始化） ──────────────────────────────

_standalone_kg = None
_standalone_retriever = None


def _ensure_standalone_graph():
    """惰性构建独立图谱实例"""
    global _standalone_kg, _standalone_retriever
    if _standalone_kg and _standalone_kg.is_built:
        return
    try:
        from graph.knowledge_graph import CourseKnowledgeGraph
        from graph.graph_retriever import GraphRetriever
        from config import KNOWLEDGE_BASE_PATH
        import json
        kb_data = json.loads(KNOWLEDGE_BASE_PATH.read_text(encoding='utf-8'))
        _standalone_kg = CourseKnowledgeGraph()
        _standalone_kg.build_from_knowledge_base(kb_data)
        _standalone_retriever = GraphRetriever(_standalone_kg)
        logger.info('GraphRAG 独立实例初始化完成: %d nodes, %d edges',
                     _standalone_kg.node_count, _standalone_kg.edge_count)
    except Exception as exc:
        logger.warning('GraphRAG 独立实例初始化失败: %s', exc)


def _get_knowledge_graph():
    """获取知识图谱实例：优先 agent 内置，回退独立实例"""
    try:
        from agent_v2 import agent_v2 as _agent
        if hasattr(_agent, '_knowledge_graph') and _agent._knowledge_graph and _agent._knowledge_graph.is_built:
            return _agent._knowledge_graph
    except Exception:
        pass
    _ensure_standalone_graph()
    return _standalone_kg


def _get_graph_retriever():
    """获取图谱检索器实例"""
    try:
        from agent_v2 import agent_v2 as _agent
        if hasattr(_agent, '_graph_retriever') and _agent._graph_retriever:
            return _agent._graph_retriever
    except Exception:
        pass
    _ensure_standalone_graph()
    return _standalone_retriever


# ── 端点 ──────────────────────────────────────────────────────────────


@router.get('/visualization')
async def get_visualization_data(
    node_type: Optional[str] = Query(None, description='过滤节点类型: course/concept/requirement'),
    community_id: Optional[int] = Query(None, description='过滤社区 ID'),
):
    """获取完整图谱的可视化数据（前端渲染用）"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    data = kg.get_visualization_data()

    # 可选过滤
    if node_type:
        data['nodes'] = [n for n in data['nodes'] if n.get('type') == node_type]
        node_ids = {n['id'] for n in data['nodes']}
        data['edges'] = [e for e in data['edges'] if e['source'] in node_ids and e['target'] in node_ids]

    if community_id is not None:
        data['nodes'] = [n for n in data['nodes'] if n.get('community') == community_id]
        node_ids = {n['id'] for n in data['nodes']}
        data['edges'] = [e for e in data['edges'] if e['source'] in node_ids and e['target'] in node_ids]

    return data


@router.get('/stats')
async def get_graph_stats():
    """获取图谱统计信息"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    viz = kg.get_visualization_data()
    return viz.get('stats', {})


@router.post('/search')
async def search_subgraph(request: GraphSearchRequest):
    """基于查询的子图检索"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    import jieba
    keywords = [w for w in jieba.cut(request.query) if len(w) >= 2]
    result = kg.search_subgraph(keywords, max_hops=request.max_hops, max_nodes=request.max_nodes)
    return result


@router.post('/learning-path')
async def get_learning_path(request: LearningPathRequest):
    """获取课程学习路径"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    result = kg.get_course_learning_path(request.course_keyword)
    return result


@router.get('/alignment')
async def get_alignment_analysis():
    """获取培养方案一致性分析报告"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    return kg.get_alignment_analysis()


@router.get('/communities')
async def get_communities():
    """获取社区列表及摘要"""
    kg = _get_knowledge_graph()
    if not kg:
        raise HTTPException(status_code=503, detail='GraphRAG 知识图谱未就绪')

    viz = kg.get_visualization_data()
    return {
        'communities': viz.get('communities', {}),
        'total': len(viz.get('communities', {})),
    }
