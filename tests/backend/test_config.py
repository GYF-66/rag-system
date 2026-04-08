# -*- coding: utf-8 -*-
import pytest
from pathlib import Path


@pytest.mark.unit
def test_config_imports():
    from backend.config import (
        AGENT_NAME,
        API_HOST,
        API_PORT,
        TOP_K_RESULTS,
        MIN_SIMILARITY,
        USE_CHROMADB,
    )

    assert isinstance(AGENT_NAME, str)
    assert AGENT_NAME.strip()
    assert API_HOST == '0.0.0.0'
    assert API_PORT == 8001
    assert isinstance(TOP_K_RESULTS, int)
    assert isinstance(MIN_SIMILARITY, float)
    assert isinstance(USE_CHROMADB, bool)


@pytest.mark.unit
def test_config_paths():
    from backend.config import BASE_DIR, KNOWLEDGE_BASE_PATH

    assert BASE_DIR.exists()
    assert isinstance(BASE_DIR, Path)
    assert isinstance(KNOWLEDGE_BASE_PATH, Path)


@pytest.mark.unit
def test_config_values():
    from backend.config import (
        TOP_K_RESULTS,
        MIN_SIMILARITY,
        MAX_CONTEXT_LENGTH,
        MAX_HISTORY_TURNS,
    )

    assert TOP_K_RESULTS > 0
    assert 0 <= MIN_SIMILARITY <= 1
    assert MAX_CONTEXT_LENGTH > 0
    assert MAX_HISTORY_TURNS > 0


@pytest.mark.unit
def test_config_mongodb():
    from backend.config import (
        MONGODB_URL,
        MONGODB_DATABASE,
        MONGODB_MAX_POOL_SIZE,
        MONGODB_MIN_POOL_SIZE,
    )

    assert isinstance(MONGODB_URL, str)
    assert isinstance(MONGODB_DATABASE, str)
    assert MONGODB_MAX_POOL_SIZE > 0
    assert MONGODB_MIN_POOL_SIZE > 0
    assert MONGODB_MIN_POOL_SIZE <= MONGODB_MAX_POOL_SIZE


@pytest.mark.unit
def test_config_jwt():
    from backend.config import (
        SECRET_KEY,
        ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES,
        REFRESH_TOKEN_EXPIRE_DAYS,
    )

    assert isinstance(SECRET_KEY, str)
    assert len(SECRET_KEY) > 0
    assert isinstance(ALGORITHM, str)
    assert ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert REFRESH_TOKEN_EXPIRE_DAYS > 0
