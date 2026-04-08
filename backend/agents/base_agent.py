# -*- coding: utf-8 -*-
"""
Agent 基类 - 抽取 agent.py 和 agent_v2.py 的公共逻辑
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import re
import jieba

# ---- 模块级工具函数（可在 main.py 等外部导入） ----

_SENTENCE_END_RE = re.compile(r'[。！？!?；;）)\]】」』\n]')


def trim_to_complete_sentence(text: str) -> str:
    """将文本修剪到最后一个完整句子边界，避免显示半截句子。"""
    if not text:
        return text
    if _SENTENCE_END_RE.search(text[-1]):
        return text
    matches = list(_SENTENCE_END_RE.finditer(text))
    if matches:
        return text[:matches[-1].end()]
    return text

from config import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_DESCRIPTION,
    SEARCH_TOP_K,
)


class BaseAgent(ABC):
    """Agent 公共基类，包含查询分析、上下文构建等共享逻辑"""

    # 预编译正则
    _RE_CHINESE = re.compile(r'[\u4e00-\u9fff]')
    _RE_CHINESE_WORDS = re.compile(r'[\u4e00-\u9fff]{2,4}')
    _RE_SECTION_PATTERN = re.compile(
        r'(?:第[一二三四五六七八九十]+[编章节条])|(?:第\d+[条节])'
    )
    _RE_PAGE_PATTERN = re.compile(r'(?:第?\d+\s*页)|(?:p\.\s*\d+)')

    def __init__(self):
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.description = AGENT_DESCRIPTION

        self.chapter_patterns = [
            r'第[一二三四五六七八九十]+[编章节]',
            r'第\d+[编章节]',
            r'第[一二三四五六七八九十]+[条]',
            r'第\d+[条]',
            r'安徽信息工程学院[^\n]+（实施）办法',
            r'安徽信息工程学院[^\n]+管理[办法细则条例]',
        ]
        self._compiled_chapter_patterns = [
            re.compile(p) for p in self.chapter_patterns
        ]

    @abstractmethod
    def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True,
    ) -> Dict:
        """处理用户查询，子类必须实现"""

    def _analyze_query(self, query: str) -> Dict:
        """分析查询意图和关键词"""
        keywords = [w for w in jieba.cut(query) if len(w) > 1]

        query_type = "general"
        if any(kw in query for kw in ['什么', '如何', '怎么', '怎样']):
            query_type = "how_to"
        elif any(kw in query for kw in ['是否', '能不能', '可以']):
            query_type = "yes_no"
        elif any(kw in query for kw in ['哪些', '多少', '几个']):
            query_type = "quantity"

        return {
            'keywords': keywords,
            'query_type': query_type,
            'complexity': len(keywords),
        }

    def _build_context(self, sources: List[Dict]) -> str:
        """从检索结果构建 LLM 上下文"""
        if not sources:
            return ""

        parts = []
        for i, src in enumerate(sources, 1):
            text = src.get('text', '')
            section = src.get('section', '')
            similarity = src.get('similarity', 0)
            rerank_score = src.get('rerank_score', 0)
            parts.append(f"[来源{i}] {section}")
            parts.append(f"({similarity:.2f}, rerank: {rerank_score:.2f})")
            parts.append(text)
            parts.append("")

        return '\n'.join(parts)

    def _extract_section_info(self, text: str) -> Tuple[str, str]:
        """从文本中提取章节和页码信息"""
        sections = self._RE_SECTION_PATTERN.findall(text)
        section = sections[0] if sections else ""
        pages = self._RE_PAGE_PATTERN.findall(text)
        page = pages[0] if pages else ""
        return section, page

    def _get_content_fingerprint(self, text: str) -> str:
        """获取内容指纹用于去重"""
        chinese_chars = self._RE_CHINESE.findall(text)
        chinese_part = ''.join(chinese_chars[:200])

        words = self._RE_CHINESE_WORDS.findall(text)
        word_freq: Dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        top_keywords = sorted(
            word_freq.items(), key=lambda x: x[1], reverse=True
        )[:3]
        kw_str = ''.join(k for k, _ in top_keywords)
        return chinese_part + kw_str

    def _extract_section_title(self, text: str) -> str:
        """从文本中提取章节标题"""
        for compiled in self._compiled_chapter_patterns:
            match = compiled.search(text)
            if match:
                return match.group(0)

        if text.startswith('安徽信息工程学院'):
            for line in text.split('\n')[:3]:
                if '（实施）办法' in line or '管理' in line:
                    return line[:50]
        return ''


class PerspectiveAgentBase:
    """视角 Agent 通用基类 —— 支持补充检索、上下文增强和多步推理。

    子类必须设置 ``perspective_key``，可选重写：
    - ``_enhance_query``  — 视角专属的查询改写
    - ``_retrieve_supplemental`` — 补充检索（在共享上下文之外）
    - ``_enrich_context``  — 利用工具/图谱等增强上下文
    """

    perspective_key: str = ''  # 子类必须赋值

    def __init__(self) -> None:
        from agents.perspective_prompts import PERSPECTIVE_META
        meta = PERSPECTIVE_META[self.perspective_key]
        self.name: str = meta['name']
        self.icon: str = meta['icon']
        self.tagline: str = meta['tagline']
        self.system_prompt: str = meta['system_prompt']

    # ---- 延迟加载（避免循环导入） ----

    _llm_service = None
    _knowledge_base = None
    _chroma_kb = None

    @classmethod
    def _get_llm(cls):
        if cls._llm_service is None:
            try:
                from llm_service import llm_service
                cls._llm_service = llm_service
            except ImportError:
                cls._llm_service = None
        return cls._llm_service

    @classmethod
    def _get_knowledge_base(cls):
        if cls._knowledge_base is None:
            try:
                from retrieval.knowledge_base import knowledge_base
                cls._knowledge_base = knowledge_base
            except ImportError:
                cls._knowledge_base = None
        return cls._knowledge_base

    @classmethod
    def _get_chroma_kb(cls):
        if cls._chroma_kb is None:
            try:
                from retrieval.chroma_knowledge_base import chroma_knowledge_base
                cls._chroma_kb = chroma_knowledge_base
            except ImportError:
                cls._chroma_kb = None
        return cls._chroma_kb

    # ---- 视角专属查询增强（子类可重写） ----

    def _enhance_query(self, query: str, context: str) -> str:
        """子类可重写，为 LLM 提供视角专属的查询补充说明。"""
        return query

    # ---- 文本修剪工具 ----

    @staticmethod
    def _trim_to_complete_sentence(text: str) -> str:
        return trim_to_complete_sentence(text)

    # ---- 补充检索（子类可重写） ----

    async def _retrieve_supplemental(
        self,
        query: str,
        shared_sources: List[Dict],
    ) -> List[Dict]:
        """基于视角需要执行补充检索，在共享上下文之外获取额外材料。

        默认使用 ``_supplemental_queries`` 生成的变体查询进行检索。
        子类可重写以实现更精准的视角检索策略。
        返回补充来源列表（与共享来源格式一致）。
        """
        extra_queries = self._supplemental_queries(query)
        if not extra_queries:
            return []

        import asyncio
        kb = self._get_chroma_kb() or self._get_knowledge_base()
        if not kb:
            return []

        existing_ids = {s.get('id', '') for s in shared_sources if s.get('id')}
        supplemental: List[Dict] = []

        for eq in extra_queries[:3]:  # 最多 3 条补充查询
            try:
                results = kb.search(eq, top_k=3)
                for r in results:
                    if r.get('id', '') not in existing_ids:
                        existing_ids.add(r.get('id', ''))
                        r['supplemental_query'] = eq
                        # 修剪到完整句子边界
                        if r.get('text'):
                            r['text'] = self._trim_to_complete_sentence(r['text'])
                        supplemental.append(r)
            except Exception:
                continue

        return supplemental[:6]  # 补充来源上限 6 条

    def _supplemental_queries(self, query: str) -> List[str]:
        """生成视角专属的补充检索查询。子类重写以定制。"""
        return []

    # ---- 上下文增强（子类可重写） ----

    def _enrich_context(
        self,
        query: str,
        context: str,
        shared_sources: List[Dict],
        supplemental_sources: List[Dict],
    ) -> str:
        """利用工具/图谱等在 LLM 调用前增强上下文。

        子类可重写以注入视角专属的结构化信息（如 OBE 映射、课程链等）。
        默认将补充来源追加到上下文末尾。
        """
        if not supplemental_sources:
            return context

        parts = [context] if context else []
        parts.append(f'\n--- {self.name}补充检索 ---')
        for i, s in enumerate(supplemental_sources, 1):
            section = s.get('section', '')
            text = s.get('text', '')
            parts.append(f'[补充{i}] {section}\n{text}')
        return '\n\n'.join(parts)

    # ---- 核心多步分析方法 ----

    async def analyze(
        self,
        query: str,
        context: str,
        session_history: Optional[List[Dict]] = None,
        shared_sources: Optional[List[Dict]] = None,
        enable_deep: bool = True,
    ) -> Dict:
        """多步推理流程：增强查询 → 补充检索 → 上下文增强 → LLM 生成。

        Parameters
        ----------
        query : 用户原始查询
        context : 共享 RAG 上下文（由 main.py 传入）
        session_history : 会话历史
        shared_sources : 共享检索来源（用于去重）
        enable_deep : 是否启用补充检索和上下文增强
        """
        import time as _time
        import logging as _logging
        _logger = _logging.getLogger(__name__)

        llm = self._get_llm()
        if not llm or not llm.is_available():
            return self._error_result('llm_unavailable')

        total_start = _time.time()
        steps: List[Dict] = []
        supplemental_sources: List[Dict] = []
        enriched_context = context

        # Step 1: 查询增强
        step_start = _time.time()
        enhanced_query = self._enhance_query(query, context)
        steps.append({
            'step': 'query_enhance',
            'description': '视角查询增强',
            'duration_ms': (_time.time() - step_start) * 1000,
            'output': enhanced_query if enhanced_query != query else None,
        })

        # Step 2: 补充检索（深度模式）
        if enable_deep:
            step_start = _time.time()
            try:
                supplemental_sources = await self._retrieve_supplemental(
                    query, shared_sources or [],
                )
            except Exception as exc:
                _logger.warning("%s 补充检索失败: %s", self.name, exc)
                supplemental_sources = []
            steps.append({
                'step': 'supplemental_retrieval',
                'description': '视角补充检索',
                'duration_ms': (_time.time() - step_start) * 1000,
                'output': {'count': len(supplemental_sources)},
            })

        # Step 3: 上下文增强
        if enable_deep:
            step_start = _time.time()
            enriched_context = self._enrich_context(
                query, context, shared_sources or [], supplemental_sources,
            )
            steps.append({
                'step': 'context_enrich',
                'description': '上下文增强',
                'duration_ms': (_time.time() - step_start) * 1000,
                'output': {
                    'context_length': len(enriched_context),
                    'supplemental_count': len(supplemental_sources),
                },
            })

        # Step 4: LLM 生成
        step_start = _time.time()
        try:
            response = await llm.chat(
                query=enhanced_query,
                context=enriched_context,
                history=session_history,
                system_prompt=self.system_prompt,
            )
        except Exception as exc:
            _logger.error("%sAgent 生成失败: %s", self.name, exc)
            return self._error_result(str(exc))
        steps.append({
            'step': 'llm_generate',
            'description': 'LLM 响应生成',
            'duration_ms': (_time.time() - step_start) * 1000,
        })

        return {
            'perspective': self.perspective_key,
            'name': self.name,
            'icon': self.icon,
            'tagline': self.tagline,
            'response': response or '',
            'duration_ms': (_time.time() - total_start) * 1000,
            'steps': steps,
            'supplemental_sources': [
                {
                    'id': s.get('id', ''),
                    'text': s.get('text', '')[:200],
                    'section': s.get('section', ''),
                    'similarity': s.get('similarity', 0),
                }
                for s in supplemental_sources
            ],
        }

    def _error_result(self, error: str) -> Dict:
        return {
            'perspective': self.perspective_key,
            'name': self.name,
            'icon': self.icon,
            'tagline': self.tagline,
            'response': '',
            'error': error,
        }
