# -*- coding: utf-8 -*-
"""
知识库模块测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
def test_knowledge_base_load():
    """测试知识库加载"""
    from backend.retrieval.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    assert kb is not None


@pytest.mark.unit
def test_knowledge_base_search():
    """测试知识库搜索"""
    from backend.retrieval.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()

    # 测试基本搜索
    results = kb.search("请假", top_k=5)

    assert isinstance(results, list)
    assert len(results) <= 5


@pytest.mark.unit
def test_knowledge_base_search_empty_query():
    """测试空查询处理"""
    from backend.retrieval.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()

    results = kb.search("", top_k=5)
    assert isinstance(results, list)


@pytest.mark.unit
def test_knowledge_base_search_special_chars():
    """测试特殊字符查询"""
    from backend.retrieval.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()

    results = kb.search("请假!@#$%", top_k=5)
    assert isinstance(results, list)


@pytest.mark.unit
def test_knowledge_base_chunk_format():
    """测试知识块格式"""
    from backend.retrieval.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()

    if kb.chunks:
        chunk = kb.chunks[0]
        assert "id" in chunk or hasattr(chunk, "id")
        assert "text" in chunk or hasattr(chunk, "text")
