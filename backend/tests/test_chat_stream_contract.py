# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import main as app_main
from models import ReflectionResult, ThinkingProcess, ThinkingStep


class StubSessionManager:
    def __init__(self):
        self.sessions: dict[str, dict] = {}

    async def create_session(self, user_id=None):
        session_id = 'session-new'
        self.sessions[session_id] = {'session_id': session_id, 'user_id': user_id, 'messages': []}
        return session_id

    async def get_session(self, session_id):
        return self.sessions.get(session_id)

    async def get_session_history(self, session_id):
        session = self.sessions.get(session_id)
        return session.get('messages', []) if session else []

    async def update_session(self, session_id, user_message, assistant_message):
        self.sessions.setdefault(session_id, {'session_id': session_id, 'messages': []})
        self.sessions[session_id]['messages'].extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': assistant_message},
        ])
        return True

    async def ping(self):
        return None


class AvailableStreamingLLM:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def is_available(self):
        return True

    async def chat_stream(self, *args, **kwargs):
        for chunk in self.chunks:
            yield chunk


class UnavailableLLM:
    def is_available(self):
        return False


class StubAgentV2:
    def __init__(self):
        self.use_chromadb = False
        self._graph_retriever = None
        self._hybrid_retriever = None
        self._response_gen = type('FallbackGen', (), {'generate': lambda self, *_args, **_kwargs: 'fallback answer'})()

    def _analyze_query(self, query):
        return {
            'normalized_query': query,
            'keywords': ['人工智能'],
            'variants': ['人工智能专业'],
            'intents': ['curriculum'],
            'query_type': 'general',
            'complexity': 1,
            'adaptive_top_k': 3,
        }

    async def _retrieve_sources(self, query, use_rag, query_analysis):
        return (
            [
                {
                    'id': 'source-1',
                    'text': '人工智能专业核心课程包括机器学习与深度学习。',
                    'char_count': 24,
                    'similarity': 0.92,
                    'section': '培养方案',
                    'metadata': {'title': '培养方案'},
                }
            ],
            {
                'method': 'hybrid',
                'route': 'standard',
                'hyde_used': False,
            },
        )

    def _prepare_sources(self, query, sources, query_analysis):
        return sources

    def _build_context(self, sources):
        return '\n'.join(item['text'] for item in sources)

    def _build_course_graph_supplement(self, query, query_analysis):
        return '', None

    def _build_cot_system_prompt(self, query_analysis, sources):
        return 'cot prompt'

    def _parse_cot_response(self, full_response):
        return '最终答案', '推理过程'

    def _build_response_metadata(
        self,
        *,
        query,
        query_analysis,
        retrieval_info,
        sources,
        used_llm,
        total_duration_ms=None,
        crag_info=None,
        cot_used=False,
        reflection_result=None,
        self_rag_pending=False,
    ):
        return {
            'request_id': '',
            'retrieval_method': retrieval_info.get('method', 'hybrid'),
            'retrieval_variant_count': 1,
            'retrieval_variants': query_analysis.get('variants', []),
            'query_rewrite': {
                'original_query': query,
                'normalized_query': query_analysis.get('normalized_query', query),
                'keywords': query_analysis.get('keywords', []),
                'intents': query_analysis.get('intents', []),
                'variants': query_analysis.get('variants', []),
            },
            'adaptive_route': retrieval_info.get('route', 'standard'),
            'used_llm': used_llm,
            'source_count': len(sources),
            'total_duration_ms': total_duration_ms,
            'hyde_used': retrieval_info.get('hyde_used', False),
            'graph_rag_used': False,
            'cot_used': cot_used,
            'crag_evaluation': {
                'mode': 'online_heuristic',
                'quality_score': 0.57,
                'action': 'refine',
                'details': {
                    'similarity': 0.72,
                    'keyword_coverage': 0.62,
                    'diversity': 0.41,
                    'completeness': 0.45,
                },
                'thresholds': {'low': 0.3, 'high': 0.6},
                'correction_hints': ['expand_top_k'],
                'correction': {
                    'corrected': True,
                    'actions_taken': ['keyword_supplement'],
                },
            },
            'self_rag_reflection': reflection_result.status if reflection_result else None,
            'self_rag': {
                'mode': 'llm_reflection',
                'status': reflection_result.status if reflection_result else ('waiting' if self_rag_pending else 'skipped'),
                'confidence': reflection_result.confidence if reflection_result else None,
                'issues_count': len(reflection_result.issues) if reflection_result else 0,
                'revision_applied': reflection_result.revision_applied if reflection_result else False,
                'evidence_count': min(len(sources), 5),
            },
        }

    async def _self_rag_reflect(self, query, response, sources, llm):
        reflection = ReflectionResult(
            status='supported',
            confidence=0.93,
            issues=[],
            revision_applied=False,
        )
        return reflection, None

    def _build_thinking_process(self, *args, **kwargs):
        return ThinkingProcess(
            query_analysis=ThinkingStep(step_id=1, step_name='问题理解', description='分析问题', reasoning='完成'),
            retrieval=ThinkingStep(step_id=2, step_name='证据检索', description='召回证据', reasoning='完成'),
            reranking=ThinkingStep(step_id=3, step_name='上下文整理', description='整理上下文', reasoning='完成'),
            reasoning=ThinkingStep(step_id=4, step_name='回答生成', description='生成回答', reasoning='推理过程'),
            reflection=ThinkingStep(step_id=5, step_name='Self-RAG 校验', description='校验答案', reasoning='完成'),
            reflection_result=ReflectionResult(
                status='supported',
                confidence=0.93,
                issues=[],
                revision_applied=False,
            ),
            summary='一次完整的流式回答流程',
            total_duration_ms=123.0,
        )


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for chunk in body.strip().split('\n\n'):
        if not chunk.strip():
            continue
        event_name = 'message'
        payload = {}
        for line in chunk.splitlines():
            if line.startswith('event:'):
                event_name = line.split(':', 1)[1].strip()
            elif line.startswith('data:'):
                payload = json.loads(line.split(':', 1)[1].strip())
        events.append((event_name, payload))
    return events


@pytest.fixture
def client(monkeypatch):
    stub_session_manager = StubSessionManager()
    stub_agent = StubAgentV2()

    async def fake_check_connection():
        return {'status': 'healthy'}

    monkeypatch.setattr(app_main, 'session_manager', stub_session_manager)
    monkeypatch.setattr(app_main, 'agent_v2', stub_agent)
    monkeypatch.setattr(app_main, 'AGENT_V2_AVAILABLE', True)
    monkeypatch.setattr(app_main, 'check_connection', fake_check_connection)
    monkeypatch.setattr(app_main.knowledge_base, 'load', lambda: True)
    monkeypatch.setattr(app_main.knowledge_base, 'is_loaded', lambda: True)
    monkeypatch.setattr(app_main.knowledge_base, 'chunks', [{'id': 'chunk-1'}], raising=False)
    monkeypatch.setattr(app_main, 'USE_CHROMADB', False, raising=False)
    monkeypatch.setattr(app_main, 'hybrid_retriever', None, raising=False)
    app_main.app.dependency_overrides[app_main.get_optional_current_user] = lambda: None

    with TestClient(app_main.app) as test_client:
        yield test_client

    app_main.app.dependency_overrides.clear()


def test_chat_stream_emits_contract_events_with_structured_metadata(client, monkeypatch):
    monkeypatch.setattr('llm_service.get_default_llm_service', lambda: AvailableStreamingLLM(['<thinking>', '回答片段']))

    with client.stream(
        'POST',
        '/api/chat/stream',
        json={'message': '人工智能专业核心课程有哪些？', 'use_rag': True, 'enable_thinking': True},
    ) as response:
        body = ''.join(response.iter_text())

    assert response.status_code == 200
    assert response.headers['x-request-id']

    events = _parse_sse_events(body)
    event_names = [name for name, _payload in events]

    assert event_names[:2] == ['metadata', 'token']
    assert 'reflection' in event_names
    assert 'thinking' in event_names
    assert event_names[-1] == 'done'

    metadata_payload = events[0][1]
    assert metadata_payload['request_id'] == response.headers['x-request-id']
    assert metadata_payload['contract_version'] == 1
    assert metadata_payload['metadata']['request_id'] == response.headers['x-request-id']
    assert metadata_payload['metadata']['crag_evaluation']['mode'] == 'online_heuristic'
    assert metadata_payload['metadata']['crag_evaluation']['details']['similarity'] == 0.72
    assert metadata_payload['metadata']['crag_evaluation']['thresholds']['high'] == 0.6
    assert metadata_payload['metadata']['self_rag']['status'] == 'waiting'
    assert metadata_payload['metadata']['query_rewrite']['original_query'] == '人工智能专业核心课程有哪些？'

    reflection_payload = next(payload for name, payload in events if name == 'reflection')
    assert reflection_payload['status'] == 'supported'

    done_payload = next(payload for name, payload in events if name == 'done')
    assert done_payload['request_id'] == response.headers['x-request-id']
    assert done_payload['total_duration_ms'] >= 0


def test_chat_stream_falls_back_to_non_stream_llm_when_unavailable(client, monkeypatch):
    monkeypatch.setattr('llm_service.get_default_llm_service', lambda: UnavailableLLM())

    with client.stream(
        'POST',
        '/api/chat/stream',
        json={'message': '请说明实践环节安排', 'use_rag': True, 'enable_thinking': True},
    ) as response:
        body = ''.join(response.iter_text())

    events = _parse_sse_events(body)
    token_payload = next(payload for name, payload in events if name == 'token')
    done_payload = next(payload for name, payload in events if name == 'done')

    assert token_payload['content'] == 'fallback answer'
    assert done_payload['request_id'] == response.headers['x-request-id']


def test_chat_stream_emits_error_event_on_internal_failure(client, monkeypatch):
    async def broken_retrieve(*args, **kwargs):
        raise RuntimeError('retrieval failed')

    monkeypatch.setattr(app_main.agent_v2, '_retrieve_sources', broken_retrieve)
    monkeypatch.setattr('llm_service.get_default_llm_service', lambda: AvailableStreamingLLM(['ignored']))

    with client.stream(
        'POST',
        '/api/chat/stream',
        json={'message': '测试异常链路', 'use_rag': True, 'enable_thinking': True},
    ) as response:
        body = ''.join(response.iter_text())

    events = _parse_sse_events(body)
    assert events[-1][0] == 'error'
    assert events[-1][1]['message'] == 'retrieval failed'
    assert events[-1][1]['request_id'] == response.headers['x-request-id']


def test_ready_check_reports_llm_degraded_but_keeps_service_ready_when_not_required(client, monkeypatch):
    monkeypatch.setattr('llm_service.get_default_llm_service', lambda: UnavailableLLM())
    monkeypatch.setattr(app_main, 'LLM_REQUIRED', False, raising=False)

    response = client.get('/health/ready')

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ready'
    assert payload['checks']['llm']['status'] == 'degraded'


def test_ready_check_fails_when_required_llm_is_unavailable(client, monkeypatch):
    monkeypatch.setattr('llm_service.get_default_llm_service', lambda: UnavailableLLM())
    monkeypatch.setattr(app_main, 'LLM_REQUIRED', True, raising=False)

    response = client.get('/health/ready')

    assert response.status_code == 503
    payload = response.json()
    assert payload['status'] == 'not_ready'
    assert payload['checks']['llm']['status'] in {'required_unavailable', 'unhealthy'}
