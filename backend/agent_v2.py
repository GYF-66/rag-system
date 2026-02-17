# -*- coding: utf-8 -*-
"""
AI智能体核心模块 - Reasoning-RAG 版本
整合 ChromaDB 向量检索、Rerank 重排序和推理引擎
"""
from datetime import datetime
from typing import List, Dict, Optional
import re
import time

from models import ChatResponse, ThinkingProcess, KnowledgeChunk, ThinkingStep
from config import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_DESCRIPTION,
    TOP_K_RESULTS,
    SEARCH_TOP_K,
    MAX_CONTEXT_LENGTH
)
from reasoning_engine import reasoning_engine
from reranker import reranker
from cross_retrieval_engine import cross_retrieval_engine

# 尝试导入 ChromaDB
try:
    from chroma_knowledge_base import chroma_knowledge_base
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chroma_knowledge_base = None

# 降级到原始知识库
from knowledge_base import knowledge_base


class StudentManualAgentV2:
    """学生手册智能问答智能体 - Reasoning-RAG 版本"""

    def __init__(self):
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.description = AGENT_DESCRIPTION
        self.use_chromadb = CHROMADB_AVAILABLE and chroma_knowledge_base is not None

        # 章节标题模式
        self.chapter_patterns = [
            r'第[一二三四五六七八九十]+[编章节]',
            r'第\d+[编章节]',
            r'第[一二三四五六七八九十]+[条]',
            r'第\d+[条]',
            r'安徽信息工程学院[^\n]+（实施）办法',
            r'安徽信息工程学院[^\n]+管理[办法细则条例]',
        ]

    def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True,
        enable_thinking: bool = True
    ) -> Dict:
        """
        处理用户查询 - Reasoning-RAG 版本

        Args:
            query: 用户查询
            session_history: 会话历史
            use_rag: 是否使用RAG检索
            enable_thinking: 是否显示思考过程

        Returns:
            包含回复、知识来源和思考过程的字典
        """
        total_start = time.time()

        # 1. 查询分析
        step1_start = time.time()
        query_analysis = self._analyze_query(query)
        step1_duration = (time.time() - step1_start) * 1000

        # 2. 检索
        step2_start = time.time()
        sources = []
        context = ""
        is_cross_query = False
        cross_reasoning = None

        if use_rag:
            # 检测是否为交叉查询
            if cross_retrieval_engine:
                cross_result = cross_retrieval_engine.process_cross_query(query)
                is_cross_query = cross_result['is_cross_query']
                cross_reasoning = cross_result['thinking_content']

                if is_cross_query:
                    sources = cross_result['final_documents']
                else:
                    # 普通查询
                    if self.use_chromadb:
                        sources = chroma_knowledge_base.search(query, top_k=SEARCH_TOP_K)
                    else:
                        sources = knowledge_base.search(query, top_k=SEARCH_TOP_K)
            else:
                # 没有交叉检索引擎，使用普通检索
                if self.use_chromadb:
                    sources = chroma_knowledge_base.search(query, top_k=SEARCH_TOP_K)
                else:
                    sources = knowledge_base.search(query, top_k=SEARCH_TOP_K)

            # 重排序
            if reranker and len(sources) > 0:
                sources = reranker.rerank(query, sources)
                sources = sources[:TOP_K_RESULTS]

            context = self._build_context(sources)

        step2_duration = (time.time() - step2_start) * 1000

        # 3. 推理
        step3_start = time.time()
        reasoning_steps = []
        if reasoning_engine and enable_thinking:
            reasoning_steps = reasoning_engine.reason(query, context, sources)
        step3_duration = (time.time() - step3_start) * 1000

        # 4. 生成回复
        step4_start = time.time()
        response = self._generate_response(query, context, session_history, sources)
        step4_duration = (time.time() - step4_start) * 1000

        # 5. 构建思考过程
        thinking_process = None
        if enable_thinking:
            thinking_process = self._build_thinking_process(
                query_analysis,
                sources,
                reasoning_steps,
                [step1_duration, step2_duration, step3_duration, step4_duration]
            )

        total_duration = (time.time() - total_start) * 1000

        return {
            'response': response,
            'sources': sources,
            'thinking_process': thinking_process,
            'cross_reasoning': cross_reasoning,
            'is_cross_query': is_cross_query,
            'metadata': {
                'retrieval_method': 'chromadb' if self.use_chromadb else 'tfidf',
                'rerank_method': 'cross_encoder' if reranker and reranker.use_cross_encoder else 'rule_based',
                'is_cross_query': is_cross_query,
                'total_duration_ms': total_duration
            }
        }

    def _analyze_query(self, query: str) -> Dict:
        """分析查询意图"""
        keywords = []
        # 使用 jieba 分词
        import jieba
        for word in jieba.cut(query):
            if len(word) > 1:
                keywords.append(word)

        # 检测查询类型
        query_type = "general"
        if any(kw in query for kw in ['什么', '如何', '怎么', '怎样']):
            query_type = "how_to"
        elif any(kw in query for kw in ['是否', '能不能', '可以']):
            query_type = "yes_no"
        elif any(kw in query for kw in ['哪些', '多少', '几个']):
            query_type = "quantity"

        return {
            'keywords': keywords,
            'query_type': query_type,
            'complexity': len(keywords)
        }

    def _build_context(self, sources: List[Dict]) -> str:
        """构建上下文"""
        if not sources:
            return ""

        context_parts = []
        for i, source in enumerate(sources, 1):
            text = source.get('text', '')
            section = source.get('section', '')
            similarity = source.get('similarity', 0)
            rerank_score = source.get('rerank_score', 0)

            context_parts.append(f"[来源{i}] {section}")
            context_parts.append(f"({similarity:.2f}, rerank: {rerank_score:.2f})")
            context_parts.append(text)
            context_parts.append("")

        return '\n'.join(context_parts)

    def _generate_response(self, query: str, context: str, history: Optional[List[Dict]], sources: List[Dict]) -> str:
        """生成回复"""
        if not sources:
            return f"抱歉，我在《学生手册》中没有找到与「{query}」直接相关的信息。建议您咨询辅导员或查看《学生手册》完整内容。"

        response_parts = []
        response_parts.append("根据《学生手册》相关规定：")

        for i, source in enumerate(sources[:3], 1):
            text = source.get('text', '')
            section = source.get('section', '')
            similarity = source.get('similarity', 0)
            rerank_score = source.get('rerank_score', similarity)

            # 提取关键句子
            sentences = self._extract_key_sentences(text, 3)
            if sentences:
                response_parts.append(f"\n【{section if section else '相关规定'}】")
                for sent in sentences:
                    response_parts.append(f"{sent}")

        response_parts.append("\n\n温馨提示：如需了解更多详细信息，建议查阅《学生手册》完整内容或咨询相关部门。")

        return '\n'.join(response_parts)

    def _extract_key_sentences(self, text: str, max_sentences: int = 3) -> List[str]:
        """提取关键句子"""
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？\n]', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s) > 10]

        return sentences[:max_sentences]

    def _build_thinking_process(
        self,
        query_analysis: Dict,
        sources: List[Dict],
        reasoning_steps: List[Dict],
        durations: List[float]
    ) -> ThinkingProcess:
        """构建思考过程"""
        # 查询分析步骤
        query_step = ThinkingStep(
            step_id=1,
            step_name="查询分析",
            description="分析用户查询意图和关键词",
            input_data={'query': query_analysis.get('keywords', [])},
            output_data={'query_type': query_analysis.get('query_type')},
            reasoning=f"识别到查询类型为「{query_analysis.get('query_type')}」，关键词为：{', '.join(query_analysis.get('keywords', []))}",
            duration_ms=durations[0]
        )

        # 检索步骤
        retrieval_step = ThinkingStep(
            step_id=2,
            step_name="知识检索",
            description="从知识库检索相关内容",
            input_data={'top_k': SEARCH_TOP_K},
            output_data={'retrieved_count': len(sources)},
            reasoning=f"使用{'ChromaDB向量检索' if self.use_chromadb else 'TF-IDF检索'}，检索到{len(sources)}个相关文档",
            duration_ms=durations[1]
        )

        # 重排序步骤
        rerank_step = ThinkingStep(
            step_id=3,
            step_name="结果重排序",
            description="对检索结果进行重排序",
            input_data={'method': 'cross_encoder' if reranker and reranker.use_cross_encoder else 'rule_based'},
            output_data={'reranked_count': len(sources[:TOP_K_RESULTS])},
            reasoning=f"使用{'交叉编码器' if reranker and reranker.use_cross_encoder else '规则'}进行重排序，保留{TOP_K_RESULTS}个最相关结果",
            duration_ms=durations[2]
        )

        # 推理步骤
        reasoning_text = "基于检索结果进行逻辑推理"
        if reasoning_steps:
            reasoning_text = f"执行{len(reasoning_steps)}步推理："
            for step in reasoning_steps:
                reasoning_text += f"\n- {step.get('description', '')}"

        reasoning_step = ThinkingStep(
            step_id=4,
            step_name="逻辑推理",
            description="基于知识库内容进行推理",
            input_data={'source_count': len(sources)},
            output_data={'reasoning_steps': len(reasoning_steps)},
            reasoning=reasoning_text,
            duration_ms=durations[3]
        )

        # 总结
        summary = f"完成查询处理，检索到{len(sources)}个相关文档，生成回复。"

        return ThinkingProcess(
            query_analysis=query_step,
            retrieval=retrieval_step,
            reranking=rerank_step,
            reasoning=reasoning_step,
            summary=summary,
            total_duration_ms=sum(durations)
        )


# 创建全局实例
agent_v2 = StudentManualAgentV2()