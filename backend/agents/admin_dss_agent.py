# -*- coding: utf-8 -*-
"""教务管理 Agent —— 以决策支持系统视角，做结构化分析和一致性检查。

增强能力：
- 学分结构分析：自动统计学分分布、课程分类占比
- 一致性检查：培养目标→课程大纲→教学实施的对齐检查
- 跨专业对比：AI 专业与大数据专业的课程差异分析
- 覆盖度检测：毕业要求指标点的课程覆盖度
"""
from __future__ import annotations

from typing import Dict, List

from agents.base_agent import PerspectiveAgentBase


class AdminDSSAgent(PerspectiveAgentBase):
    """教务管理视角 Agent：数据驱动、结构分析、一致性检查、优化建议。"""

    perspective_key = 'admin'

    _ADMIN_KEYWORDS = {
        '学分', '学时', '比例', '分布', '结构', '重叠', '断层', '衔接', '对齐',
        '覆盖度', '培养目标', '毕业要求', '指标点', '课程矩阵', '一致性',
    }
    _STRUCTURE_KEYWORDS = {
        '学分', '学时', '比例', '分布', '结构', '分类', '必修', '选修',
        '通识', '专业', '实践', '理论',
    }
    _ALIGNMENT_KEYWORDS = {
        '对齐', '一致性', '覆盖', '支撑', '映射', '达成度', '检查',
        '重叠', '断层', '缺失', '冗余',
    }
    _COMPARE_KEYWORDS = {
        '对比', '比较', '差异', '区别', '共同', '大数据', '人工智能',
        '软件工程', '计算机', '专业',
    }

    def _enhance_query(self, query: str, context: str) -> str:
        hints: list[str] = []
        if any(kw in query for kw in self._STRUCTURE_KEYWORDS):
            hints.append('请用表格或数据化方式呈现学分/学时结构分析结果')
        if any(kw in query for kw in self._ALIGNMENT_KEYWORDS):
            hints.append('请检查培养目标→课程大纲→教学实施的对齐情况并标记 ⚠️')
        if any(kw in query for kw in self._COMPARE_KEYWORDS):
            hints.append('请对比不同专业的课程设置，找出差异和共性')
        if '优化' in query or '改进' in query or '建议' in query:
            hints.append('请按优先级给出可执行的改进方向')
        if not hints:
            return query
        return query + '\n（决策提示：' + '；'.join(hints) + '）'

    def _supplemental_queries(self, query: str) -> List[str]:
        """生成教务管理视角的补充检索查询。"""
        queries: list[str] = []
        # 结构分析：补充检索培养方案中的学分结构
        if any(kw in query for kw in self._STRUCTURE_KEYWORDS):
            queries.append('培养方案 学分结构 课程分类 必修选修比例')
        # 一致性检查：补充检索毕业要求和课程矩阵
        if any(kw in query for kw in self._ALIGNMENT_KEYWORDS):
            queries.append('毕业要求 指标点 课程矩阵 支撑关系')
            queries.append('课程目标 达成度 考核方式')
        # 跨专业对比：补充检索另一个专业的数据
        if any(kw in query for kw in self._COMPARE_KEYWORDS):
            if '大数据' in query:
                queries.append('人工智能专业 培养方案 课程设置')
            else:
                queries.append('大数据技术 培养方案 课程设置')
        return queries

    def _enrich_context(
        self,
        query: str,
        context: str,
        shared_sources: List[Dict],
        supplemental_sources: List[Dict],
    ) -> str:
        """教务视角上下文增强：注入结构化分析数据和课程体系信息。"""
        parts = [context] if context else []

        # 课程体系结构信息
        structure_info = self._build_curriculum_structure(query)
        if structure_info:
            parts.append(f'\n--- 课程体系结构数据 ---\n{structure_info}')

        # 覆盖度分析
        coverage_info = self._build_coverage_analysis(query)
        if coverage_info:
            parts.append(f'\n--- 毕业要求覆盖度 ---\n{coverage_info}')

        # 补充来源
        if supplemental_sources:
            parts.append(f'\n--- 教务补充数据 ---')
            for i, s in enumerate(supplemental_sources, 1):
                section = s.get('section', '')
                text = s.get('text', '')
                parts.append(f'[教务数据{i}] {section}\n{text}')

        return '\n\n'.join(parts)

    def _build_curriculum_structure(self, query: str) -> str:
        """从知识库构建课程体系结构分析数据。"""
        if not any(kw in query for kw in self._STRUCTURE_KEYWORDS | self._COMPARE_KEYWORDS):
            return ''

        kb = self._get_knowledge_base()
        if not kb:
            return ''

        lines: list[str] = []
        try:
            graph = kb.get_course_graph()
            if not graph:
                return ''

            # 统计课程分类
            categories: Dict[str, list] = {}
            total_credits = 0.0
            for cid, info in graph.items():
                cat = info.get('category', '未分类')
                categories.setdefault(cat, []).append(info)
                credits = info.get('credits', 0)
                if isinstance(credits, (int, float)):
                    total_credits += credits

            if total_credits > 0:
                lines.append(f'课程总数：{len(graph)} 门，总学分：{total_credits}')
                lines.append('课程分类统计：')
                for cat, courses in sorted(categories.items()):
                    cat_credits = sum(
                        c.get('credits', 0) for c in courses
                        if isinstance(c.get('credits', 0), (int, float))
                    )
                    pct = (cat_credits / total_credits) * 100 if total_credits else 0
                    lines.append(f'  {cat}：{len(courses)}门 / {cat_credits}学分（{pct:.1f}%）')

            # 学期分布
            semesters: Dict[str, int] = {}
            for cid, info in graph.items():
                sem = str(info.get('semester', '?'))
                semesters[sem] = semesters.get(sem, 0) + 1
            if semesters:
                lines.append('学期分布：')
                for sem in sorted(semesters.keys()):
                    lines.append(f'  第{sem}学期：{semesters[sem]}门')
        except Exception:
            return ''

        return '\n'.join(lines)

    def _build_coverage_analysis(self, query: str) -> str:
        """构建毕业要求指标点覆盖度分析。"""
        if not any(kw in query for kw in self._ALIGNMENT_KEYWORDS):
            return ''

        kb = self._get_knowledge_base()
        if not kb:
            return ''

        lines: list[str] = []
        try:
            graph = kb.get_course_graph()
            if not graph:
                return ''

            # 统计每个毕业要求被多少门课程支撑
            req_coverage: Dict[str, list] = {}
            for cid, info in graph.items():
                grad_reqs = info.get('graduation_requirements', [])
                name = info.get('name', cid)
                for req in grad_reqs:
                    req_key = str(req)
                    req_coverage.setdefault(req_key, []).append(name)

            if req_coverage:
                lines.append('毕业要求课程支撑度：')
                for req in sorted(req_coverage.keys()):
                    courses = req_coverage[req]
                    status = '✅' if len(courses) >= 2 else '⚠️'
                    lines.append(
                        f'  {status} 毕业要求{req}：{len(courses)}门课程支撑'
                        f'（{", ".join(courses[:5])}{"..." if len(courses) > 5 else ""}）'
                    )
        except Exception:
            return ''

        return '\n'.join(lines)


admin_dss_agent = AdminDSSAgent()
