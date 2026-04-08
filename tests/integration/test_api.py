# -*- coding: utf-8 -*-
import importlib
from typing import Any

import pytest
from fastapi.testclient import TestClient


class FakeSessionManager:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.counter = 0

    async def create_session(self, user_id: str) -> str:
        self.counter += 1
        session_id = f'session-{self.counter}'
        now = '2026-03-06T00:00:00'
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': now,
            'updated_at': now,
            'messages': [],
        }
        return session_id

    async def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    async def get_session_history(self, session_id: str):
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [
            {'role': item['role'], 'content': item['content']}
            for item in session.get('messages', [])
        ]

    async def update_session(self, session_id: str, user_message: str, assistant_message: str):
        session = self.sessions.setdefault(
            session_id,
            {
                'session_id': session_id,
                'user_id': 'guest:test',
                'created_at': '2026-03-06T00:00:00',
                'updated_at': '2026-03-06T00:00:00',
                'messages': [],
            },
        )
        session['updated_at'] = '2026-03-06T00:00:00'
        session['messages'].extend(
            [
                {'role': 'user', 'content': user_message, 'timestamp': '2026-03-06T00:00:00'},
                {'role': 'assistant', 'content': assistant_message, 'timestamp': '2026-03-06T00:00:00'},
            ]
        )

    async def delete_session(self, session_id: str) -> bool:
        return self.sessions.pop(session_id, None) is not None

    async def list_user_sessions(self, user_id: str):
        return [
            {
                'session_id': session['session_id'],
                'created_at': session['created_at'],
                'updated_at': session['updated_at'],
                'message_count': len(session.get('messages', [])),
            }
            for session in self.sessions.values()
            if session.get('user_id') == user_id
        ]


@pytest.fixture
def api_module(monkeypatch):
    main_module = importlib.import_module('backend.main')
    fake_session_manager = FakeSessionManager()

    async def fake_run_chat_query(chat_request, history):
        return {
            'response': f'演示回答：{chat_request.message}',
            'sources': [
                {
                    'id': 'chunk-1',
                    'text': '人工智能专业培养方案强调数学基础、编程能力与实践教学。',
                    'char_count': 29,
                    'section': '培养目标',
                    'similarity': 0.92,
                    'rerank_score': 0.87,
                }
            ],
            'metadata': {
                'retrieval_method': 'demo-fixture',
                'rerank_method': 'demo-fixture',
                'used_llm': False,
                'fallback': 'template',
            },
            'thinking_process': None,
        }

    async def fake_check_connection():
        return {'status': 'healthy', 'timestamp': '2026-03-06T00:00:00'}

    monkeypatch.setattr(main_module, 'session_manager', fake_session_manager)
    monkeypatch.setattr(main_module, '_run_chat_query', fake_run_chat_query)
    monkeypatch.setattr(main_module, 'check_connection', fake_check_connection)
    monkeypatch.setattr(main_module.knowledge_base, 'is_loaded', lambda: True)
    monkeypatch.setattr(main_module.knowledge_base, 'load', lambda: True)
    monkeypatch.setattr(main_module.knowledge_base, 'search', lambda query, top_k=5: [
        {
            'id': 'chunk-1',
            'text': f'关于“{query}”的检索结果',
            'char_count': len(query) + 8,
            'section': '课程体系',
            'similarity': 0.81,
            'rerank_score': 0.73,
        }
    ])
    monkeypatch.setattr(main_module.knowledge_base, 'get_statistics', lambda: {'total_chunks': 1})
    return main_module


@pytest.fixture
def client(api_module):
    return TestClient(api_module.app)


@pytest.mark.integration
def test_health_endpoint(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json()['status'] in {'healthy', 'degraded'}


@pytest.mark.integration
def test_readiness_endpoint_reports_dependencies(client):
    response = client.get('/health/ready')

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ready'
    assert body['database']['status'] == 'healthy'
    assert body['session_store']['backend'] == 'FakeSessionManager'
    assert body['knowledge_base']['loaded'] is True


@pytest.mark.integration
def test_stats_endpoint(client):
    response = client.get('/stats')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'knowledge_base' in data
    assert data['features']['session_backend'] == 'FakeSessionManager'


@pytest.mark.integration
def test_public_demo_chat_allows_anonymous_access(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, 'PUBLIC_DEMO_MODE', True)

    response = client.post('/api/chat', json={'message': '培养目标是什么？', 'enable_thinking': False})

    assert response.status_code == 200
    data = response.json()
    assert data['response'].startswith('演示回答：')
    assert data['session_id'].startswith('session-')
    assert data['sources']
    assert data['sources'][0]['section'] == '培养目标'
    assert data['sources'][0]['similarity'] == pytest.approx(0.92)
    assert data['sources'][0]['rerank_score'] == pytest.approx(0.87)
    assert data['metadata']['environment']


@pytest.mark.integration
def test_public_demo_chat_returns_401_when_disabled(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, 'PUBLIC_DEMO_MODE', False)

    response = client.post('/api/chat', json={'message': '培养目标是什么？'})

    assert response.status_code == 401


@pytest.mark.integration
def test_public_demo_search_allows_anonymous_access(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, 'PUBLIC_DEMO_MODE', True)

    response = client.post('/api/search', json={'query': '核心课程', 'top_k': 1})

    assert response.status_code == 200
    data = response.json()
    assert data['total_results'] == 1
    assert data['results'][0]['section'] == '课程体系'


@pytest.mark.integration
def test_session_creation_and_resume_for_guest(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, 'PUBLIC_DEMO_MODE', True)

    created = client.post('/api/sessions', json={})
    assert created.status_code == 200
    created_body = created.json()

    resumed = client.post('/api/sessions', json={'session_id': created_body['session_id']})
    assert resumed.status_code == 200
    resumed_body = resumed.json()

    assert resumed_body['session_id'] == created_body['session_id']
    assert resumed_body['message_count'] == 0


@pytest.mark.integration
def test_chat_returns_offline_fallback_metadata(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, 'PUBLIC_DEMO_MODE', True)

    response = client.post('/api/chat', json={'message': '毕业要求有哪些？', 'enable_thinking': False})

    assert response.status_code == 200
    body = response.json()
    assert body['metadata']['used_llm'] is False
    assert body['metadata']['fallback'] == 'template'
