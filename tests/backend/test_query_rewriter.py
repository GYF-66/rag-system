# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
def test_query_rewriter_returns_structured_payload():
    from backend.pipeline.query_rewriter import query_rewriter

    result = query_rewriter.rewrite('人工智能专业核心课程怎么安排？', max_variants=4)

    assert result['normalized_query'] == '人工智能专业核心课程怎么安排?'
    assert 'curriculum' in result['intents']
    assert result['query_category'] == 'program'
    assert result['intent_confidence']['curriculum'] > 0
    assert result['keywords']
    assert result['variants']
    assert len(result['variants']) <= 3


@pytest.mark.unit
def test_query_rewriter_keeps_technical_query_conservative():
    from backend.pipeline.query_rewriter import query_rewriter

    result = query_rewriter.rewrite('机器学习 API 接口要求是什么？', max_variants=5)

    assert result['query_category'] == 'technical'
    assert any('api' in variant.lower() for variant in result['variants'])
    assert len(result['variants']) <= 3


@pytest.mark.unit
def test_query_rewriter_generates_refinement_suggestions():
    from backend.pipeline.query_rewriter import query_rewriter

    suggestions = query_rewriter.suggest('奖学金申请条件有哪些？', max_suggestions=3)

    assert 1 <= len(suggestions) <= 3
    assert all('refined_query' in item for item in suggestions)
    assert any(item['strategy'] == 'intent_expansion' for item in suggestions)
