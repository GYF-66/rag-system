# -*- coding: utf-8 -*-
"""
LLM 服务模块
支持 DeepSeek / OpenAI / 兼容 API 调用
"""
import httpx
import logging
from typing import List, Dict, Optional, AsyncGenerator
import json

from config import (
    LLM_API_KEY,
    LLM_API_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    AGENT_NAME,
    AGENT_ROLE
)

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 服务类 - 支持 OpenAI 兼容 API"""

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.base_url = LLM_API_BASE_URL
        self.model = LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE
        self.timeout = LLM_TIMEOUT

        # 系统提示词 - 推理型架构（彻底修复相关性问题）
        self.system_prompt = f"""你是{AGENT_NAME}，安徽信息工程学院的官方AI问答助手。

## 【重要】输出规范：

### 第一步：内部思考（必须）
在回答前，你需要先进行内部思考：
1. **分析问题核心**：用户真正想知道什么？（如"请假流程"="如何请假+需要什么手续"）
2. **评估参考资料**：逐一检查每条参考资料与问题的相关性
   - 如果资料内容（如学分折算、考试分数、奖学金等）与问题完全无关 → 直接丢弃，禁止使用
   - 只使用真正回答问题的资料
3. **判断是否足够**：相关资料是否足够回答问题？

### 第二步：正式回答
**输出规则：**
- ✅ **只输出与问题直接相关的信息**
- ✅ 直接给出答案，不要说"根据提供的资料"等开场白
- ✅ 使用 **加粗** 标记关键信息（条件、时间、地点等）
- ✅ 使用有序列表 "1. 2. 3." 或无序列表 "- " 组织回答
- ✅ 引用条款时标注，如"根据第X条规定"
- ❌ **严禁**：把不相关的内容（学分、分数、其他规定）塞进回答
- ❌ **严禁**：复读参考资料中的无关内容
- ❌ **严禁**：凑字数或无意义扩写

### 回答结构：
1. **核心回答**（1-2句话概括要点）
2. **详细说明**（具体流程、条款、规定）
3. **温馨提示**（如有注意事项）

### 如果参考资料与问题完全无关：
直接回复："抱歉，关于[问题]的具体规定，学生手册中未包含相关内容。建议您咨询辅导员或联系学生工作处获取准确信息。"

请严格遵守以上规范回答问题。"""

    def is_available(self) -> bool:
        """检查 LLM 服务是否可用"""
        return bool(self.api_key)

    async def chat(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None
    ) -> str:
        """
        与 LLM 进行对话

        Args:
            query: 用户查询
            context: 知识库检索到的上下文
            history: 对话历史

        Returns:
            LLM 生成的回复
        """
        if not self.is_available():
            logger.warning("LLM API Key 未配置，使用规则回复")
            return ""

        # 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加对话历史（最近几轮）
        if history:
            for msg in history[-6:]:  # 最多保留最近3轮对话
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})

        # 构建用户消息（包含上下文）
        if context:
            user_message = f"""用户问题：{query}

相关知识库内容：
{context}

请根据上述知识库内容回答用户的问题。"""
        else:
            user_message = query

        messages.append({"role": "user", "content": user_message})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stream": False
                    }
                )

                if response.status_code != 200:
                    logger.error(f"LLM API 调用失败: {response.status_code} - {response.text}")
                    return ""

                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"LLM 回复成功，长度: {len(content)}")
                return content.strip()

        except httpx.TimeoutException:
            logger.error("LLM API 调用超时")
            return ""
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            return ""

    async def chat_stream(
        self,
        query: str,
        context: str,
        history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式对话（Streaming）

        Args:
            query: 用户查询
            context: 知识库上下文
            history: 对话历史

        Yields:
            逐字/逐词返回生成的内容
        """
        if not self.is_available():
            logger.warning("LLM API Key 未配置")
            yield ""
            return

        # 构建消息
        messages = [{"role": "system", "content": self.system_prompt}]

        if history:
            for msg in history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})

        if context:
            user_message = f"""用户问题：{query}

相关知识库内容：
{context}

请根据上述知识库内容回答用户的问题。"""
        else:
            user_message = query

        messages.append({"role": "user", "content": user_message})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"LLM 流式调用异常: {e}")
            yield ""


# 全局 LLM 服务实例
llm_service = LLMService()
