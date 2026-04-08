# -*- coding: utf-8 -*-
"""
交叉检索引擎 - 改进版
修复了逻辑严密性和连贯性问题
"""
import time
import re
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

import jieba

from config import SEARCH_TOP_K, MIN_SIMILARITY

# 尝试导入知识库
try:
    from .chroma_knowledge_base import chroma_knowledge_base
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chroma_knowledge_base = None

from .knowledge_base import knowledge_base


class CrossRetrievalEngineImproved:
    """交叉检索引擎 - 改进版"""

    def __init__(self):
        self.use_chromadb = CHROMADB_AVAILABLE and chroma_knowledge_base is not None

        # 隐含关联问题模式库
        self.cross_query_patterns = {
            '挂科奖学金': {
                'keywords': ['挂科', '不及格', '奖学金', '助学金', '评选', '条件'],
                'query_type': 'cross_reference',
                'description': '挂科对奖学金申请的影响'
            },
            '软著加分': {
                'keywords': ['软件著作权', '软著', '加分', '综测', '综合素质', '创新'],
                'query_type': 'cross_reference',
                'description': '软件著作权在综合素质测评中的加分政策'
            },
            '专利加分': {
                'keywords': ['专利', '发明', '实用新型', '加分', '综测', '创新'],
                'query_type': 'cross_reference',
                'description': '专利在综合素质测评中的加分政策'
            },
            '竞赛加分': {
                'keywords': ['竞赛', '比赛', '获奖', '加分', '综测', '奖项'],
                'query_type': 'cross_reference',
                'description': '竞赛获奖在综合素质测评中的加分政策'
            },
            '转专业': {
                'keywords': ['转专业', '条件', '要求', '申请', '绩点', '成绩'],
                'query_type': 'cross_reference',
                'description': '转专业的条件和要求'
            },
            '延期毕业': {
                'keywords': ['延期毕业', '延毕', '就业', '档案', '派遣', '影响'],
                'query_type': 'cross_reference',
                'description': '延期毕业对就业和档案的影响'
            },
            '重修费用': {
                'keywords': ['重修', '费用', '学费', '学分费', '收费'],
                'query_type': 'cross_reference',
                'description': '课程重修的相关费用规定'
            },
            '补考绩点': {
                'keywords': ['补考', '绩点', '成绩', '记载', '计算'],
                'query_type': 'cross_reference',
                'description': '补考成绩对绩点计算的影响'
            },
            '处分评优': {
                'keywords': ['处分', '违纪', '评优', '评选', '资格', '取消'],
                'query_type': 'cross_reference',
                'description': '违纪处分对评优资格的影响'
            },
            '宿舍处分': {
                'keywords': ['宿舍', '违规', '处分', '警告', '记过'],
                'query_type': 'cross_reference',
                'description': '宿舍违规行为的处分规定'
            }
        }

    def is_cross_query(self, query: str) -> Tuple[bool, Optional[Dict]]:
        """判断是否为隐含关联问题"""
        query_lower = query.lower()

        for pattern_name, pattern_info in self.cross_query_patterns.items():
            keywords = pattern_info['keywords']
            # 检查是否包含至少两个关键词
            matched_keywords = [kw for kw in keywords if kw in query_lower]
            if len(matched_keywords) >= 2:
                return True, {
                    'pattern_name': pattern_name,
                    'keywords': matched_keywords,
                    'description': pattern_info['description'],
                    'all_keywords': keywords
                }

        return False, None

    def cross_retrieve(
        self,
        query: str,
        pattern_info: Dict,
        top_k: int = SEARCH_TOP_K
    ) -> Dict:
        """执行交叉检索"""
        start_time = time.time()

        keywords = pattern_info['all_keywords']
        retrieval_results = {}

        # 对每个关键词进行检索
        for keyword in keywords:
            if self.use_chromadb and chroma_knowledge_base and chroma_knowledge_base.is_loaded():
                results = chroma_knowledge_base.search(keyword, top_k=top_k, min_similarity=MIN_SIMILARITY)
            elif knowledge_base.is_loaded():
                results = knowledge_base.search(keyword, top_k=top_k, min_similarity=MIN_SIMILARITY)
            else:
                results = []

            retrieval_results[keyword] = results

        duration = time.time() - start_time

        return {
            'query': query,
            'pattern': pattern_info,
            'retrieval_results': retrieval_results,
            'total_documents': sum(len(results) for results in retrieval_results.values()),
            'duration_ms': duration * 1000
        }

    def compare_and_merge(
        self,
        retrieval_results: Dict,
        query: str
    ) -> Dict:
        """交叉比对并合并结果（改进版）"""
        start_time = time.time()

        # 1. 按章节分组文档（改进版）
        section_groups = defaultdict(list)
        all_documents = []
        sectionless_docs = []

        for keyword, results in retrieval_results.items():
            for doc in results:
                section = doc.get('section', '').strip()

                if section:
                    section_groups[section].append({
                        'document': doc,
                        'keyword': keyword,
                        'similarity': doc.get('similarity', 0)
                    })
                else:
                    sectionless_docs.append({
                        'document': doc,
                        'keyword': keyword,
                        'similarity': doc.get('similarity', 0)
                    })

                all_documents.append(doc)

        # 2. 处理没有章节标题的文档
        if sectionless_docs:
            section_groups['其他相关内容'] = sectionless_docs

        # 3. 识别关键章节（更灵活的识别策略）
        key_sections = []
        for section, docs in section_groups.items():
            unique_keywords = set(doc['keyword'] for doc in docs)
            avg_similarity = sum(doc['similarity'] for doc in docs) / len(docs) if docs else 0
            max_similarity = max(doc['similarity'] for doc in docs) if docs else 0

            # 多重判断标准
            is_key_section = False
            match_reason = ""

            # 标准1：包含2个以上关键词
            if len(unique_keywords) >= 2:
                is_key_section = True
                match_reason = f"{len(unique_keywords)}个关键词"

            # 标准2：包含1个关键词但平均相似度高
            elif len(unique_keywords) >= 1 and avg_similarity > 0.7:
                is_key_section = True
                match_reason = f"平均相似度{avg_similarity:.2f}"

            # 标准3：有高相似度的文档
            elif max_similarity > 0.85:
                is_key_section = True
                match_reason = f"最高相似度{max_similarity:.2f}"

            if is_key_section:
                key_sections.append({
                    'section': section,
                    'keywords': list(unique_keywords),
                    'document_count': len(docs),
                    'documents': docs,
                    'avg_similarity': avg_similarity,
                    'max_similarity': max_similarity,
                    'match_reason': match_reason
                })

        # 4. 按相关性排序关键章节（改进排序）
        key_sections.sort(
            key=lambda x: (
                len(x['keywords']),  # 关键词数量（越多越优先）
                x['avg_similarity'],  # 平均相似度（越高越优先）
                x['document_count']   # 文档数量（越多越优先）
            ),
            reverse=True
        )

        # 5. 生成比对摘要
        comparison_summary = self._generate_comparison_summary(
            key_sections,
            retrieval_results,
            query
        )

        # 6. 生成最终文档列表（去重）
        final_documents = self._deduplicate_documents(all_documents, top_k=10)

        duration = time.time() - start_time

        return {
            'key_sections': key_sections,
            'comparison_summary': comparison_summary,
            'final_documents': final_documents,
            'sectionless_count': len(sectionless_docs),
            'duration_ms': duration * 1000
        }

    def _generate_comparison_summary(
        self,
        key_sections: List[Dict],
        retrieval_results: Dict,
        query: str
    ) -> str:
        """生成交叉比对摘要"""
        if not key_sections:
            return "未找到包含多个关键词的关联章节，将分别展示各关键词的相关规定。"

        summary_parts = []

        # 概述
        summary_parts.append(f"通过交叉检索，发现 {len(key_sections)} 个章节同时涉及多个相关主题：")

        # 每个关键章节的说明
        for i, section_info in enumerate(key_sections[:3], 1):
            section = section_info['section']
            keywords = section_info['keywords']
            doc_count = section_info['document_count']
            match_reason = section_info.get('match_reason', '')

            if section:
                summary_parts.append(f"\n{i}. 《{section}》：")
            else:
                summary_parts.append(f"\n{i}. 相关章节：")

            summary_parts.append(f"   - 涉及关键词：{', '.join(keywords)}")
            summary_parts.append(f"   - 文档数量：{doc_count}")
            if match_reason:
                summary_parts.append(f"   - 匹配原因：{match_reason}")

        # 检索范围说明
        summary_parts.append(f"\n检索范围：共检索 {len(retrieval_results)} 个关键词，获取 {sum(len(r) for r in retrieval_results.values())} 个相关文档。")

        return ''.join(summary_parts)

    def _deduplicate_documents(
        self,
        documents: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """去重文档"""
        seen_ids = set()
        unique_docs = []

        for doc in documents:
            doc_id = doc.get('id', '')
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)

        return unique_docs[:top_k]

    def _extract_key_content(self, text: str, max_chars: int = 150) -> str:
        """提取关键内容，确保句子完整（改进版）"""
        if not text:
            return "（无内容）"

        # 移除多余空格和换行
        text = ' '.join(text.split())

        # 如果文本较短，直接返回
        if len(text) <= max_chars:
            return text

        # 尝试在句子边界截断
        for i in range(max_chars, max_chars - 50, -1):
            if i >= len(text):
                continue
            char = text[i]
            if char in '。！？\n':
                return text[:i+1]

        # 如果找不到句子边界，在空格处截断
        last_space = text.rfind(' ', 0, max_chars)
        if last_space > max_chars // 2:
            return text[:last_space] + '...'

        # 最后截断，添加省略号
        return text[:max_chars-3] + '...'

    def generate_thinking_block(
        self,
        query: str,
        pattern_info: Dict,
        retrieval_results: Dict,
        comparison_result: Dict
    ) -> str:
        """生成 <thinking> 标签内的交叉比对内容（改进版）"""
        thinking_parts = []

        # 1. 问题识别
        thinking_parts.append("## 问题识别")
        thinking_parts.append(f"识别到隐含关联问题：{query}")
        thinking_parts.append(f"问题类型：{pattern_info['description']}")
        thinking_parts.append(f"关联关键词：{', '.join(pattern_info['keywords'])}")
        thinking_parts.append("")

        # 2. 检索策略
        thinking_parts.append("## 检索策略")
        thinking_parts.append(f"采用交叉检索策略，对以下 {len(retrieval_results)} 个关键词分别检索：")
        for keyword, results in retrieval_results.items():
            thinking_parts.append(f"- 「{keyword}」：检索到 {len(results)} 个相关文档")
        thinking_parts.append("")

        # 3. 交叉比对
        thinking_parts.append("## 交叉比对")
        key_sections = comparison_result['key_sections']

        if key_sections:
            thinking_parts.append(f"发现 {len(key_sections)} 个章节同时涉及多个关键词：")

            for i, section_info in enumerate(key_sections[:3], 1):
                section = section_info['section']
                keywords = section_info['keywords']
                doc_count = section_info['document_count']

                # 章节标题
                if section:
                    thinking_parts.append(f"\n{i}. 《{section}》")
                else:
                    thinking_parts.append(f"\n{i}. 相关章节")

                # 涉及关键词
                thinking_parts.append(f"   - 涉及关键词：{', '.join(keywords)}")
                thinking_parts.append(f"   - 文档数量：{doc_count}")

                # 提取关键内容（改进版，避免截断）
                docs = section_info['documents'][:2]
                for j, doc in enumerate(docs, 1):
                    text = doc['document'].get('text', '')
                    content = self._extract_key_content(text, max_chars=150)
                    thinking_parts.append(f"   - 关键内容{j}：{content}")
        else:
            thinking_parts.append("未发现同时涉及多个关键词的章节，将分别展示各关键词的相关规定。")
            thinking_parts.append("\n以下为各关键词检索到的相关规定：")
            for keyword, results in retrieval_results.items():
                if results:
                    thinking_parts.append(f"\n「{keyword}」相关：")
                    for doc in results[:2]:
                        text = doc.get('text', '')
                        content = self._extract_key_content(text, max_chars=120)
                        thinking_parts.append(f"  - {content}")

        thinking_parts.append("")

        # 4. 规章关联分析（动态分析）
        thinking_parts.append("## 规章关联分析")
        correlation = self._analyze_regulation_correlation_dynamic(
            pattern_info,
            comparison_result
        )
        thinking_parts.append(correlation)
        thinking_parts.append("")

        # 5. 结论总结
        thinking_parts.append("## 结论总结")
        thinking_parts.append(comparison_result['comparison_summary'])
        thinking_parts.append("")

        return '\n'.join(thinking_parts)

    def _analyze_regulation_correlation_dynamic(
        self,
        pattern_info: Dict,
        comparison_result: Dict
    ) -> str:
        """动态分析规章关联性（改进版 - 替换硬编码模板）"""
        pattern_name = pattern_info.get('pattern_name', '')
        key_sections = comparison_result['key_sections']

        correlation_parts = []

        # 基础模板
        correlation_parts.append("相关规章关联分析：")

        # 动态生成分析
        if key_sections:
            # 1. 章节关联性分析
            correlation_parts.append("\n1. 章节关联：")
            for section_info in key_sections[:3]:
                section = section_info['section']
                keywords = section_info['keywords']
                match_reason = section_info.get('match_reason', '')
                if section:
                    correlation_parts.append(f"   - 《{section}》：涉及 {', '.join(keywords)} 等关键词（{match_reason}）")

            # 2. 规章内容提取
            if len(key_sections) > 0:
                correlation_parts.append("\n2. 规章要点：")
                for section_info in key_sections[:2]:
                    docs = section_info['documents'][:2]
                    for doc in docs:
                        text = doc['document'].get('text', '')
                        content = self._extract_key_content(text, max_chars=100)
                        correlation_parts.append(f"   - {content}")
        else:
            correlation_parts.append("\n1. 未发现直接关联的章节")
            correlation_parts.append("\n2. 将基于各关键词独立分析相关规定")

        # 3. 根据问题类型补充具体分析
        if pattern_name == '挂科奖学金':
            correlation_parts.append("\n\n3. 影响评估：")
            correlation_parts.append("   - 挂科直接降低智育成绩，影响奖学金评选")
            correlation_parts.append("   - 补考成绩可能无法达到评选标准")
            correlation_parts.append("   - 建议通过补考或重修改善成绩")
        elif pattern_name == '软著加分':
            correlation_parts.append("\n\n3. 加分评估：")
            correlation_parts.append("   - 软著属于创新实践成果，可获加分")
            correlation_parts.append("   - 不同级别软著加分标准不同")
            correlation_parts.append("   - 需按要求准备申请材料")
        elif pattern_name == '专利加分':
            correlation_parts.append("\n\n3. 加分评估：")
            correlation_parts.append("   - 专利属于科技创新成果，可获加分")
            correlation_parts.append("   - 发明专利加分高于实用新型专利")
            correlation_parts.append("   - 需提供专利证书等证明材料")
        elif pattern_name == '竞赛加分':
            correlation_parts.append("\n\n3. 加分评估：")
            correlation_parts.append("   - 竞赛获奖属于实践创新模块")
            correlation_parts.append("   - 竞赛级别（国家级/省级/校级）和获奖等级决定加分数值")
            correlation_parts.append("   - 需提供获奖证书等证明材料")
        elif pattern_name == '转专业':
            correlation_parts.append("\n\n3. 条件分析：")
            correlation_parts.append("   - 转专业有明确的时间窗口和条件要求")
            correlation_parts.append("   - 通常要求原专业成绩良好，无不及格课程")
            correlation_parts.append("   - 部分专业要求达到一定的绩点标准")
        elif pattern_name == '重修费用':
            correlation_parts.append("\n\n3. 费用分析：")
            correlation_parts.append("   - 重修课程按学分收取费用")
            correlation_parts.append("   - 每学分费用有明确规定")
            correlation_parts.append("   - 特定情况（如家庭困难）可申请减免")
        elif pattern_name == '补考绩点':
            correlation_parts.append("\n\n3. 影响分析：")
            correlation_parts.append("   - 补考成绩如实记载，不会标注'补考'字样")
            correlation_parts.append("   - 补考成绩按实际成绩计算绩点")
            correlation_parts.append("   - 补考成绩通常不及格课程不能参与评优")
        elif pattern_name == '处分评优':
            correlation_parts.append("\n\n3. 影响分析：")
            correlation_parts.append("   - 违纪行为将受到相应处分")
            correlation_parts.append("   - 受处分期间取消评优资格")
            correlation_parts.append("   - 处分有明确的解除条件和流程")

        # 4. 结论
        correlation_parts.append("\n\n4. 结论：")
        if key_sections:
            correlation_parts.append("   - 多项规章存在明确关联，需综合考虑")
            correlation_parts.append("   - 建议同时参考所有相关规定")
        else:
            correlation_parts.append("   - 各项规定相对独立，需分别了解")

        return '\n'.join(correlation_parts)

    def process_cross_query(
        self,
        query: str
    ) -> Optional[Dict]:
        """处理隐含关联问题的完整流程"""
        # 1. 判断是否为交叉查询
        is_cross, pattern_info = self.is_cross_query(query)
        if not is_cross:
            return None

        # 2. 执行交叉检索
        retrieval_result = self.cross_retrieve(query, pattern_info)

        # 3. 交叉比对和合并
        comparison_result = self.compare_and_merge(
            retrieval_result['retrieval_results'],
            query
        )

        # 4. 生成 thinking 内容
        thinking_content = self.generate_thinking_block(
            query,
            pattern_info,
            retrieval_result,
            comparison_result
        )

        return {
            'is_cross_query': True,
            'pattern_info': pattern_info,
            'thinking_content': thinking_content,
            'documents': comparison_result['final_documents'],
            'retrieval_duration_ms': retrieval_result['duration_ms'],
            'comparison_duration_ms': comparison_result['duration_ms'],
            'total_duration_ms': retrieval_result['duration_ms'] + comparison_result['duration_ms']
        }


# 全局交叉检索引擎实例
cross_retrieval_engine_improved = CrossRetrievalEngineImproved()