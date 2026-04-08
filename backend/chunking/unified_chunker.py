# -*- coding: utf-8 -*-
"""Enterprise-oriented structural chunking with heading and page metadata."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import jieba

from utils.structured_text import normalize_spacing, split_structured_fragments

HEADING_PATTERNS = [
    (1, re.compile(r'^第[一二三四五六七八九十百零\d]+[章节篇]\s*(.+)?$')),
    (2, re.compile(r'^[一二三四五六七八九十]+、(.+)$')),
    (3, re.compile(r'^\(?[1-9]\d*\)?[、.]?(.+)$')),
]

TABLE_HINTS = (
    '关联度矩阵',
    '课程体系与毕业要求',
    '毕业要求与培养目标',
    '课程矩阵',
    '指标点',
)

# 不过滤而是保留为结构化数据的映射矩阵关键词
MATRIX_PRESERVE_HINTS = (
    '关联度矩阵',
    '课程体系与毕业要求',
    '毕业要求与培养目标',
    '课程矩阵',
)

STOPWORDS = {'的', '和', '及', '与', '为', '等', '学生', '专业', '课程'}


@dataclass
class LineRecord:
    text: str
    page: int


@dataclass
class BlockRecord:
    title: str
    level: int
    section_path: List[str]
    page_start: int
    page_end: int
    text: str


class UnifiedChunker:
    """Chunks curriculum-like documents into retrieval-friendly passages."""

    def __init__(
        self,
        chunk_size: int = 680,
        chunk_overlap: int = 120,
        min_chunk_size: int = 180,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        lines = [LineRecord(text=line, page=int(metadata.get('page', 1) if metadata else 1)) for line in text.splitlines()]
        return self.chunk_lines(lines, metadata=metadata)

    def chunk_documents(self, documents: Sequence[Dict]) -> List[Dict]:
        from .contextual_enricher import inject_contextual_prefix, build_document_summary

        chunks: List[Dict] = []
        for doc_index, document in enumerate(documents):
            metadata = dict(document.get('metadata') or {})
            metadata.setdefault('doc_index', doc_index)
            pages = document.get('pages')
            if pages:
                lines = self._page_records_to_lines(pages)
                doc_chunks = self.chunk_lines(lines, metadata=metadata)
            else:
                doc_chunks = self.chunk_text(str(document.get('text', '')), metadata=metadata)

            # Contextual Retrieval: 注入文档级上下文前缀
            doc_title = metadata.get('title') or metadata.get('document_id') or ''
            doc_summary = build_document_summary(doc_chunks)
            doc_chunks = inject_contextual_prefix(doc_chunks, doc_title, doc_summary)

            chunks.extend(doc_chunks)
        return chunks

    def chunk_lines(self, lines: Sequence[LineRecord], metadata: Optional[Dict] = None) -> List[Dict]:
        usable_lines = self._normalize_lines(lines)
        blocks = self._build_blocks(usable_lines)
        chunks = self._blocks_to_chunks(blocks, metadata or {})
        return self._merge_small_chunks(chunks)

    def _page_records_to_lines(self, pages: Sequence[Dict]) -> List[LineRecord]:
        lines: List[LineRecord] = []
        for page in pages:
            page_number = int(page.get('page', 1))
            for line in str(page.get('text', '')).splitlines():
                lines.append(LineRecord(text=line, page=page_number))
        return lines

    def _normalize_lines(self, lines: Sequence[LineRecord]) -> List[LineRecord]:
        normalized: List[LineRecord] = []
        for record in lines:
            raw_line = str(record.text).replace('\u3000', ' ').strip()
            if not raw_line:
                continue

            page = record.page
            inline_page = re.match(r'^(\d{1,3})(?=[\u4e00-\u9fff])', raw_line)
            if inline_page:
                page = int(inline_page.group(1))
                raw_line = raw_line[inline_page.end():].strip()

            raw_line = re.sub(r'\s+', ' ', raw_line)
            if not raw_line or self._is_noise_line(raw_line):
                continue

            normalized.append(LineRecord(text=raw_line, page=page))
        return normalized

    def _build_blocks(self, lines: Sequence[LineRecord]) -> List[BlockRecord]:
        blocks: List[BlockRecord] = []
        section_stack: List[str] = []
        current_title = '文档概览'
        current_level = 0
        current_text: List[str] = []
        block_page_start = lines[0].page if lines else 1
        block_page_end = block_page_start

        def flush() -> None:
            nonlocal current_text, block_page_start, block_page_end
            if not current_text:
                return
            text = '\n'.join(current_text).strip()
            if len(text) < self.min_chunk_size // 2:
                return
            blocks.append(
                BlockRecord(
                    title=current_title,
                    level=current_level,
                    section_path=list(section_stack) or [current_title],
                    page_start=block_page_start,
                    page_end=block_page_end,
                    text=text,
                )
            )
            current_text = []

        for record in lines:
            heading = self._match_heading(record.text)
            if heading:
                flush()
                level = heading['level']
                title = heading['title']
                section_stack = section_stack[: max(level - 1, 0)]
                section_stack.append(title)
                current_title = title
                current_level = level
                block_page_start = record.page
                block_page_end = record.page
                current_text = []
                continue

            if not current_text:
                block_page_start = record.page
            block_page_end = record.page
            current_text.append(record.text)

        flush()
        return blocks

    def _blocks_to_chunks(self, blocks: Sequence[BlockRecord], base_metadata: Dict) -> List[Dict]:
        chunks: List[Dict] = []
        chunk_id = 0
        for block in blocks:
            sentences = self._split_sentences(block.text)
            if not sentences:
                continue

            cursor = 0
            while cursor < len(sentences):
                current: List[str] = []
                size = 0
                start_cursor = cursor
                while cursor < len(sentences):
                    sentence = sentences[cursor]
                    projected = size + len(sentence)
                    if current and projected > self.chunk_size:
                        break
                    current.append(sentence)
                    size = projected
                    cursor += 1

                if cursor < len(sentences) and size < self.min_chunk_size:
                    while cursor < len(sentences) and size < self.min_chunk_size:
                        sentence = sentences[cursor]
                        current.append(sentence)
                        size += len(sentence)
                        cursor += 1

                remaining_size = sum(len(sentence) for sentence in sentences[cursor:])
                if current and 0 < remaining_size < self.min_chunk_size:
                    current.extend(sentences[cursor:])
                    cursor = len(sentences)

                chunk_text = ''.join(current).strip()
                if not chunk_text:
                    break

                keywords = self._extract_keywords(chunk_text, top_n=8)
                metadata = {
                    **base_metadata,
                    'title': block.title,
                    'section': block.section_path[-1],
                    'section_path': list(block.section_path),
                    'section_path_text': ' > '.join(block.section_path),
                    'heading_level': block.level,
                    'page_start': block.page_start,
                    'page_end': block.page_end,
                    'keywords': keywords,
                }
                chunks.append(
                    {
                        'id': str(chunk_id),
                        'text': chunk_text,
                        'char_count': len(chunk_text),
                        'section': block.section_path[-1],
                        'title': block.title,
                        'metadata': metadata,
                    }
                )
                chunk_id += 1

                if cursor >= len(sentences):
                    break

                cursor = self._rewind_for_overlap(sentences, start_cursor, cursor)
        return chunks

    def _merge_small_chunks(self, chunks: Sequence[Dict]) -> List[Dict]:
        merged: List[Dict] = []
        for chunk in chunks:
            if not merged:
                merged.append(chunk)
                continue
            previous = merged[-1]
            same_section = previous.get('section') == chunk.get('section')
            if same_section and previous['char_count'] < self.min_chunk_size:
                previous['text'] = f"{previous['text']} {chunk['text']}".strip()
                previous['char_count'] = len(previous['text'])
                previous['metadata']['page_end'] = chunk['metadata']['page_end']
                previous['metadata']['keywords'] = self._extract_keywords(previous['text'], top_n=8)
                continue
            merged.append(chunk)
        return merged

    def _match_heading(self, line: str) -> Optional[Dict[str, object]]:
        candidate = re.sub(r'^\d{1,3}', '', line).strip()
        if not candidate:
            return None
        if any(hint in candidate for hint in TABLE_HINTS):
            return None
        for level, pattern in HEADING_PATTERNS:
            match = pattern.match(candidate)
            if not match:
                continue
            title = candidate
            if len(title) > 50:
                return None
            return {'level': level, 'title': title}
        return None

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split('([\u3002\uff01\uff1f\uff1b\n])', text)
        sentences: List[str] = []
        buffer = ''
        for part in parts:
            if not part:
                continue
            buffer += part
            if re.fullmatch('[\u3002\uff01\uff1f\uff1b\n]', part):
                sentences.extend(self._collect_sentence_fragments(buffer))
                buffer = ''
        if buffer.strip():
            sentences.extend(self._collect_sentence_fragments(buffer))
        return sentences

    def _collect_sentence_fragments(self, text: str) -> List[str]:
        fragments: List[str] = []
        for fragment in split_structured_fragments(text, min_fragment_chars=12):
            candidate = normalize_spacing(fragment)
            if len(candidate) >= 12 and not self._is_noise_line(candidate):
                fragments.append(candidate)
        return fragments

    def _rewind_for_overlap(self, sentences: Sequence[str], start: int, end: int) -> int:
        overlap = 0
        cursor = end
        while cursor > start and overlap < self.chunk_overlap:
            cursor -= 1
            overlap += len(sentences[cursor])
        return max(cursor, start + 1)

    def _extract_keywords(self, text: str, top_n: int = 8) -> List[str]:
        counter: Counter[str] = Counter()
        for token in jieba.cut(text):
            token = token.strip()
            if len(token) < 2 or token in STOPWORDS:
                continue
            counter[token] += 1
        return [word for word, _ in counter.most_common(top_n)]

    def _is_noise_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return True
        if re.fullmatch(r'\d{1,3}', stripped):
            return True
        if stripped.count('…') >= 3 or stripped.count('.') >= 10:
            return True
        # 保留映射矩阵相关行（用于一致性分析）
        if any(hint in stripped for hint in MATRIX_PRESERVE_HINTS):
            return False
        if any(hint in stripped for hint in TABLE_HINTS):
            return True
        if stripped.count('√') >= 2 or stripped.count('✓') >= 2:
            return True
        if '|' in stripped and len(re.findall(r'[\u4e00-\u9fff]', stripped)) < 8:
            return True
        if stripped.count('毕业要求') >= 3 or stripped.count('培养目标') >= 3:
            return True
        return False


default_chunker = UnifiedChunker()


def chunk_text(text: str, metadata: Optional[Dict] = None) -> List[Dict]:
    return default_chunker.chunk_text(text, metadata)


def chunk_documents(documents: Sequence[Dict]) -> List[Dict]:
    return default_chunker.chunk_documents(documents)
