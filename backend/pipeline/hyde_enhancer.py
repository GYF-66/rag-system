# -*- coding: utf-8 -*-
"""HyDE (Hypothetical Document Embedding) 查询增强模块。

让 LLM 先生成一个假设性回答文档，再用该文档作为检索查询，
解决用户 Query 过短或语义不匹配的问题。
"""
from __future__ import annotations

import logging
from typing import Optional

from config import LLM_API_KEY

logger = logging.getLogger(__name__)

HYDE_PROMPT_TEMPLATE = """你是安徽信息工程学院人工智能专业的知识库助手。
请根据以下问题，写一段详细的假设性回答（约 150-250 字），就好像你已经找到了准确的资料。
回答应包含具体的课程名称、学分学时、培养要求等细节（可以合理假设）。
不要说"根据资料"等开头，直接给出信息性内容。

问题：{query}

假设性回答："""

# 简单查询无需 HyDE（如单个词、问候语等）
_SIMPLE_QUERY_MAX_LEN = 6
_GREETING_WORDS = {'你好', '您好', '在吗', '谢谢', 'hello', 'hi', '帮助', '是谁'}


def _is_simple_query(query: str) -> bool:
    """判断是否为不需要 HyDE 的简单查询。"""
    stripped = query.strip()
    if len(stripped) <= _SIMPLE_QUERY_MAX_LEN:
        return True
    if stripped.lower() in _GREETING_WORDS:
        return True
    return False


async def generate_hyde_document(query: str) -> Optional[str]:
    """异步生成 HyDE 假设性文档。

    Returns:
        假设性文档文本，如果无法生成则返回 None。
    """
    if not LLM_API_KEY or _is_simple_query(query):
        return None

    try:
        from llm_service import llm_service
    except ImportError:
        return None

    if not llm_service.is_available():
        return None

    try:
        prompt = HYDE_PROMPT_TEMPLATE.format(query=query)
        hyde_doc = await llm_service.chat(
            query=prompt,
            context='',
            history=None,
        )
        if hyde_doc and len(hyde_doc.strip()) > 30:
            logger.info('HyDE 文档生成成功，长度 %d', len(hyde_doc))
            return hyde_doc.strip()
    except Exception as exc:
        logger.warning('HyDE 文档生成失败: %s', exc)

    return None
