# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
def test_unified_chunker_keeps_short_sentences_and_tail_content():
    from backend.chunking.unified_chunker import UnifiedChunker

    chunker = UnifiedChunker(chunk_size=18, chunk_overlap=6, min_chunk_size=15)
    text = (
        '第一句介绍课程目标。'
        '第二句说明教学安排。'
        '第三句补充考核方式。'
    )

    chunks = chunker.chunk_text(text, metadata={'page': 1})

    assert chunks
    combined = ''.join(chunk['text'] for chunk in chunks)
    assert '第一句介绍课程目标' in combined
    assert '第二句说明教学安排' in combined
    assert '第三句补充考核方式' in combined


@pytest.mark.unit
def test_unified_chunker_splits_structured_course_line_into_fragments():
    from backend.chunking.unified_chunker import UnifiedChunker

    chunker = UnifiedChunker(chunk_size=80, chunk_overlap=16, min_chunk_size=20)
    text = (
        '课程代码 CSE324 总计：120 学时 学分 3 '
        '课内：64 学时 理论：32 学时 '
        '上机：32 学时 教材：深度学习入门 基于 Python 的理论与实现'
    )

    sentences = chunker._split_sentences(text)

    assert len(sentences) >= 3
    joined = ' '.join(sentences)
    assert '课程代码 CSE324' in joined
    assert '总计：120 学时' in joined
    assert '教材：深度学习入门' in joined
