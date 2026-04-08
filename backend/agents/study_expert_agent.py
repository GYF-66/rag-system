# -*- coding: utf-8 -*-
"""学霸 Agent —— 以优秀学长/学姐的视角，从实战经验出发回答问题。

增强能力：
- 学习路径构建：自动构建课程学习路径和知识地图
- 先修课程链：查询课程前置依赖并给出学习建议
- 知识串联：跨课程知识点关联
"""
from __future__ import annotations

from typing import Dict, List

from agents.base_agent import PerspectiveAgentBase


class StudyExpertAgent(PerspectiveAgentBase):
    """学霸视角 Agent：亲切接地气、经验分享、类比教学、串联知识、路径导航。"""

    perspective_key = 'student'

    _LEARNING_KEYWORDS = {
        '怎么学', '学习方法', '复习', '备考', '考试', '难不难', '挂科', '学分',
        '知识地图', '学习路径', '前置课程', '预习', '难点', '重点', '入门', '进阶',
    }
    _PATH_KEYWORDS = {
        '先修', '前置', '后续', '路径', '顺序', '先学', '再学', '基础',
        '进阶', '高阶', '入门', '方向', '规划',
    }
    _CONNECT_KEYWORDS = {
        '关系', '联系', '区别', '对比', '串联', '结合', '交叉', '应用',
        '实践', '项目', '实习', '竞赛',
    }

    def _enhance_query(self, query: str, context: str) -> str:
        hints: list[str] = []
        if any(kw in query for kw in self._LEARNING_KEYWORDS):
            hints.append('请侧重分享实际学习经验和备考策略')
        if any(kw in query for kw in self._PATH_KEYWORDS):
            hints.append('请构建清晰的学习路径，标注每一步的前置知识要求')
        if any(kw in query for kw in self._CONNECT_KEYWORDS):
            hints.append('请串联相关课程知识点，说明它们在实际应用中如何配合')
        if '课程' in query or '先修' in query:
            hints.append('请串联前置与后续课程的知识关系')
        if not hints:
            return query
        return query + '\n（学伴提示：' + '；'.join(hints) + '）'

    def _supplemental_queries(self, query: str) -> List[str]:
        """生成学习视角的补充检索查询。"""
        queries: list[str] = []
        # 学习路径：补充检索课程先修关系
        if any(kw in query for kw in self._PATH_KEYWORDS):
            queries.append(f'{query} 先修课程 学习顺序')
        # 学习方法：补充检索考核方式和重点
        if any(kw in query for kw in self._LEARNING_KEYWORDS):
            queries.append(f'{query} 考核方式 重点难点')
        # 知识串联：补充检索相关课程
        if any(kw in query for kw in self._CONNECT_KEYWORDS):
            queries.append(f'{query} 相关课程 知识串联')
        return queries

    def _enrich_context(
        self,
        query: str,
        context: str,
        shared_sources: List[Dict],
        supplemental_sources: List[Dict],
    ) -> str:
        """学霸视角上下文增强：注入学习路径和课程链信息。"""
        parts = [context] if context else []

        # 学习路径注入
        path_info = self._build_learning_path_info(query)
        if path_info:
            parts.append(f'\n--- 学习路径参考 ---\n{path_info}')

        # 补充来源
        if supplemental_sources:
            parts.append(f'\n--- 学长补充材料 ---')
            for i, s in enumerate(supplemental_sources, 1):
                section = s.get('section', '')
                text = s.get('text', '')
                parts.append(f'[学习补充{i}] {section}\n{text}')

        return '\n\n'.join(parts)

    def _build_learning_path_info(self, query: str) -> str:
        """从课程图谱构建学习路径信息。"""
        kb = self._get_knowledge_base()
        if not kb:
            return ''

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
                semester = course_info.get('semester', '?')
                lines.append(f'📘 **{name}**（第{semester}学期）')

                # 先修链（递归向上追溯）
                prereq_chain = self._trace_prerequisites(course_id, graph, depth=3)
                if prereq_chain:
                    chain_str = ' → '.join(prereq_chain)
                    lines.append(f'  📍 先修链：{chain_str} → **{name}**')

                # 后续发展方向
                successors = graph.get(course_id, {}).get('successors', [])
                if successors:
                    succ_names = [graph.get(s, {}).get('name', s) for s in successors]
                    lines.append(f'  🔜 后续可选：{", ".join(succ_names)}')

                # 课程难度提示
                credits = course_info.get('credits', 0)
                hours = course_info.get('hours', 0)
                if credits and hours:
                    lines.append(f'  📊 {credits}学分/{hours}学时')
        except Exception:
            return ''

        return '\n'.join(lines)

    @staticmethod
    def _trace_prerequisites(course_id: str, graph: Dict, depth: int = 3) -> List[str]:
        """递归追溯先修课程链。"""
        chain: list[str] = []
        current = course_id
        visited: set[str] = {current}

        for _ in range(depth):
            prereqs = graph.get(current, {}).get('prerequisites', [])
            if not prereqs:
                break
            # 取第一个先修课程（主线路径）
            prev = prereqs[0]
            if prev in visited:
                break
            visited.add(prev)
            chain.insert(0, graph.get(prev, {}).get('name', prev))
            current = prev

        return chain

    @staticmethod
    def _extract_course_mentions(query: str) -> List[str]:
        """从查询文本中提取课程名称关键词。"""
        import re
        codes = re.findall(r'[A-Z]{2,4}\d{3,4}', query)
        cn_courses = re.findall(
            r'(?:机器学习|深度学习|人工智能|数据结构|操作系统|计算机网络'
            r'|数据库|算法|编译原理|线性代数|概率论|离散数学'
            r'|Python|Java|C语言|大数据|自然语言处理|计算机视觉'
            r'|数字图像处理|模式识别|软件工程|数据挖掘'
            r'|云计算|物联网|信息安全|嵌入式)',
            query,
        )
        return codes + cn_courses


study_expert_agent = StudyExpertAgent()
