# -*- coding: utf-8 -*-
"""Utilities for splitting OCR-style structured text into readable fragments."""
from __future__ import annotations

import re
from typing import List

_STRUCTURED_FIELD_LABELS = (
    '课程代码',
    '课程名称',
    '课程类别',
    '授课对象',
    '任课教师',
    '主讲教师',
    '专业班级',
    '总计',
    '课内',
    '理论',
    '实验',
    '上机',
    '课外',
    '其他',
    '学分',
    '类别',
    '名称',
    '职称',
    '对象',
    '教材',
    '主要参考资料',
    '参考资料',
)


def _build_spaced_pattern(label: str) -> str:
    tokens = [re.escape(char) for char in label if not char.isspace()]
    return r'\s*'.join(tokens)


_FIELD_PATTERNS = [re.compile(_build_spaced_pattern(label)) for label in _STRUCTURED_FIELD_LABELS]
_FIELD_PATTERN_TEXT = '|'.join(
    sorted((_build_spaced_pattern(label) for label in _STRUCTURED_FIELD_LABELS), key=len, reverse=True)
)
_FIELD_SPLIT_RE = re.compile(rf'(?=(?:{_FIELD_PATTERN_TEXT})(?:\s*[：:]|\s+))')


def normalize_spacing(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text).replace('\u3000', ' ')).strip()


def contains_structured_label(text: str) -> bool:
    normalized = normalize_spacing(text)
    return any(pattern.search(normalized) for pattern in _FIELD_PATTERNS)


def looks_like_structured_line(text: str) -> bool:
    normalized = normalize_spacing(text)
    if len(normalized) < 28:
        return False
    label_hits = sum(1 for pattern in _FIELD_PATTERNS if pattern.search(normalized))
    return label_hits >= 2


def split_structured_fragments(text: str, *, min_fragment_chars: int = 8) -> List[str]:
    normalized = normalize_spacing(text)
    if not normalized:
        return []
    if not looks_like_structured_line(normalized):
        return [normalized]

    fragments: List[str] = []
    for raw_fragment in _FIELD_SPLIT_RE.split(normalized):
        fragment = raw_fragment.strip(' ，、；：,.')
        if not fragment:
            continue

        compact = re.sub(r'\s+', '', fragment)
        if len(compact) < min_fragment_chars:
            if fragments:
                fragments[-1] = f'{fragments[-1]} {fragment}'.strip()
            continue
        fragments.append(fragment)

    return fragments or [normalized]


def truncate_text_at_boundary(text: str, *, max_length: int, min_ratio: float = 0.55) -> str:
    if len(text) <= max_length:
        return text

    candidate = text[:max_length].rstrip('，、；：,. ')
    minimum = max(12, int(max_length * min_ratio))

    for marker in ('\n\n', '。', '！', '？', '；', '：', '，', ' '):
        if marker not in candidate:
            continue
        trimmed = candidate.rsplit(marker, 1)[0].strip(' ，、；：,.')
        if len(trimmed) >= minimum:
            return trimmed

    structured_fragments = split_structured_fragments(candidate, min_fragment_chars=6)
    if len(structured_fragments) > 1:
        rebuilt = '。'.join(structured_fragments[:-1]).strip('。 ')
        if len(rebuilt) >= minimum:
            return rebuilt

    return candidate
