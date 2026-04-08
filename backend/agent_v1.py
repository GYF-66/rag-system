# -*- coding: utf-8 -*-
"""
AI智能体核心模块
精简编排层：负责检索→清洗→上下文构建→回复生成的流水线调度
文本清洗委托给 text_cleaner，回复生成委托给 response_generator
支持重排序和性能监控
"""
import re
import asyncio
import logging
import time
from typing import List, Dict, Optional

from retrieval.knowledge_base import knowledge_base
from pipeline.text_cleaner import text_cleaner
from pipeline.response_generator import ResponseGenerator
from config import (
    AGENT_NAME,
    AGENT_ROLE,
    AGENT_DESCRIPTION,
    TOP_K_RESULTS,
    SEARCH_TOP_K,
    MIN_SIMILARITY,
    MEMORY_CONFIG
)
from utils.memory_monitor import monitor_memory

logger = logging.getLogger(__name__)

# 延迟导入重排序器和指标收集器
_reranker = None
_metrics_collector = None

def get_reranker():
    """获取重排序器实例（延迟加载）"""
    global _reranker
    if _reranker is None:
        try:
            from retrieval.reranker import reranker
            _reranker = reranker
        except ImportError:
            logger.warning("重排序器未找到")
            _reranker = None
    return _reranker

def get_metrics_collector():
    """获取指标收集器实例（延迟加载）"""
    global _metrics_collector
    if _metrics_collector is None:
        try:
            from monitoring.metrics_collector import get_metrics_collector as _get_collector
            _metrics_collector = _get_collector()
        except ImportError:
            logger.warning("指标收集器未找到")
            _metrics_collector = None
    return _metrics_collector

# 延迟导入 LLM 服务避免循环依赖
_llm_service = None

def get_llm_service():
    """获取 LLM 服务实例（延迟加载）"""
    global _llm_service
    if _llm_service is None:
        try:
            from llm_service import llm_service
            _llm_service = llm_service
        except ImportError:
            _llm_service = None
    return _llm_service


class AISpecialtyAgent:
    """人工智能专业智能问答智能体"""

    def __init__(self):
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.description = AGENT_DESCRIPTION
        self._response_gen = ResponseGenerator(AGENT_NAME)

        # 章节标题模式 - 用于识别章节结构
        self.chapter_patterns = [
            r'第[一二三四五六七八九十]+[编章节]',
            r'第\d+[编章节]',
            r'第[一二三四五六七八九十]+[条]',
            r'第\d+[条]',
            r'安徽信息工程学院[^\n]+（实施）办法',
            r'安徽信息工程学院[^\n]+管理[办法细则条例]',
        ]
        self._compiled_chapter_patterns = [re.compile(p) for p in self.chapter_patterns]

    def process_query(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True
    ) -> Dict:
        """处理用户查询（同步）"""
        start_time = time.time()
        sources = []
        context = ""
        cache_hit = False

        if use_rag and knowledge_base.is_loaded():
            # 使用重排序检索
            sources = self._retrieve_and_rerank(query, top_k=SEARCH_TOP_K)
            merged_sources = self._merge_continuous_chunks(sources)
            context = self._build_context(merged_sources)
            sources = merged_sources

        response = self._response_gen.generate(query, context, sources)
        
        # 记录查询指标
        total_latency = time.time() - start_time
        metrics = get_metrics_collector()
        if metrics:
            metrics.track_query(
                query=query,
                total_latency=total_latency,
                num_results=len(sources),
                cache_hit=cache_hit,
                success=True
            )

        return {
            'response': response,
            'sources': sources,
            'context_used': len(sources) > 0
        }

    async def process_query_async(
        self,
        query: str,
        session_history: Optional[List[Dict]] = None,
        use_rag: bool = True,
        use_llm: bool = True
    ) -> Dict:
        """异步处理用户查询（支持 LLM）"""
        start_time = time.time()
        sources = []
        context = ""
        cache_hit = False

        if use_rag and knowledge_base.is_loaded():
            # 使用重排序检索
            sources = self._retrieve_and_rerank(query, top_k=SEARCH_TOP_K)
            merged_sources = self._merge_continuous_chunks(sources)
            context = self._build_context(merged_sources)
            sources = merged_sources

        response = ""
        used_llm = False

        if use_llm:
            llm = get_llm_service()
            if llm and llm.is_available():
                try:
                    gen_start = time.time()
                    response = await llm.chat(query, context, session_history)
                    if response:
                        used_llm = True
                        # 记录生成指标
                        metrics = get_metrics_collector()
                        if metrics:
                            metrics.track_generation(
                                query=query,
                                generation_time=time.time() - gen_start,
                                answer_length=len(response),
                                context_length=len(context),
                                model="llm"
                            )
                except Exception as e:
                    logger.error(f"LLM 调用失败: {e}")
                    response = ""

        if not response:
            response = self._response_gen.generate(query, context, sources)

        # 记录查询指标
        total_latency = time.time() - start_time
        metrics = get_metrics_collector()
        if metrics:
            metrics.track_query(
                query=query,
                total_latency=total_latency,
                num_results=len(sources),
                cache_hit=cache_hit,
                success=True
            )

        return {
            'response': response,
            'sources': sources,
            'context_used': len(sources) > 0,
            'used_llm': used_llm
        }

    # ============ 检索后处理 ============

    def _retrieve_and_rerank(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        检索并重排序
        
        Args:
            query: 查询文本
            top_k: 返回的文档数量
            
        Returns:
            重排序后的文档列表
        """
        retrieval_start = time.time()
        
        # 第一步：初始检索（获取更多候选）
        initial_k = top_k * 3  # 获取3倍候选进行重排序
        candidates = knowledge_base.search(query, top_k=initial_k)
        
        if not candidates:
            return []
        
        # 记录检索时间
        retrieval_time = time.time() - retrieval_start
        
        # 第二步：重排序
        reranker = get_reranker()
        if reranker:
            try:
                rerank_start = time.time()
                reranked = reranker.rerank(query, candidates, top_k=top_k)
                rerank_time = time.time() - rerank_start
                
                # 记录检索指标
                metrics = get_metrics_collector()
                if metrics:
                    metrics.track_retrieval(
                        query=query,
                        retrieval_time=retrieval_time + rerank_time,
                        num_candidates=len(candidates),
                        num_final=len(reranked)
                    )
                
                return reranked
            except Exception as e:
                logger.warning(f"重排序失败: {e}，使用原始结果")
        
        # 如果重排序失败或未启用，返回原始top_k结果
        metrics = get_metrics_collector()
        if metrics:
            metrics.track_retrieval(
                query=query,
                retrieval_time=retrieval_time,
                num_candidates=len(candidates),
                num_final=min(top_k, len(candidates))
            )
        
        return candidates[:top_k]

    def _merge_continuous_chunks(self, sources: List[Dict]) -> List[Dict]:
        """合并连续的知识块，深度清理和去重（内存优化版）"""
        if not sources:
            return []

        sorted_sources = sorted(sources, key=lambda x: x.get('similarity', 0), reverse=True)

        # 第一步：深度清理和过滤
        cleaned_sources = []
        for source in sorted_sources:
            similarity = source.get('similarity', 0)
            if similarity < MIN_SIMILARITY:
                continue

            text = source.get('text', '')
            if not text:
                continue

            cleaned_text = text_cleaner.deep_clean_text(text)

            if not text_cleaner.is_valid_content(cleaned_text):
                continue

            cleaned_sources.append({
                'id': source.get('id', ''),
                'text': cleaned_text,
                'char_count': len(cleaned_text),
                'similarity': source.get('similarity', 0),
                'section': text_cleaner.extract_section_title(cleaned_text, self._compiled_chapter_patterns)
            })

        # 第二步：智能合并连续内容（带缓冲区限制）
        MAX_BUFFER_SIZE = 10  # 最多缓存10个chunk
        MAX_BUFFER_CHARS = 5000  # 最多5000字符
        
        merged = []
        buffer_texts = []
        buffer_id = None
        buffer_sim = 0
        buffer_section = ''

        def flush_buffer():
            """刷新缓冲区"""
            nonlocal buffer_texts, buffer_id, buffer_sim, buffer_section
            if buffer_texts and len(''.join(buffer_texts)) > 80:
                merged_content = ''.join(buffer_texts)
                merged.append({
                    'id': buffer_id,
                    'text': merged_content,
                    'char_count': len(merged_content),
                    'similarity': buffer_sim,
                    'section': buffer_section
                })
            buffer_texts = []
            buffer_id = None
            buffer_sim = 0
            buffer_section = ''

        for source in cleaned_sources:
            text = source['text']
            section = source.get('section', '')

            # 检查缓冲区大小限制
            current_buffer_chars = len(''.join(buffer_texts))
            if len(buffer_texts) >= MAX_BUFFER_SIZE or (current_buffer_chars + len(text) > MAX_BUFFER_CHARS):
                flush_buffer()

            if section and section != buffer_section:
                if buffer_texts and len(''.join(buffer_texts)) > 80:
                    flush_buffer()
                buffer_id = source['id']
                buffer_sim = source['similarity']
                buffer_section = section

            buffer_texts.append(text)
            if not buffer_id:
                buffer_id = source['id']
                buffer_sim = source['similarity']
            if not buffer_section:
                buffer_section = section

            if text.rstrip().endswith(('。', '！', '？', '\n')):
                full_text = ''.join(buffer_texts)
                if len(full_text) > 50 and text_cleaner.is_valid_content(full_text):
                    merged.append({
                        'id': buffer_id,
                        'text': full_text,
                        'char_count': len(full_text),
                        'similarity': buffer_sim,
                        'section': buffer_section
                    })
                buffer_texts = []
                buffer_id = None
                buffer_sim = 0
                buffer_section = ''

        # 刷新剩余缓冲区
        flush_buffer()

        # 第三步：智能去重
        unique_merged = []
        seen_fingerprints = set()

        for item in merged:
            fingerprint = text_cleaner.get_content_fingerprint(item['text'])
            if fingerprint and fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                unique_merged.append(item)

        return unique_merged[:TOP_K_RESULTS]

    def _build_context(self, sources: List[Dict]) -> str:
        """构建上下文，包含来源信息"""
        if not sources:
            return ""

        context_parts = []
        for i, source in enumerate(sources):
            text = source.get('text', '')
            section = source.get('section', '')

            source_info = f"\n\n——来源{i+1}"
            if section:
                source_info += f"《{section[:30]}》"
            else:
                extracted_section = text_cleaner.extract_section_title(text, self._compiled_chapter_patterns)
                if extracted_section:
                    source_info += f"《{extracted_section[:30]}》"
                else:
                    source_info += " 人工智能专业知识库"

            context_parts.append(text + source_info)

        return "\n\n".join(context_parts)

    # ============ 向后兼容方法 ============

    def _extract_keywords(self, query: str) -> list:
        """提取关键词（向后兼容）"""
        import jieba
        stopwords = {'的', '是', '在', '了', '有', '和', '与', '个', '可以', '什么', '怎样', '如何', '哪些', '怎么'}
        return [w for w in jieba.cut(query) if w not in stopwords and len(w) >= 2]

    def _extract_key_sentences(self, text: str, max_sentences: int = 3) -> List[str]:
        """提取关键句子（向后兼容，委托给 text_cleaner）"""
        return text_cleaner.extract_key_sentences(text, max_sentences)

    def _generate_fallback_response(self, query: str) -> str:
        """兜底回复（向后兼容，委托给 response_generator）"""
        return self._response_gen.fallback(query)

    def _detect_query_type(self, query: str) -> str:
        """检测查询意图类型（how_to/yes_no/quantity/general）"""
        if any(kw in query for kw in ['什么', '如何', '怎么', '怎样']):
            return "how_to"
        elif any(kw in query for kw in ['是否', '能不能', '可以']):
            return "yes_no"
        elif any(kw in query for kw in ['哪些', '多少', '几个']):
            return "quantity"
        return "general"

    def _generate_response(self, query, context, history, sources):
        """生成回复（向后兼容，委托给 response_generator）"""
        return self._response_gen.generate(query, context, sources)
    
    async def search_batch(self, queries: List[str], top_k: int = 3) -> List[List[Dict]]:
        """批量处理查询，避免内存峰值"""
        BATCH_SIZE = 5
        all_results = []
        
        for i in range(0, len(queries), BATCH_SIZE):
            batch = queries[i:i+BATCH_SIZE]
            batch_results = []
            
            # 批量检索
            for query in batch:
                if knowledge_base.is_loaded():
                    sources = knowledge_base.search(query, top_k=top_k)
                    batch_results.append(sources)
                else:
                    batch_results.append([])
            
            all_results.extend(batch_results)
            
            # 每批次后清理
            import gc
            gc.collect()
        
        return all_results


# 全局智能体实例
agent = AISpecialtyAgent()

# 向后兼容别名
StudentManualAgent = AISpecialtyAgent