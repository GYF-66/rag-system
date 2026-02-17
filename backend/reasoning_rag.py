"""
Reasoning-RAG (推理增强检索) 模块

核心功能：
1. 向量数据库语义搜索（基于 ChromaDB）
2. 多步检索逻辑（Multi-step Retrieval）
3. AI 思考过程输出（Thinking Process）
4. 上下文智能聚合与推理
"""

import logging
from typing import List, Dict, Optional, Tuple
import re
from collections import Counter

from knowledge_base import knowledge_base
from config import (
    TOP_K_RESULTS,
    SEARCH_TOP_K,
    MIN_SIMILARITY,
    USE_CHROMADB
)

logger = logging.getLogger(__name__)


class ReasoningRAG:
    """推理增强检索系统"""

    def __init__(self):
        self.use_vector_db = USE_CHROMADB
        logger.info(f"Reasoning-RAG 初始化完成，向量数据库: {'启用' if self.use_vector_db else '禁用'}")

    def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        处理查询，返回推理过程和结果

        Args:
            query: 用户查询
            session_history: 会话历史

        Returns:
            包含 thinking_process, response, sources 的字典
        """
        # 步骤1：查询分析
        thinking_steps = []
        thinking_steps.append({
            "step": 1,
            "action": "查询分析",
            "content": f"分析用户查询: '{query}'",
            "details": self._analyze_query(query)
        })

        # 步骤2：多步检索
        thinking_steps.append({
            "step": 2,
            "action": "多步检索",
            "content": "执行多步检索获取相关信息"
        })

        # 第一轮：直接检索
        direct_results = self._retrieve_direct(query, thinking_steps)

        # 第二轮：扩展检索（基于关键词和语义）
        expanded_results = self._retrieve_expanded(query, thinking_steps)

        # 第三轮：上下文检索（如果有多轮对话）
        context_results = []
        if session_history and len(session_history) > 0:
            context_results = self._retrieve_contextual(query, session_history, thinking_steps)

        # 步骤3：智能聚合
        thinking_steps.append({
            "step": 3,
            "action": "智能聚合",
            "content": "聚合多轮检索结果，去重和排序"
        })

        merged_sources = self._merge_retrieval_results(
            direct_results,
            expanded_results,
            context_results,
            thinking_steps
        )

        # 步骤4：相关性推理
        thinking_steps.append({
            "step": 4,
            "action": "相关性推理",
            "content": "评估检索结果的相关性和完整性"
        })

        relevance_analysis = self._analyze_relevance(query, merged_sources, thinking_steps)

        # 步骤5：答案合成
        thinking_steps.append({
            "step": 5,
            "action": "答案合成",
            "content": "基于检索结果合成最终答案"
        })

        response = self._synthesize_answer(query, merged_sources, relevance_analysis, thinking_steps)

        # 格式化思考过程
        formatted_thinking = self._format_thinking_process(thinking_steps)

        return {
            "thinking_process": formatted_thinking,
            "response": response,
            "sources": merged_sources[:TOP_K_RESULTS],
            "relevance_score": relevance_analysis.get("overall_score", 0),
            "confidence_level": relevance_analysis.get("confidence", "low")
        }

    def _analyze_query(self, query: str) -> Dict:
        """分析查询意图和关键词"""
        query_lower = query.lower()

        # 提取关键词
        chinese_keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', query)
        keywords = list(set(chinese_keywords[:10]))

        # 识别查询类型
        query_types = []
        if '奖学金' in query_lower or '助学金' in query_lower:
            query_types.append('scholarship')
        if '考试' in query_lower or '补考' in query_lower or '重修' in query_lower:
            query_types.append('exam')
        if '申请' in query_lower or '条件' in query_lower or '流程' in query_lower:
            query_types.append('procedure')
        if '条件' in query_lower or '要求' in query_lower:
            query_types.append('condition')

        # 识别疑问词
        question_words = ['怎么', '如何', '什么', '为什么', '哪里', '多少', '如何']
        has_question = any(qw in query_lower for qw in question_words)

        return {
            "keywords": keywords,
            "query_types": query_types,
            "is_question": has_question,
            "length": len(query)
        }

    def _retrieve_direct(self, query: str, thinking_steps: List[Dict]) -> List[Dict]:
        """直接检索"""
        results = knowledge_base.search(query, top_k=SEARCH_TOP_K, min_similarity=MIN_SIMILARITY)

        thinking_steps.append({
            "step": 2.1,
            "action": "直接检索",
            "content": f"直接检索得到 {len(results)} 个结果",
            "details": [{"id": r.get('id'), "similarity": r.get('similarity', 0), "preview": r.get('text', '')[:50]} for r in results[:5]]
        })

        return results

    def _retrieve_expanded(self, query: str, thinking_steps: List[Dict]) -> List[Dict]:
        """扩展检索"""
        # 提取查询中的核心词
        core_keywords = self._extract_core_keywords(query)

        expanded_results = []
        for keyword in core_keywords[:3]:  # 扩展检索最多3个关键词
            results = knowledge_base.search(keyword, top_k=5, min_similarity=MIN_SIMILARITY * 0.9)
            for result in results:
                # 避免重复
                if not any(r.get('id') == result.get('id') for r in expanded_results):
                    expanded_results.append(result)

        thinking_steps.append({
            "step": 2.2,
            "action": "扩展检索",
            "content": f"基于关键词 {core_keywords} 扩展检索得到 {len(expanded_results)} 个额外结果"
        })

        return expanded_results

    def _retrieve_contextual(self, query: str, history: List[Dict], thinking_steps: List[Dict]) -> List[Dict]:
        """基于上下文检索"""
        # 分析历史对话，提取上下文关键词
        context_keywords = []
        for msg in history[-3:]:  # 只看最近3轮
            if msg.get('role') == 'user':
                keywords = re.findall(r'[\u4e00-\u9fff]{2,3}', msg.get('content', ''))
                context_keywords.extend(keywords[:3])

        context_results = []
        if context_keywords:
            for keyword in context_keywords[:2]:
                results = knowledge_base.search(keyword, top_k=5, min_similarity=MIN_SIMILARITY * 0.85)
                for result in results:
                    if not any(r.get('id') == result.get('id') for r in context_results):
                        context_results.append(result)

        thinking_steps.append({
            "step": 2.3,
            "action": "上下文检索",
            "content": f"基于会话历史上下文检索得到 {len(context_results)} 个结果"
        })

        return context_results

    def _merge_retrieval_results(
        self,
        direct_results: List[Dict],
        expanded_results: List[Dict],
        context_results: List[Dict],
        thinking_steps: List[Dict]
    ) -> List[Dict]:
        """合并多轮检索结果"""
        all_results = {}

        # 按优先级添加结果
        for result in direct_results:
            rid = result.get('id')
            if rid not in all_results:
                all_results[rid] = {
                    **result,
                    "source_type": "direct",
                    "priority_score": result.get('similarity', 0) * 1.0
                }

        for result in expanded_results:
            rid = result.get('id')
            if rid not in all_results:
                all_results[rid] = {
                    **result,
                    "source_type": "expanded",
                    "priority_score": result.get('similarity', 0) * 0.8
                }

        for result in context_results:
            rid = result.get('id')
            if rid not in all_results:
                all_results[rid] = {
                    **result,
                    "source_type": "contextual",
                    "priority_score": result.get('similarity', 0) * 0.7
                }

        # 排序
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x["priority_score"],
            reverse=True
        )

        thinking_steps.append({
            "step": 3.1,
            "action": "结果合并",
            "content": f"合并后共 {len(sorted_results)} 个唯一结果",
            "details": {
                "direct": len([r for r in sorted_results if r.get('source_type') == 'direct']),
                "expanded": len([r for r in sorted_results if r.get('source_type') == 'expanded']),
                "contextual": len([r for r in sorted_results if r.get('source_type') == 'contextual'])
            }
        })

        return sorted_results

    def _analyze_relevance(self, query: str, sources: List[Dict], thinking_steps: List[Dict]) -> Dict:
        """分析检索结果的相关性"""
        if not sources:
            return {
                "overall_score": 0,
                "confidence": "low",
                "analysis": "未找到相关结果"
            }

        # 计算平均相似度
        similarities = [s.get('similarity', 0) for s in sources]
        avg_similarity = sum(similarities) / len(similarities)
        max_similarity = max(similarities)

        # 评估覆盖度
        query_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,3}', query))
        coverage_count = 0
        for source in sources[:5]:
            source_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,3}', source.get('text', '')))
            coverage_count += len(query_keywords & source_keywords)

        coverage_ratio = coverage_count / len(query_keywords) if query_keywords else 0

        # 评估置信度
        confidence = "low"
        if max_similarity > 0.7 and avg_similarity > 0.5:
            confidence = "high"
        elif max_similarity > 0.5 and avg_similarity > 0.3:
            confidence = "medium"

        analysis = {
            "overall_score": avg_similarity,
            "max_score": max_similarity,
            "confidence": confidence,
            "coverage_ratio": coverage_ratio,
            "result_count": len(sources),
            "analysis": f"检索到{len(sources)}个结果，最高相似度{max_similarity:.2f}，平均相似度{avg_similarity:.2f}"
        }

        thinking_steps.append({
            "step": 4.1,
            "action": "相关性评估",
            "content": analysis["analysis"],
            "details": analysis
        })

        return analysis

    def _synthesize_answer(
        self,
        query: str,
        sources: List[Dict],
        relevance: Dict,
        thinking_steps: List[Dict]
    ) -> str:
        """合成最终答案"""
        if not sources:
            return f"抱歉，我没有找到关于'{query}'的相关信息。"

        # 根据相关性选择回答策略
        if relevance["confidence"] == "high":
            return self._synthesize_detailed_answer(query, sources[:TOP_K_RESULTS], thinking_steps)
        else:
            return self._synthesize_cautious_answer(query, sources[:TOP_K_RESULTS], thinking_steps)

    def _synthesize_detailed_answer(self, query: str, sources: List[Dict], thinking_steps: List[Dict]) -> str:
        """合成详细答案（高置信度）"""
        response_parts = []

        # 提取关键信息
        for i, source in enumerate(sources, 1):
            text = source.get('text', '')
            section = source.get('section', '')
            similarity = source.get('similarity', 0)

            sentences = re.split(r'[。！？\n]', text)
            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

            response_parts.append(f"\n【来源{i}】")
            if section:
                response_parts.append(f"  所属篇章: {section}")
            response_parts.append(f"  相似度: {similarity:.2f}")
            response_parts.append(f"  关键内容:")
            for sent in key_sentences[:3]:
                response_parts.append(f"    • {sent}")

        # 添加总结
        response_parts.append(f"\n【总结】")
        response_parts.append(f"  基于以上{len(sources)}个相关来源，为您提供了关于'{query}'的详细信息。")
        response_parts.append(f"  建议您结合实际情况进一步查阅《学生手册2024版》的完整内容。")

        return '\n'.join(response_parts)

    def _synthesize_cautious_answer(self, query: str, sources: List[Dict], thinking_steps: List[Dict]) -> str:
        """合成谨慎答案（低置信度）"""
        response_parts = []

        response_parts.append(f"关于'{query}'，我找到了一些相关信息，但可能不够完整：")

        for i, source in enumerate(sources, 1):
            text = source.get('text', '')
            section = source.get('section', '')

            # 提取最相关的句子
            sentences = re.split(r'[。！？\n]', text)
            relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

            response_parts.append(f"\n【参考信息{i}】")
            if section:
                response_parts.append(f"  {section}")
            if relevant_sentences:
                response_parts.append(f"  {relevant_sentences[0]}")

        response_parts.append(f"\n【建议】")
        response_parts.append(f"  由于找到的相关信息有限，建议您：")
        response_parts.append(f"  1. 查阅《学生手册2024版》完整内容")
        response_parts.append(f"  2. 咨询相关部门（教务处、学生处、辅导员等）")
        response_parts.append(f"  3. 尝试用不同的方式重新提问")

        return '\n'.join(response_parts)

    def _extract_core_keywords(self, query: str) -> List[str]:
        """提取核心关键词"""
        # 移除常见的疑问词和停用词
        stop_words = {'怎么', '如何', '什么', '为什么', '哪里', '多少', '的', '是', '在', '和', '了'}

        # 提取2-4个字的中文词
        all_words = re.findall(r'[\u4e00-\u9fff]{2,4}', query)

        # 过滤停用词并返回
        core_keywords = [w for w in all_words if w not in stop_words]

        return core_keywords[:5]

    def _format_thinking_process(self, thinking_steps: List[Dict]) -> str:
        """格式化思考过程为可读文本"""
        formatted = []
        formatted.append("## AI 思考过程\n")

        for step in thinking_steps:
            step_num = step.get("step", "")
            action = step.get("action", "")
            content = step.get("content", "")

            # 主步骤
            if isinstance(step_num, int):
                formatted.append(f"**{action}**")
                formatted.append(f"{content}")
            # 子步骤
            else:
                formatted.append(f"  - {content}")

            # 添加详细信息
            details = step.get("details")
            if details and isinstance(details, dict):
                for key, value in details.items():
                    formatted.append(f"  - {key}: {value}")

            formatted.append("")

        return '\n'.join(formatted).strip()


# 全局实例
reasoning_rag = ReasoningRAG()