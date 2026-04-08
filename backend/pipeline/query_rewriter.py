# -*- coding: utf-8 -*-
"""Rule-based query rewriting for retrieval-oriented recall expansion."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import jieba

from config import QUERY_VARIANT_LIMIT

STOPWORDS = {
    '什么', '如何', '怎么', '怎样', '是否', '可以', '请问', '一下', '有关', '关于',
    '哪些', '多少', '几个', '安排', '要求', '介绍', '说明', '专业', '人工智能', '还有',
    '通常', '基本', '具体', '需要', '一下子', '一下儿', '哪些方面', '一下吧', '是什么',
    '一下呢', '吗', '呢', '呀', '啊', '吧', '构成', '包括',
}

DOMAIN_SYNONYMS: Dict[str, List[str]] = {
    '培养目标': ['培养方案', '人才培养', '毕业要求', '能力结构'],
    '核心课程': ['课程体系', '主要课程', '专业核心课', '课程安排'],
    '实践环节': ['实践教学', '企业实习', '毕业设计', '综合实践'],
    '学分要求': ['总学分', '学分结构', '实践学分', '学时要求'],
    '毕业设计': ['毕业论文', '开题', '中期检查', '答辩'],
    '奖学金': ['奖助学金', '评定条件', '申请材料', '评审办法'],
    '转专业': ['专业调整', '转入条件', '申请流程'],
    '课程考核': ['考核方式', '成绩评定', '平时成绩'],
}

INTENT_PATTERNS = {
    'training': ('培养目标', '培养方案', '毕业要求', '能力结构'),
    'curriculum': ('核心课程', '课程体系', '选修课', '先修课', '课程安排'),
    'course_chain': ('后续课程', '先修课程', '课程链', '学习路径', '先导课', '前置课程', '课程关系', '课程衔接', '课程顺序'),
    'practice': ('实践环节', '实践教学', '实习', '毕业设计', '论文', '答辩'),
    'credit': ('学分', '总学分', '实践学分', '学时'),
    'scholarship': ('奖学金', '奖助学金', '资助', '申请材料'),
    'student_affairs': ('转专业', '学籍', '违纪', '评优', '宿舍', '请假'),
}

INTENT_EXPLANATIONS = {
    'training': '补充培养方案与毕业要求术语，提升培养方案类问题召回。',
    'curriculum': '扩展核心课程、课程体系、教学安排等表达。',
    'course_chain': '补充课程先后修关系、学习路径等表达，触发课程图谱检索。',
    'practice': '补充实践教学、实习、毕业设计等近义表达。',
    'credit': '补充总学分、学分结构、学时等指标词。',
    'scholarship': '补充奖助学金、评定条件和申请材料表达。',
    'student_affairs': '补充学籍管理、转专业、学生事务词汇。',
    'general': '保留原问题并抽取关键词，减少口语化噪声。',
}

POLICY_HINTS = ('办法', '规定', '条件', '流程', '申请', '评定', '要求', '管理', '细则', '条例')
PROGRAM_HINTS = ('培养目标', '课程体系', '毕业要求', '学分', '实践教学', '培养方案', '课程安排')
TECHNICAL_PATTERNS = (
    re.compile(r'[A-Za-z]{2,}[\-_/]?[A-Za-z0-9]*'),
    re.compile(r'\bAPI\b', re.IGNORECASE),
    re.compile(r'\d+[A-Za-z]+|[A-Za-z]+\d+'),
)
NOISE_PATTERN = re.compile(r'[?？!！,，。；;：:、()（）\[\]{}]+')
FULLWIDTH_TRANSLATION = str.maketrans(
    {
        '，': ' ',
        '。': ' ',
        '：': ':',
        '；': ';',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '？': '?',
    }
)


@dataclass
class QueryRewriteResult:
    normalized_query: str
    intents: List[str]
    intent_confidence: Dict[str, float]
    keywords: List[str]
    variants: List[str]
    query_category: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class QueryRewriter:
    """Creates stable query variants for hybrid recall and refinement UX."""

    def normalize(self, query: str) -> str:
        normalized = (query or '').strip().translate(FULLWIDTH_TRANSLATION)
        normalized = re.sub(r'[“”"\']', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def analyze(self, query: str, max_variants: int = QUERY_VARIANT_LIMIT) -> QueryRewriteResult:
        normalized = self.normalize(query)
        keywords = self._extract_keywords(normalized)
        intents, confidence = self._detect_intents(normalized, keywords)
        query_category = self._classify_query(normalized, keywords, intents)
        variants = self._build_variants(
            normalized,
            keywords,
            intents,
            query_category=query_category,
            max_variants=max_variants,
        )
        return QueryRewriteResult(
            normalized_query=normalized,
            intents=intents,
            intent_confidence=confidence,
            keywords=keywords,
            variants=variants,
            query_category=query_category,
        )

    def rewrite(self, query: str, max_variants: int = QUERY_VARIANT_LIMIT) -> Dict[str, object]:
        return self.analyze(query, max_variants=max_variants).to_dict()

    def suggest(
        self,
        query: str,
        max_suggestions: int = 3,
        strategies: Optional[List[str]] = None,
    ) -> List[Dict[str, object]]:
        analysis = self.analyze(query, max_variants=max(max_suggestions, QUERY_VARIANT_LIMIT))
        strategies = strategies or ['normalized_query', 'intent_expansion', 'keyword_focus']
        suggestions: List[Dict[str, object]] = []

        for strategy in strategies:
            suggestion = self._build_suggestion(strategy, analysis)
            if not suggestion:
                continue
            refined_query = str(suggestion['refined_query']).strip()
            if not refined_query:
                continue
            if any(existing['refined_query'] == refined_query for existing in suggestions):
                continue
            suggestions.append(suggestion)
            if len(suggestions) >= max_suggestions:
                break

        if len(suggestions) < max_suggestions:
            for variant in analysis.variants:
                if variant == analysis.normalized_query:
                    continue
                if any(existing['refined_query'] == variant for existing in suggestions):
                    continue
                suggestions.append(
                    {
                        'refined_query': variant,
                        'strategy': 'variant_fallback',
                        'reason': '保留高置信检索变体以减少漏召回。',
                    }
                )
                if len(suggestions) >= max_suggestions:
                    break

        return suggestions

    def _extract_keywords(self, query: str) -> List[str]:
        tokens = []
        for token in jieba.cut(query):
            cleaned = NOISE_PATTERN.sub('', token).strip().lower()
            if not cleaned or cleaned in STOPWORDS or len(cleaned) <= 1:
                continue
            if cleaned not in tokens:
                tokens.append(cleaned)
        return tokens[:8]

    def _detect_intents(self, query: str, keywords: List[str]) -> tuple[List[str], Dict[str, float]]:
        hits: Dict[str, float] = {}
        lower_query = query.lower()
        for intent, terms in INTENT_PATTERNS.items():
            score = 0.0
            for term in terms:
                if term in query:
                    score += 1.0
                elif term.lower() in lower_query:
                    score += 0.8
                elif term.lower() in keywords:
                    score += 0.6
            if score > 0:
                hits[intent] = round(min(score / max(len(terms), 1), 1.0), 3)

        if not hits:
            return ['general'], {'general': 0.5}

        ordered = sorted(hits.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in ordered], {name: score for name, score in ordered}

    def _classify_query(self, query: str, keywords: List[str], intents: List[str]) -> str:
        if any(pattern.search(query) for pattern in TECHNICAL_PATTERNS):
            return 'technical'
        if any(hint in query for hint in POLICY_HINTS) or 'scholarship' in intents or 'student_affairs' in intents:
            return 'policy'
        if any(hint in query for hint in PROGRAM_HINTS) or any(intent in intents for intent in ('training', 'curriculum', 'practice', 'credit')):
            return 'program'
        if any(pattern.search(token) for token in keywords for pattern in TECHNICAL_PATTERNS):
            return 'technical'
        return 'general'

    def _build_variants(
        self,
        normalized_query: str,
        keywords: List[str],
        intents: List[str],
        query_category: str,
        max_variants: int,
    ) -> List[str]:
        limit = max(1, min(max_variants, QUERY_VARIANT_LIMIT))
        variants = [normalized_query]

        if query_category == 'technical':
            technical_keywords = [keyword for keyword in keywords if any(pattern.search(keyword) for pattern in TECHNICAL_PATTERNS)]
            if technical_keywords:
                variants.append(' '.join(dict.fromkeys(technical_keywords)))
        elif intents and intents[0] != 'general':
            focus_terms: List[str] = []
            for intent in intents[:2]:
                focus_terms.extend(INTENT_PATTERNS.get(intent, ())[:2])
            for keyword in keywords[:2]:
                if keyword not in focus_terms:
                    focus_terms.append(keyword)
            if focus_terms:
                variants.append(' '.join(dict.fromkeys(focus_terms[:4])))

        if query_category != 'technical':
            synonym_variant = self._build_synonym_variant(keywords)
            if synonym_variant:
                variants.append(synonym_variant)

        unique_variants: List[str] = []
        for variant in variants:
            cleaned = variant.strip()
            if cleaned and cleaned not in unique_variants:
                unique_variants.append(cleaned)
        return unique_variants[:limit]

    def _build_synonym_variant(self, keywords: List[str]) -> str:
        expanded: List[str] = []
        for keyword in keywords:
            matched = False
            for canonical, synonyms in DOMAIN_SYNONYMS.items():
                if keyword in canonical.lower() or keyword in {item.lower() for item in synonyms}:
                    expanded.append(canonical)
                    expanded.extend(synonyms[:2])
                    matched = True
                    break
            if matched and len(expanded) >= 4:
                break
        return ' '.join(dict.fromkeys(expanded[:4]))

    def _build_suggestion(self, strategy: str, analysis: QueryRewriteResult) -> Optional[Dict[str, object]]:
        if strategy == 'normalized_query':
            return {
                'refined_query': analysis.normalized_query,
                'strategy': strategy,
                'reason': '统一标点和口语化表达，保持问题主语义稳定。',
            }

        if strategy == 'intent_expansion' and analysis.intents:
            primary_intent = analysis.intents[0]
            intent_terms = list(INTENT_PATTERNS.get(primary_intent, ()))[:3]
            refined_query = ' '.join(dict.fromkeys(intent_terms + analysis.keywords[:2]))
            if refined_query:
                return {
                    'refined_query': refined_query,
                    'strategy': strategy,
                    'reason': INTENT_EXPLANATIONS.get(primary_intent, INTENT_EXPLANATIONS['general']),
                }

        if strategy == 'keyword_focus' and analysis.keywords:
            refined_query = ' '.join(analysis.keywords[:4])
            if refined_query:
                return {
                    'refined_query': refined_query,
                    'strategy': strategy,
                    'reason': '聚焦关键术语，减少口语噪声对检索的干扰。',
                }

        return None


query_rewriter = QueryRewriter()
