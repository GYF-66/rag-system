# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
def test_response_generator_creation():
    from backend.pipeline.response_generator import ResponseGenerator

    generator = ResponseGenerator('测试助手')
    assert generator.agent_name == '测试助手'


@pytest.mark.unit
def test_classify_query_groups_curriculum_and_practice():
    from backend.pipeline.response_generator import ResponseGenerator

    generator = ResponseGenerator('测试助手')
    assert generator.classify_query('培养目标是什么？') == 'curriculum'
    assert generator.classify_query('毕业设计怎么安排？') == 'practice'
    assert generator.classify_query('先修课程有哪些？') == 'prerequisite'


@pytest.mark.unit
def test_fallback_response_has_natural_paragraph_break():
    from backend.pipeline.response_generator import ResponseGenerator

    generator = ResponseGenerator('测试助手')
    response = generator.fallback('随机问题')

    assert '随机问题' in response
    assert '\n\n' in response


@pytest.mark.unit
def test_generate_with_sources_outputs_markdown_sections_and_bullets():
    from backend.pipeline.response_generator import ResponseGenerator

    generator = ResponseGenerator('测试助手')
    sources = [
        {
            'text': '人工智能专业强调数学基础与编程能力培养。课程体系覆盖机器学习、深度学习和工程实践。',
            'section': '培养目标',
        },
        {
            'text': '实践教学包括课程实验、课程设计、专业实习和毕业设计等环节。',
            'section': '实践环节',
        },
    ]

    response = generator.generate('人工智能专业的核心课程与实践环节如何安排？', 'context', sources)

    assert response.startswith('围绕')
    assert '### 培养目标' in response
    assert '### 实践环节' in response
    assert '- 人工智能专业强调数学基础与编程能力培养。' in response
    assert '\n\n如果' in response


@pytest.mark.unit
def test_generate_without_sources_uses_fallback():
    from backend.pipeline.response_generator import ResponseGenerator

    generator = ResponseGenerator('测试助手')
    response = generator.generate('未知问题', '', [])

    assert '当前知识库中没有检索到' in response
