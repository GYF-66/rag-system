# -*- coding: utf-8 -*-
"""Professional cleaning pipeline for PDF-based RAG corpora."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Tuple


class ProfessionalCleaningPipeline:
    """Runs page cleaning, chunk quality scoring, and report generation."""

    PAGE_NOISE_PATTERNS = (
        re.compile(r'^第\s*\d+\s*页$'),
        re.compile(r'^\d+\s*/\s*\d+$'),
        re.compile(r'^(目录|contents)$', re.IGNORECASE),
    )
    TOC_LINE_PATTERN = re.compile(r'[.．…]{4,}\s*\d+$')
    HEADING_ONLY_PATTERN = re.compile(
        r'^(?:第[一二三四五六七八九十百零\d]+[章节篇条款]\s*[^。；;!?！？]{0,40}|[一二三四五六七八九十]+、[^。；;!?！？]{0,40})$'
    )
    OCR_NOISE_PATTERN = re.compile(r'[�□◻]|[A-Za-z]{8,}\d{3,}')

    def clean_pages(
        self,
        lines_by_page: Sequence[Tuple[int, List[str]]],
    ) -> Tuple[List[Tuple[int, List[str]]], Dict[str, int | List[str]]]:
        if not lines_by_page:
            return [], self._empty_page_report()

        header_candidates = self._edge_line_candidates(lines_by_page, edge='header')
        footer_candidates = self._edge_line_candidates(lines_by_page, edge='footer')

        cleaned_pages: List[Tuple[int, List[str]]] = []
        report = self._empty_page_report()
        report['page_count'] = len(lines_by_page)
        report['header_candidates'] = sorted(header_candidates)
        report['footer_candidates'] = sorted(footer_candidates)

        for page_number, lines in lines_by_page:
            cleaned_lines: List[str] = []
            for index, raw_line in enumerate(lines):
                line = self._normalize_line(raw_line)
                if not line:
                    continue
                is_header = index < 2 and line in header_candidates
                is_footer = index >= max(len(lines) - 2, 0) and line in footer_candidates
                if is_header:
                    report['header_footer_removed'] += 1
                    continue
                if is_footer:
                    report['header_footer_removed'] += 1
                    continue
                if self._is_toc_line(line):
                    report['toc_removed'] += 1
                    continue
                if self._is_page_noise(line):
                    report['noise_lines_removed'] += 1
                    continue
                cleaned_lines.append(line)
            if cleaned_lines:
                cleaned_pages.append((page_number, cleaned_lines))

        report['cleaned_page_count'] = len(cleaned_pages)
        return cleaned_pages, report

    def assess_chunks(
        self,
        chunks: Sequence[Dict],
        *,
        document_metadata: Dict | None = None,
        section_count: int = 0,
        paragraph_count: int = 0,
        page_report: Dict | None = None,
    ) -> Tuple[List[Dict], Dict[str, object]]:
        assessed: List[Dict] = []
        seen_hashes: set[str] = set()
        status_counts = {'pass': 0, 'warn': 0, 'reject': 0}
        length_distribution = {'lt_120': 0, '120_300': 0, 'gt_300': 0}

        for chunk in chunks:
            evaluated = self._assess_single_chunk(chunk, seen_hashes)
            status = evaluated['metadata']['chunk_quality_status']
            status_counts[status] += 1
            char_count = int(evaluated.get('char_count') or len(evaluated.get('text') or ''))
            if char_count < 120:
                length_distribution['lt_120'] += 1
            elif char_count <= 300:
                length_distribution['120_300'] += 1
            else:
                length_distribution['gt_300'] += 1
            if status != 'reject':
                assessed.append(evaluated)

        report: Dict[str, object] = {
            'document_id': (document_metadata or {}).get('document_id'),
            'document_type': (document_metadata or {}).get('document_type') or (document_metadata or {}).get('document_kind'),
            'page_count': (page_report or {}).get('page_count', 0),
            'cleaned_page_count': (page_report or {}).get('cleaned_page_count', 0),
            'section_count': section_count,
            'paragraph_count': paragraph_count,
            'chunk_count': len(chunks),
            'kept_chunk_count': len(assessed),
            'quality_status_counts': status_counts,
            'header_footer_removed': (page_report or {}).get('header_footer_removed', 0),
            'toc_removed': (page_report or {}).get('toc_removed', 0),
            'noise_lines_removed': (page_report or {}).get('noise_lines_removed', 0),
            'duplicate_chunk_count': status_counts['reject'],
            'average_chunk_length': round(sum(len(item.get('text') or '') for item in chunks) / max(len(chunks), 1), 2),
            'chunk_length_distribution': length_distribution,
        }
        return assessed, report

    def _assess_single_chunk(self, chunk: Dict, seen_hashes: set[str]) -> Dict:
        text = str(chunk.get('text') or '').strip()
        metadata = dict(chunk.get('metadata') or {})
        flags: List[str] = []
        score = 1.0
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest() if text else ''

        if not text:
            flags.append('empty_chunk')
            score -= 1.0
        if len(text) < 18:
            flags.append('too_short')
            score -= 0.45
        if self.HEADING_ONLY_PATTERN.match(text):
            flags.append('heading_only')
            score -= 0.55
        if self.OCR_NOISE_PATTERN.search(text):
            flags.append('ocr_noise')
            score -= 0.25
        if not text.endswith(('。', '！', '？', '.', ';', '；')):
            flags.append('incomplete_sentence')
            score -= 0.10
        if not metadata.get('section_path_text'):
            flags.append('missing_section_path')
            score -= 0.15
        if content_hash and content_hash in seen_hashes:
            flags.append('duplicate_content')
            score -= 0.9
        if content_hash:
            seen_hashes.add(content_hash)

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if text and chinese_chars / max(len(text), 1) < 0.10:
            flags.append('low_chinese_ratio')
            score -= 0.20

        score = max(0.0, min(score, 1.0))
        status = 'pass'
        if any(flag in flags for flag in ('empty_chunk', 'heading_only', 'duplicate_content')) or score < 0.35:
            status = 'reject'
        elif flags:
            status = 'warn'

        metadata.update(
            {
                'chunk_quality_score': round(score, 3),
                'chunk_quality_status': status,
                'cleaning_flags': flags,
            }
        )
        enriched = dict(chunk)
        enriched['metadata'] = metadata
        enriched['chunk_quality_score'] = metadata['chunk_quality_score']
        enriched['chunk_quality_status'] = status
        enriched['cleaning_flags'] = flags
        return enriched

    def _edge_line_candidates(self, lines_by_page: Sequence[Tuple[int, List[str]]], *, edge: str) -> set[str]:
        candidates: Counter[str] = Counter()
        for _, lines in lines_by_page:
            edge_lines = lines[:2] if edge == 'header' else lines[-2:]
            for line in edge_lines:
                normalized = self._normalize_line(line)
                if normalized and len(normalized) >= 4 and not self._is_page_noise(normalized):
                    candidates[normalized] += 1
        threshold = 2 if len(lines_by_page) >= 3 else len(lines_by_page)
        return {line for line, count in candidates.items() if count >= threshold}

    def _normalize_line(self, line: str) -> str:
        return re.sub(r'\s+', ' ', str(line).replace('\u3000', ' ').strip())

    def _is_page_noise(self, line: str) -> bool:
        return any(pattern.match(line) for pattern in self.PAGE_NOISE_PATTERNS)

    def _is_toc_line(self, line: str) -> bool:
        return bool(self.TOC_LINE_PATTERN.search(line) or ('目录' in line and len(line) <= 12))

    def _empty_page_report(self) -> Dict[str, int | List[str]]:
        return {
            'page_count': 0,
            'cleaned_page_count': 0,
            'header_footer_removed': 0,
            'toc_removed': 0,
            'noise_lines_removed': 0,
            'header_candidates': [],
            'footer_candidates': [],
        }


professional_cleaning_pipeline = ProfessionalCleaningPipeline()
