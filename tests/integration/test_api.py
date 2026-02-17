# -*- coding: utf-8 -*-
"""
API 端点测试
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from backend.main import app
    return TestClient(app)


@pytest.mark.integration
def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.integration
def test_root_endpoint(client):
    """测试根端点"""
    response = client.get("/")
    assert response.status_code in [200, 404]


@pytest.mark.integration
def test_docs_endpoint(client):
    """测试文档端点"""
    response = client.get("/docs")
    assert response.status_code == 200


@pytest.mark.integration
def test_openapi_endpoint(client):
    """测试 OpenAPI 端点"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data


@pytest.mark.integration
def test_query_without_auth(client):
    """测试未认证查询"""
    response = client.post("/api/query", json={"query": "测试"})
    # 可能返回 401 或 422，取决于认证配置
    assert response.status_code in [200, 401, 422]
