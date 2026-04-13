# -*- coding: utf-8 -*-
import base64
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from llm_service import SparkWebSocketLLMService, get_default_llm_service


def test_spark_websocket_service_builds_authorized_url():
    service = SparkWebSocketLLMService(
        app_id='app-id',
        api_key='api-key',
        api_secret='api-secret',
        ws_url='wss://spark-api.xf-yun.com/v1.1/chat',
        model='sparklite',
    )

    authorized_url = service._build_authorized_ws_url()
    parsed = urlparse(authorized_url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == 'wss'
    assert parsed.netloc == 'spark-api.xf-yun.com'
    assert parsed.path == '/v1.1/chat'
    assert 'authorization' in params
    assert 'date' in params
    assert params.get('host') == ['spark-api.xf-yun.com']

    authorization_text = base64.b64decode(params['authorization'][0]).decode('utf-8')
    assert 'api_key="api-key"' in authorization_text
    assert 'algorithm="hmac-sha256"' in authorization_text


def test_spark_websocket_payload_uses_lite_domain():
    service = SparkWebSocketLLMService(
        app_id='app-id',
        api_key='api-key',
        api_secret='api-secret',
        model='sparklite',
    )

    payload = service._build_request_payload(
        [
            {'role': 'system', 'content': 'system prompt'},
            {'role': 'user', 'content': 'hello'},
        ]
    )

    assert payload['header']['app_id'] == 'app-id'
    assert payload['parameter']['chat']['domain'] == 'lite'
    assert payload['payload']['message']['text'][1]['content'] == 'hello'


def test_get_default_llm_service_returns_spark_service():
    service = get_default_llm_service('spark')
    assert isinstance(service, SparkWebSocketLLMService)
