# -*- coding: utf-8 -*-
"""Hybrid retrieval with query expansion, multi-channel recall, and RRF fusion."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import jieba

from config import (
    ENABLE_ADAPTIVE_WEIGHTS,
    ENABLE_PARALLEL_RETRIEVAL,
    FIRST_STAGE_CANDIDATE_K,
    LOW_QUALITY_CHUNK_FILTER_ENABLED,
    MAX_RETRIEVAL_RESULTS,
    MIN_EFFECTIVE_CHUNK_LENGTH,
    QUERY_VARIANT_LIMIT,
    RERANK_CANDIDATE_K,
    SEARCH_TOP_K,
    SECTION_DIVERSITY_LIMIT,
    USE_CHROMADB,
    USE_HYBRID_SEARCH,
    VECTOR_SEARCH_WEIGHT,
    KEYWORD_SEARCH_WEIGHT,
)
from .knowledge_base import knowledge_base as tfidf_kb
from pipeline.query_rewriter import query_rewriter
from .reranker import reranker

try:
    from .chroma_knowledge_base import chroma_knowledge_base
except Exception:  # pragma: no cover - optional dependency
    chroma_knowledge_base = None

logger = logging.getLogger(__name__)

STOPWORDS = {
    '什么', '如何', '怎么', '怎样', '是否', '可以', '一下', '一下子', '有关', '关于',
    '以及', '需要', '哪些', '多少', '几个', '一个', '我们', '你们', '请问', '这个', '那个',
    '专业', '课程', '人工智能', '一下', '说明', '介绍', '相关', '要求', '安排',
}

TECHNICAL_PATTERNS = [
    re.compile(r'[A-Za-z]{2,}[\-_/]?[A-Za-z0-9]*'),
    re.compile(r'\d+[A-Za-z]+|[A-Za-z]+\d+'),
]
LOW_QUALITY_PATTERNS = [
    re.compile(r'^目录[\s\S]{0,80}$'),
    re.compile(r'^第?[一二三四五六七八九十0-9]+页$'),
    re.compile(r'版权所有|仅供参考|教务处|安徽信息工程学院'),
]


class HybridRetriever:
    """Mixes vector and keyword retrieval using query variants and reciprocal rank fusion."""

    def __init__(
        self,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        enable_cache: bool = True,
        enable_parallel: bool = ENABLE_PARALLEL_RETRIEVAL,
        enable_adaptive: bool = ENABLE_ADAPTIVE_WEIGHTS,
        vector_backend: Any = None,
        keyword_backend: Any = None,
        cache_backend: Any = None,
    ) -> None:
        self.vector_weight = vector_weight if vector_weight is not None else VECTOR_SEARCH_WEIGHT
        self.keyword_weight = keyword_weight if keyword_weight is not None else KEYWORD_SEARCH_WEIGHT
        self.enable_cache = enable_cache
        self.enable_parallel = enable_parallel
        self.enable_adaptive = enable_adaptive
        self._vector_backend_injected = vector_backend is not None
        self.vector_backend = vector_backend if vector_backend is not None else chroma_knowledge_base
        self.keyword_backend = keyword_backend if keyword_backend is not None else tfidf_kb
        self.use_chroma = False
        self.use_tfidf = False
        self._refresh_backend_flags()
        self.cache = cache_backend
        self.metrics = None

        if self.enable_cache and self.cache is None:
            try:
                from cache.query_cache import get_query_cache

                self.cache = get_query_cache(cache_type='memory', max_size=1000, ttl=3600)
            except Exception as exc:
                logger.warning('Query cache unavailable: %s', exc)
                self.enable_cache = False

        try:
            from monitoring.metrics_collector import get_metrics_collector

            self.metrics = get_metrics_collector()
        except Exception as exc:
            logger.debug('Metrics collector unavailable: %s', exc)

    def _refresh_backend_flags(self) -> None:
        self.use_chroma = bool(self.vector_backend is not None and (self._vector_backend_injected or USE_CHROMADB))
        if self.keyword_backend is None:
            self.use_tfidf = False
        else:
            self.use_tfidf = bool(getattr(self.keyword_backend, 'is_loaded', lambda: True)())

        logger.info(
            'HybridRetriever initialized (vector=%s keyword=%s parallel=%s adaptive=%s)',
            self.use_chroma,
            self.use_tfidf,
            self.enable_parallel,
            self.enable_adaptive,
        )

    def search(
        self,
        query: str,
        top_k: int = SEARCH_TOP_K,
        use_vector: Optional[bool] = None,
        use_keyword: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        query = (query or '').strip()
        if not query:
            return []

        start = time.time()
        cache_key = self._cache_key(query, top_k, use_vector, use_keyword)
        if self.enable_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                if self.metrics:
                    self.metrics.track_query(query, time.time() - start, len(cached), cache_hit=True)
                return cached[:top_k]

        self._refresh_backend_flags()
        use_vector = self.use_chroma if use_vector is None else bool(use_vector and self.use_chroma)
        use_keyword = self.use_tfidf if use_keyword is None else bool(use_keyword and self.use_tfidf)
        if not use_vector and not use_keyword:
            return []

        query_analysis = query_rewriter.rewrite(query, max_variants=QUERY_VARIANT_LIMIT)
        query_variants = self._build_query_variants(query, query_analysis)
        fanout = min(MAX_RETRIEVAL_RESULTS, max(FIRST_STAGE_CANDIDATE_K, top_k * 3, 8))

        retrieval_start = time.time()
        channel_results, channel_timings = self._retrieve_candidates(query_variants, fanout, use_vector, use_keyword)
        merged = self._merge_results(query, query_analysis, query_variants, channel_results, top_k)
        retrieval_time = time.time() - retrieval_start
        total_latency = time.time() - start

        if self.enable_cache and self.cache and merged:
            self.cache.set(cache_key, merged)

        if self.metrics:
            self.metrics.track_query(query, total_latency, len(merged), cache_hit=False)
            self.metrics.track_retrieval(
                query=query,
                retrieval_time=retrieval_time,
                vector_time=channel_timings.get('vector'),
                keyword_time=channel_timings.get('keyword'),
                num_candidates=sum(len(items) for items in channel_results.values()),
                num_final=len(merged),
            )

        return merged[:top_k]

    def _retrieve_candidates(
        self,
        query_variants: Sequence[str],
        fanout: int,
        use_vector: bool,
        use_keyword: bool,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, float]]:
        channel_results: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        timings: Dict[str, float] = {}

        if use_vector:
            start = time.time()
            channel_results['vector'] = self._search_channel(self.vector_backend, query_variants, fanout, 'vector')
            timings['vector'] = time.time() - start

        if use_keyword:
            start = time.time()
            channel_results['keyword'] = self._search_channel(self.keyword_backend, query_variants, fanout, 'keyword')
            timings['keyword'] = time.time() - start

        return channel_results, timings

    def _search_channel(
        self,
        backend: Any,
        query_variants: Sequence[str],
        fanout: int,
        channel: str,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for variant in query_variants:
            try:
                raw_items = self._call_search(backend, variant, fanout)
            except Exception as exc:
                logger.warning('%s retrieval failed for query "%s": %s', channel, variant, exc)
                continue

            for rank, item in enumerate(raw_items):
                normalized = self._normalize_result(item, variant, channel, rank)
                if normalized is not None:
                    results.append(normalized)
        return results

    def _call_search(self, backend: Any, query: str, fanout: int) -> Iterable[Dict[str, Any]]:
        if backend is None:
            return []
        try:
            return backend.search(query, top_k=fanout, min_similarity=0.03)
        except TypeError:
            return backend.search(query, top_k=fanout)

    def _normalize_result(
        self,
        item: Dict[str, Any],
        variant: str,
        channel: str,
        rank: int,
    ) -> Optional[Dict[str, Any]]:
        text = str(item.get('text', '')).strip()
        if not text:
            return None

        identifier = str(item.get('id') or self._text_fingerprint(text))
        section = item.get('section')
        metadata = dict(item.get('metadata') or {})
        similarity = float(item.get('similarity') or item.get('score') or 0.0)

        return {
            'id': identifier,
            'text': text,
            'section': section or metadata.get('section') or metadata.get('title') or '知识片段',
            'metadata': metadata,
            'char_count': int(item.get('char_count') or len(text)),
            'similarity': similarity,
            'variant': variant,
            'channel': channel,
            'rank': rank,
            'rrf': 1.0 / (60 + rank + 1),
        }

    def _merge_results(
        self,
        original_query: str,
        query_analysis: Dict[str, Any],
        query_variants: Sequence[str],
        channel_results: Dict[str, List[Dict[str, Any]]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        vector_weight, keyword_weight = self._adaptive_weights(original_query, query_analysis)
        channel_weights = {
            'vector': vector_weight,
            'keyword': keyword_weight,
        }

        merged: Dict[str, Dict[str, Any]] = {}
        for channel, items in channel_results.items():
            for item in items:
                doc = merged.setdefault(
                    item['id'],
                    {
                        'id': item['id'],
                        'text': item['text'],
                        'section': item['section'],
                        'metadata': dict(item.get('metadata') or {}),
                        'char_count': item['char_count'],
                        'similarity': 0.0,
                        'rrf_score': 0.0,
                        'channel_scores': defaultdict(float),
                        'matched_queries': [],
                        'matched_channels': set(),
                    },
                )
                doc['similarity'] = max(doc['similarity'], item['similarity'])
                doc['rrf_score'] += item['rrf'] * channel_weights.get(channel, 0.0)
                doc['channel_scores'][channel] = max(doc['channel_scores'][channel], item['similarity'])
                if item['variant'] not in doc['matched_queries']:
                    doc['matched_queries'].append(item['variant'])
                doc['matched_channels'].add(channel)

        results = self._filter_candidates(list(merged.values()), query_analysis)
        for doc in results:
            vector_score = doc['channel_scores'].get('vector', 0.0)
            keyword_score = doc['channel_scores'].get('keyword', 0.0)
            weighted_similarity = (vector_score * vector_weight) + (keyword_score * keyword_weight)
            exact_bonus = 0.08 if original_query in doc['text'] else 0.0
            section_bonus = 0.05 if self._section_matches_query(doc, query_analysis) else 0.0
            variant_bonus = min(0.02 * max(len(doc['matched_queries']) - 1, 0), 0.06)
            doc['retrieval_method'] = 'hybrid_rrf'
            doc['rerank_score'] = doc['rrf_score'] + weighted_similarity + exact_bonus + section_bonus + variant_bonus
            doc['matched_channels'] = sorted(doc['matched_channels'])

        if reranker and results:
            pre_ranked = sorted(results, key=lambda item: item['rerank_score'], reverse=True)
            reranked = reranker.rerank(original_query, pre_ranked[:RERANK_CANDIDATE_K], top_k=RERANK_CANDIDATE_K)
            if len(pre_ranked) > RERANK_CANDIDATE_K:
                reranked.extend(pre_ranked[RERANK_CANDIDATE_K:])
        else:
            reranked = sorted(results, key=lambda item: item['rerank_score'], reverse=True)

        return self._dedupe_results(reranked, top_k)

    def _dedupe_results(self, documents: Sequence[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen = set()
        section_counts: Dict[str, int] = defaultdict(int)
        for doc in documents:
            signature = (doc.get('section'), self._text_fingerprint(doc.get('text', '')[:180]))
            if signature in seen:
                continue
            section_key = str(doc.get('section') or '').strip().lower()
            if section_key and section_counts[section_key] >= SECTION_DIVERSITY_LIMIT:
                continue
            seen.add(signature)
            if section_key:
                section_counts[section_key] += 1
            deduped.append(doc)
            if len(deduped) >= top_k:
                break
        return deduped

    def _build_query_variants(self, query: str, rewrite: Optional[Dict[str, Any]] = None) -> List[str]:
        rewrite = rewrite or query_rewriter.rewrite(query, max_variants=QUERY_VARIANT_LIMIT)
        normalized = str(rewrite.get('normalized_query', query)).strip()
        keywords = [
            token.strip()
            for token in rewrite.get('keywords', [])
            if len(token.strip()) > 1 and token.strip() not in STOPWORDS
        ]

        variants = list(rewrite.get('variants', []) or [normalized])
        for token in keywords[:4]:
            if any(pattern.search(token) for pattern in TECHNICAL_PATTERNS):
                lowered = token.lower()
                if lowered not in variants:
                    variants.append(lowered)

        unique_variants: List[str] = []
        for variant in variants:
            cleaned = variant.strip()
            if cleaned and cleaned not in unique_variants:
                unique_variants.append(cleaned)
        return unique_variants[:QUERY_VARIANT_LIMIT]

    def _adaptive_weights(self, query: str, query_analysis: Optional[Dict[str, Any]] = None) -> Tuple[float, float]:
        if not self.enable_adaptive:
            return self.vector_weight, self.keyword_weight

        query_length = len(query.strip())
        vector_weight = self.vector_weight
        keyword_weight = self.keyword_weight
        query_category = str((query_analysis or {}).get('query_category') or 'general')

        if query_length <= 8:
            keyword_weight = max(keyword_weight, 0.45)
            vector_weight = min(vector_weight, 0.55)
        elif query_length >= 20:
            vector_weight = max(vector_weight, 0.75)
            keyword_weight = min(keyword_weight, 0.25)

        if query_category == 'policy':
            keyword_weight = max(keyword_weight, 0.58)
            vector_weight = min(vector_weight, 0.42)
        elif query_category == 'program':
            vector_weight = max(vector_weight, 0.55)
            keyword_weight = min(keyword_weight, 0.45)
        elif query_category == 'technical':
            keyword_weight = max(keyword_weight, 0.62)
            vector_weight = min(vector_weight, 0.38)

        if any(pattern.search(query) for pattern in TECHNICAL_PATTERNS):
            keyword_weight = min(keyword_weight + 0.1, 0.6)
            vector_weight = max(1.0 - keyword_weight, 0.4)

        total = vector_weight + keyword_weight
        if total <= 0:
            return 0.5, 0.5
        return vector_weight / total, keyword_weight / total

    def _filter_candidates(
        self,
        documents: Sequence[Dict[str, Any]],
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for doc in documents:
            text = str(doc.get('text') or '').strip()
            if not text:
                continue
            if LOW_QUALITY_CHUNK_FILTER_ENABLED and self._is_low_quality_chunk(doc):
                continue
            doc['quality_flags'] = self._quality_flags(doc, query_analysis)
            filtered.append(doc)
        return filtered

    def _is_low_quality_chunk(self, document: Dict[str, Any]) -> bool:
        text = str(document.get('text') or '').strip()
        metadata = dict(document.get('metadata') or {})
        if metadata.get('chunk_quality_status') == 'reject':
            return True
        if float(metadata.get('chunk_quality_score') or 1.0) < 0.30:
            return True
        if len(text) < MIN_EFFECTIVE_CHUNK_LENGTH:
            return True
        if any(pattern.search(text) for pattern in LOW_QUALITY_PATTERNS):
            return True
        section = str(document.get('section') or '').strip()
        if section and text == section:
            return True
        punctuation_ratio = sum(1 for char in text if char in '，。；：,.?!！？、/ ') / max(len(text), 1)
        return punctuation_ratio > 0.55 and len(set(text)) < 18

    def _section_matches_query(self, document: Dict[str, Any], query_analysis: Optional[Dict[str, Any]]) -> bool:
        section_blob = ' '.join(
            [
                str(document.get('section') or ''),
                str((document.get('metadata') or {}).get('section_path_text') or ''),
                str((document.get('metadata') or {}).get('title') or ''),
            ]
        ).lower()
        for keyword in (query_analysis or {}).get('keywords', []):
            if keyword.lower() in section_blob:
                return True
        return False

    def _quality_flags(self, document: Dict[str, Any], query_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        section_blob = ' '.join(
            [
                str(document.get('section') or ''),
                str((document.get('metadata') or {}).get('section_path_text') or ''),
            ]
        ).lower()
        return {
            'section_match': self._section_matches_query(document, query_analysis),
            'sentence_complete': str(document.get('text') or '').rstrip().endswith(('。', '！', '？', '.', ';', '；')),
            'has_section_path': bool((document.get('metadata') or {}).get('section_path_text')),
            'section_blob': section_blob,
        }

    def _cache_key(
        self,
        query: str,
        top_k: int,
        use_vector: Optional[bool],
        use_keyword: Optional[bool],
    ) -> str:
        return json.dumps(
            {
                'query': query,
                'top_k': top_k,
                'use_vector': use_vector,
                'use_keyword': use_keyword,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _text_fingerprint(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'use_chroma': self.use_chroma,
            'use_tfidf': self.use_tfidf,
            'vector_weight': self.vector_weight,
            'keyword_weight': self.keyword_weight,
            'parallel_enabled': self.enable_parallel,
            'adaptive_enabled': self.enable_adaptive,
        }


hybrid_retriever = HybridRetriever() if USE_HYBRID_SEARCH else None

if USE_HYBRID_SEARCH and hybrid_retriever:
    logger.info('Hybrid retriever enabled')
else:
    logger.info('Hybrid retriever disabled')




