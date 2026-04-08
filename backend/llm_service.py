# -*- coding: utf-8 -*-
"""
Ollama 本地 LLM GPU 推理服务
支持在本地 GPU 上运行量化版 LLM（如 Qwen2.5-7B-Q4）

RTX 5070 (8GB VRAM) 推荐模型：
  - qwen2.5:7b-instruct-q4_K_M  (~4.5GB VRAM)
  - deepseek-r1:7b-distill-qwen-q4_K_M (~4GB VRAM)
  - llama3.2:3b-instruct         (~2GB VRAM)

安装 ollama: https://ollama.com/download
启动示例: ollama run qwen2.5:7b-instruct-q4_K_M
"""
import asyncio
import json
import logging
from typing import List, Dict, Optional, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# API-based LLM Service（原有实现，保留）
# ─────────────────────────────────────────────────────────────────────────────
try:
    from config import (
        LLM_API_KEY, LLM_API_BASE_URL, LLM_MODEL,
        LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_TIMEOUT,
        AGENT_NAME, AGENT_ROLE, LLM_PROVIDER,
    )
except ImportError:
    LLM_API_KEY = LLM_API_BASE_URL = LLM_MODEL = ''
    LLM_MAX_TOKENS = 2048; LLM_TEMPERATURE = 0.7; LLM_TIMEOUT = 60.0
    AGENT_NAME = 'AI Assistant'; AGENT_ROLE = 'AI Knowledge Assistant'
    LLM_PROVIDER = 'api'

MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0


class LLMService:
    """LLM 服务类 - 支持 OpenAI 兼容 API"""

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.base_url = LLM_API_BASE_URL
        self.model = LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE
        self.timeout = LLM_TIMEOUT
        self.system_prompt = f"""你是{AGENT_NAME}，安徽信息工程学院人工智能专业的AI问答助手。

## 身份与职责：
你专注于回答人工智能专业培养方案、专业课程教案、课程体系、实践教学等方面的问题。

## 回答规范：
- 直接回答问题，不要说"根据提供的资料"等开场白
- 使用 **加粗** 标记关键信息
- 只使用与问题直接相关的参考资料，严禁塞入无关内容

## 无法回答时：
回复："关于这个问题，专业知识库中暂无相关内容。建议咨询专业负责人或教务处获取准确信息。"
请严格遵守以上规范。"""

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _request_with_retry(self, client, method, url, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                if method == "POST":
                    response = await client.post(url, **kwargs)
                else:
                    response = await client.get(url, **kwargs)
                if response.status_code == 429:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"LLM API 速率限制，{delay}s 后重试")
                    await asyncio.sleep(delay); continue
                if response.status_code >= 500:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"LLM API 错误 {response.status_code}，{delay}s 后重试")
                    await asyncio.sleep(delay); continue
                return response
            except httpx.TimeoutException as e:
                last_error = e; delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"LLM API 超时，{delay}s 后重试"); await asyncio.sleep(delay)
            except httpx.ConnectError as e:
                last_error = e; delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"LLM API 连接失败，{delay}s 后重试"); await asyncio.sleep(delay)
            except Exception as e:
                last_error = e; logger.error(f"LLM API 请求异常: {e}"); break
        raise last_error or Exception("LLM API 请求失败，已达最大重试次数")

    def _build_messages(self, query, context, history=None, system_prompt=None):
        messages = [{"role": "system", "content": system_prompt or self.system_prompt}]
        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})
        if context:
            user_message = f"""## 用户问题：\n{query}\n\n## 参考资料：\n{context}\n\n请基于参考资料回答用户问题。只使用与问题相关的资料，忽略无关内容。"""
        else:
            user_message = query
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, query, context="", history=None, system_prompt=None) -> str:
        if not self.is_available():
            return ""
        messages = self._build_messages(query, context, history, system_prompt)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._request_with_retry(
                    client, "POST", f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": messages,
                          "max_tokens": self.max_tokens, "temperature": self.temperature, "stream": False}
                )
                if response.status_code != 200:
                    logger.error(f"LLM API 失败: {response.status_code} - {response.text}"); return ""
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"LLM API 最终失败: {e}"); return ""

    async def chat_stream(self, query, context="", history=None, system_prompt=None) -> AsyncGenerator[str, None]:
        if not self.is_available():
            yield ""; return
        messages = self._build_messages(query, context, history, system_prompt)
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST", f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json={"model": self.model, "messages": messages,
                              "max_tokens": self.max_tokens, "temperature": self.temperature, "stream": True}
                    ) as response:
                        if response.status_code == 429 or response.status_code >= 500:
                            delay = RETRY_DELAY_BASE * (2 ** attempt)
                            logger.warning(f"LLM 流式错误 {response.status_code}，{delay}s 后重试")
                            await asyncio.sleep(delay); continue
                        if response.status_code != 200:
                            yield ""; return
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]": break
                                try:
                                    chunk = json.loads(data)
                                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                                    if content: yield content
                                except json.JSONDecodeError: continue
                        return
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"LLM 流式异常，{delay}s 后重试: {e}")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"LLM 流式异常: {e}"); yield ""; return
        yield ""


llm_service = LLMService()


try:
    from config import (
        OLLAMA_BASE_URL,
        OLLAMA_MODEL,
        OLLAMA_NUM_CTX,
        LLM_MAX_TOKENS,
        LLM_TEMPERATURE,
        LLM_TIMEOUT,
        AGENT_NAME,
        AGENT_ROLE,
    )
except ImportError:
    OLLAMA_BASE_URL = 'http://localhost:11434'
    OLLAMA_MODEL = 'qwen2.5:7b-instruct-q4_K_M'
    OLLAMA_NUM_CTX = 4096
    LLM_MAX_TOKENS = 2048
    LLM_TEMPERATURE = 0.7
    LLM_TIMEOUT = 60.0
    AGENT_NAME = 'AI Assistant'
    AGENT_ROLE = 'AI Knowledge Assistant'

logger = logging.getLogger(__name__)


class OllamaLLMService:
    """Ollama 本地 LLM 服务（GPU 加速）"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        num_ctx: int = None,
        max_tokens: int = None,
        temperature: float = None,
        timeout: float = None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip('/')
        self.model = model or OLLAMA_MODEL
        self.num_ctx = num_ctx or OLLAMA_NUM_CTX
        self.max_tokens = max_tokens or LLM_MAX_TOKENS
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.timeout = timeout or LLM_TIMEOUT

        self.system_prompt = f"""你是{AGENT_NAME}，安徽信息工程学院人工智能专业的AI问答助手。

## 身份与职责：
你专注于回答人工智能专业培养方案、专业课程教案、课程体系、实践教学等方面的问题。
你的知识来源包括：培养方案文件、各门专业课教案（机器学习、深度学习、计算机视觉、Python数据分析、操作系统、数据库等）。

## 回答规范：
- 直接回答问题，不要说"根据提供的资料"等开场白
- 使用 **加粗** 标记关键信息（课程名称、学分、学时、先修课程等）
- 使用列表组织回答，层次清晰
- 只使用与问题直接相关的参考资料，严禁塞入无关内容

## 无法回答时：
回复："关于这个问题，专业知识库中暂无相关内容。建议咨询专业负责人或教务处获取准确信息。"
请严格遵守以上规范。"""

    def is_available(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _build_messages(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """构建 Ollama 格式的消息列表（兼容 chatml）。"""
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        if context:
            user_content = f"""## 用户问题：
{query}

## 参考资料：
{context}

请基于参考资料回答用户问题。只使用与问题相关的资料，忽略无关内容。"""
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
        """
        非流式对话（Ollama /chat/completions 兼容接口）。

        Falls back to /api/chat if available, else uses /api/generate.
        """
        messages = self._build_messages(query, context, history)
        if system_prompt:
            messages[0] = {"role": "system", "content": system_prompt}

        # Try /api/chat first (structured chat API)
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
                    result = response.json()
                    content = result.get("message", {}).get("content", "")
                    logger.info(f"Ollama 回复成功，长度: {len(content)}")
                    return content.strip()
                logger.warning(f"Ollama /api/chat 失败: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ollama /api/chat 异常: {e}")

        # Fallback to /api/generate (legacy)
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
                    result = response.json()
                    content = result.get("response", "")
                    return content.strip()
        except Exception as e:
            logger.error(f"Ollama /api/generate 也失败: {e}")

        return ""

    async def chat_stream(
        self,
        query: str,
        context: str = "",
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话。"""
        messages = self._build_messages(query, context, history)
        if system_prompt:
            messages[0] = {"role": "system", "content": system_prompt}

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
                        logger.error(f"Ollama 流式失败: {response.status_code}")
                        yield ""
                        return

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                    return
        except Exception as e:
            logger.error(f"Ollama 流式异常: {e}")
            yield ""

    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """将消息列表转换为纯文本 prompt（用于 /generate）。"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"<|system|>\n{content}")
            elif role == "user":
                parts.append(f"<|user|>\n{content}")
            elif role == "assistant":
                parts.append(f"<|assistant|>\n{content}")
        parts.append("<|assistant|>")
        return "\n".join(parts)


# 全局实例
ollama_llm_service = OllamaLLMService()
