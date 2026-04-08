# -*- coding: utf-8 -*-
"""Enterprise retrieval evaluator for the AI-major RAG system."""
from __future__ import annotations

import json
import logging
import math
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = (1, 3, 5)


class RAGEvaluator:
    """Evaluates retrieval quality against selector-based relevance rules."""

    def __init__(
        self,
        test_dataset_path: Optional[str] = None,
        retriever: Any = None,
    ) -> None:
        self.test_dataset_path = test_dataset_path
        self.retriever = retriever
        self.test_cases: List[Dict[str, Any]] = []

        if test_dataset_path and Path(test_dataset_path).exists():
            self.load_test_dataset(test_dataset_path)

    def load_test_dataset(self, path: str) -> None:
        dataset_path = Path(path)
        with dataset_path.open('r', encoding='utf-8-sig') as handle:
            self.test_cases = json.load(handle)
        logger.info('Loaded %s evaluation cases from %s', len(self.test_cases), dataset_path)

    def evaluate_retrieval(
        self,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        retriever: Any = None,
        top_k_values: Sequence[int] = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        cases = test_cases or self.test_cases
        active_retriever = retriever or self.retriever
        if not cases:
            logger.warning('No retrieval evaluation cases available')
            return {}
        if active_retriever is None:
            raise ValueError('A retriever instance must be provided for retrieval evaluation.')

        max_k = max(top_k_values)
        corpus = self._get_corpus_chunks(active_retriever)
        metric_buckets: Dict[str, List[float]] = {}
        per_case: List[Dict[str, Any]] = []

        for case in cases:
            start = time.perf_counter()
            retrieved = active_retriever.search(case['query'], top_k=max_k)
            latency_ms = (time.perf_counter() - start) * 1000
            relevance = [1 if self._is_relevant(item, case) else 0 for item in retrieved]
            total_relevant = self._count_relevant(corpus, case)
            duplication_rate = self._duplication_rate(retrieved)
            irrelevant_rate = self._irrelevant_rate(relevance)

            case_metrics: Dict[str, Any] = {
                'id': case.get('id'),
                'query': case.get('query'),
                'latency_ms': latency_ms,
                'relevant_hits': int(sum(relevance)),
                'relevant_pool_size': total_relevant,
                'context_duplication_rate': duplication_rate,
                'irrelevant_doc_rate': irrelevant_rate,
                'retrieved_ids': [item.get('id') for item in retrieved],
                'matched_sections': [item.get('section') for item, flag in zip(retrieved, relevance) if flag],
            }
            self._push_metric(metric_buckets, 'latency_ms', latency_ms)
            self._push_metric(metric_buckets, 'context_duplication_rate', duplication_rate)
            self._push_metric(metric_buckets, 'irrelevant_doc_rate', irrelevant_rate)

            for k in top_k_values:
                rel_k = relevance[:k]
                precision = self._precision_at_k(rel_k, k)
                recall = self._recall_at_k(total_relevant, rel_k)
                ndcg = self._ndcg_at_k(rel_k, total_relevant)
                self._push_metric(metric_buckets, f'precision_at_{k}', precision)
                self._push_metric(metric_buckets, f'recall_at_{k}', recall)
                self._push_metric(metric_buckets, f'ndcg_at_{k}', ndcg)
                case_metrics[f'precision_at_{k}'] = precision
                case_metrics[f'recall_at_{k}'] = recall
                case_metrics[f'ndcg_at_{k}'] = ndcg

            mrr = self._mrr(relevance)
            self._push_metric(metric_buckets, 'mrr', mrr)
            case_metrics['mrr'] = mrr
            per_case.append(case_metrics)

        summary = self._summarize_metrics(metric_buckets)
        summary['num_test_cases'] = len(per_case)
        summary['top_k_values'] = list(top_k_values)
        summary['per_case'] = per_case
        return summary

    def run_full_evaluation(
        self,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        retriever: Any = None,
        top_k_values: Sequence[int] = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        retrieval = self.evaluate_retrieval(test_cases=test_cases, retriever=retriever, top_k_values=top_k_values)
        overall_score = self._overall_score(retrieval, top_k_values)
        return {
            'retrieval': retrieval,
            'overall_score': overall_score,
        }

    def save_evaluation_results(self, results: Dict[str, Any], output_path: str) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8-sig')
        logger.info('Saved evaluation results to %s', output)

    def _get_corpus_chunks(self, retriever: Any) -> List[Dict[str, Any]]:
        # Try direct chunks attribute
        if hasattr(retriever, 'chunks') and getattr(retriever, 'chunks', None):
            return [dict(item) for item in retriever.chunks]
        # hybrid_retriever → use keyword_backend (TF-IDF KB) as corpus
        keyword_backend = getattr(retriever, 'keyword_backend', None)
        if keyword_backend is not None and hasattr(keyword_backend, 'chunks') and getattr(keyword_backend, 'chunks', None):
            return [dict(item) for item in keyword_backend.chunks]
        # Fallback: use global TF-IDF KB instance directly, load if needed
        try:
            from retrieval.knowledge_base import knowledge_base as tfidf_kb
            if not getattr(tfidf_kb, '_loaded', False):
                tfidf_kb.load()
            if getattr(tfidf_kb, 'chunks', None):
                return [dict(item) for item in tfidf_kb.chunks]
        except Exception:
            pass
        return []

    def _count_relevant(self, corpus: Sequence[Dict[str, Any]], case: Dict[str, Any]) -> int:
        if not corpus:
            return 0
        return sum(1 for item in corpus if self._is_relevant(item, case))

    def _is_relevant(self, item: Dict[str, Any], case: Dict[str, Any]) -> bool:
        metadata = dict(item.get('metadata') or {})
        section = str(item.get('section') or metadata.get('section') or '')
        title = str(item.get('title') or metadata.get('title') or '')
        text = str(item.get('text') or '')
        chunk_id = str(item.get('id') or '')
        document_fields = ' '.join(
            [
                str(metadata.get('document_id') or ''),
                str(metadata.get('title') or ''),
                str(metadata.get('source_path') or ''),
                str(metadata.get('category') or ''),
                title,
            ]
        ).lower()
        section_fields = ' '.join(
            [
                section,
                str(metadata.get('section_title') or ''),
                str(metadata.get('section_path_text') or ''),
                ' '.join(metadata.get('section_path') or []),
            ]
        ).lower()
        text_lower = text.lower()

        if case.get('relevant_chunk_ids') and chunk_id in set(case['relevant_chunk_ids']):
            return True

        # Each selector type uses OR (match any keyword), different types use AND (all must pass)
        # This is more robust for RAG evaluation: a chunk is relevant if it has the right document
        # OR the right section OR the right chunk type OR required terms
        selector_checks: List[bool] = []
        if case.get('relevant_document_keywords'):
            # OR: match if ANY document keyword appears in document_fields
            selector_checks.append(
                any(keyword.lower() in document_fields for keyword in case['relevant_document_keywords'])
            )
        if case.get('relevant_section_keywords'):
            # OR: match if ANY section keyword appears in section_fields
            selector_checks.append(
                any(keyword.lower() in section_fields for keyword in case['relevant_section_keywords'])
            )
        if case.get('relevant_chunk_types'):
            selector_checks.append(str(metadata.get('chunk_type') or '') in set(case['relevant_chunk_types']))
        if case.get('must_include_terms'):
            # ALL must_include terms must appear (stricter)
            selector_checks.append(
                all(term.lower() in text_lower or term.lower() in section_fields for term in case['must_include_terms'])
            )
        if case.get('acceptable_terms'):
            # ANY acceptable term is sufficient
            selector_checks.append(
                any(term.lower() in text_lower or term.lower() in section_fields for term in case['acceptable_terms'])
            )

        return bool(selector_checks) and all(selector_checks)

    def _duplication_rate(self, retrieved: Sequence[Dict[str, Any]]) -> float:
        if not retrieved:
            return 0.0
        signatures = [
            (
                str(item.get('section') or '').strip().lower(),
                str(item.get('text') or '').strip()[:120].lower(),
            )
            for item in retrieved
        ]
        unique = len(set(signatures))
        return max(0.0, 1.0 - (unique / len(signatures)))

    def _irrelevant_rate(self, relevance: Sequence[int]) -> float:
        if not relevance:
            return 0.0
        return sum(1 for flag in relevance if not flag) / len(relevance)

    def _precision_at_k(self, relevance_at_k: Sequence[int], k: int) -> float:
        if k <= 0:
            return 0.0
        denominator = min(k, len(relevance_at_k) or k)
        return sum(relevance_at_k) / denominator if denominator else 0.0

    def _recall_at_k(self, total_relevant: int, relevance_at_k: Sequence[int]) -> float:
        if total_relevant <= 0:
            return 0.0
        return sum(relevance_at_k) / total_relevant

    def _mrr(self, relevance: Sequence[int]) -> float:
        for index, flag in enumerate(relevance, start=1):
            if flag:
                return 1.0 / index
        return 0.0

    def _ndcg_at_k(self, relevance_at_k: Sequence[int], total_relevant: int) -> float:
        if not relevance_at_k:
            return 0.0
        dcg = sum(flag / math.log2(index + 2) for index, flag in enumerate(relevance_at_k))
        ideal_hits = min(total_relevant, len(relevance_at_k))
        ideal = [1] * ideal_hits + [0] * max(len(relevance_at_k) - ideal_hits, 0)
        idcg = sum(flag / math.log2(index + 2) for index, flag in enumerate(ideal))
        if idcg == 0:
            return 0.0
        return dcg / idcg

    def _overall_score(self, retrieval: Dict[str, Any], top_k_values: Sequence[int]) -> float:
        priority_k = 3 if 3 in top_k_values else max(top_k_values)
        weighted_metrics = {
            f'precision_at_{priority_k}': 0.35,
            f'recall_at_{priority_k}': 0.30,
            'mrr': 0.20,
            f'ndcg_at_{priority_k}': 0.15,
        }
        total = 0.0
        weight_sum = 0.0
        for metric_name, weight in weighted_metrics.items():
            value = retrieval.get(metric_name)
            if value is None:
                continue
            total += float(value) * weight
            weight_sum += weight
        return total / weight_sum if weight_sum else 0.0

    def _push_metric(self, bucket: Dict[str, List[float]], name: str, value: float) -> None:
        bucket.setdefault(name, []).append(float(value))

    def _summarize_metrics(self, metric_buckets: Dict[str, List[float]]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for name, values in metric_buckets.items():
            if not values:
                continue
            summary[name] = statistics.mean(values)
            summary[f'{name}_std'] = statistics.pstdev(values) if len(values) > 1 else 0.0
        return summary


def evaluate_rag_system(retriever: Any, test_dataset_path: str) -> Dict[str, Any]:
    evaluator = RAGEvaluator(test_dataset_path=test_dataset_path, retriever=retriever)
    return evaluator.run_full_evaluation()

