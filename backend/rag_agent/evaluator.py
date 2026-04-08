"""
结果质量评估器
评估检索结果的质量，包括相似度、覆盖度、多样性、完整性
"""

from typing import List, Dict, Set
import logging
import jieba
from collections import Counter

logger = logging.getLogger(__name__)


class ResultEvaluator:
    """
    结果质量评估器
    
    评估维度：
    1. 相似度 (Similarity): 检索结果与查询的相关性
    2. 覆盖度 (Coverage): 查询关键词在结果中的覆盖率
    3. 多样性 (Diversity): 结果之间的差异性，避免重复
    4. 完整性 (Completeness): 结果是否包含完整答案
    """
    
    def __init__(self, 
                 min_similarity: float = 0.3,
                 min_coverage: float = 0.5,
                 min_diversity: float = 0.6,
                 min_completeness: float = 0.5):
        """
        初始化评估器
        
        Args:
            min_similarity: 最低相似度阈值
            min_coverage: 最低覆盖度阈值
            min_diversity: 最低多样性阈值
            min_completeness: 最低完整性阈值
        """
        self.min_similarity = min_similarity
        self.min_coverage = min_coverage
        self.min_diversity = min_diversity
        self.min_completeness = min_completeness
    
    def evaluate(self, 
                query: str, 
                results: List[Dict],
                analysis: any = None) -> 'QualityScore':
        """
        评估检索结果质量
        
        Args:
            query: 查询文本
            results: 检索结果列表
            analysis: 查询分析结果（可选）
            
        Returns:
            QualityScore: 质量评分对象
        """
        from .rag_agent import QualityScore
        
        if not results:
            logger.warning("[Evaluator] 结果为空，返回零分")
            return QualityScore(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # 1. 评估相似度
        similarity = self._evaluate_similarity(results)
        logger.debug(f"[Evaluator] 相似度: {similarity:.3f}")
        
        # 2. 评估覆盖度
        coverage = self._evaluate_coverage(query, results)
        logger.debug(f"[Evaluator] 覆盖度: {coverage:.3f}")
        
        # 3. 评估多样性
        diversity = self._evaluate_diversity(results)
        logger.debug(f"[Evaluator] 多样性: {diversity:.3f}")
        
        # 4. 评估完整性
        completeness = self._evaluate_completeness(query, results)
        logger.debug(f"[Evaluator] 完整性: {completeness:.3f}")
        
        # 5. 计算综合置信度
        confidence = self._calculate_confidence(
            similarity, coverage, diversity, completeness
        )
        logger.info(f"[Evaluator] 综合置信度: {confidence:.3f}")
        
        return QualityScore(
            similarity=similarity,
            coverage=coverage,
            diversity=diversity,
            completeness=completeness,
            confidence=confidence
        )
    
    def _evaluate_similarity(self, results: List[Dict]) -> float:
        """
        评估相似度
        
        使用检索结果中的相似度分数
        """
        if not results:
            return 0.0
        
        # 提取相似度分数
        scores = []
        for result in results:
            # 尝试多个可能的分数字段
            score = (result.get('similarity') or 
                    result.get('score') or 
                    result.get('hybrid_score') or 
                    result.get('rerank_score') or 
                    0.0)
            scores.append(score)
        
        if not scores:
            return 0.0
        
        # 使用加权平均：前面的结果权重更高
        weights = [1.0 / (i + 1) for i in range(len(scores))]
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        weight_sum = sum(weights)
        
        avg_similarity = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        return min(1.0, max(0.0, avg_similarity))
    
    def _evaluate_coverage(self, query: str, results: List[Dict]) -> float:
        """
        评估覆盖度
        
        计算查询关键词在结果中的覆盖率
        """
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return 1.0  # 无关键词时认为完全覆盖
        
        # 合并所有结果的内容
        all_content = " ".join([
            result.get('content', '') for result in results
        ])
        
        # 提取结果中的关键词
        result_keywords = self._extract_keywords(all_content)
        
        # 计算覆盖率
        covered = sum(1 for kw in query_keywords if kw in result_keywords)
        coverage = covered / len(query_keywords)
        
        return coverage
    
    def _evaluate_diversity(self, results: List[Dict]) -> float:
        """
        评估多样性
        
        计算结果之间的差异性，避免重复内容
        """
        if len(results) <= 1:
            return 1.0  # 单个结果认为多样性完美
        
        # 提取所有结果的关键词集合
        keyword_sets = []
        for result in results:
            content = result.get('content', '')
            keywords = set(self._extract_keywords(content))
            keyword_sets.append(keywords)
        
        # 计算两两之间的Jaccard距离（1 - Jaccard相似度）
        distances = []
        for i in range(len(keyword_sets)):
            for j in range(i + 1, len(keyword_sets)):
                set_i = keyword_sets[i]
                set_j = keyword_sets[j]
                
                if not set_i or not set_j:
                    continue
                
                # Jaccard相似度
                intersection = len(set_i & set_j)
                union = len(set_i | set_j)
                similarity = intersection / union if union > 0 else 0
                
                # Jaccard距离
                distance = 1 - similarity
                distances.append(distance)
        
        # 平均距离作为多样性分数
        diversity = sum(distances) / len(distances) if distances else 0.5
        
        return min(1.0, max(0.0, diversity))
    
    def _evaluate_completeness(self, query: str, results: List[Dict]) -> float:
        """
        评估完整性
        
        判断结果是否包含完整答案
        """
        if not results:
            return 0.0
        
        # 简化评估：基于结果数量和内容长度
        
        # 1. 结果数量评分（至少3个结果较好）
        count_score = min(1.0, len(results) / 3.0)
        
        # 2. 内容长度评分（每个结果至少50字）
        length_scores = []
        for result in results:
            content = result.get('content', '')
            length = len(content)
            # 50-200字认为是合适的长度
            if length < 50:
                score = length / 50.0
            elif length > 200:
                score = 1.0
            else:
                score = 0.5 + (length - 50) / 300.0
            length_scores.append(score)
        
        avg_length_score = sum(length_scores) / len(length_scores) if length_scores else 0.0
        
        # 3. 关键词密度评分
        query_keywords = set(self._extract_keywords(query))
        if query_keywords:
            density_scores = []
            for result in results:
                content = result.get('content', '')
                content_keywords = self._extract_keywords(content)
                # 计算查询关键词在内容中的出现频率
                keyword_count = sum(1 for kw in content_keywords if kw in query_keywords)
                density = min(1.0, keyword_count / len(query_keywords))
                density_scores.append(density)
            
            avg_density = sum(density_scores) / len(density_scores) if density_scores else 0.0
        else:
            avg_density = 0.5
        
        # 综合评分
        completeness = (count_score * 0.3 + 
                       avg_length_score * 0.4 + 
                       avg_density * 0.3)
        
        return min(1.0, max(0.0, completeness))
    
    def _calculate_confidence(self, 
                             similarity: float,
                             coverage: float,
                             diversity: float,
                             completeness: float) -> float:
        """
        计算综合置信度
        
        使用加权平均，不同维度权重不同
        """
        # 权重配置
        weights = {
            'similarity': 0.35,      # 相似度最重要
            'coverage': 0.25,        # 覆盖度次之
            'completeness': 0.25,    # 完整性
            'diversity': 0.15        # 多样性权重较低
        }
        
        confidence = (
            similarity * weights['similarity'] +
            coverage * weights['coverage'] +
            completeness * weights['completeness'] +
            diversity * weights['diversity']
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词
        
        使用jieba分词，过滤停用词和短词
        """
        if not text:
            return []
        
        # 停用词列表（简化版）
        stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '吗', '啊'
        }
        
        # 分词
        words = jieba.cut(text)
        
        # 过滤：去除停用词、单字、标点
        keywords = [
            word for word in words
            if len(word) > 1 and word not in stopwords and word.strip()
        ]
        
        return keywords
