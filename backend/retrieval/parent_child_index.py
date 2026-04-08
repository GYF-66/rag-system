# -*- coding: utf-8 -*-
"""父子文档双粒度索引策略。

检索时使用小块（子块，150-300字符）进行精确匹配，
生成时返回所属父块（800-1200字符）以提供完整背景上下文。

此模块为 unified_chunker 产生的 chunks 生成父子映射关系。
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# 子块参数
CHILD_CHUNK_SIZE = 250
CHILD_CHUNK_OVERLAP = 50
MIN_CHILD_CHUNK_SIZE = 80

# 父块作为输出时的最大长度
MAX_PARENT_CONTEXT_LENGTH = 1200


class ParentChildIndex:
    """维护父块 -> 子块的映射关系，支持检索时返回父块上下文。"""

    def __init__(self) -> None:
        # parent_id -> parent chunk dict
        self._parents: Dict[str, Dict] = {}
        # child_id -> parent_id
        self._child_to_parent: Dict[str, str] = {}
        # parent_id -> [child_ids]
        self._parent_to_children: Dict[str, List[str]] = {}

    @property
    def parent_count(self) -> int:
        return len(self._parents)

    @property
    def child_count(self) -> int:
        return len(self._child_to_parent)

    def build_from_chunks(self, parent_chunks: Sequence[Dict]) -> List[Dict]:
        """从父级 chunks 生成子块并建立映射。

        Returns:
            子块列表（用于索引到向量库中做检索）
        """
        self._parents.clear()
        self._child_to_parent.clear()
        self._parent_to_children.clear()

        child_chunks: List[Dict] = []
        child_id_counter = 0

        for parent in parent_chunks:
            parent_id = str(parent.get('id', ''))
            parent_text = str(parent.get('text', ''))
            if not parent_text.strip():
                continue

            self._parents[parent_id] = parent
            self._parent_to_children[parent_id] = []

            # 将父块文本切分成子块
            sub_chunks = self._split_into_children(parent_text)

            for sub_text in sub_chunks:
                child_id = f'{parent_id}_c{child_id_counter}'
                child_id_counter += 1

                child_chunk = {
                    'id': child_id,
                    'text': sub_text,
                    'char_count': len(sub_text),
                    'section': parent.get('section', ''),
                    'title': parent.get('title', ''),
                    'metadata': {
                        **(parent.get('metadata') or {}),
                        'parent_id': parent_id,
                        'is_child_chunk': True,
                    },
                    'similarity': 0.0,
                }
                child_chunks.append(child_chunk)

                self._child_to_parent[child_id] = parent_id
                self._parent_to_children[parent_id].append(child_id)

        logger.info(
            '父子索引构建完成: %d 父块 -> %d 子块',
            len(self._parents),
            len(child_chunks),
        )
        return child_chunks

    def get_parent_context(self, child_id: str) -> Optional[Dict]:
        """根据子块 ID 获取其父块完整上下文。"""
        parent_id = self._child_to_parent.get(child_id)
        if not parent_id:
            return None
        return self._parents.get(parent_id)

    def expand_to_parents(self, child_results: Sequence[Dict]) -> List[Dict]:
        """将检索命中的子块结果扩展为父块上下文。

        相同父块的多个子块命中会被合并为一个父块结果，
        父块获得所有子块分数中的最高分。
        """
        parent_scores: Dict[str, float] = {}
        parent_hits: Dict[str, Dict] = {}

        for child in child_results:
            child_id = str(child.get('id', ''))
            # 从 metadata 中获取 parent_id
            parent_id = (child.get('metadata') or {}).get('parent_id', '')
            if not parent_id:
                parent_id = self._child_to_parent.get(child_id, '')

            if not parent_id or parent_id not in self._parents:
                # 非子块或找不到父块，原样返回
                if child_id not in parent_hits:
                    parent_hits[child_id] = child
                    parent_scores[child_id] = child.get('similarity', 0.0)
                continue

            score = max(
                child.get('similarity', 0.0),
                child.get('rerank_score', 0.0),
            )

            if parent_id not in parent_hits:
                parent = dict(self._parents[parent_id])
                parent['similarity'] = score
                parent['rerank_score'] = score
                parent_hits[parent_id] = parent
                parent_scores[parent_id] = score
            else:
                if score > parent_scores[parent_id]:
                    parent_scores[parent_id] = score
                    parent_hits[parent_id]['similarity'] = score
                    parent_hits[parent_id]['rerank_score'] = score

        # 按分数排序
        results = sorted(
            parent_hits.values(),
            key=lambda x: max(x.get('similarity', 0), x.get('rerank_score', 0)),
            reverse=True,
        )
        return results

    def _split_into_children(self, text: str) -> List[str]:
        """将文本切分为子块。"""
        if len(text) <= CHILD_CHUNK_SIZE:
            return [text]

        children: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + CHILD_CHUNK_SIZE, len(text))

            # 尝试在句子边界断开
            if end < len(text):
                for delimiter in ('。', '；', '！', '？', '\n', '，'):
                    boundary = text.rfind(delimiter, start + MIN_CHILD_CHUNK_SIZE, end)
                    if boundary > start:
                        end = boundary + 1
                        break

            chunk = text[start:end].strip()
            if len(chunk) >= MIN_CHILD_CHUNK_SIZE:
                children.append(chunk)
            elif children:
                # 尾部小段合并到前一个子块
                children[-1] = children[-1] + ' ' + chunk

            start = end - CHILD_CHUNK_OVERLAP if end < len(text) else end

        return children if children else [text]


# 全局实例
parent_child_index = ParentChildIndex()
