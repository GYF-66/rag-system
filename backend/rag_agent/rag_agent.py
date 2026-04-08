"""
RAG Agent核心实现
实现Think-Decide-Act-Observe循环的智能检索Agent
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """结果质量评分"""
    similarity: float  # 相似度评分 (0-1)
    coverage: float    # 覆盖度评分 (0-1)
    diversity: float   # 多样性评分 (0-1)
    completeness: float  # 完整性评分 (0-1)
    confidence: float  # 综合置信度 (0-1)
    
    def is_sufficient(self, threshold: float = 0.7) -> bool:
        """判断质量是否足够"""
        return self.confidence >= threshold
    
    def get_weakness(self) -> str:
        """识别主要弱点"""
        scores = {
            'similarity': self.similarity,
            'coverage': self.coverage,
            'diversity': self.diversity,
            'completeness': self.completeness
        }
        min_aspect = min(scores.items(), key=lambda x: x[1])
        return min_aspect[0]


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    query_type: str  # 查询类型: factual, policy, procedural, complex
    keywords: List[str]  # 关键词列表
    intent: str  # 用户意图
    complexity: str  # 复杂度: simple, medium, complex
    requires_context: bool  # 是否需要上下文
    
    
@dataclass
class IterationRecord:
    """单次迭代记录"""
    iteration: int
    timestamp: datetime
    analysis: QueryAnalysis
    strategy: str
    tool_used: str
    results_count: int
    quality_score: QualityScore
    decision: str
    refined_query: Optional[str] = None


@dataclass
class AgentResult:
    """Agent执行结果"""
    success: bool
    answer: str
    sources: List[Dict]
    thinking_process: List[IterationRecord]
    final_quality: QualityScore
    total_iterations: int
    error: Optional[str] = None


class RAGAgent:
    """
    RAG智能Agent
    实现自适应检索循环：Think -> Decide -> Act -> Observe
    """
    
    def __init__(self, 
                 tools: Dict[str, Any],
                 evaluator: Any,
                 query_refiner: Any,
                 max_iterations: int = 3,
                 quality_threshold: float = 0.7):
        """
        初始化RAG Agent
        
        Args:
            tools: 可用工具字典 {tool_name: tool_instance}
            evaluator: 结果质量评估器
            query_refiner: 查询改进器
            max_iterations: 最大迭代次数
            quality_threshold: 质量阈值
        """
        self.tools = tools
        self.evaluator = evaluator
        self.query_refiner = query_refiner
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.history: List[IterationRecord] = []
        
    def run(self, 
            query: str, 
            session_history: Optional[List[Dict]] = None) -> AgentResult:
        """
        执行Agent循环
        
        Args:
            query: 用户查询
            session_history: 会话历史
            
        Returns:
            AgentResult: 执行结果
        """
        self.history = []
        current_query = query
        best_results = None
        best_quality = None
        
        try:
            for iteration in range(1, self.max_iterations + 1):
                logger.info(f"开始第 {iteration} 次迭代，查询: {current_query}")
                
                # Think: 分析查询
                analysis = self._analyze_query(current_query, session_history)
                logger.info(f"查询分析: 类型={analysis.query_type}, 复杂度={analysis.complexity}")
                
                # Decide: 选择策略
                strategy = self._select_strategy(analysis, iteration)
                logger.info(f"选择策略: {strategy}")
                
                # Act: 执行检索
                results = self._execute_tool(strategy, current_query, session_history)
                logger.info(f"检索完成: 获得 {len(results)} 个结果")
                
                # Observe: 评估结果
                quality = self._evaluate_results(results, current_query, analysis)
                logger.info(f"质量评估: 置信度={quality.confidence:.2f}, 弱点={quality.get_weakness()}")
                
                # 记录本次迭代
                record = IterationRecord(
                    iteration=iteration,
                    timestamp=datetime.now(),
                    analysis=analysis,
                    strategy=strategy,
                    tool_used=strategy,
                    results_count=len(results),
                    quality_score=quality,
                    decision=""
                )
                
                # 保存最佳结果
                if best_quality is None or quality.confidence > best_quality.confidence:
                    best_results = results
                    best_quality = quality
                
                # 判断是否满足质量要求
                if quality.is_sufficient(self.quality_threshold):
                    record.decision = "质量满足要求，生成答案"
                    self.history.append(record)
                    logger.info("质量满足要求，结束迭代")
                    break
                
                # 如果是最后一次迭代
                if iteration == self.max_iterations:
                    record.decision = "达到最大迭代次数，使用最佳结果"
                    self.history.append(record)
                    logger.warning("达到最大迭代次数")
                    break
                
                # 改进查询
                refined_query = self._refine_query(
                    current_query, 
                    results, 
                    quality,
                    analysis
                )
                record.decision = f"质量不足（{quality.get_weakness()}），改进查询"
                record.refined_query = refined_query
                self.history.append(record)
                
                current_query = refined_query
                logger.info(f"查询已改进: {refined_query}")
            
            # 生成最终答案
            if best_results:
                answer = self._generate_answer(best_results, query, best_quality)
                return AgentResult(
                    success=True,
                    answer=answer,
                    sources=best_results,
                    thinking_process=self.history,
                    final_quality=best_quality,
                    total_iterations=len(self.history)
                )
            else:
                return AgentResult(
                    success=False,
                    answer="抱歉，未能找到相关信息。",
                    sources=[],
                    thinking_process=self.history,
                    final_quality=QualityScore(0, 0, 0, 0, 0),
                    total_iterations=len(self.history),
                    error="未检索到任何结果"
                )
                
        except Exception as e:
            logger.error(f"Agent执行失败: {str(e)}", exc_info=True)
            return AgentResult(
                success=False,
                answer=f"系统错误: {str(e)}",
                sources=[],
                thinking_process=self.history,
                final_quality=QualityScore(0, 0, 0, 0, 0),
                total_iterations=len(self.history),
                error=str(e)
            )
    
    def _analyze_query(self, 
                       query: str, 
                       session_history: Optional[List[Dict]] = None) -> QueryAnalysis:
        """
        Think阶段: 分析查询
        
        识别查询类型、提取关键词、判断复杂度
        """
        # 简单的查询类型识别
        query_lower = query.lower()
        
        # 识别查询类型
        if any(word in query_lower for word in ['什么', '是什么', '定义', '概念']):
            query_type = 'factual'
        elif any(word in query_lower for word in ['政策', '规定', '要求', '条件', '标准']):
            query_type = 'policy'
        elif any(word in query_lower for word in ['如何', '怎么', '流程', '步骤', '方法']):
            query_type = 'procedural'
        else:
            query_type = 'complex'
        
        # 提取关键词（简化版，实际应使用jieba等工具）
        import jieba
        keywords = [word for word in jieba.cut(query) if len(word) > 1]
        
        # 判断复杂度
        if len(keywords) <= 3 and '?' not in query and '，' not in query:
            complexity = 'simple'
        elif len(keywords) <= 6:
            complexity = 'medium'
        else:
            complexity = 'complex'
        
        # 判断是否需要上下文
        requires_context = bool(session_history and len(session_history) > 0)
        
        return QueryAnalysis(
            query_type=query_type,
            keywords=keywords[:5],  # 保留前5个关键词
            intent=query_type,
            complexity=complexity,
            requires_context=requires_context
        )
    
    def _select_strategy(self, 
                        analysis: QueryAnalysis, 
                        iteration: int) -> str:
        """
        Decide阶段: 选择检索策略
        
        根据查询特征和迭代次数选择最佳策略
        """
        # 第一次迭代：根据查询类型选择
        if iteration == 1:
            if analysis.query_type == 'factual':
                return 'vector_search'  # 事实查询优先向量检索
            elif analysis.query_type == 'policy':
                return 'keyword_search'  # 政策查询优先关键词
            else:
                return 'hybrid_search'  # 其他使用混合检索
        
        # 后续迭代：尝试不同策略
        elif iteration == 2:
            return 'hybrid_search'  # 第二次尝试混合检索
        else:
            return 'keyword_search'  # 第三次降级到关键词检索
    
    def _execute_tool(self, 
                     strategy: str, 
                     query: str,
                     session_history: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Act阶段: 执行检索工具
        """
        if strategy not in self.tools:
            logger.warning(f"工具 {strategy} 不存在，使用默认工具")
            strategy = 'hybrid_search'
        
        tool = self.tools[strategy]
        
        try:
            results = tool.execute(query=query, session_history=session_history)
            return results if results else []
        except Exception as e:
            logger.error(f"工具执行失败: {str(e)}")
            return []
    
    def _evaluate_results(self, 
                         results: List[Dict], 
                         query: str,
                         analysis: QueryAnalysis) -> QualityScore:
        """
        Observe阶段: 评估结果质量
        """
        return self.evaluator.evaluate(query, results, analysis)
    
    def _refine_query(self, 
                     original_query: str,
                     results: List[Dict],
                     quality: QualityScore,
                     analysis: QueryAnalysis) -> str:
        """
        改进查询
        """
        return self.query_refiner.refine(
            original_query=original_query,
            failed_results=results,
            quality_score=quality,
            analysis=analysis
        )
    
    def _generate_answer(self, 
                        results: List[Dict], 
                        query: str,
                        quality: QualityScore) -> str:
        """
        生成最终答案
        
        这里简化处理，实际应调用LLM生成
        """
        if not results:
            return "抱歉，未找到相关信息。"
        
        # 简化版：返回最相关的结果
        top_result = results[0]
        return f"根据检索结果：{top_result.get('content', '无内容')}"
