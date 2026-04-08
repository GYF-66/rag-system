# -*- coding: utf-8 -*-
import re

import pytest


@pytest.mark.unit
def test_text_cleaner_creation():
    from backend.pipeline.text_cleaner import TextCleaner, text_cleaner

    assert isinstance(text_cleaner, TextCleaner)


@pytest.mark.unit
def test_deep_clean_text_removes_noise():
    from backend.pipeline.text_cleaner import text_cleaner

    text = '这是正常内容。\n123 456\n...........\n第二段正常内容。'
    cleaned = text_cleaner.deep_clean_text(text)

    assert '123 456' not in cleaned
    assert '...........' not in cleaned
    assert '这是正常内容' in cleaned
    assert '第二段正常内容' in cleaned


@pytest.mark.unit
def test_clean_for_display_adds_natural_paragraph_breaks():
    from backend.pipeline.text_cleaner import text_cleaner

    text = (
        '人工智能专业培养强调数学基础与工程能力。'
        '课程体系覆盖机器学习、深度学习和数据分析。'
        '实践教学包括课程实验、课程设计和毕业设计。'
        '学生需要具备解决复杂工程问题的能力。'
    )
    cleaned = text_cleaner.clean_for_display(text, max_length=200)

    assert '\n\n' in cleaned
    assert cleaned.count('。') >= 3


@pytest.mark.unit
def test_clean_for_query_prioritizes_keyword_sentences():
    from backend.pipeline.text_cleaner import text_cleaner

    text = (
        '培养目标强调家国情怀与工程伦理。'
        '核心课程包括机器学习、深度学习、计算机视觉。'
        '实践环节包含课程实验、实习和毕业设计。'
    )
    cleaned = text_cleaner.clean_for_query(text, ['核心课程', '机器学习'], max_length=180)

    assert '核心课程' in cleaned
    assert '机器学习' in cleaned
    assert '家国情怀' not in cleaned


@pytest.mark.unit
def test_format_source_excerpt_keeps_source_readable():
    from backend.pipeline.text_cleaner import text_cleaner

    text = (
        '课程体系包括数学基础、编程基础和机器学习核心课程。'
        '实践教学覆盖实验、实训、实习与毕业设计。'
        '学生需要完成规定学分和综合实践要求。'
    )
    excerpt = text_cleaner.format_source_excerpt(text, max_length=160)

    assert '\n\n' in excerpt
    assert excerpt.count('。') >= 2


@pytest.mark.unit
def test_extract_key_sentences_returns_meaningful_sentences():
    from backend.pipeline.text_cleaner import text_cleaner

    text = '第一句话包含足够多的信息。第二句话也包含足够多的信息！第三句话继续补充关键内容。'
    sentences = text_cleaner.extract_key_sentences(text, max_sentences=2)

    assert len(sentences) == 2
    assert '第一句话' in sentences[0]


@pytest.mark.unit
def test_extract_section_title():
    from backend.pipeline.text_cleaner import text_cleaner

    patterns = [re.compile(r'第[一二三四五六七八九十]+章')]
    title = text_cleaner.extract_section_title('第三章 培养目标\n相关内容', patterns)

    assert '第三章' in title


@pytest.mark.unit
def test_extract_key_sentences_splits_structured_metadata_line():
    from backend.pipeline.text_cleaner import text_cleaner

    text = (
        '课程代码 CSE324 总计：120 学时 学分 3 '
        '课内：64 学时 理论：32 学时 '
        '上机：32 学时 教材：深度学习入门 基于 Python 的理论与实现'
    )

    sentences = text_cleaner.extract_key_sentences(text, max_sentences=4)

    assert len(sentences) >= 3
    joined = ' '.join(sentences)
    assert '课程代码 CSE324' in joined
    assert '总计：120 学时' in joined
    assert '教材：深度学习入门' in joined


@pytest.mark.unit
def test_format_source_excerpt_keeps_structured_metadata_complete():
    from backend.pipeline.text_cleaner import text_cleaner

    text = (
        '课程代码 CSE324 总计：120 学时 学分 3 '
        '课内：64 学时 理论：32 学时 '
        '上机：32 学时 教材：深度学习入门 基于 Python 的理论与实现'
    )

    excerpt = text_cleaner.format_source_excerpt(text, max_length=120, max_sentences=4)

    assert excerpt.count('。') >= 2
    assert excerpt.endswith('。')
    assert '课程代码 CSE324' in excerpt
