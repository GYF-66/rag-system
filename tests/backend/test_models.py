# -*- coding: utf-8 -*-
"""
数据模型测试
"""
import pytest
from datetime import datetime
from pydantic import ValidationError


@pytest.mark.unit
def test_chat_request_model():
    """测试 ChatRequest 模型"""
    from backend.models import ChatRequest

    # 有效请求
    request = ChatRequest(
        message="测试消息",
        session_id="test-session",
        user_id="test-user",
        use_rag=True,
        enable_thinking=True
    )

    assert request.message == "测试消息"
    assert request.session_id == "test-session"
    assert request.user_id == "test-user"
    assert request.use_rag is True
    assert request.enable_thinking is True

    # 最小请求
    minimal_request = ChatRequest(message="测试")
    assert minimal_request.message == "测试"


@pytest.mark.unit
def test_chat_request_validation():
    """测试 ChatRequest 验证"""
    from backend.models import ChatRequest

    # 测试缺少必填字段
    with pytest.raises(ValidationError):
        ChatRequest()


@pytest.mark.unit
def test_knowledge_chunk_model():
    """测试 KnowledgeChunk 模型"""
    from backend.models import KnowledgeChunk

    chunk = KnowledgeChunk(
        id="0",
        text="测试内容",
        char_count=4,
        similarity=0.85,
        rerank_score=0.90,
        section="测试章节"
    )

    assert chunk.id == "0"
    assert chunk.text == "测试内容"
    assert chunk.char_count == 4
    assert chunk.similarity == 0.85
    assert chunk.rerank_score == 0.90
    assert chunk.section == "测试章节"


@pytest.mark.unit
def test_chat_response_model():
    """测试 ChatResponse 模型"""
    from backend.models import ChatResponse, KnowledgeChunk

    response = ChatResponse(
        response="这是回复",
        session_id="test-session",
        sources=[
            KnowledgeChunk(id="0", text="内容", char_count=2)
        ],
        is_cross_query=False
    )

    assert response.response == "这是回复"
    assert response.session_id == "test-session"
    assert len(response.sources) == 1
    assert response.is_cross_query is False
    assert isinstance(response.timestamp, datetime)


@pytest.mark.unit
def test_thinking_process_model():
    """测试 ThinkingProcess 模型"""
    from backend.models import ThinkingProcess, ThinkingStep

    step = ThinkingStep(
        step_id=1,
        step_name="测试步骤",
        description="测试描述",
        reasoning="测试推理",
        duration_ms=100.0
    )

    process = ThinkingProcess(
        query_analysis=step,
        retrieval=step,
        reranking=step,
        reasoning=step,
        summary="测试总结",
        total_duration_ms=400.0
    )

    assert process.query_analysis.step_id == 1
    assert process.summary == "测试总结"
    assert process.total_duration_ms == 400.0


@pytest.mark.unit
def test_user_info_model():
    """测试 UserInfo 模型"""
    from backend.models import UserInfo

    user = UserInfo(
        user_id="test-123",
        username="testuser",
        nickname="测试用户",
        avatar="https://example.com/avatar.png"
    )

    assert user.user_id == "test-123"
    assert user.username == "testuser"
    assert user.nickname == "测试用户"
    assert user.avatar == "https://example.com/avatar.png"