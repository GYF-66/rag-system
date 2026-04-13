# -*- coding: utf-8 -*-
"""
LLM service adapters.

- Spark uses the official WebSocket interface.
- Generic API provider uses an OpenAI-compatible `/chat/completions` interface.
- Ollama uses `/api/chat` with a fallback to `/api/generate`.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import quote, urlparse

import httpx
from websockets.asyncio.client import connect as ws_connect

logger = logging.getLogger(__name__)

try:
    from config import (
        AGENT_NAME,
        LLM_API_BASE_URL,
        LLM_API_KEY,
        LLM_MAX_TOKENS,
        LLM_MODEL,
        LLM_PROVIDER,
        LLM_TEMPERATURE,
        LLM_TIMEOUT,
        OLLAMA_BASE_URL,
        OLLAMA_MODEL,
        OLLAMA_NUM_CTX,
        SPARK_API_BASE_URL,
        SPARK_API_KEY,
        SPARK_API_PASSWORD,
        SPARK_API_SECRET,
        SPARK_APP_ID,
        SPARK_MODEL,
        SPARK_WS_URL,
    )
except ImportError:
    AGENT_NAME = "AI Assistant"
    LLM_API_BASE_URL = ""
    LLM_API_KEY = ""
    LLM_MAX_TOKENS = 2048
    LLM_MODEL = ""
    LLM_PROVIDER = "api"
    LLM_TEMPERATURE = 0.7
    LLM_TIMEOUT = 60.0
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
    OLLAMA_NUM_CTX = 4096
    SPARK_API_BASE_URL = "https://spark-api-open.xf-yun.com/v1"
    SPARK_API_KEY = ""
    SPARK_API_PASSWORD = ""
    SPARK_API_SECRET = ""
    SPARK_APP_ID = ""
    SPARK_MODEL = "sparklite"
    SPARK_WS_URL = "wss://spark-api.xf-yun.com/v1.1/chat"

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0


def build_default_system_prompt() -> str:
    return (
        f"你是{AGENT_NAME}，负责回答人工智能专业培养方案、课程体系、教学安排和实践环节相关问题。\n"
        "请直接回答用户问题，优先基于检索到的参考资料给出准确、简洁、结构清晰的中文答案。\n"
        "如果资料不足，请明确说明不确定部分，不要编造。"
    )


def normalize_provider(provider: Optional[str]) -> str:
    value = (provider or "").strip().lower()
    if value in {"spark", "sparklite", "spark-lite", "xfyun", "xunfei"}:
        return "spark"
    if value == "ollama":
        return "ollama"
    return "api"


def normalize_model(provider: Optional[str], model: Optional[str]) -> str:
    normalized_provider = normalize_provider(provider)
    value = (model or "").strip()
    if not value:
        return "lite" if normalized_provider == "spark" else ""

    lowered = value.lower()
    if normalized_provider == "spark":
        aliases = {
            "sparklite": "lite",
            "spark-lite": "lite",
            "spark lite": "lite",
            "lite": "lite",
        }
        return aliases.get(lowered, value)
    return value


def resolve_api_key(provider: Optional[str], api_key: Optional[str] = None) -> str:
    if api_key:
        return api_key
    if normalize_provider(provider) == "spark":
        return SPARK_API_PASSWORD or LLM_API_KEY
    return LLM_API_KEY


def resolve_base_url(provider: Optional[str], base_url: Optional[str] = None) -> str:
    candidate = base_url
    if not candidate:
        candidate = SPARK_API_BASE_URL if normalize_provider(provider) == "spark" else LLM_API_BASE_URL
    return (candidate or "").rstrip("/")


def extract_message_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()


def extract_stream_delta(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    if delta.get("content"):
        return str(delta["content"])
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")


class LLMService:
    """OpenAI-compatible chat service."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        self.provider = normalize_provider(provider or LLM_PROVIDER)
        self.api_key = resolve_api_key(self.provider, api_key)
        self.base_url = resolve_base_url(self.provider, base_url)
        self.model = normalize_model(self.provider, model or LLM_MODEL or SPARK_MODEL)
        self.max_tokens = max_tokens or LLM_MAX_TOKENS
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.timeout = timeout or LLM_TIMEOUT
        self.system_prompt = build_default_system_prompt()

    def is_available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    async def _request_with_retry(self, client: httpx.AsyncClient, method: str, url: str, **kwargs):
        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning("LLM request failed with status %s, retrying in %ss", response.status_code, delay)
                    await asyncio.sleep(delay)
                    continue
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = exc
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning("LLM request error %s, retrying in %ss", exc, delay)
                await asyncio.sleep(delay)
            except Exception as exc:
                last_error = exc
                logger.error("Unexpected LLM request error: %s", exc)
                break

        raise last_error or RuntimeError("LLM request failed after retries")

    def _build_messages(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt or self.system_prompt}]

        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        if context:
            user_message = (
                f"## 用户问题\n{query}\n\n"
                f"## 参考资料\n{context}\n\n"
                "请基于参考资料回答用户问题，只使用与问题直接相关的内容。"
            )
        else:
            user_message = query

        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        if not self.is_available():
            return ""

        messages = self._build_messages(query, context, history, system_prompt)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._request_with_retry(
                    client,
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stream": False,
                    },
                )
                if response.status_code != 200:
                    logger.error("LLM API failed: %s - %s", response.status_code, response.text)
                    return ""
                return extract_message_content(response.json())
        except Exception as exc:
            logger.error("LLM API final failure: %s", exc)
            return ""

    async def chat_stream(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield ""
            return

        messages = self._build_messages(query, context, history, system_prompt)

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "max_tokens": self.max_tokens,
                            "temperature": self.temperature,
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code == 429 or response.status_code >= 500:
                            delay = RETRY_DELAY_BASE * (2 ** attempt)
                            logger.warning(
                                "LLM streaming failed with status %s, retrying in %ss",
                                response.status_code,
                                delay,
                            )
                            await asyncio.sleep(delay)
                            continue
                        if response.status_code != 200:
                            logger.error("LLM streaming failed: %s - %s", response.status_code, response.text)
                            yield ""
                            return

                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            content = extract_stream_delta(chunk)
                            if content:
                                yield content
                        return
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning("LLM streaming error %s, retrying in %ss", exc, delay)
                await asyncio.sleep(delay)
            except Exception as exc:
                logger.error("LLM streaming unexpected failure: %s", exc)
                yield ""
                return

        yield ""


class SparkWebSocketLLMService:
    """Official Spark WebSocket service."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        ws_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        self.app_id = app_id or SPARK_APP_ID
        self.api_key = api_key or SPARK_API_KEY
        self.api_secret = api_secret or SPARK_API_SECRET
        self.ws_url = (ws_url or SPARK_WS_URL).strip()
        self.model = normalize_model("spark", model or LLM_MODEL or SPARK_MODEL)
        self.max_tokens = max_tokens or LLM_MAX_TOKENS
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.timeout = timeout or LLM_TIMEOUT
        self.system_prompt = build_default_system_prompt()

    def is_available(self) -> bool:
        return bool(self.app_id and self.api_key and self.api_secret and self.ws_url and self.model)

    def _connect_timeout(self) -> float:
        return min(float(self.timeout), 8.0)

    def _response_timeout(self) -> float:
        return min(float(self.timeout), 12.0)

    def _build_messages(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt or self.system_prompt}]

        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        if context:
            user_message = (
                f"## 用户问题\n{query}\n\n"
                f"## 参考资料\n{context}\n\n"
                "请基于参考资料回答用户问题，只使用与问题直接相关的内容。"
            )
        else:
            user_message = query

        messages.append({"role": "user", "content": user_message})
        return messages

    def _build_authorized_ws_url(self) -> str:
        parsed = urlparse(self.ws_url)
        host = parsed.netloc
        path = parsed.path
        date = format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        return (
            f"{self.ws_url}?authorization={quote(authorization)}"
            f"&date={quote(date)}&host={quote(host)}"
        )

    def _build_request_payload(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "header": {
                "app_id": self.app_id,
                "uid": "rag-system",
            },
            "parameter": {
                "chat": {
                    "domain": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
            },
            "payload": {
                "message": {
                    "text": messages,
                }
            },
        }

    @staticmethod
    def _extract_spark_content(payload: Dict[str, Any]) -> tuple[str, bool]:
        header = payload.get("header") or {}
        if header.get("code", 0) != 0:
            raise RuntimeError(header.get("message") or f"Spark websocket error {header.get('code')}")

        choices = ((payload.get("payload") or {}).get("choices") or {})
        texts = choices.get("text") or []
        content = "".join(str(item.get("content") or "") for item in texts)
        done = header.get("status") == 2 or choices.get("status") == 2
        return content, done

    async def chat(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        chunks: List[str] = []
        async for chunk in self.chat_stream(query, context, history, system_prompt):
            if chunk:
                chunks.append(chunk)
        return "".join(chunks).strip()

    async def chat_stream(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield ""
            return

        messages = self._build_messages(query, context, history, system_prompt)
        payload = self._build_request_payload(messages)

        for attempt in range(MAX_RETRIES):
            try:
                async with ws_connect(
                    self._build_authorized_ws_url(),
                    open_timeout=self._connect_timeout(),
                    close_timeout=self._connect_timeout(),
                    ping_interval=20,
                ) as websocket:
                    await websocket.send(json.dumps(payload, ensure_ascii=False))
                    while True:
                        raw = await asyncio.wait_for(websocket.recv(), timeout=self._response_timeout())
                        data = json.loads(raw)
                        content, done = self._extract_spark_content(data)
                        if content:
                            yield content
                        if done:
                            return
            except Exception as exc:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning("Spark websocket error %s, retrying in %ss", exc, delay)
                if attempt == MAX_RETRIES - 1:
                    yield ""
                    return
                await asyncio.sleep(delay)


class OllamaLLMService:
    """Local Ollama chat service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        num_ctx: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_MODEL
        self.num_ctx = num_ctx or OLLAMA_NUM_CTX
        self.max_tokens = max_tokens or LLM_MAX_TOKENS
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.timeout = timeout or LLM_TIMEOUT
        self.system_prompt = build_default_system_prompt()

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def _build_messages(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt or self.system_prompt}]

        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        if context:
            user_content = (
                f"## 用户问题\n{query}\n\n"
                f"## 参考资料\n{context}\n\n"
                "请基于参考资料回答用户问题，只使用与问题直接相关的内容。"
            )
        else:
            user_content = query

        messages.append({"role": "user", "content": user_content})
        return messages

    async def chat(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        messages = self._build_messages(query, context, history, system_prompt)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                            "num_ctx": self.num_ctx,
                        },
                        "stream": False,
                    },
                )
                if response.status_code == 200:
                    payload = response.json()
                    return str(payload.get("message", {}).get("content", "")).strip()
                logger.warning("Ollama /api/chat failed: %s", response.status_code)
        except Exception as exc:
            logger.warning("Ollama /api/chat error: %s", exc)

        try:
            prompt = self._messages_to_prompt(messages)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                            "num_ctx": self.num_ctx,
                        },
                        "stream": False,
                    },
                )
                if response.status_code == 200:
                    payload = response.json()
                    return str(payload.get("response", "")).strip()
        except Exception as exc:
            logger.error("Ollama /api/generate failed: %s", exc)

        return ""

    async def chat_stream(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(query, context, history, system_prompt)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                            "num_ctx": self.num_ctx,
                        },
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        logger.error("Ollama streaming failed: %s", response.status_code)
                        yield ""
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = str(chunk.get("message", {}).get("content", "") or "")
                        if content:
                            yield content
                    return
        except Exception as exc:
            logger.error("Ollama streaming error: %s", exc)
            yield ""

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"<|{role}|>\n{content}")
        parts.append("<|assistant|>")
        return "\n".join(parts)


spark_llm_service = SparkWebSocketLLMService()
api_llm_service = LLMService()
ollama_llm_service = OllamaLLMService()


def get_default_llm_service(provider: Optional[str] = None):
    normalized_provider = normalize_provider(provider or LLM_PROVIDER)
    if normalized_provider == "ollama":
        return ollama_llm_service
    if normalized_provider == "spark":
        return spark_llm_service
    return api_llm_service


llm_service = get_default_llm_service()
