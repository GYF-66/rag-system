# -*- coding: utf-8 -*-
"""
Agent 模块测试
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
def test_agent_creation():
    """测试 Agent 创建"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    assert agent.name == "安信工AI小助手"
    assert agent.role == "学生手册智能问答助手"
    assert agent.description is not None
    assert len(agent.chapter_patterns) > 0


@pytest.mark.unit
def test_agent_query_analysis():
    """测试查询分析"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    # 测试简单查询
    query = "请假流程是什么？"
    keywords = agent._extract_keywords(query)

    assert isinstance(keywords, list)
    assert len(keywords) > 0


@pytest.mark.unit
def test_agent_extract_key_sentences():
    """测试关键句子提取"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    text = "这是第一句话。这是第二句话！这是第三句话？"
    sentences = agent._extract_key_sentences(text, max_sentences=3)

    assert len(sentences) == 3
    assert "这是第一句话" in sentences[0]


@pytest.mark.unit
def test_agent_generate_response_no_sources():
    """测试无来源时的回复生成"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()
    response = agent._generate_fallback_response("测试查询")

    assert "抱歉" in response
    assert "测试查询" in response


@pytest.mark.unit
def test_agent_merge_continuous_chunks():
    """测试连续块合并"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    chunks = [
        {"id": "0", "text": "第一段内容", "section": "第一章", "similarity": 0.9},
        {"id": "1", "text": "第二段内容", "section": "第一章", "similarity": 0.85},
        {"id": "2", "text": "其他章节内容", "section": "第二章", "similarity": 0.8}
    ]

    merged = agent._merge_continuous_chunks(chunks)

    assert len(merged) <= len(chunks)  # 合并后数量应该减少或不变


@pytest.mark.unit
def test_agent_process_query_without_rag():
    """测试不使用 RAG 的查询处理"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    with patch.object(agent, '_generate_response', return_value="测试回复"):
        result = agent.process_query(
            query="测试问题",
            use_rag=False
        )

        assert result['response'] == "测试回复"
        assert 'sources' in result


@pytest.mark.unit
def test_agent_detect_query_type():
    """测试查询类型检测"""
    from backend.agent import StudentManualAgent

    agent = StudentManualAgent()

    # 测试"如何"类查询
    query1 = "如何申请奖学金？"
    type1 = agent._detect_query_type(query1)
    assert type1 == "how_to"

    # 测试"是否"类查询
    query2 = "可以请假吗？"
    type2 = agent._detect_query_type(query2)
    assert type2 == "yes_no"

    # 测试"哪些"类查询
    query3 = "有哪些奖学金？"
    type3 = agent._detect_query_type(query3)
    assert type3 == "quantity"