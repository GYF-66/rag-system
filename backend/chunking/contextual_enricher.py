# -*- coding: utf-8 -*-
"""Contextual Retrieval — 为分块注入文档级上下文前缀。

参考 Anthropic 的 Contextual Retrieval 方案：
在 chunk 向量化之前为其添加一段简短的上下文背景，使其携带文档全局语义，
从而提高 embedding 和 BM25 的检索准确率。

支持两种模式：
1. 规则模式（默认）：基于 section_path + 文档标题自动拼接上下文前缀
2. LLM 模式（可选）：调用 LLM 为每个 chunk 生成语义化的上下文摘要
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


def inject_contextual_prefix(
    chunks: Sequence[Dict],
    document_title: str = '',
    document_summary: str = '',
) -> List[Dict]:
    """为每个 chunk 注入上下文前缀（规则模式）。

    最终 chunk 的 text 变为:
        [上下文前缀]\n\n[原始文本]

    同时保留原始文本在 metadata['original_text'] 中。
    """
    enriched: List[Dict] = []

    for chunk in chunks:
        enriched_chunk = dict(chunk)
        metadata = dict(chunk.get('metadata') or {})

        # 构建上下文前缀
        prefix_parts: List[str] = []

        # 文档标题
        doc_title = document_title or metadata.get('title') or metadata.get('document_id') or ''
        if doc_title:
            prefix_parts.append(f'本段来自：{doc_title}')

        # 文档摘要
        if document_summary:
            prefix_parts.append(f'文档概述：{document_summary}')

        # 章节路径
        section_path = metadata.get('section_path_text') or ''
        if not section_path:
            section_path_list = metadata.get('section_path', [])
            if section_path_list:
                section_path = ' > '.join(section_path_list)
        if section_path:
            prefix_parts.append(f'章节位置：{section_path}')

        # 页码信息
        page_start = metadata.get('page_start')
        page_end = metadata.get('page_end')
        if page_start:
            if page_end and page_end != page_start:
                prefix_parts.append(f'页码：p.{page_start}-{page_end}')
            else:
                prefix_parts.append(f'页码：p.{page_start}')

        # 拼接
        original_text = str(chunk.get('text', ''))
        if prefix_parts:
            contextual_prefix = '；'.join(prefix_parts) + '。'
            enriched_text = f'{contextual_prefix}\n\n{original_text}'
        else:
            enriched_text = original_text

        # 更新 chunk
        enriched_chunk['text'] = enriched_text
        enriched_chunk['char_count'] = len(enriched_text)

        # 保留原始文本供生成阶段使用（避免 prefix 干扰 LLM）
        metadata['original_text'] = original_text
        metadata['contextual_prefix'] = '；'.join(prefix_parts) if prefix_parts else ''
        enriched_chunk['metadata'] = metadata

        enriched.append(enriched_chunk)

    logger.info('Contextual prefix 注入完成，共处理 %d 个 chunk', len(enriched))
    return enriched


def build_document_summary(chunks: Sequence[Dict]) -> str:
    """从 chunks 中提取文档级摘要（基于前几个 chunk 的标题和关键词）。"""
    titles_seen = set()
    keywords_seen = set()

    for chunk in chunks[:10]:
        metadata = chunk.get('metadata') or {}
        title = metadata.get('title', '')
        if title and title not in titles_seen:
            titles_seen.add(title)
        for kw in (metadata.get('keywords') or [])[:3]:
            keywords_seen.add(kw)

    parts: List[str] = []
    if titles_seen:
        parts.append('涉及内容：' + '、'.join(list(titles_seen)[:5]))
    if keywords_seen:
        parts.append('关键词：' + '、'.join(list(keywords_seen)[:8]))

    return '；'.join(parts)
