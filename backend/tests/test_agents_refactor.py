# -*- coding: utf-8 -*-
"""agents 重构验证测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents import multi_perspective_agent, teacher_agent, study_expert_agent, admin_dss_agent
from agents.teacher_agent import TeacherAgent
from agents.study_expert_agent import StudyExpertAgent


def test_teacher_query_enhance():
    q = teacher_agent._enhance_query('机器学习课程的教学设计', '')
    assert '教学提示' in q


def test_teacher_supplemental_queries():
    sq = teacher_agent._supplemental_queries('机器学习课程目标和毕业要求指标点')
    assert len(sq) >= 1


def test_study_expert_query_enhance():
    q = study_expert_agent._enhance_query('怎么学深度学习', '')
    assert '学伴提示' in q


def test_study_expert_supplemental_queries():
    sq = study_expert_agent._supplemental_queries('Python先修课程有哪些')
    assert len(sq) >= 1


def test_admin_query_enhance():
    q = admin_dss_agent._enhance_query('学分结构分布和比例分析', '')
    assert '决策提示' in q


def test_admin_supplemental_queries():
    sq = admin_dss_agent._supplemental_queries('毕业要求覆盖度一致性检查')
    assert len(sq) >= 1


def test_available_perspectives():
    avail = multi_perspective_agent.available_perspectives
    assert len(avail) == 3
    keys = {p['key'] for p in avail}
    assert keys == {'student', 'teacher', 'admin'}


def test_course_mentions_extraction():
    mentions = TeacherAgent._extract_course_mentions('CSE318机器学习和深度学习的先修关系')
    assert 'CSE318' in mentions
    assert '机器学习' in mentions


def test_prerequisites_tracing():
    graph = {
        'A': {'prerequisites': [], 'name': 'A'},
        'B': {'prerequisites': ['A'], 'name': 'B'},
        'C': {'prerequisites': ['B'], 'name': 'C'},
    }
    chain = StudyExpertAgent._trace_prerequisites('C', graph)
    assert chain == ['A', 'B']


def test_perspective_result_model():
    from models import PerspectiveResult, PerspectiveStep, SupplementalSource
    fields = list(PerspectiveResult.model_fields.keys())
    assert 'steps' in fields
    assert 'supplemental_sources' in fields
    # steps 和 supplemental_sources 应为可选
    r = PerspectiveResult(
        perspective='teacher', name='教研智囊', icon='👨‍🏫',
        tagline='OBE 教学设计', response='测试回答',
    )
    assert r.steps is None
    assert r.supplemental_sources is None
