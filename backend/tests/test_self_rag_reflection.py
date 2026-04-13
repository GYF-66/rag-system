# -*- coding: utf-8 -*-
import asyncio
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from agent_v2 import AISpecialtyAgentV2


class StubLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    async def chat(self, *args, **kwargs):
        if not self._responses:
            return ''
        return self._responses.pop(0)

    def is_available(self):
        return True


class SlowLLM:
    def is_available(self):
        return True

    async def chat(self, *args, **kwargs):
        await asyncio.sleep(0.05)
        return 'timeout'


@pytest.mark.anyio
async def test_self_rag_reflection_can_return_revised_answer():
    agent = AISpecialtyAgentV2.__new__(AISpecialtyAgentV2)
    llm = StubLLM([
        'STATUS: partially_supported\nCONFIDENCE: 0.78\nISSUES: 缺少对实践环节的直接证据',
        '修订后的回答：当前证据显示实践环节以课程实验和综合实践为主，资料未明确说明额外必修安排。',
    ])

    reflection, revised = await agent._self_rag_reflect(
        query='人工智能专业实践环节如何安排？',
        response='原始回答：实践环节覆盖多个方向并包含额外校企模块。',
        sources=[
            {'text': '证据一：培养方案显示实践环节包括课程实验、综合实践和毕业设计。'},
            {'text': '证据二：资料未明确说明额外校企模块为必修内容。'},
        ],
        llm=llm,
    )

    assert reflection.status == 'partially_supported'
    assert reflection.revision_applied is True
    assert revised is not None
    assert '资料未明确说明' in revised


@pytest.mark.anyio
async def test_self_rag_reflection_keeps_original_when_supported():
    agent = AISpecialtyAgentV2.__new__(AISpecialtyAgentV2)
    llm = StubLLM([
        'STATUS: supported\nCONFIDENCE: 0.95\nISSUES: 无',
    ])

    reflection, revised = await agent._self_rag_reflect(
        query='人工智能专业核心课程有哪些？',
        response='原始回答：核心课程包括机器学习、深度学习等。',
        sources=[
            {'text': '证据一：培养方案列出机器学习、深度学习、计算机视觉等核心课程。'},
        ],
        llm=llm,
    )

    assert reflection.status == 'supported'
    assert reflection.revision_applied is False
    assert revised is None


@pytest.mark.anyio
async def test_process_query_falls_back_when_llm_times_out(monkeypatch):
    agent = AISpecialtyAgentV2.__new__(AISpecialtyAgentV2)
    agent._response_gen = type('ResponseGen', (), {'generate': lambda self, query, context, sources: 'fallback answer'})()
    agent._hybrid_retriever = None
    agent._graph_retriever = None
    agent._knowledge_graph = None
    agent.use_chromadb = False

    monkeypatch.setattr('agent_v2.get_llm_service', lambda: SlowLLM())
    monkeypatch.setattr('agent_v2.LLM_GENERATION_TIMEOUT_SECONDS', 0.01)
    monkeypatch.setattr(agent, '_analyze_query', lambda query: {
        'normalized_query': query,
        'keywords': ['测试'],
        'variants': [],
        'intents': ['general'],
        'query_type': 'general',
        'complexity': 1,
        'adaptive_top_k': 3,
    })

    async def fake_retrieve_sources(query, use_rag, query_analysis):
        return ([{'id': '1', 'text': '证据片段', 'section': '测试章节', 'metadata': {}}], {
            'method': 'tfidf',
            'variant_count': 1,
            'query_variants': [],
            'route': 'simple',
            'hyde_used': False,
            'is_cross_query': False,
        })

    monkeypatch.setattr(agent, '_retrieve_sources', fake_retrieve_sources)
    monkeypatch.setattr(agent, '_prepare_sources', lambda query, sources, query_analysis=None: sources)
    monkeypatch.setattr(agent, '_build_context', lambda sources: '证据片段')

    result = await agent.process_query('测试问题', session_history=[], use_rag=True, enable_thinking=True)

    assert result['response'] == 'fallback answer'
    assert result['metadata']['used_llm'] is False
