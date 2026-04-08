# -*- coding: utf-8 -*-
"""教师 Agent —— 以专业课教师的视角，从教学体系出发系统讲解。

增强能力：
- OBE 映射：自动关联毕业要求指标点
- 课程图谱注入：注入先修/后续课程关系
- 教学设计补充检索：在共享上下文外检索教案、实验方案等材料
"""
from __future__ import annotations

from typing import Dict, List

from agents.base_agent import PerspectiveAgentBase


class TeacherAgent(PerspectiveAgentBase):
    """教师视角 Agent：严谨专业、教学体系化、标注考核重点、OBE 映射。"""

    perspective_key = 'teacher'

    _TEACH_KEYWORDS = {
        '教案', '教学', '实验', '案例', '代码', '编程', '项目', '考核',
        'Python', '实验设计', '教学设计', '教学案例', '课堂活动',
        '毕业要求', '指标点', '课程目标',
    }
    _OBE_KEYWORDS = {
        '培养', '目标', '毕业要求', '指标点', '课程矩阵', 'OBE',
        '达成度', '支撑', '映射', '课程目标',
    }
    _COURSE_KEYWORDS = {
        '课程', '先修', '后续', '衔接', '前置', '知识点', '大纲',
        '学分', '学时', '课程体系',
    }

    def _enhance_query(self, query: str, context: str) -> str:
        hints: list[str] = []
        if any(kw in query for kw in self._TEACH_KEYWORDS):
            hints.append('请融入教学设计思路，给出可落地的实验/案例方案')
        if any(kw in query for kw in self._OBE_KEYWORDS):
            hints.append('请映射到培养方案的具体条款，说明对应的毕业要求指标点编号')
        if any(kw in query for kw in self._COURSE_KEYWORDS):
            hints.append('请注明课程的先修和后续衔接关系，构建知识脉络')
        if not hints:
            return query
        return query + '\n（教学提示：' + '；'.join(hints) + '）'

    def _supplemental_queries(self, query: str) -> List[str]:
        """生成教学视角的补充检索查询。"""
        queries: list[str] = []
        # OBE 相关：补充检索毕业要求/指标点
        if any(kw in query for kw in self._OBE_KEYWORDS):
            queries.append(f'{query} 毕业要求指标点对应关系')
        # 教学设计：补充检索实验方案和教案
        if any(kw in query for kw in self._TEACH_KEYWORDS):
            queries.append(f'{query} 教学设计 实验方案')
        # 课程内容：补充检索课程大纲
        if any(kw in query for kw in self._COURSE_KEYWORDS):
            queries.append(f'{query} 课程大纲 教学内容')
        return queries

    def _enrich_context(
        self,
        query: str,
        context: str,
        shared_sources: List[Dict],
        supplemental_sources: List[Dict],
    ) -> str:
        """教师视角上下文增强：注入课程图谱和 OBE 映射信息。"""
        parts = [context] if context else []

        # 课程图谱注入
        graph_info = self._build_course_graph_info(query)
        if graph_info:
            parts.append(f'\n--- 课程关系图谱 ---\n{graph_info}')

        # 补充检索来源
        if supplemental_sources:
            parts.append(f'\n--- 教学补充材料 ---')
            for i, s in enumerate(supplemental_sources, 1):
                section = s.get('section', '')
                text = s.get('text', '')
                parts.append(f'[教学补充{i}] {section}\n{text}')

        return '\n\n'.join(parts)

    def _build_course_graph_info(self, query: str) -> str:
        """从知识库课程图谱构建教学关系补充上下文。"""
        kb = self._get_knowledge_base()
        if not kb:
            return ''

        # 提取查询中的课程关键词
        course_names = self._extract_course_mentions(query)
        if not course_names:
            return ''

        lines: list[str] = []
        try:
            matched = kb.find_courses_by_name(course_names)
            if not matched:
                return ''

            graph = kb.get_course_graph()
            for course_id, course_info in matched.items():
                name = course_info.get('name', course_id)
                credits = course_info.get('credits', '?')
                hours = course_info.get('hours', '?')
                lines.append(f'**{name}**（{credits}学分/{hours}学时）')

                # 先修课程
                prereqs = graph.get(course_id, {}).get('prerequisites', [])
                if prereqs:
                    prereq_names = [graph.get(p, {}).get('name', p) for p in prereqs]
                    lines.append(f'  先修：{", ".join(prereq_names)}')

                # 后续课程
                successors = graph.get(course_id, {}).get('successors', [])
                if successors:
                    succ_names = [graph.get(s, {}).get('name', s) for s in successors]
                    lines.append(f'  后续：{", ".join(succ_names)}')

                # 支撑的毕业要求
                grad_reqs = course_info.get('graduation_requirements', [])
                if grad_reqs:
                    lines.append(f'  支撑毕业要求：{", ".join(str(r) for r in grad_reqs)}')
        except Exception:
            return ''

        return '\n'.join(lines)

    @staticmethod
    def _extract_course_mentions(query: str) -> List[str]:
        """从查询文本中提取课程名称关键词。"""
        import re
        # 匹配课程编号（如 CSE318, CSE3003）
        codes = re.findall(r'[A-Z]{2,4}\d{3,4}', query)
        # 匹配中文课程名（如 机器学习、深度学习、Python程序设计）
        cn_courses = re.findall(
            r'(?:机器学习|深度学习|人工智能|数据结构|操作系统|计算机网络'
            r'|数据库|算法|编译原理|线性代数|概率论|离散数学'
            r'|Python|Java|C语言|大数据|自然语言处理|计算机视觉'
            r'|数字图像处理|模式识别|软件工程|数据挖掘'
            r'|云计算|物联网|信息安全|嵌入式)',
            query,
        )
        return codes + cn_courses


teacher_agent = TeacherAgent()
