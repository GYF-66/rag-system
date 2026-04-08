# -*- coding: utf-8 -*-
import asyncio

import pytest


@pytest.mark.unit
def test_agent_v2_uses_hybrid_retriever_when_available(monkeypatch):
    """Test that when chroma is unavailable and hybrid_retriever is available, hybrid_retriever is used."""
    import backend.agent_v2 as agent_module

    class FakeHybridRetriever:
        def search(self, query, top_k=6):
            return [
                {
                    'id': 'doc-1',
                    'text': '核心课程包括机器学习、深度学习与工程实践。',
                    'section': '课程体系',
                    'similarity': 0.86,
                    'rerank_score': 0.88,
                    'matched_queries': [query, '核心课程'],
                    'matched_channels': ['keyword', 'vector'],
                }
            ]

    # Patch chroma to None so use_chromadb=False, forcing hybrid_retriever path
    monkeypatch.setattr(agent_module, 'chroma_knowledge_base', None)
    monkeypatch.setattr(agent_module, 'hybrid_retriever', FakeHybridRetriever())
    monkeypatch.setattr(agent_module, 'cross_retrieval_engine', None)
    monkeypatch.setattr(agent_module, 'get_llm_service', lambda: None)

    agent = agent_module.AISpecialtyAgentV2()
    result = asyncio.run(agent.process_query('核心课程有哪些？', use_rag=True, enable_thinking=False))

    assert result['sources']
    # When chroma unavailable + hybrid available, simple queries use hybrid_retriever directly
    # with simple_direct method (no multi-variant RRF for ROUTE_SIMPLE)
    assert result['metadata']['retrieval_method'] == 'simple_direct'


@pytest.mark.unit
def test_agent_v2_builds_clean_context_blocks(monkeypatch):
    import backend.agent_v2 as agent_module

    monkeypatch.setattr(agent_module, 'get_llm_service', lambda: None)
    agent = agent_module.AISpecialtyAgentV2()

    sources = [
        {
            'id': '1',
            'section': '培养目标',
            'text': '人工智能专业培养目标强调工程实践能力。 还强调创新能力和综合素养。',
            'metadata': {'title': '人工智能专业培养方案', 'page_start': 12},
            'similarity': 0.8,
            'rerank_score': 0.9,
        },
        {
            'id': '2',
            'section': '培养目标',
            'text': '毕业要求覆盖知识、能力和素质三个方面。',
            'metadata': {'title': '人工智能专业培养方案', 'page_start': 12},
            'similarity': 0.79,
            'rerank_score': 0.88,
        },
    ]

    context = agent._build_context(sources)

    assert '[证据1]' in context
    assert '来源：人工智能专业培养方案 / 章节：培养目标 / 页码 p.12' in context
    assert 'similarity=' not in context
    assert '毕业要求覆盖知识、能力和素质三个方面。' in context

