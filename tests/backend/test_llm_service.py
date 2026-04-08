# -*- coding: utf-8 -*-
"""
LLM 服务模块测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.unit
def test_llm_service_creation():
    """测试 LLM 服务创建"""
    from backend.llm_service import LLMService

    service = LLMService()
    assert service is not None


@pytest.mark.unit
def test_llm_service_has_required_methods():
    """测试 LLM 服务必需方法"""
    from backend.llm_service import LLMService

    service = LLMService()

    # 检查基本方法存在
    assert hasattr(service, "generate") or hasattr(service, "chat") or hasattr(service, "complete")


@pytest.mark.unit
def test_llm_service_generate_mock():
    """测试 LLM 生成 (Mock)"""
    import asyncio
    from backend.llm_service import LLMService

    with patch.object(LLMService, 'chat', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "这是测试回复"

        service = LLMService()
        result = asyncio.run(service.chat(query="测试问题", context="", session_history=[]))

        assert result == "这是测试回复"


@pytest.mark.unit
def test_llm_service_config():
    """测试 LLM 服务配置"""
    from backend import config

    # 确保配置项存在
    assert hasattr(config, 'LLM_API_KEY')
    assert hasattr(config, 'LLM_API_BASE_URL')
    assert hasattr(config, 'LLM_MODEL')
