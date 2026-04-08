# -*- coding: utf-8 -*-
"""规则化降级回复生成。"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .text_cleaner import text_cleaner


class ResponseGenerator:
    """当 LLM 不可用时，基于检索结果生成可读回复。"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def generate(self, query: str, context: str, sources: List[Dict]) -> str:
        """根据查询类型生成回复。"""
        if not sources or not context:
            return self.fallback(query)

        query_type = self.classify_query(query)
        dispatch = {
            'greeting': self._greeting,
            'help': self._help,
            'curriculum': lambda: self._curriculum(sources),
            'course_detail': lambda: self._course_detail(sources),
            'practice': lambda: self._practice(sources),
            'credit': lambda: self._credit(sources),
            'prerequisite': lambda: self._prerequisite(sources),
            'general': lambda: self._general(sources),
        }
        return dispatch.get(query_type, lambda: self._general(sources))()

    def classify_query(self, query: str) -> str:
        """粗粒度分类用户问题。"""
        q = query.lower()

        if any(token in q for token in ['你好', '您好', 'hello', 'hi']):
            return 'greeting'
        if any(token in q for token in ['帮助', 'help', '能做什么', '功能']):
            return 'help'
        if any(token in q for token in ['培养方案', '培养计划', '课程体系', '培养目标', '毕业要求', '学位']):
            return 'curriculum'
        if any(token in q for token in ['学分', '总学分', '必修', '选修', '学时']):
            return 'credit'
        if any(token in q for token in ['实践', '实习', '实验', '毕业设计', '毕业论文', '课程设计', '项目']):
            return 'practice'
        if any(token in q for token in ['先修', '前置', '基础课', '先学']):
            return 'prerequisite'
        if any(token in q for token in ['课程', '学什么', '教学内容', '大纲', '机器学习', '深度学习', 'python']):
            return 'course_detail'
        return 'general'

    def fallback(self, query: str) -> str:
        """无来源时的兜底回复。"""
        return (
            f'当前知识库中没有检索到能够直接支撑“{query}”的片段。\n\n'
            '建议换一种更具体的问法，例如直接说明课程名称、培养目标、学分要求或毕业环节。'
        )

    def _greeting(self) -> str:
        return (
            f'你好，我是{self.agent_name}。\n\n'
            '你可以直接询问培养方案、课程体系、学分要求、奖助学金或毕业设计相关问题。'
        )

    def _help(self) -> str:
        return (
            f'{self.agent_name}当前支持基于知识库回答以下内容：\n\n'
            '- 培养方案与毕业要求\n'
            '- 课程体系与先修关系\n'
            '- 学分结构与实践教学安排\n'
            '- 学生事务相关政策'
        )

    def _curriculum(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='围绕培养方案，当前检索结果可以归纳为以下几部分：',
            sources=sources,
            closing='如果你需要，我可以继续拆解成培养目标、毕业要求或课程结构。',
        )

    def _course_detail(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='围绕课程内容，当前检索结果可以归纳为以下信息：',
            sources=sources,
            closing='如果要继续追问某门课程的考核方式、先修要求或实践安排，可以直接补充课程名。',
        )

    def _practice(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='围绕实践教学环节，当前可以确认以下要点：',
            sources=sources,
            closing='实践安排通常会随学期或学院通知调整，最终以当期发布内容为准。',
        )

    def _credit(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='围绕学分要求，当前可以确认以下内容：',
            sources=sources,
            closing='如果你想进一步区分必修、选修或实践学分，我可以继续按模块展开。',
        )

    def _prerequisite(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='围绕先修关系，当前检索结果可以整理为：',
            sources=sources,
            closing='如果你提供具体课程名，我可以继续按学习顺序整理。',
        )

    def _general(self, sources: List[Dict]) -> str:
        return self._build_thematic_response(
            intro='根据当前检索结果，可以先确认以下信息：',
            sources=sources,
            closing='如果你希望答案更聚焦，可以继续限定主题或给出具体课程、章节名称。',
        )

    def _build_thematic_response(self, intro: str, sources: List[Dict], closing: str) -> str:
        evidence = self._collect_evidence(sources)
        if not evidence:
            return self.fallback('当前问题')

        parts = [intro.strip()]
        for section, sentences in evidence:
            bullets = text_cleaner.format_answer_markdown(sentences)
            if not bullets:
                continue
            parts.append(f'### {section}\n{bullets}')

        parts.append(closing.strip())
        return '\n\n'.join(part for part in parts if part.strip())

    def _collect_evidence(self, sources: List[Dict], limit: int = 3) -> List[Tuple[str, List[str]]]:
        evidence: List[Tuple[str, List[str]]] = []
        seen_sentences = set()

        for source in sources[:limit]:
            raw_text = str(source.get('text', ''))
            cleaned_text = text_cleaner.deep_clean_text(raw_text)
            sentences = []
            for sentence in text_cleaner.extract_key_sentences(cleaned_text, max_sentences=3):
                normalized = sentence.strip()
                if not normalized or normalized in seen_sentences:
                    continue
                seen_sentences.add(normalized)
                sentences.append(normalized)

            if not sentences:
                fallback = text_cleaner.clean_for_display(cleaned_text, max_length=160)
                if fallback and fallback not in seen_sentences:
                    seen_sentences.add(fallback)
                    sentences.append(fallback)

            if not sentences:
                continue

            section = str(source.get('section') or '相关片段').strip() or '相关片段'
            evidence.append((section, sentences))

        return evidence
