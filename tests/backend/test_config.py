# -*- coding: utf-8 -*-
"""
配置模块测试
"""
import pytest
from pathlib import Path


@pytest.mark.unit
def test_config_imports():
    """测试配置模块可以正常导入"""
    try:
        from backend.config import (
            AGENT_NAME,
            API_HOST,
            API_PORT,
            TOP_K_RESULTS,
            MIN_SIMILARITY,
            USE_CHROMADB
        )
        assert AGENT_NAME == "安信工AI小助手"
        assert API_HOST == "0.0.0.0"
        assert API_PORT == 8001
        assert isinstance(TOP_K_RESULTS, int)
        assert isinstance(MIN_SIMILARITY, float)
        assert isinstance(USE_CHROMADB, bool)
    except ImportError as e:
        pytest.fail(f"配置模块导入失败: {e}")


@pytest.mark.unit
def test_config_paths():
    """测试配置路径"""
    from backend.config import BASE_DIR, KNOWLEDGE_BASE_PATH

    assert BASE_DIR.exists()
    assert isinstance(BASE_DIR, Path)
    assert isinstance(KNOWLEDGE_BASE_PATH, Path)


@pytest.mark.unit
def test_config_values():
    """测试配置值的有效性"""
    from backend.config import (
        TOP_K_RESULTS,
        MIN_SIMILARITY,
        MAX_CONTEXT_LENGTH,
        MAX_HISTORY_TURNS
    )

    # 检查数值范围
    assert TOP_K_RESULTS > 0
    assert 0 <= MIN_SIMILARITY <= 1
    assert MAX_CONTEXT_LENGTH > 0
    assert MAX_HISTORY_TURNS > 0


@pytest.mark.unit
def test_config_mongodb():
    """测试 MongoDB 配置"""
    from backend.config import (
        MONGODB_URL,
        MONGODB_DATABASE,
        MONGODB_MAX_POOL_SIZE,
        MONGODB_MIN_POOL_SIZE
    )

    assert isinstance(MONGODB_URL, str)
    assert isinstance(MONGODB_DATABASE, str)
    assert MONGODB_MAX_POOL_SIZE > 0
    assert MONGODB_MIN_POOL_SIZE > 0
    assert MONGODB_MIN_POOL_SIZE <= MONGODB_MAX_POOL_SIZE


@pytest.mark.unit
def test_config_jwt():
    """测试 JWT 配置"""
    from backend.config import (
        SECRET_KEY,
        ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES,
        REFRESH_TOKEN_EXPIRE_DAYS
    )

    assert isinstance(SECRET_KEY, str)
    assert len(SECRET_KEY) > 0
    assert isinstance(ALGORITHM, str)
    assert ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert REFRESH_TOKEN_EXPIRE_DAYS > 0