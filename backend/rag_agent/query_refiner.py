"""
查询改进器
实现查询优化策略，包括关键词扩展、查询重写、问题分解
"""

from typing import List, Dict, Optional
import logging
import jieba
import jieba.analyse

logger = logging.getLogger(__name__)


class QueryRefiner:
    """
    查询改进器
    
    策略：
    1. 关键词扩展：添加同义词、相关词
    2. 查询重写：使用LLM改写为更精确的查询
    3. 问题分解：将复杂问题拆分为多个子问题
    4. 上下文融合：结合历史对话上下文
    """
    
    def __init__(self, llm_client=None):
        """
        初始化查询改进器
        
        Args:
            llm_client: LLM客户端（用于查询重写）
        """
        self.llm_client = llm_client
        
        # 同义词词典（简化版）
        self.synonyms = {
            '奖学金': ['助学金', '资助', '补助'],
            '申请': ['办理', '提交', '递交'],
            '条件': ['要求', '标准', '资格'],
            '流程': ['步骤', '程序', '过程'],
            '专业': ['学科', '方向'],
            '课程': ['科目', '课'],
            '考试': ['测试', '考核'],
            '成绩': ['分数', '绩点', 'GPA'],
        }
    
    def refine(self,
               original_query: str,
               failed_results: List[Dict],
               quality_score: any,
               analysis: any = None) -> str:
        """
        改进查询
        
        根据质量评分的弱点选择改进策略
        
        Args:
            original_query: 原始查询
            failed_results: 失败的检索结果
            quality_score: 质量评分
            analysis: 查询分析结果
            
        Returns:
            改进后的查询
        """
        logger.info(f"[QueryRefiner] 开始改进查询: {original_query}")
        logger.info(f"[QueryRefiner] 质量弱点: {quality_score.get_weakness()}")
        
        weakness = quality_score.get_weakness()
        
        # 根据弱点选择策略
        if weakness == 'similarity':
            # 相似度低：扩展关键词
            refined = self._expand_keywords(original_query)
            logger.info(f"[QueryRefiner] 策略: 关键词扩展")
        
        elif weakness == 'coverage':
            # 覆盖度低：重写查询
            refined = self._rewrite_query(original_query, failed_results)
            logger.info(f"[QueryRefiner] 策略: 查询重写")
        
        elif weakness == 'completeness':
            # 完整性低：分解问题
            refined = self._decompose_query(original_query)
            logger.info(f"[QueryRefiner] 策略: 问题分解")
        
        else:
            # 默认：简化查询
            refined = self._simplify_query(original_query)
            logger.info(f"[QueryRefiner] 策略: 查询简化")
        
        logger.info(f"[QueryRefiner] 改进后: {refined}")
        return refined
    
    def _expand_keywords(self, query: str) -> str:
        """
        关键词扩展
        
        添加同义词和相关词
        """
        # 提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=5, withWeight=False)
        
        # 扩展同义词
        expanded = []
        for keyword in keywords:
            expanded.append(keyword)
            # 查找同义词
            if keyword in self.synonyms:
                expanded.extend(self.synonyms[keyword][:2])  # 最多添加2个同义词
        
        # 去重并保持顺序
        seen = set()
        unique_expanded = []
        for word in expanded:
            if word not in seen:
                seen.add(word)
                unique_expanded.append(word)
        
        # 构建扩展查询
        if len(unique_expanded) > len(keywords):
            expanded_query = query + " " + " ".join(unique_expanded[len(keywords):])
            return expanded_query
        
        return query
    
    def _rewrite_query(self, query: str, failed_results: List[Dict]) -> str:
        """
        查询重写
        
        使用LLM改写为更精确的查询
        """
        if self.llm_client:
            try:
                # 构建重写提示
                prompt = f"""请将以下查询改写为更精确、更容易检索的形式。
保持原意，但使用更规范的表达。

原查询：{query}

改写后的查询："""
                
                # 调用LLM
                response = self.llm_client.generate(prompt, max_tokens=100)
                rewritten = response.strip()
                
                if rewritten and rewritten != query:
                    return rewritten
            
            except Exception as e:
                logger.warning(f"[QueryRefiner] LLM重写失败: {str(e)}")
        
        # 降级：使用规则重写
        return self._rule_based_rewrite(query)
    
    def _rule_based_rewrite(self, query: str) -> str:
        """
        基于规则的查询重写
        
        简单的规则转换
        """
        # 移除口语化表达
        replacements = {
            '怎么': '如何',
            '咋': '如何',
            '啥': '什么',
            '咋样': '怎样',
            '能不能': '是否可以',
            '可不可以': '是否可以',
        }
        
        rewritten = query
        for old, new in replacements.items():
            rewritten = rewritten.replace(old, new)
        
        # 添加规范化后缀
        if '?' not in rewritten and '？' not in rewritten:
            if any(word in rewritten for word in ['如何', '怎样', '方法']):
                rewritten += '的方法'
            elif any(word in rewritten for word in ['什么', '哪些']):
                rewritten += '有哪些'
        
        return rewritten if rewritten != query else query
    
    def _decompose_query(self, query: str) -> str:
        """
        问题分解
        
        将复杂问题拆分为更简单的子问题
        """
        # 检测是否包含多个问题
        separators = ['，', '、', '和', '以及', '还有']
        
        for sep in separators:
            if sep in query:
                # 拆分并取第一个子问题
                parts = query.split(sep)
                if len(parts) > 1:
                    first_part = parts[0].strip()
                    logger.info(f"[QueryRefiner] 问题分解: {query} -> {first_part}")
                    return first_part
        
        # 如果无法分解，尝试提取核心问题
        return self._extract_core_question(query)
    
    def _extract_core_question(self, query: str) -> str:
        """
        提取核心问题
        
        去除修饰词，保留核心查询
        """
        # 提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=3, withWeight=False)
        
        if keywords:
            # 构建简化查询
            core_query = " ".join(keywords)
            return core_query
        
        return query
    
    def _simplify_query(self, query: str) -> str:
        """
        简化查询
        
        移除冗余词汇，保留核心内容
        """
        # 移除常见的冗余词
        redundant_words = [
            '请问', '想问', '我想知道', '能告诉我',
            '麻烦', '谢谢', '请', '帮忙'
        ]
        
        simplified = query
        for word in redundant_words:
            simplified = simplified.replace(word, '')
        
        # 清理多余空格
        simplified = ' '.join(simplified.split())
        
        return simplified.strip() if simplified.strip() else query
    
    def add_context(self, 
                   query: str, 
                   session_history: List[Dict]) -> str:
        """
        添加上下文
        
        将历史对话上下文融合到查询中
        """
        if not session_history:
            return query
        
        # 提取最近的相关上下文
        recent_context = []
        for item in session_history[-3:]:  # 最近3轮对话
            if 'query' in item:
                recent_context.append(item['query'])
        
        if recent_context:
            # 构建带上下文的查询
            context_str = "；".join(recent_context)
            contextualized = f"基于之前的问题（{context_str}），{query}"
            return contextualized
        
        return query
