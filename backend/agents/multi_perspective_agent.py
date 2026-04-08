# -*- coding: utf-8 -*-
"""多视角 Agent 调度器 —— 编排学霸/老师/教务三视角并行回答，带容错与超时控制。

2025 升级：增加 Planner（任务规划）和 Grader（质量评审）节点，
实现 Supervisor 模式编排：
  Planner → 并行视角 Agent → Grader (质量审核)
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from agents.study_expert_agent import study_expert_agent
from agents.teacher_agent import teacher_agent
from agents.admin_dss_agent import admin_dss_agent

logger = logging.getLogger(__name__)

# 注册所有可用视角 Agent
_PERSPECTIVE_AGENTS = {
    'student': study_expert_agent,
    'teacher': teacher_agent,
    'admin': admin_dss_agent,
}

# 单视角超时（秒）—— 增强模式需要更多时间
_PERSPECTIVE_TIMEOUT = 30.0
_PERSPECTIVE_TIMEOUT_DEEP = 45.0


class QueryPlanner:
    """Planner 节点：分析查询并决定需要哪些视角参与。"""

    # 视角路由规则
    _ROUTING_RULES = {
        'student': ('学习', '复习', '考试', '先修', '学长', '经验', '难度', '怎么学', '推荐'),
        'teacher': ('教学', '教案', '大纲', '课程设计', '教学目标', 'OBE', '教学方法', '实验'),
        'admin': ('学分', '培养方案', '毕业要求', '课程体系', '转专业', '学位', '教务', '选课'),
    }

    def plan(
        self,
        query: str,
        intents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """规划查询应该路由到哪些视角。

        Returns:
            {
                'perspectives': ['student', 'teacher', ...],
                'reason': str,
                'is_multi': bool,
            }
        """
        matched: Dict[str, int] = {}

        for perspective, keywords in self._ROUTING_RULES.items():
            score = sum(1 for kw in keywords if kw in query)
            if score > 0:
                matched[perspective] = score

        # 如果没有明确匹配，默认所有视角
        if not matched:
            return {
                'perspectives': list(_PERSPECTIVE_AGENTS.keys()),
                'reason': '查询意图不明确，启用全视角分析',
                'is_multi': True,
            }

        # 按匹配度排序
        sorted_perspectives = sorted(matched.items(), key=lambda x: x[1], reverse=True)
        perspectives = [p for p, _ in sorted_perspectives]

        # 复杂查询（多意图）启用多视角
        if len(perspectives) >= 2 or (intents and len(intents) >= 2):
            return {
                'perspectives': perspectives,
                'reason': f'多意图查询，启用视角: {", ".join(perspectives)}',
                'is_multi': True,
            }

        return {
            'perspectives': perspectives[:1],
            'reason': f'单一意图查询，路由到: {perspectives[0]}',
            'is_multi': False,
        }


class ResponseGrader:
    """Grader 节点：评审视角 Agent 的输出质量。"""

    def grade(
        self,
        query: str,
        responses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """评审并标注每个视角回答的质量。

        为每个 response 添加 'grade' 字段：
        - 'high': 回答充实且相关
        - 'medium': 回答基本可用
        - 'low': 回答质量差或空
        """
        graded: List[Dict[str, Any]] = []

        for resp in responses:
            response_text = str(resp.get('response', '')).strip()
            grade_info = self._evaluate_response(query, response_text)
            resp['grade'] = grade_info['grade']
            resp['grade_score'] = grade_info['score']
            graded.append(resp)

        # 按质量分排序
        graded.sort(key=lambda x: x.get('grade_score', 0), reverse=True)
        return graded

    def _evaluate_response(self, query: str, response: str) -> Dict[str, Any]:
        """评估单个回答的质量。"""
        if not response:
            return {'grade': 'low', 'score': 0.0}

        score = 0.0

        # 长度评分
        if len(response) >= 200:
            score += 0.3
        elif len(response) >= 50:
            score += 0.15

        # 是否包含结构化格式（列表、加粗等）
        if '**' in response or '- ' in response or '1.' in response:
            score += 0.2

        # 是否包含查询关键词
        query_chars = set(query)
        overlap = len(query_chars & set(response)) / max(len(query_chars), 1)
        score += overlap * 0.3

        # 是否有实质内容（非模板回复）
        refusal_hints = ('暂无相关内容', '无法回答', '建议咨询', '我不太确定')
        if any(h in response for h in refusal_hints):
            score *= 0.3

        # 错误标记
        if response.startswith('[ERROR]') or response.startswith('抱歉'):
            score *= 0.1

        score = min(score, 1.0)

        if score >= 0.5:
            grade = 'high'
        elif score >= 0.2:
            grade = 'medium'
        else:
            grade = 'low'

        return {'grade': grade, 'score': round(score, 3)}


# 实例
_planner = QueryPlanner()
_grader = ResponseGrader()


class MultiPerspectiveAgent:
    """编排多个视角 Agent，复用 RAG 检索结果，并行生成多维度回答。"""

    @property
    def available_perspectives(self) -> List[Dict[str, str]]:
        """返回所有可用视角的元信息。"""
        return [
            {
                'key': key,
                'name': ag.name,
                'icon': ag.icon,
                'tagline': ag.tagline,
            }
            for key, ag in _PERSPECTIVE_AGENTS.items()
        ]

    async def generate_perspective(
        self,
        perspective_key: str,
        query: str,
        context: str,
        session_history: Optional[List[Dict[str, Any]]] = None,
        shared_sources: Optional[List[Dict[str, Any]]] = None,
        enable_deep: bool = True,
    ) -> Dict[str, Any]:
        """委托给具体的视角 Agent 执行分析。"""
        ag = _PERSPECTIVE_AGENTS.get(perspective_key)
        if not ag:
            return {'perspective': perspective_key, 'response': '', 'error': 'unknown perspective'}

        timeout = _PERSPECTIVE_TIMEOUT_DEEP if enable_deep else _PERSPECTIVE_TIMEOUT
        try:
            return await asyncio.wait_for(
                ag.analyze(
                    query, context, session_history,
                    shared_sources=shared_sources,
                    enable_deep=enable_deep,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("视角 %s 超时 (%.0fs)", perspective_key, timeout)
            return ag._error_result('timeout')
        except Exception as exc:
            logger.error("视角 %s 异常: %s", perspective_key, exc)
            return ag._error_result(str(exc))

    async def generate_dual(
        self,
        query: str,
        context: str,
        session_history: Optional[List[Dict[str, Any]]] = None,
        shared_sources: Optional[List[Dict[str, Any]]] = None,
        enable_deep: bool = True,
    ) -> List[Dict[str, Any]]:
        """Supervisor 模式编排: Planner → 并行视角 Agent → Grader。"""
        timeout = _PERSPECTIVE_TIMEOUT_DEEP if enable_deep else _PERSPECTIVE_TIMEOUT

        # Step 1: Planner 规划
        plan = _planner.plan(query)
        planned_perspectives = plan['perspectives']
        logger.info('Planner 规划: %s (%s)', planned_perspectives, plan['reason'])

        # 按规划选择需要的 Agent
        agents_to_run = {
            key: ag for key, ag in _PERSPECTIVE_AGENTS.items()
            if key in planned_perspectives
        }
        # 如果规划没有匹配到任何 agent，使用全部
        if not agents_to_run:
            agents_to_run = _PERSPECTIVE_AGENTS

        # Step 2: 并行调用选中的视角 Agent
        tasks = [
            asyncio.wait_for(
                ag.analyze(
                    query, context, session_history,
                    shared_sources=shared_sources,
                    enable_deep=enable_deep,
                ),
                timeout=timeout,
            )
            for ag in agents_to_run.values()
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[Dict[str, Any]] = []
        for key, item in zip(agents_to_run, raw):
            if isinstance(item, BaseException):
                ag = agents_to_run[key]
                err_msg = 'timeout' if isinstance(item, asyncio.TimeoutError) else str(item)
                logger.warning("视角 %s 失败 → %s", key, err_msg)
                results.append(ag._error_result(err_msg))
            else:
                results.append(item)

        # Step 3: Grader 评审
        graded_results = _grader.grade(query, results)

        # 在结果中添加编排元信息
        for r in graded_results:
            r['orchestration'] = {
                'plan': plan,
                'graded': True,
            }

        return graded_results


multi_perspective_agent = MultiPerspectiveAgent()
