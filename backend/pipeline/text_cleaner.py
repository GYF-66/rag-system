# -*- coding: utf-8 -*-
"""文本清洗与展示优化。"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from utils.structured_text import contains_structured_label, normalize_spacing, split_structured_fragments, truncate_text_at_boundary


class TextCleaner:
    """处理知识片段中的表格噪音、碎片内容与展示清洗。"""

    _RE_CHINESE = re.compile(r'[\u4e00-\u9fff]')
    _RE_CHINESE_WORDS = re.compile(r'[\u4e00-\u9fff]{2,4}')
    _RE_SENTENCE_SPLIT = re.compile(r'[。！？!?；;\n]+')
    _RE_SENTENCE_KEEPER = re.compile(r'[^。！？!?；;\n]+[。！？!?；;]?')
    _RE_MULTI_NEWLINES = re.compile(r'\n{3,}')
    _RE_MULTI_SPACES = re.compile(r'[\t ]{2,}')
    _RE_DUP_PUNCTUATION = re.compile(r'([，。！？；、])\1+')
    _RE_NOISE_DIGITS = re.compile(r'^[\d\s\.,\-—_，、:：/]+$')
    _RE_NOISE_ELLIPSIS = re.compile(r'^[\.\s\u2026\u22ef·•]+$')
    _RE_NOISE_FRAGMENT = re.compile(r'^\d+[\.、，]\s*[^\u4e00-\u9fff]{0,40}$')
    _RE_NOISE_EN_START = re.compile(r'^[a-zA-Z0-9][^\u4e00-\u9fff]{0,50}$')
    _RE_PAGE_REF = re.compile(r'(第\s*\d+\s*页|page\s*\d+)', re.IGNORECASE)
    _RE_SECTION_PATTERN = re.compile(r'(第[一二三四五六七八九十百零\d]+[章节条款]|[一二三四五六七八九十]+、[^。\n]{1,20})')
    _RE_PAGE_PATTERN = re.compile(r'(第?\s*\d+\s*页|p\.\s*\d+)', re.IGNORECASE)
    _RE_REMOVE_FRAG_PREFIX = re.compile(r'^\s*(?:\d+[\.、，]\s*|[一二三四五六七八九十]+、\s*)')
    _RE_MAIN_CN_NUM = re.compile(r'^[\s\u3000]*[一二三四五六七八九十]+[、.．]\s*')
    _RE_MAIN_DIGIT_NUM = re.compile(r'^[\s\u3000]*(?:\d+[、.．]\s*|\d{1,3}(?=[\u4e00-\u9fff]))')
    _RE_META_CHAPTER = re.compile(r'^第[一二三四五六七八九十百零\d]+[章节条款]$')
    _RE_META_DIGIT_LINE = re.compile(r'^[\s\u3000]*[\d\-]+[.、，]?.*$')
    _RE_TABLE_BORDER = re.compile(r'^[\|:：\-_=+\/\\\s]+$')
    _RE_CHECKMARK = re.compile(r'[√✓✔☑□■◆●○]')
    _TABLE_HINTS = (
        '对应关系',
        '支撑关系',
        '指标点',
        '课程矩阵',
        '关联矩阵',
        '毕业要求矩阵',
        '课程体系与毕业要求',
        '课程体系毕业要求',
        '毕业要求与培养目标',
        '关联度矩阵',
        '达成度',
    )

    def deep_clean_text(self, text: str) -> str:
        """深度清洗文本，移除表格行、对钩行和明显碎片。"""
        if not text:
            return ''

        cleaned_lines: List[str] = []
        seen_lines = set()
        for raw_line in str(text).splitlines():
            line = self._normalize_line(raw_line)
            if not line:
                continue
            if self._is_noise_line(line) or self._looks_like_matrix_row(line):
                continue
            if line in seen_lines:
                continue
            seen_lines.add(line)
            cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines)
        result = self._RE_MULTI_NEWLINES.sub('\n\n', result)
        result = self._RE_DUP_PUNCTUATION.sub(r'\1', result)
        return result.strip()

    def clean_for_display(self, text: str, max_length: int = 320) -> str:
        """输出到前端前的展示清洗。"""
        cleaned = self.deep_clean_text(text)
        if not cleaned:
            return ''

        fragments = self.extract_key_sentences(cleaned, max_sentences=4)
        if not fragments:
            fragments = [candidate for candidate in cleaned.splitlines() if candidate.strip()]
        return self._compose_display_blocks(
            fragments,
            max_length=max_length,
            max_blocks=2,
            max_block_chars=88,
            max_fragments_per_block=2,
        )

    def clean_for_query(self, text: str, keywords: List[str], max_length: int = 320) -> str:
        """根据查询关键词提取更相关的展示片段。"""
        cleaned = self.deep_clean_text(text)
        if not cleaned:
            return ''

        normalized_keywords = [keyword.strip() for keyword in keywords if len(keyword.strip()) >= 2]
        if not normalized_keywords:
            return self.clean_for_display(cleaned, max_length=max_length)

        matched = []
        seen = set()
        for sentence in self.extract_key_sentences(cleaned, max_sentences=8):
            if not any(keyword in sentence for keyword in normalized_keywords):
                continue
            if sentence in seen:
                continue
            seen.add(sentence)
            matched.append(sentence)
            if len(matched) >= 4:
                break

        if matched:
            return self._compose_display_blocks(
                matched,
                max_length=max_length,
                max_blocks=2,
                max_block_chars=96,
                max_fragments_per_block=2,
            )

        return self.clean_for_display(cleaned, max_length=max_length)

    def format_answer_markdown(self, sentences: List[str]) -> str:
        """将句子整理成适合 Markdown 展示的项目列表。"""
        bullets = []
        for sentence in sentences:
            normalized = self._finalize_sentence(sentence)
            if normalized:
                bullets.append(f'- {normalized}')
        return '\n'.join(bullets)

    def format_source_excerpt(self, text: str, max_length: int = 220, max_sentences: int = 3) -> str:
        """为来源卡片生成自然换段的摘要。"""
        cleaned = self.deep_clean_text(text)
        if not cleaned:
            return ''

        sentences = self.extract_key_sentences(cleaned, max_sentences=max_sentences)
        if not sentences:
            sentences = [candidate for candidate in cleaned.splitlines() if candidate.strip()]

        return self._compose_display_blocks(
            sentences,
            max_length=max_length,
            max_blocks=2,
            max_block_chars=72,
            max_fragments_per_block=2,
        )

    def is_valid_content(self, text: str) -> bool:
        """判断内容是否具备最基本的可读性。"""
        cleaned = self.deep_clean_text(text)
        if len(cleaned) < 20:
            return False

        chinese_count = len(self._RE_CHINESE.findall(cleaned))
        if chinese_count < 8:
            return False

        unique_chars = len(set(cleaned))
        if unique_chars < max(int(len(cleaned) * 0.2), 6):
            return False

        return True

    def get_content_fingerprint(self, text: str) -> str:
        """获取内容指纹用于去重。"""
        cleaned = self.deep_clean_text(text)
        chinese_chars = self._RE_CHINESE.findall(cleaned)
        chinese_part = ''.join(chinese_chars[:200])

        words = self._RE_CHINESE_WORDS.findall(cleaned)
        word_freq: Dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        top_keywords = sorted(word_freq.items(), key=lambda item: item[1], reverse=True)[:3]
        keywords = ''.join(word for word, _ in top_keywords)
        return chinese_part + keywords

    def extract_section_title(self, text: str, compiled_chapter_patterns: list) -> str:
        """从文本中提取章节标题。"""
        cleaned = self.deep_clean_text(text)
        if not cleaned:
            return ''

        for compiled in compiled_chapter_patterns:
            match = compiled.search(cleaned)
            if match:
                return match.group(0).strip()

        for line in cleaned.splitlines()[:3]:
            match = self._RE_SECTION_PATTERN.search(line)
            if match and not self._looks_like_matrix_row(line):
                return match.group(0).strip()

        return ''

    def extract_section_info(self, text: str) -> Tuple[str, str]:
        """提取章节与页码信息。"""
        cleaned = self.deep_clean_text(text)
        section_match = self._RE_SECTION_PATTERN.search(cleaned)
        page_match = self._RE_PAGE_PATTERN.search(cleaned)
        return (
            section_match.group(0).strip() if section_match else '',
            page_match.group(0).strip() if page_match else '',
        )

    def extract_key_sentences(self, text: str, max_sentences: int = 3) -> List[str]:
        """Return readable key sentences for UI display."""
        cleaned = self.deep_clean_text(text)
        if not cleaned:
            return []

        key_sentences: List[str] = []
        seen = set()
        for sentence in self._iter_sentence_candidates(cleaned):
            candidate = self._normalize_sentence(sentence)
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            key_sentences.append(candidate)
            if len(key_sentences) >= max_sentences:
                break

        if key_sentences:
            return key_sentences

        fallback_lines: List[str] = []
        for line in cleaned.splitlines():
            for fragment in split_structured_fragments(line, min_fragment_chars=8):
                candidate = self._normalize_sentence(fragment)
                if not candidate:
                    continue
                fallback_lines.append(candidate)
                if len(fallback_lines) >= max_sentences:
                    return fallback_lines
        return fallback_lines

    def _iter_sentence_candidates(self, text: str) -> List[str]:
        candidates: List[str] = []
        for line in str(text).splitlines():
            normalized_line = normalize_spacing(line)
            if not normalized_line:
                continue
            parts = self._RE_SENTENCE_KEEPER.findall(normalized_line) or [normalized_line]
            for part in parts:
                for fragment in split_structured_fragments(part, min_fragment_chars=8):
                    candidate = normalize_spacing(fragment)
                    if candidate:
                        candidates.append(candidate)
        return candidates

    def remove_fragment_prefix(self, text: str) -> str:
        """移除条目编号等碎片前缀。"""
        return self._RE_REMOVE_FRAG_PREFIX.sub('', str(text)).strip()

    def is_valid_meaningful_text(self, text: str) -> bool:
        """更严格的文本有效性判断。"""
        cleaned = self.deep_clean_text(text)
        chinese_count = len(self._RE_CHINESE.findall(cleaned))
        if chinese_count < 20:
            return False
        if len(cleaned) < 80 or len(cleaned) > 3000:
            return False

        unique_chars = len(set(cleaned))
        if unique_chars < len(cleaned) * 0.25:
            return False

        return True

    def clean_fragments(self, text: str) -> str:
        """按行去除碎片内容。"""
        lines = [
            self.remove_fragment_prefix(self._normalize_line(line))
            for line in str(text).splitlines()
        ]
        cleaned_lines = [line for line in lines if line and not self._is_noise_line(line) and not self._looks_like_matrix_row(line)]
        return '\n'.join(cleaned_lines)

    def extract_main_content(self, text: str) -> str:
        """移除条目序号。"""
        main_text = self._RE_MAIN_CN_NUM.sub('', str(text))
        main_text = self._RE_MAIN_DIGIT_NUM.sub('', main_text)
        return self._normalize_line(main_text)

    def is_fragment_pattern(self, text: str) -> bool:
        """判断是否是明显碎片。"""
        candidate = self._normalize_line(text)
        if not candidate:
            return True
        if len(candidate) < 10 and len(self._RE_CHINESE.findall(candidate)) < 4:
            return True
        if self._RE_NOISE_FRAGMENT.match(candidate):
            return True
        if self._RE_NOISE_EN_START.match(candidate):
            return True
        return False

    def is_metadata_or_noise(self, text: str) -> bool:
        """判断是否为页码、章节号或表格噪音。"""
        candidate = self._normalize_line(text)
        if not candidate:
            return True
        if self._RE_META_CHAPTER.match(candidate):
            return True
        if self._RE_NOISE_DIGITS.match(candidate) or self._RE_NOISE_ELLIPSIS.match(candidate):
            return True
        if self._RE_PAGE_REF.search(candidate) and len(self._RE_CHINESE.findall(candidate)) < 6:
            return True
        if self._RE_META_DIGIT_LINE.match(candidate) and len(candidate) < 30:
            return True
        if self._looks_like_matrix_row(candidate):
            return True
        return False

    def get_chinese_fingerprint(self, text: str, length: int = 80) -> str:
        """获取中文指纹用于近似去重。"""
        cleaned = self.deep_clean_text(text)
        chinese_chars = self._RE_CHINESE.findall(cleaned)
        return ''.join(chinese_chars[:length])

    def _normalize_line(self, text: str) -> str:
        line = str(text).replace('\u3000', ' ').strip()
        line = self._RE_MULTI_SPACES.sub(' ', line)
        return line.strip(' |\t')

    def _normalize_sentence(self, text: str) -> str:
        candidate = self._normalize_line(text)
        if not candidate:
            return ''

        for keyword in self._TABLE_HINTS:
            if keyword in candidate:
                candidate = candidate.split(keyword, 1)[0].strip()

        candidate = re.sub(r'毕业要求\d+', '', candidate)
        candidate = re.sub(r'培养目标\d+', '', candidate)
        candidate = self._normalize_line(candidate)
        if not candidate:
            return ''
        if len(candidate) < 10:
            return ''
        if candidate.count('毕业要求') >= 3 or candidate.count('培养目标') >= 3:
            return ''
        if self._is_noise_line(candidate) or self._looks_like_matrix_row(candidate):
            return ''
        if len(self._RE_CHINESE.findall(candidate)) < 6:
            return ''
        return candidate.rstrip('，、；：,. ')

    def _compose_display_blocks(
        self,
        fragments: List[str],
        *,
        max_length: int,
        max_blocks: int,
        max_block_chars: int,
        max_fragments_per_block: int,
    ) -> str:
        blocks: List[str] = []
        current = ''
        current_count = 0

        for fragment in fragments:
            normalized = self._finalize_sentence(fragment)
            if not normalized:
                continue

            if current and (
                len(current) + len(normalized) > max_block_chars
                or current_count >= max_fragments_per_block
            ):
                blocks.append(current)
                current = normalized
                current_count = 1
            else:
                current += normalized
                current_count += 1

            if len(blocks) >= max_blocks:
                break

        if current and len(blocks) < max_blocks:
            blocks.append(current)

        display = '\n\n'.join(blocks).strip()
        if len(display) <= max_length:
            return display

        truncated = truncate_text_at_boundary(display, max_length=max_length)
        if not truncated:
            return display[:max_length]
        if truncated[-1] not in '。！？':
            truncated = f'{truncated}。'
        return truncated

    def _finalize_sentence(self, text: str) -> str:
        candidate = self.remove_fragment_prefix(self._normalize_sentence(text))
        if not candidate:
            return ''
        if candidate[-1] not in '。！？':
            candidate = f'{candidate}。'
        return candidate

    def _is_noise_line(self, line: str) -> bool:
        if self._RE_NOISE_DIGITS.match(line):
            return True
        if self._RE_NOISE_ELLIPSIS.match(line):
            return True
        if self._RE_TABLE_BORDER.match(line):
            return True
        if self._RE_NOISE_FRAGMENT.match(line):
            return True
        if line.endswith('......................') and len(line) < 100:
            return True
        chinese_count = len(self._RE_CHINESE.findall(line))
        if self._RE_NOISE_EN_START.match(line) and chinese_count < 5 and len(line) < 50:
            return True
        return False

    def _looks_like_matrix_row(self, line: str) -> bool:
        if not line:
            return False

        normalized = line.replace('\t', ' ')
        chinese_count = len(self._RE_CHINESE.findall(normalized))
        check_count = len(self._RE_CHECKMARK.findall(normalized))
        column_markers = normalized.count('|') + len(re.findall(r'\s{2,}', normalized))

        if any(keyword in normalized for keyword in self._TABLE_HINTS):
            return True
        if check_count >= 2:
            return True
        if check_count >= 1 and column_markers >= 2:
            return True
        if '|' in normalized and chinese_count < len(normalized) * 0.45:
            return True
        if column_markers >= 3 and chinese_count < 14:
            return True

        return False


text_cleaner = TextCleaner()
