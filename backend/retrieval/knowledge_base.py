# -*- coding: utf-8 -*-
"""Keyword and vector retrieval over the local JSON knowledge base."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import KNOWLEDGE_BASE_PATH, TOP_K_RESULTS
from pipeline.query_rewriter import query_rewriter
from utils.bm25 import BM25

CACHE_DIR = Path('cache/tfidf')
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class KnowledgeBase:
    """Metadata-aware local retriever backed by JSON chunks."""

    def __init__(self, kb_path: Path = KNOWLEDGE_BASE_PATH, enable_cache: bool = True) -> None:
        self.kb_path = kb_path
        self.enable_cache = enable_cache
        self.metadata: Dict[str, Any] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.search_texts: List[str] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.chunk_vectors = None
        self.bm25: Optional[BM25] = None
        self._loaded = False
        self._course_name_index: Optional[Dict[str, Dict[str, Any]]] = None

    def load(self) -> bool:
        if not self.kb_path.exists():
            return False

        try:
            data = json.loads(self.kb_path.read_text(encoding='utf-8'))
            self.metadata = dict(data.get('metadata') or {})
            self.chunks = []
            for index, raw_chunk in enumerate(data.get('chunks') or []):
                normalized = self._normalize_chunk(raw_chunk, index)
                if normalized is not None:
                    self.chunks.append(normalized)

            if not self.chunks:
                return False

            self.search_texts = [self._build_search_text(chunk) for chunk in self.chunks]
            self._build_or_load_vectors()
            self._build_bm25()
            self._loaded = True
            return True
        except Exception:
            return False

    def _normalize_chunk(self, chunk: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        text = str(chunk.get('text', '')).strip()
        if len(text) < 40:
            return None

        metadata = dict(chunk.get('metadata') or {})
        section = str(chunk.get('section') or metadata.get('section') or metadata.get('title') or '知识片段').strip()
        title = str(chunk.get('title') or metadata.get('title') or section).strip()
        metadata.setdefault('section', section)
        metadata.setdefault('title', title)
        metadata.setdefault('keywords', metadata.get('keywords') or chunk.get('keywords') or self._extract_keywords(text))
        metadata.setdefault('document_id', chunk.get('document_id') or metadata.get('document_id') or title)
        metadata.setdefault('source_path', chunk.get('source_path') or metadata.get('source_path') or '')
        metadata.setdefault('section_path', metadata.get('section_path') or [section])
        metadata.setdefault('section_path_text', metadata.get('section_path_text') or ' > '.join(metadata['section_path']))
        metadata.setdefault('chunk_type', chunk.get('chunk_type') or metadata.get('chunk_type') or 'general')
        metadata.setdefault('page_start', chunk.get('page_start') or metadata.get('page_start'))
        metadata.setdefault('page_end', chunk.get('page_end') or metadata.get('page_end'))

        return {
            'id': str(chunk.get('id', index)),
            'text': text,
            'char_count': int(chunk.get('char_count') or len(text)),
            'section': section,
            'title': title,
            'document_id': metadata.get('document_id'),
            'source_path': metadata.get('source_path'),
            'page_start': metadata.get('page_start'),
            'page_end': metadata.get('page_end'),
            'chunk_type': metadata.get('chunk_type', 'general'),
            'education_level': chunk.get('education_level') or metadata.get('education_level', ''),
            'bloom_level': chunk.get('bloom_level') or metadata.get('bloom_level', ''),
            'knowledge_concepts': chunk.get('knowledge_concepts') or [],
            'mapped_objectives': chunk.get('mapped_objectives') or [],
            'course_code': chunk.get('course_code', ''),
            'semester': chunk.get('semester'),
            'metadata': metadata,
        }

    def _build_or_load_vectors(self) -> None:
        cache_vectorizer = CACHE_DIR / 'vectorizer.pkl'
        cache_vectors = CACHE_DIR / 'vectors.npy'

        if self.enable_cache and cache_vectorizer.exists() and cache_vectors.exists():
            try:
                self.vectorizer = joblib.load(cache_vectorizer)
                self.chunk_vectors = np.load(cache_vectors, allow_pickle=True)
                if self.chunk_vectors.shape[0] == len(self.chunks):
                    return
            except Exception:
                pass

        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda text: list(jieba.cut(text)),
            max_features=8000,
            ngram_range=(1, 2),
        )
        self.chunk_vectors = self.vectorizer.fit_transform(self.search_texts)
        if self.enable_cache:
            try:
                joblib.dump(self.vectorizer, cache_vectorizer)
                np.save(cache_vectors, self.chunk_vectors)
            except Exception:
                pass

    def _build_bm25(self) -> None:
        self.bm25 = BM25()
        self.bm25.fit(self.search_texts)

    def _build_search_text(self, chunk: Dict[str, Any]) -> str:
        metadata = chunk.get('metadata') or {}
        keywords = ' '.join(metadata.get('keywords') or [])
        section_path = str(metadata.get('section_path_text') or '')
        concepts = ' '.join(chunk.get('knowledge_concepts') or [])
        objectives = ' '.join(chunk.get('mapped_objectives') or [])
        header = ' '.join(
            [
                str(chunk.get('title') or ''),
                str(chunk.get('document_id') or ''),
                str(chunk.get('section') or ''),
                section_path,
                str(metadata.get('chunk_type') or ''),
                keywords,
                concepts,
                objectives,
            ]
        )
        return f"{header} {header} {chunk.get('text', '')}".strip()

    def search(self, query: str, top_k: int = TOP_K_RESULTS, min_similarity: float = 0.05,
               education_level: str | None = None) -> List[Dict[str, Any]]:
        if not self._loaded or not query.strip():
            return []

        analysis = query_rewriter.analyze(query, max_variants=4)
        rewritten_query = ' '.join(analysis.variants[:3])
        tfidf_scores = cosine_similarity(self.vectorizer.transform([rewritten_query]), self.chunk_vectors).flatten()
        bm25_scores = np.array(self.bm25.get_scores(rewritten_query)) if self.bm25 else np.zeros(len(self.chunks))
        bm25_scores = self._normalize_scores(bm25_scores)
        matched_course_codes = {mc.get('code', '') for mc in self.find_courses_by_name(analysis.keywords)}
        metadata_scores = np.array([self._metadata_score(chunk, analysis.keywords, matched_course_codes) for chunk in self.chunks])

        combined_scores = 0.40 * tfidf_scores + 0.30 * bm25_scores + 0.30 * metadata_scores
        candidate_indices = np.argsort(combined_scores)[::-1][: max(top_k * 4, top_k)]

        results: List[Dict[str, Any]] = []
        for index in candidate_indices:
            score = float(combined_scores[index])
            if score < min_similarity:
                continue
            chunk = self.chunks[index]
            # 层级过滤
            if education_level and chunk.get('education_level') != education_level:
                continue
            result = dict(chunk)
            result['similarity'] = score
            result['tfidf_score'] = float(tfidf_scores[index])
            result['bm25_score'] = float(bm25_scores[index])
            result['metadata_score'] = float(metadata_scores[index])
            results.append(result)
            if len(results) >= top_k:
                break
        return results

    def get_course_graph(self) -> Dict[str, Any]:
        """获取课程关联图谱"""
        return self.metadata.get('course_graph', {})

    def _get_course_name_index(self) -> Dict[str, Dict[str, Any]]:
        """懒加载：课程名→图谱条目的反向索引"""
        if self._course_name_index is not None:
            return self._course_name_index
        graph = self.get_course_graph()
        index: Dict[str, Dict[str, Any]] = {}
        for doc_id, entry in graph.items():
            name = entry.get('name', '')
            if name:
                index[name] = {**entry, 'doc_id': doc_id}
        self._course_name_index = index
        return index

    def find_courses_by_name(self, query_keywords: List[str]) -> List[Dict[str, Any]]:
        """根据查询关键词匹配课程图谱条目（精确子串匹配）"""
        index = self._get_course_name_index()
        matched: List[Dict[str, Any]] = []
        query_text = ''.join(query_keywords)
        for name, entry in index.items():
            if name in query_text or any(name in kw or kw in name for kw in query_keywords if len(kw) >= 2):
                matched.append(entry)
        return matched

    def get_course_prerequisites(self, course_id: str) -> List[str]:
        """获取课程先修课程列表"""
        graph = self.get_course_graph()
        return graph.get(course_id, {}).get('prerequisites', [])

    def get_course_chain(self, course_id: str) -> List[str]:
        """获取课程的完整学习链（先修→当前→后续）"""
        graph = self.get_course_graph()
        chain = []
        # 先修
        prereqs = graph.get(course_id, {}).get('prerequisites', [])
        chain.extend(prereqs)
        chain.append(course_id)
        # 后续
        leads = graph.get(course_id, {}).get('leads_to', [])
        chain.extend(leads)
        return chain

    def _metadata_score(self, chunk: Dict[str, Any], keywords: List[str], matched_course_codes: set = None) -> float:
        if not keywords:
            return 0.0

        metadata = chunk.get('metadata') or {}
        fields = [
            chunk.get('section', ''),
            chunk.get('title', ''),
            metadata.get('document_id', ''),
            metadata.get('section_path_text', ''),
            metadata.get('chunk_type', ''),
            ' '.join(metadata.get('keywords') or []),
            ' '.join(chunk.get('knowledge_concepts') or []),
            ' '.join(chunk.get('mapped_objectives') or []),
        ]
        haystack = ' '.join(str(field) for field in fields)
        overlap = sum(1 for keyword in keywords if keyword in haystack)
        exact_bonus = 1 if any(keyword in chunk.get('text', '')[:160] for keyword in keywords[:3]) else 0
        document_bonus = 1 if any(keyword in str(metadata.get('document_id', '')) for keyword in keywords[:2]) else 0

        # 精确课程名匹配加权：查询中包含的课程名与 chunk 所属课程一致时大幅提权
        course_name_bonus = 0.0
        if matched_course_codes:
            chunk_course = chunk.get('course_code', '')
            if chunk_course and chunk_course in matched_course_codes:
                course_name_bonus = 0.30

        # 针对教育层级查询的加权
        query_text = ' '.join(keywords)
        type_bonus = 0.0
        if any(kw in query_text for kw in ('培养目标', '毕业要求', '培养方案')):
            if chunk.get('chunk_type') == 'program_spec':
                type_bonus = 0.15
        elif any(kw in query_text for kw in ('教学大纲', '课程目标', '课程设置')):
            if chunk.get('education_level') == 'meso':
                type_bonus = 0.1

        return min((overlap / max(len(keywords), 1)) + 0.2 * exact_bonus + 0.2 * document_bonus + course_name_bonus + type_bonus, 1.0)

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        if scores.size == 0:
            return scores
        max_score = float(scores.max())
        if max_score <= 0:
            return np.zeros_like(scores)
        return scores / max_score

    def _extract_keywords(self, text: str, limit: int = 8) -> List[str]:
        keywords: List[str] = []
        for token in jieba.cut(text):
            token = token.strip()
            if len(token) < 2:
                continue
            if token not in keywords:
                keywords.append(token)
            if len(keywords) >= limit:
                break
        return keywords

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        for chunk in self.chunks:
            if chunk['id'] == chunk_id:
                return dict(chunk)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'total_chunks': len(self.chunks),
            'source': self.metadata.get('source'),
            'chunking_method': self.metadata.get('chunking_method'),
        }

    def is_loaded(self) -> bool:
        return self._loaded


knowledge_base = KnowledgeBase()
