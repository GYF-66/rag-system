# -*- coding: utf-8 -*-
"""Reasoning-first RAG agent used by the public chat API."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from config import (
    AGENT_DESCRIPTION,
    AGENT_NAME,
    AGENT_ROLE,
    CRAG_QUALITY_THRESHOLD_HIGH,
    CRAG_QUALITY_THRESHOLD_LOW,
    FINAL_CONTEXT_K,
    LOW_QUALITY_CHUNK_FILTER_ENABLED,
    MAX_CONTEXT_LENGTH,
    MIN_EFFECTIVE_CHUNK_LENGTH,
    QUERY_VARIANT_LIMIT,
    RERANK_CANDIDATE_K,
    SEARCH_TOP_K,
    SECTION_DIVERSITY_LIMIT,
    TOP_K_RESULTS,
)
from retrieval.knowledge_base import knowledge_base
from pipeline.query_rewriter import query_rewriter
from pipeline.reasoning_engine import reasoning_engine
from pipeline.response_generator import ResponseGenerator
from retrieval.reranker import reranker
from pipeline.text_cleaner import text_cleaner
from pipeline.hyde_enhancer import generate_hyde_document
from pipeline.adaptive_router import adaptive_router, ROUTE_SIMPLE, ROUTE_STANDARD, ROUTE_COMPLEX

try:
    from retrieval.parent_child_index import parent_child_index
except ImportError:
    parent_child_index = None

try:
    from retrieval.crag_evaluator import quality_evaluator, apply_corrections
except Exception as exc:
    logger.warning('CRAG evaluator unavailable: %s', exc)
    quality_evaluator = None
    apply_corrections = None

try:
    from retrieval.chroma_knowledge_base import chroma_knowledge_base

    CHROMADB_AVAILABLE = True
except ImportError:
    chroma_knowledge_base = None
    CHROMADB_AVAILABLE = False

try:
    from retrieval.cross_retrieval_engine import cross_retrieval_engine_improved as cross_retrieval_engine
except (ImportError, AttributeError):
    cross_retrieval_engine = None

try:
    from retrieval.hybrid_retriever import hybrid_retriever
except ImportError:
    hybrid_retriever = None

try:
    from graph.knowledge_graph import CourseKnowledgeGraph
    from graph.graph_retriever import GraphRetriever
    from config import GRAPH_RAG_ENABLED
    _graph_rag_available = GRAPH_RAG_ENABLED
except ImportError:
    _graph_rag_available = False
    CourseKnowledgeGraph = None
    GraphRetriever = None

from models import ThinkingProcess, ThinkingStep, ReflectionResult

_llm_service = None
logger = logging.getLogger(__name__)
LLM_GENERATION_TIMEOUT_SECONDS = 18.0
LLM_REFLECTION_TIMEOUT_SECONDS = 10.0


def get_llm_service():
    global _llm_service
    if _llm_service is None:
        try:
            from llm_service import get_default_llm_service
            _llm_service = get_default_llm_service()
        except ImportError:
            _llm_service = None
    return _llm_service


class AISpecialtyAgentV2:
    """Primary RAG agent for public and authenticated chat flows."""

    def __init__(self) -> None:
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.description = AGENT_DESCRIPTION
        self.use_chromadb = CHROMADB_AVAILABLE and chroma_knowledge_base is not None
        self._response_gen = ResponseGenerator(AGENT_NAME)
        self._hybrid_retriever = hybrid_retriever

        # GraphRAG 初始化
        self._graph_retriever: Optional[Any] = None
        self._knowledge_graph: Optional[Any] = None
        if _graph_rag_available and CourseKnowledgeGraph and GraphRetriever:
            try:
                self._knowledge_graph = CourseKnowledgeGraph()
                kb_data = self._load_kb_data()
                if kb_data:
                    self._knowledge_graph.build_from_knowledge_base(kb_data)
                    self._graph_retriever = GraphRetriever(self._knowledge_graph)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning('GraphRAG 初始化失败: %s', exc)

    @staticmethod
    def _load_kb_data() -> Optional[Dict[str, Any]]:
        """加载知识库 JSON 数据用于构建知识图谱"""
        import json
        from config import KNOWLEDGE_BASE_PATH
        try:
            return json.loads(KNOWLEDGE_BASE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return None

    @staticmethod
    def _build_query_rewrite_metadata(query: str, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'original_query': query,
            'normalized_query': query_analysis.get('normalized_query', query),
            'keywords': query_analysis.get('keywords', []),
            'intents': query_analysis.get('intents', []),
            'variants': query_analysis.get('variants', []),
        }

    @staticmethod
    def _build_crag_metadata(
        crag_info: Optional[Dict[str, Any]],
        *,
        route: Optional[str] = None,
    ) -> Dict[str, Any]:
        info = crag_info or {}
        details = info.get('details') or {}
        correction_info = info.get('correction') or {}
        action = info.get('action')
        if not action and route == ROUTE_SIMPLE:
            action = 'skipped'

        return {
            'mode': 'online_heuristic',
            'quality_score': info.get('quality_score'),
            'action': action,
            'details': {
                'similarity': details.get('similarity'),
                'keyword_coverage': details.get('keyword_coverage'),
                'diversity': details.get('diversity'),
                'completeness': details.get('completeness'),
                'reason': details.get('reason'),
            },
            'thresholds': {
                'low': CRAG_QUALITY_THRESHOLD_LOW,
                'high': CRAG_QUALITY_THRESHOLD_HIGH,
            },
            'correction_hints': list(info.get('correction_hints') or []),
            'correction': {
                'corrected': bool(correction_info.get('corrected')),
                'actions_taken': list(correction_info.get('actions_taken') or []),
            },
        }

    @staticmethod
    def _build_self_rag_metadata(
        reflection_result: Optional[ReflectionResult],
        *,
        evidence_count: int,
        pending: bool = False,
    ) -> Dict[str, Any]:
        if reflection_result:
            return {
                'mode': 'llm_reflection',
                'status': reflection_result.status,
                'confidence': round(reflection_result.confidence, 3),
                'issues_count': len(reflection_result.issues or []),
                'revision_applied': bool(reflection_result.revision_applied),
                'evidence_count': evidence_count,
            }

        return {
            'mode': 'llm_reflection',
            'status': 'waiting' if pending else 'skipped',
            'confidence': None,
            'issues_count': 0,
            'revision_applied': False,
            'evidence_count': evidence_count,
        }

    def _build_response_metadata(
        self,
        *,
        query: str,
        query_analysis: Dict[str, Any],
        retrieval_info: Dict[str, Any],
        sources: List[Dict[str, Any]],
        used_llm: bool,
        total_duration_ms: Optional[float] = None,
        crag_info: Optional[Dict[str, Any]] = None,
        cot_used: bool = False,
        reflection_result: Optional[ReflectionResult] = None,
        self_rag_pending: bool = False,
    ) -> Dict[str, Any]:
        return {
            'retrieval_method': retrieval_info.get('method', 'tfidf'),
            'retrieval_variant_count': retrieval_info.get('variant_count', 1),
            'retrieval_variants': retrieval_info.get('query_variants', query_analysis.get('variants', [])),
            'query_rewrite': self._build_query_rewrite_metadata(query, query_analysis),
            'rerank_method': 'cross_encoder' if reranker and reranker.use_cross_encoder else 'rule_based',
            'adaptive_route': retrieval_info.get('route', 'standard'),
            'is_cross_query': retrieval_info.get('is_cross_query', False),
            'used_llm': used_llm,
            'source_count': len(sources),
            'total_duration_ms': total_duration_ms,
            'crag_evaluation': self._build_crag_metadata(
                crag_info,
                route=retrieval_info.get('route', ROUTE_STANDARD),
            ),
            'hyde_used': retrieval_info.get('hyde_used', False),
            'graph_rag_used': self._graph_retriever is not None,
            'cot_used': cot_used,
            'self_rag_reflection': reflection_result.status if reflection_result else None,
            'self_rag': self._build_self_rag_metadata(
                reflection_result,
                evidence_count=min(len(sources), 5),
                pending=self_rag_pending,
            ),
        }

    async def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict[str, Any]]] = None,
        use_rag: bool = True,
        enable_thinking: bool = True,
    ) -> Dict[str, Any]:
        total_start = time.time()

        analysis_start = time.time()
        query_analysis = self._analyze_query(query)
        analysis_duration = (time.time() - analysis_start) * 1000

        retrieval_start = time.time()
        sources, retrieval_info = await self._retrieve_sources(query, use_rag, query_analysis)

        # CRAG 纠错检索: 仅对 standard/complex 路由启用
        crag_info: Dict[str, Any] = {}
        adaptive_k = query_analysis.get('adaptive_top_k', SEARCH_TOP_K)
        route = retrieval_info.get('route', ROUTE_STANDARD)
        if quality_evaluator and sources and route != ROUTE_SIMPLE:
            crag_eval = quality_evaluator.evaluate(query, sources, query_analysis)
            crag_info = crag_eval
            if crag_eval.get('action') != 'accept' and apply_corrections:
                retriever = self._hybrid_retriever or (chroma_knowledge_base if self.use_chromadb else knowledge_base)
                sources, correction_result = apply_corrections(
                    query, sources, crag_eval, retriever=retriever, top_k=adaptive_k,
                )
                crag_info['correction'] = correction_result

        sources = self._prepare_sources(query, sources, query_analysis)
        context = self._build_context(sources)
        # 课程图谱增强：为课程关系类查询注入结构化图谱上下文
        graph_supplement, graph_context = self._build_course_graph_supplement(query, query_analysis)
        if graph_supplement:
            context = f"{context}\n\n{graph_supplement}" if context else graph_supplement
        retrieval_duration = (time.time() - retrieval_start) * 1000

        reasoning_start = time.time()
        reasoning_steps = []
        if enable_thinking:
            reasoning_steps = [
                {
                    'description': f"基于 {len(sources)} 个来源片段整理上下文并生成回答。"
                },
                {
                    'description': (
                        f"检索策略：{retrieval_info.get('method', 'unknown')}，"
                        f"查询变体：{retrieval_info.get('variant_count', 1)} 个。"
                    )
                },
                {
                    'description': (
                        '改写关键词：' + (', '.join(query_analysis.get('keywords', [])[:6]) or '未识别')
                    )
                },
            ]
            if query_analysis.get('intents'):
                reasoning_steps.append(
                    {
                        'description': '意图识别：' + ', '.join(query_analysis.get('intents', []))
                    }
                )
            if reasoning_engine and hasattr(reasoning_engine, 'analyze_query'):
                reasoning_steps.append(
                    {
                        'description': f"标准化查询：{query_analysis.get('normalized_query', query)}"
                    }
                )
        reasoning_duration = (time.time() - reasoning_start) * 1000

        generation_start = time.time()
        response = ''
        cot_reasoning = ''
        used_llm = False
        llm = get_llm_service()
        if llm and llm.is_available():
            try:
                # CoT 增强：使用带推理引导的 system prompt
                cot_prompt = self._build_cot_system_prompt(query_analysis, sources)
                raw_response = await asyncio.wait_for(
                    llm.chat(query, context, session_history, system_prompt=cot_prompt),
                    timeout=LLM_GENERATION_TIMEOUT_SECONDS,
                )
                if raw_response:
                    response, cot_reasoning = self._parse_cot_response(raw_response)
                    used_llm = True
            except asyncio.TimeoutError:
                logger.warning('LLM generation timed out, falling back to evidence-only response.')
                response = ''
            except Exception as exc:
                logger.warning('LLM generation failed, falling back to evidence-only response: %s', exc)
                response = ''

        if not response:
            response = self._response_gen.generate(query, context, sources)
        generation_duration = (time.time() - generation_start) * 1000

        # Self-RAG 反思验证：检查回答与来源一致性
        reflection_start = time.time()
        reflection_result = None
        reflection_step = None
        if enable_thinking and used_llm and sources and llm and llm.is_available():
            try:
                reflection_result, revised_response = await asyncio.wait_for(
                    self._self_rag_reflect(query, response, sources, llm),
                    timeout=LLM_REFLECTION_TIMEOUT_SECONDS,
                )
                if reflection_result.revision_applied and revised_response:
                    response = revised_response
            except asyncio.TimeoutError:
                logger.warning('Self-RAG reflection timed out, keeping the current answer.')
            except Exception as exc:
                logger.warning('Self-RAG reflection failed, keeping the current answer: %s', exc)
                pass
        reflection_duration = (time.time() - reflection_start) * 1000

        thinking_process = None
        if enable_thinking:
            thinking_process = self._build_thinking_process(
                query_analysis,
                sources,
                reasoning_steps,
                [analysis_duration, retrieval_duration, reasoning_duration, generation_duration, reflection_duration],
                retrieval_info,
                crag_info,
                cot_reasoning=cot_reasoning,
                reflection_result=reflection_result,
            )

        total_duration_ms = (time.time() - total_start) * 1000

        return {
            'response': response,
            'sources': sources,
            'thinking_process': thinking_process,
            'cross_reasoning': retrieval_info.get('cross_reasoning'),
            'is_cross_query': retrieval_info.get('is_cross_query', False),
            'used_llm': used_llm,
            'graph_context': graph_context,
            'metadata': self._build_response_metadata(
                query=query,
                query_analysis=query_analysis,
                retrieval_info=retrieval_info,
                sources=sources,
                used_llm=used_llm,
                total_duration_ms=total_duration_ms,
                crag_info=crag_info,
                cot_used=bool(cot_reasoning),
                reflection_result=reflection_result,
            ),
        }

    async def _retrieve_sources(
        self,
        query: str,
        use_rag: bool,
        query_analysis: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not use_rag:
            return [], {'method': 'disabled', 'variant_count': 0, 'is_cross_query': False, 'query_variants': []}

        # 动态 Top-K: 根据查询复杂度自适应
        adaptive_k = query_analysis.get('adaptive_top_k', SEARCH_TOP_K)

        # Adaptive-RAG 路由: 按查询复杂度选择检索策略
        route = adaptive_router.classify(query, query_analysis)

        if cross_retrieval_engine:
            loop = asyncio.get_running_loop()
            cross_result = await loop.run_in_executor(None, cross_retrieval_engine.process_cross_query, query)
            if cross_result and cross_result.get('is_cross_query'):
                return cross_result.get('final_documents', []), {
                    'method': 'cross_retrieval',
                    'variant_count': len(query_analysis.get('variants', [])) or 1,
                    'query_variants': query_analysis.get('variants', []),
                    'is_cross_query': True,
                    'cross_reasoning': cross_result.get('thinking_content'),
                    'route': route,
                }

        # --- simple 路由: 仅单路检索, 跳过 HyDE/CRAG ---
        if route == ROUTE_SIMPLE:
            if self.use_chromadb:
                sources = chroma_knowledge_base.search(query, top_k=adaptive_k)
            elif self._hybrid_retriever is not None:
                sources = self._hybrid_retriever.search(query, top_k=adaptive_k)
            else:
                sources = knowledge_base.search(query, top_k=adaptive_k)
            return sources, {
                'method': 'simple_direct',
                'variant_count': 1,
                'query_variants': [],
                'is_cross_query': False,
                'cross_reasoning': None,
                'hyde_used': False,
                'route': route,
            }

        # --- standard/complex 路由: 混合检索, complex 额外启用 HyDE ---
        use_hyde = (route == ROUTE_COMPLEX)

        hyde_sources: List[Dict[str, Any]] = []
        hyde_doc = await generate_hyde_document(query) if use_hyde else None

        if self._hybrid_retriever is not None:
            hybrid_sources = self._hybrid_retriever.search(query, top_k=adaptive_k)
            # HyDE 补充检索: 用假设性文档做第二路召回
            if hyde_doc:
                try:
                    hyde_sources = self._hybrid_retriever.search(hyde_doc[:500], top_k=max(adaptive_k // 2, 3))
                except Exception:
                    hyde_sources = []
            merged = self._merge_hyde_results(hybrid_sources, hyde_sources)
            if merged:
                matched_queries = set(query_analysis.get('variants', []))
                for source in merged:
                    matched_queries.update(source.get('matched_queries', []))
                return merged, {
                    'method': 'hybrid_rrf' + ('+hyde' if hyde_sources else ''),
                    'variant_count': len(matched_queries) or 1,
                    'query_variants': list(matched_queries)[:6],
                    'is_cross_query': False,
                    'cross_reasoning': None,
                    'hyde_used': bool(hyde_sources),
                    'route': route,
                }

        if self.use_chromadb:
            sources = chroma_knowledge_base.search(query, top_k=adaptive_k)
            if hyde_doc:
                try:
                    hyde_sources = chroma_knowledge_base.search(hyde_doc[:500], top_k=max(adaptive_k // 2, 3))
                except Exception:
                    hyde_sources = []
            merged = self._merge_hyde_results(sources, hyde_sources)
            return merged, {
                'method': 'chromadb' + ('+hyde' if hyde_sources else ''),
                'variant_count': len(query_analysis.get('variants', [])) or 1,
                'query_variants': query_analysis.get('variants', []),
                'is_cross_query': False,
                'cross_reasoning': None,
                'hyde_used': bool(hyde_sources),
                'route': route,
            }
        tfidf_sources = knowledge_base.search(query, top_k=adaptive_k)
        if hyde_doc:
            try:
                hyde_sources = knowledge_base.search(hyde_doc[:500], top_k=max(adaptive_k // 2, 3))
            except Exception:
                hyde_sources = []
        merged = self._merge_hyde_results(tfidf_sources, hyde_sources) if hyde_sources else tfidf_sources
        return merged, {
            'method': 'tfidf' + ('+hyde' if hyde_sources else ''),
            'variant_count': len(query_analysis.get('variants', [])) or 1,
            'query_variants': query_analysis.get('variants', []),
            'is_cross_query': False,
            'cross_reasoning': None,
            'hyde_used': bool(hyde_sources),
            'route': route,
        }

    def _merge_hyde_results(
        self,
        primary: List[Dict[str, Any]],
        hyde: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """将原始检索结果和 HyDE 检索结果通过简单 RRF 融合。"""
        if not hyde:
            return primary

        scored: Dict[str, Dict[str, Any]] = {}
        for rank, doc in enumerate(primary):
            doc_id = doc.get('id') or doc.get('text', '')[:120]
            scored[doc_id] = dict(doc)
            scored[doc_id]['rrf_score'] = scored[doc_id].get('rrf_score', 0.0) + 1.0 / (60 + rank + 1)
            scored[doc_id]['_source'] = 'primary'

        for rank, doc in enumerate(hyde):
            doc_id = doc.get('id') or doc.get('text', '')[:120]
            if doc_id in scored:
                # 两路都命中的文档获得 HyDE 加成
                scored[doc_id]['rrf_score'] += 0.6 / (60 + rank + 1)
                scored[doc_id]['_source'] = 'both'
            else:
                entry = dict(doc)
                entry['rrf_score'] = 0.4 / (60 + rank + 1)
                entry['_source'] = 'hyde'
                scored[doc_id] = entry

        merged = sorted(scored.values(), key=lambda x: x.get('rrf_score', 0), reverse=True)
        for item in merged:
            item.pop('_source', None)
        return merged

    def _prepare_sources(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not sources:
            return []

        # 父子文档扩展：将子块命中扩展为父块完整上下文
        if parent_child_index and parent_child_index.parent_count > 0:
            has_children = any((s.get('metadata') or {}).get('is_child_chunk') for s in sources)
            if has_children:
                sources = parent_child_index.expand_to_parents(sources)

        analysis = query_analysis or self._analyze_query(query)
        query_terms = [keyword for keyword in analysis.get('keywords', []) if len(keyword) >= 2]
        normalized: List[Dict[str, Any]] = []
        for source in sources:
            if not source.get('text'):
                continue
            normalized_source = self._normalize_source(source, query_terms)
            if normalized_source:
                normalized.append(normalized_source)

        if reranker and normalized:
            preranked = sorted(normalized, key=lambda item: item.get('rerank_score', item.get('similarity', 0.0)), reverse=True)
            reranked = reranker.rerank(query, preranked[:RERANK_CANDIDATE_K], top_k=RERANK_CANDIDATE_K)
            if len(preranked) > RERANK_CANDIDATE_K:
                reranked.extend(preranked[RERANK_CANDIDATE_K:])
            normalized = reranked

        deduped: List[Dict[str, Any]] = []
        seen_keys = set()
        section_counts: Dict[str, int] = {}
        for source in normalized:
            dedupe_key = source['id'] or source['text'][:120]
            if dedupe_key in seen_keys:
                continue
            section_key = str(source.get('section') or '').strip().lower()
            if section_key:
                current_count = section_counts.get(section_key, 0)
                if current_count >= SECTION_DIVERSITY_LIMIT:
                    continue
                section_counts[section_key] = current_count + 1
            seen_keys.add(dedupe_key)
            deduped.append(source)
            if len(deduped) >= max(FINAL_CONTEXT_K, TOP_K_RESULTS):
                break

        return deduped

    def _normalize_source(self, source: Dict[str, Any], query_terms: List[str]) -> Optional[Dict[str, Any]]:
        raw_text = str(source.get('text', '')).strip()
        text = text_cleaner.clean_for_query(raw_text, query_terms, max_length=420)
        if not text or text_cleaner.is_metadata_or_noise(text):
            return None
        if LOW_QUALITY_CHUNK_FILTER_ENABLED and self._is_low_quality_chunk(text, source):
            return None

        similarity = float(source.get('similarity') or 0.0)
        rerank_score = float(source.get('rerank_score') or similarity)
        metadata = dict(source.get('metadata') or {})
        section = str(source.get('section') or source.get('title') or metadata.get('section') or '知识片段').strip()
        section = text_cleaner.extract_main_content(section) or section
        return {
            'id': str(source.get('id', '')),
            'text': text,
            'char_count': int(source.get('char_count') or len(text)),
            'similarity': similarity,
            'rerank_score': rerank_score,
            'section': section,
            'metadata': metadata,
        }

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        rewrite = query_rewriter.rewrite(query, max_variants=QUERY_VARIANT_LIMIT)
        intents = list(rewrite.get('intents', []))
        query_type = intents[0] if intents else 'general'
        keywords = list(rewrite.get('keywords', []))
        complexity = self._estimate_complexity(query, keywords, intents)

        return {
            'normalized_query': rewrite.get('normalized_query', query),
            'keywords': keywords,
            'variants': list(rewrite.get('variants', [])),
            'intents': intents,
            'intent_confidence': dict(rewrite.get('intent_confidence', {})),
            'query_category': rewrite.get('query_category', 'general'),
            'query_type': query_type,
            'complexity': complexity,
            'adaptive_top_k': self._adaptive_top_k(complexity),
        }

    def _estimate_complexity(
        self, query: str, keywords: List[str], intents: List[str]
    ) -> int:
        """估算查询复杂度 (1-5 量级)。"""
        score = 1

        # 多意图
        if len(intents) >= 2:
            score += 1
        # 关键词多
        if len(keywords) >= 4:
            score += 1
        # 查询长度
        if len(query) >= 30:
            score += 1
        # 包含比较/对比/关系类词汇
        compare_hints = ('比较', '区别', '关系', '异同', '优缺点', '对比', '以及', '还有')
        if any(h in query for h in compare_hints):
            score += 1

        return min(score, 5)

    @staticmethod
    def _adaptive_top_k(complexity: int) -> int:
        """根据复杂度动态调整 top_k。"""
        mapping = {
            1: 4,   # 简单查询
            2: 5,
            3: 6,   # 中等复杂
            4: 8,
            5: 10,  # 高复杂度
        }
        return mapping.get(complexity, SEARCH_TOP_K)

    # -- 课程图谱注入 ----------------------------------------------------------

    _COURSE_CHAIN_HINTS = (
        '后续课程', '先修课程', '课程链', '学习路径', '先导课', '前置课程',
        '课程关系', '课程衔接', '课程顺序', '之后学', '之前学', '后面学',
        '前面学', '需要先学', '学完之后',
    )

    def _build_course_graph_supplement(
        self, query: str, query_analysis: Dict[str, Any]
    ) -> tuple:
        """当查询涉及课程关系时，从课程图谱构建补充上下文。
        返回 (supplement_text, graph_context_dict)。
        """
        keywords = query_analysis.get('keywords', [])
        intents = query_analysis.get('intents', [])

        # ── GraphRAG 增强路径（优先） ──────────────────────────────────
        if self._graph_retriever:
            graph_results = self._graph_retriever.search(
                query, top_k=3, keywords=keywords,
            )
            if graph_results:
                graph_texts = [r['text'] for r in graph_results if r.get('text')]
                if graph_texts:
                    # 构建结构化图谱上下文
                    graph_context = self._extract_graph_context(query, keywords)
                    return '\n\n'.join(graph_texts), graph_context

        # ── 降级：原始静态图谱逻辑 ────────────────────────────────────
        is_chain_query = 'course_chain' in intents or any(h in query for h in self._COURSE_CHAIN_HINTS)
        matched_courses = knowledge_base.find_courses_by_name(keywords)
        if not matched_courses and not is_chain_query:
            return '', None

        graph = knowledge_base.get_course_graph()
        if not graph:
            return '', None

        parts: List[str] = []

        for course in matched_courses:
            code = course.get('code', '')
            name = course.get('name', '')
            semester = course.get('semester', '?')

            prereq_names = []
            for pid in course.get('prerequisites', []):
                entry = graph.get(pid)
                if entry:
                    prereq_names.append(f"{entry.get('name', pid)}({entry.get('code', '')})")
            leads_names = []
            for lid in course.get('leads_to', []):
                entry = graph.get(lid)
                if entry:
                    leads_names.append(f"{entry.get('name', lid)}({entry.get('code', '')})")

            block = f"[课程图谱] {code} {name}（第{semester}学期）"
            if prereq_names:
                block += f"\n  先修课程：{'、'.join(prereq_names)}"
            else:
                block += "\n  先修课程：无（入门课程）"
            if leads_names:
                block += f"\n  后续课程：{'、'.join(leads_names)}"
            else:
                block += "\n  后续课程：无（终端课程）"

            concepts = course.get('knowledge_concepts', [])
            if concepts:
                block += f"\n  核心知识点：{'、'.join(concepts[:6])}"
            parts.append(block)

        if is_chain_query and not matched_courses:
            overview_lines = []
            for _doc_id, entry in graph.items():
                name = entry.get('name', '')
                code = entry.get('code', '')
                sem = entry.get('semester', '?')
                leads = []
                for lid in entry.get('leads_to', []):
                    le = graph.get(lid)
                    if le:
                        leads.append(le.get('name', lid))
                if leads:
                    overview_lines.append(f"  {code} {name}(第{sem}学期) → {'、'.join(leads)}")
            if overview_lines:
                parts.append("[课程衔接全景]\n" + '\n'.join(overview_lines))

        return '\n\n'.join(parts), None

    def _extract_graph_context(
        self, query: str, keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """从知识图谱中提取结构化图谱上下文，用于前端展示。"""
        if not self._knowledge_graph or not self._knowledge_graph.is_built:
            return None

        try:
            subgraph = self._knowledge_graph.search_subgraph(
                query_keywords=keywords if keywords else query.split(),
                max_hops=1,
                max_nodes=15,
            )
            if not subgraph or not subgraph.get('nodes'):
                return None

            node_label_map: Dict[str, str] = {}
            related_courses = []
            related_concepts = []
            for node in subgraph.get('nodes', []):
                nid = node.get('id', '')
                label = node.get('label') or node.get('name', '')
                node_label_map[nid] = label
                if node.get('type') == 'course':
                    related_courses.append({
                        'name': label,
                        'code': node.get('code', ''),
                        'semester': node.get('semester'),
                    })
                elif node.get('type') == 'concept':
                    if label:
                        related_concepts.append(label)

            relationships = []
            for edge in subgraph.get('edges', [])[:10]:
                src = edge.get('source', '')
                tgt = edge.get('target', '')
                relationships.append({
                    'source': node_label_map.get(src, src),
                    'target': node_label_map.get(tgt, tgt),
                    'type': edge.get('type', ''),
                })

            return {
                'related_courses': related_courses[:8],
                'related_concepts': related_concepts[:12],
                'relationships': relationships,
                'node_count': len(subgraph.get('nodes', [])),
                'edge_count': len(subgraph.get('edges', [])),
            }
        except Exception:
            return None

    def _build_context(self, sources: List[Dict[str, Any]]) -> str:
        if not sources:
            return ''

        merged_sources = self._merge_context_sources(sources[: max(FINAL_CONTEXT_K * 2, FINAL_CONTEXT_K)])
        remaining = MAX_CONTEXT_LENGTH
        context_parts: List[str] = []
        for index, source in enumerate(merged_sources[:FINAL_CONTEXT_K], start=1):
            metadata = dict(source.get('metadata') or {})
            page_label = ''
            if metadata.get('page_start'):
                page_label = f" / 页码 p.{metadata.get('page_start')}"
                if metadata.get('page_end') and metadata.get('page_end') != metadata.get('page_start'):
                    page_label = f" / 页码 p.{metadata.get('page_start')}-{metadata.get('page_end')}"
            title = str(metadata.get('title') or metadata.get('document_id') or '未知来源').strip()
            section = str(source.get('section', '知识片段')).strip()
            header = f"[证据{index}] 来源：{title} / 章节：{section}{page_label}"
            text = self._summarize_context_text(str(source.get('text', '')))
            if remaining <= len(header):
                break
            room_for_text = remaining - len(header) - 2
            snippet = text[: max(room_for_text, 0)]
            block = f"{header}\n{snippet}".strip()
            context_parts.append(block)
            remaining -= len(block) + 2
            if remaining <= 0:
                break

        return '\n\n'.join(context_parts)

    def _is_low_quality_chunk(self, text: str, source: Dict[str, Any]) -> bool:
        cleaned = (text or '').strip()
        metadata = dict(source.get('metadata') or {})
        if metadata.get('chunk_quality_status') == 'reject':
            return True
        if float(metadata.get('chunk_quality_score') or 1.0) < 0.30:
            return True
        if len(cleaned) < MIN_EFFECTIVE_CHUNK_LENGTH:
            return True
        section = str(source.get('section') or (source.get('metadata') or {}).get('section') or '').strip()
        if section and cleaned == section:
            return True
        punctuation_ratio = sum(1 for char in cleaned if char in '，。；：,.?!！？、/ ') / max(len(cleaned), 1)
        return punctuation_ratio > 0.55 and len(set(cleaned)) < 18

    def _merge_context_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        for source in sources:
            if not merged:
                merged.append(source)
                continue
            previous = merged[-1]
            if self._can_merge_context_source(previous, source):
                combined_text = f"{previous.get('text', '').rstrip()} {source.get('text', '').lstrip()}".strip()
                previous['text'] = combined_text
                previous['char_count'] = len(combined_text)
                continue
            merged.append(source)
        return merged

    def _can_merge_context_source(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        left_meta = dict(left.get('metadata') or {})
        right_meta = dict(right.get('metadata') or {})
        same_section = str(left.get('section') or '').strip() == str(right.get('section') or '').strip()
        same_doc = str(left_meta.get('title') or left_meta.get('document_id') or '').strip() == str(
            right_meta.get('title') or right_meta.get('document_id') or ''
        ).strip()
        if not (same_section and same_doc):
            return False
        combined_len = len(str(left.get('text') or '')) + len(str(right.get('text') or ''))
        return combined_len <= 520

    def _summarize_context_text(self, text: str) -> str:
        cleaned = ' '.join((text or '').split())
        if not cleaned:
            return ''
        # 移除 Contextual Retrieval 注入的前缀（以"。\n\n"分隔）
        if '。\n\n' in cleaned:
            parts = cleaned.split('。\n\n', 1)
            if len(parts) == 2 and parts[0].startswith('本段来自：'):
                cleaned = parts[1]
        cleaned = ' '.join(cleaned.split())
        if len(cleaned) <= 220 and cleaned.endswith(('。', '！', '？', '.', ';', '；')):
            return cleaned

        sentence_candidates = re.split(r'(?<=[。！？；.!?;])', cleaned)
        summary = ''
        for sentence in sentence_candidates:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(summary) + len(sentence) > 220:
                break
            summary += sentence
        if summary:
            return summary
        truncated = cleaned[:220].rstrip('，,；;：:、 ')
        if truncated and truncated[-1] not in '。！？.!?；;':
            truncated += '。'
        return truncated

    # ── CoT + Self-RAG 方法 ──────────────────────────────────

    @staticmethod
    def _build_cot_system_prompt(
        query_analysis: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> str:
        """构建带 Chain-of-Thought 推理引导的系统提示词"""
        complexity = query_analysis.get('complexity', 3)
        keywords = ', '.join(query_analysis.get('keywords', [])[:5]) or '无'
        source_count = len(sources)

        return (
            '你是安徽信息工程学院人工智能专业的资深问答助手。\n'
            '请严格按照以下步骤进行推理，然后给出最终回答：\n\n'
            '<thinking>\n'
            '第一步：理解问题 — 明确用户的核心问题和子问题\n'
            '第二步：筛选证据 — 从参考资料中找出直接相关的信息\n'
            '第三步：逻辑推理 — 基于证据进行分析，建立因果链\n'
            '第四步：综合回答 — 整合推理结果，形成完整回答\n'
            '</thinking>\n\n'
            '<answer>\n'
            '在此输出最终回答\n'
            '</answer>\n\n'
            '注意事项：\n'
            f'- 当前问题复杂度：{complexity}/5，关键词：{keywords}\n'
            f'- 共有 {source_count} 个参考片段，请只使用相关片段\n'
            '- 如果参考资料不足以完整回答，请明确说明不确定的部分\n'
            '- 先输出 <thinking> 推理过程，再输出 <answer> 最终回答\n'
            '- 回答使用中文，条理清晰'
        )

    @staticmethod
    def _parse_cot_response(raw: str) -> Tuple[str, str]:
        """解析 CoT 响应，提取推理过程和最终回答"""
        thinking = ''
        answer = ''

        # 提取 <thinking>...</thinking>
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw, re.DOTALL)
        if thinking_match:
            thinking = thinking_match.group(1).strip()

        # 提取 <answer>...</answer>
        answer_match = re.search(r'<answer>(.*?)</answer>', raw, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()

        # 如果 LLM 未遵循格式，整段作为回答
        if not answer:
            # 移除可能的 thinking 标签，剩余部分作为回答
            cleaned = re.sub(r'</?thinking>', '', raw).strip()
            cleaned = re.sub(r'</?answer>', '', cleaned).strip()
            answer = cleaned

        return answer, thinking

    async def _self_rag_reflect(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        llm: Any,
    ) -> Tuple[ReflectionResult, Optional[str]]:
        """Self-RAG 反思：验证回答与来源一致性"""
        # 构建精简证据摘要
        evidence_snippets = []
        for i, src in enumerate(sources[:5], 1):
            text = src.get('text', '')[:200]
            evidence_snippets.append(f'[证据{i}] {text}')
        evidence_text = '\n'.join(evidence_snippets)

        reflect_prompt = (
            '你是一个严格的事实核查员。请验证以下回答是否与提供的证据一致。\n\n'
            f'## 用户问题\n{query}\n\n'
            f'## 待验证回答\n{response[:500]}\n\n'
            f'## 参考证据\n{evidence_text}\n\n'
            '请按以下格式输出（每行一项）：\n'
            'STATUS: supported 或 partially_supported 或 not_supported\n'
            'CONFIDENCE: 0.0-1.0 的置信度\n'
            'ISSUES: 问题列表（没有问题则写"无"）\n'
        )

        reflect_start = time.time()
        try:
            result_text = await llm.chat(
                reflect_prompt, '', system_prompt='你是事实核查助手，只输出指定格式，不做额外解释。',
            )
            reflect_duration = (time.time() - reflect_start) * 1000

            status, confidence, issues = self._parse_reflection(result_text)
            revised_response = None
            revision_applied = False

            if status in ('partially_supported', 'not_supported'):
                revised_response = await self._revise_response_with_evidence(
                    query=query,
                    response=response,
                    evidence_text=evidence_text,
                    issues=issues,
                    llm=llm,
                )
                if revised_response and revised_response.strip() and revised_response.strip() != response.strip():
                    revision_applied = True

            reflection = ReflectionResult(
                status=status,
                confidence=confidence,
                issues=issues,
                revision_applied=revision_applied,
                duration_ms=reflect_duration,
            )
            return reflection, revised_response if revision_applied else None

        except Exception:
            return ReflectionResult(
                status='skipped',
                confidence=0.0,
                duration_ms=(time.time() - reflect_start) * 1000,
            ), None

    @staticmethod
    def _parse_reflection(text: str) -> Tuple[str, float, List[str]]:
        """解析反思结果"""
        status = 'partially_supported'
        confidence = 0.5
        issues: List[str] = []

        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith('STATUS:'):
                val = line.split(':', 1)[1].strip().lower()
                if val in ('supported', 'partially_supported', 'not_supported'):
                    status = val
            elif line.upper().startswith('CONFIDENCE:'):
                try:
                    confidence = max(0.0, min(1.0, float(line.split(':', 1)[1].strip())))
                except ValueError:
                    pass
            elif line.upper().startswith('ISSUES:'):
                val = line.split(':', 1)[1].strip()
                if val and val != '无':
                    issues = [s.strip() for s in val.split('；') if s.strip()]
                    if not issues:
                        issues = [s.strip() for s in val.split(';') if s.strip()]
                    if not issues and val:
                        issues = [val]

        return status, confidence, issues

    async def _revise_response_with_evidence(
        self,
        query: str,
        response: str,
        evidence_text: str,
        issues: List[str],
        llm: Any,
    ) -> Optional[str]:
        """基于反思结果按证据约束生成修正版回答。"""
        issues_text = '；'.join(issues) if issues else '请重点删除缺乏证据支撑的表述。'
        revise_prompt = (
            '你是一个教学问答修订助手。请根据用户问题、原始回答和参考证据，'
            '输出一个更严格受证据约束的修正版回答。\n\n'
            f'## 用户问题\n{query}\n\n'
            f'## 原始回答\n{response[:900]}\n\n'
            f'## 需要修正的问题\n{issues_text}\n\n'
            f'## 参考证据\n{evidence_text}\n\n'
            '修订要求：\n'
            '1. 仅保留有证据支撑的信息。\n'
            '2. 对证据不足的内容要明确说明“资料未明确说明”或“当前证据不足”。\n'
            '3. 保持中文、结构清晰、适合教学导学场景。\n'
            '4. 只输出修订后的最终回答，不要解释修订过程。\n'
        )

        try:
            revised = await llm.chat(
                revise_prompt,
                '',
                system_prompt='你是证据约束的答案修订助手，只输出修订后的最终回答。',
            )
            cleaned = (revised or '').strip()
            return cleaned or None
        except Exception:
            return None

    def _build_thinking_process(
        self,
        query_analysis: Dict[str, Any],
        sources: List[Dict[str, Any]],
        reasoning_steps: List[Dict[str, Any]],
        durations: List[float],
        retrieval_info: Optional[Dict[str, Any]] = None,
        crag_info: Optional[Dict[str, Any]] = None,
        cot_reasoning: str = '',
        reflection_result: Optional[ReflectionResult] = None,
    ) -> ThinkingProcess:
        retrieval_info = retrieval_info or {}
        crag_info = crag_info or {}
        route = retrieval_info.get('route', 'standard')
        route_labels = {'simple': '简单直检', 'standard': '标准混合', 'complex': '完整管线'}

        query_step = ThinkingStep(
            step_id=1,
            step_name='问题理解',
            description='规范化问题、识别意图并选择检索策略',
            input_data={'query': query_analysis.get('normalized_query')},
            output_data={
                'query_type': query_analysis.get('query_type'),
                'complexity': query_analysis.get('complexity'),
                'adaptive_route': route,
                'variants': query_analysis.get('variants', []),
            },
            reasoning=(
                f"识别为 {query_analysis.get('query_type')} 问题（复杂度 {query_analysis.get('complexity', '?')}），"
                f"路由至 [{route_labels.get(route, route)}] 管线。"
                f"关键词：{', '.join(query_analysis.get('keywords', [])) or '无'}"
            ),
            duration_ms=durations[0],
        )

        method = retrieval_info.get('method', 'unknown')
        hyde_used = retrieval_info.get('hyde_used', False)
        retrieval_desc = f"检索方法：{method}"
        if hyde_used:
            retrieval_desc += "（含 HyDE 假设文档生成）"

        retrieval_step = ThinkingStep(
            step_id=2,
            step_name='证据检索',
            description=f'路由={route} → {method}',
            input_data={'top_k': SEARCH_TOP_K, 'route': route},
            output_data={'retrieved_count': len(sources), 'hyde_used': hyde_used},
            reasoning=f"{retrieval_desc}，共保留 {len(sources)} 个高相关片段。",
            duration_ms=durations[1],
        )
        crag_score = crag_info.get('quality_score')
        crag_action = crag_info.get('action', 'skipped' if route == 'simple' else 'none')
        rerank_reasoning = f"最终向模型提供 {len(sources[:TOP_K_RESULTS])} 个来源片段。"
        if crag_score is not None:
            rerank_reasoning += f" CRAG 质量={crag_score:.2f}（{crag_action}）。"
        elif route == 'simple':
            rerank_reasoning += " CRAG 评估已跳过（简单查询直检模式）。"

        rerank_step = ThinkingStep(
            step_id=3,
            step_name='上下文整理',
            description='去重、重排、证据一致性检查并裁剪上下文',
            input_data={'context_budget': MAX_CONTEXT_LENGTH},
            output_data={'final_count': len(sources[:TOP_K_RESULTS]), 'crag_score': crag_score, 'crag_action': crag_action},
            reasoning=rerank_reasoning,
            duration_ms=durations[2],
        )

        # CoT 推理步骤：如果有真实的 LLM 推理链，优先使用
        if cot_reasoning:
            generation_reasoning = cot_reasoning
        elif reasoning_steps:
            generation_reasoning = '\n'.join(
                step.get('description', '') for step in reasoning_steps if step.get('description')
            ) or '未启用额外推理步骤。'
        else:
            generation_reasoning = '未启用额外推理步骤。'

        reasoning_step = ThinkingStep(
            step_id=4,
            step_name='回答生成',
            description='基于证据组织回答并输出推理摘要',
            input_data={'source_count': len(sources), 'cot_enabled': bool(cot_reasoning)},
            output_data={'reasoning_steps': len(reasoning_steps), 'cot_used': bool(cot_reasoning)},
            reasoning=generation_reasoning,
            duration_ms=durations[3],
        )

        # Self-RAG 反思步骤
        reflection_step = None
        if reflection_result and reflection_result.status != 'skipped':
            status_labels = {
                'supported': '✓ 回答与来源一致',
                'partially_supported': '△ 部分一致，存在待确认内容',
                'not_supported': '✗ 回答与来源不一致',
            }
            reflect_reasoning = status_labels.get(reflection_result.status, reflection_result.status)
            reflect_reasoning += f'（置信度 {reflection_result.confidence:.0%}）'
            if reflection_result.issues:
                reflect_reasoning += '。问题：' + '；'.join(reflection_result.issues)

            reflection_step = ThinkingStep(
                step_id=5,
                step_name='Self-RAG 校验',
                description='校验回答与来源证据的一致性，并在必要时修正回答',
                input_data={'response_length': 0},
                output_data={
                    'status': reflection_result.status,
                    'confidence': reflection_result.confidence,
                    'issues_count': len(reflection_result.issues),
                    'revision_applied': reflection_result.revision_applied,
                },
                reasoning=reflect_reasoning,
                duration_ms=durations[4] if len(durations) > 4 else None,
            )

        summary_parts = [f'完成检索增强回答，使用 {len(sources)} 个来源片段']
        if cot_reasoning:
            summary_parts.append('CoT 链式推理')
        if reflection_result and reflection_result.status != 'skipped':
            summary_parts.append(f'Self-RAG 验证（{reflection_result.status}）')
        summary = '，'.join(summary_parts) + '。'

        return ThinkingProcess(
            query_analysis=query_step,
            retrieval=retrieval_step,
            reranking=rerank_step,
            reasoning=reasoning_step,
            reflection=reflection_step,
            reflection_result=reflection_result,
            summary=summary,
            total_duration_ms=sum(durations),
        )


agent_v2 = AISpecialtyAgentV2()
StudentManualAgentV2 = AISpecialtyAgentV2
