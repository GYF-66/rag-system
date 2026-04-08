# -*- coding: utf-8 -*-
"""
测试配置和共享 fixtures
"""
import sys
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

# 将 backend/ 加入 sys.path，使裸导入（from knowledge_base import ...）在测试中可用
_backend_dir = str(Path(__file__).parent.parent / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


def pytest_configure(config):
    """注册自定义 markers"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "rag: RAG相关测试")
    config.addinivalue_line("markers", "api: API相关测试")
    config.addinivalue_line("markers", "database: 数据库相关测试")


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """测试数据目录"""
    test_data = project_root / "tests" / "data"
    test_data.mkdir(exist_ok=True)
    return test_data


@pytest.fixture
def sample_knowledge_chunk():
    """示例知识块"""
    return {
        "id": "0",
        "text": "根据人工智能专业培养方案规定，学生需完成规定的课程学分和实践环节。",
        "char_count": 35,
        "section": "学生管理篇",
        "similarity": 0.85
    }


@pytest.fixture
def sample_chat_request():
    """示例聊天请求"""
    return {
        "message": "请假流程是什么？",
        "session_id": None,
        "user_id": "test_user",
        "use_rag": True,
        "enable_thinking": True
    }


@pytest.fixture
def sample_session_history():
    """示例会话历史"""
    return [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！我是安信工AI小助手，有什么可以帮您的吗？"}
    ]


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    return {
        "response": "根据培养方案，人工智能专业课程体系包括：\n1. 专业基础课程（数学、程序设计）\n2. 专业核心课程（机器学习、深度学习）\n3. 实践环节（毕业设计、实习）",
        "sources": [],
        "used_llm": True
    }


@pytest.fixture
def mock_config():
    """模拟配置"""
    return {
        "AGENT_NAME": "安信工AI小助手",
        "API_HOST": "0.0.0.0",
        "API_PORT": 8001,
        "TOP_K_RESULTS": 3,
        "MIN_SIMILARITY": 0.4,
        "USE_CHROMADB": False
    }


@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_knowledge_base(test_data_dir):
    """临时知识库文件"""
    kb_file = test_data_dir / "temp_kb.json"
    kb_data = {
        "metadata": {
            "version": "test",
            "total_chunks": 1
        },
        "chunks": [
            {
                "id": "0",
                "text": "测试知识内容",
                "char_count": 6
            }
        ]
    }
    import json
    with open(kb_file, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, ensure_ascii=False)
    yield kb_file
    # 清理
    if kb_file.exists():
        kb_file.unlink()
