# -*- coding: utf-8 -*-
"""
结果质量评估器单元测试
测试相似度、覆盖度、多样性、完整性评估
"""
import pytest
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from rag_agent.evaluator import ResultEvaluator, QualityScore
from unittest.mock import Mock


class TestQualityScore:
    """质量评分数据类测试"""
    
    def test_quality_score_creation(self):
        """测试质量评分创建"""
        score = QualityScore(
            similarity=0.9,
            coverage=0.8,
            diversity=0.7,
            completeness=0.85,
            overall=0.82
        )
        assert score.similarity == 0.9
        assert score.coverage == 0.8
        assert score.diversity == 0.7
        assert score.completeness == 0.85
        assert score.overall == 0.82
    
    def test_quality_score_defaults(self):
        """测试默认值"""
        score = QualityScore()
        assert score.similarity == 0.0
        assert score.coverage == 0.0
        assert score.diversity == 0.0
        assert score.completeness == 0.0
        assert score.overall == 0.0


class TestResultEvaluator:
    """结果评估器测试"""
    
    @pytest.fixture
    def evaluator(self):
        """创建评估器实例"""
        return ResultEvaluator(
            similarity_weight=0.4,
            coverage_weight=0.3,
            diversity_weight=0.2,
            completeness_weight=0.1
        )
    
    @pytest.fixture
    def sample_results(self):
        """示例检索结果"""
        return [
            {"id": "1", "text": "学费缴纳政策说明", "similarity": 0.95},
            {"id": "2", "text": "学费缴纳时间安排", "similarity": 0.90},
            {"id": "3", "text": "学费减免申请流程", "similarity": 0.85},
        ]
    
    def test_evaluator_initialization(self, evaluator):
        """测试评估器初始化"""
        assert evaluator.similarity_weight == 0.4
        assert evaluator.coverage_weight == 0.3
        assert evaluator.diversity_weight == 0.2
        assert evaluator.completeness_weight == 0.1
    
    def test_evaluate_similarity(self, evaluator, sample_results):
        """测试相似度评估"""
        score = evaluator._evaluate_similarity(sample_results)
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # 高相似度结果
    
    def test_evaluate_coverage(self, evaluator, sample_results):
        """测试覆盖度评估"""
        query = "学费缴纳"
        score = evaluator._evaluate_coverage(sample_results, query)
        assert 0.0 <= score <= 1.0
    
    def test_evaluate_diversity(self, evaluator, sample_results):
        """测试多样性评估"""
        score = evaluator._evaluate_diversity(sample_results)
        assert 0.0 <= score <= 1.0
    
    def test_evaluate_completeness(self, evaluator, sample_results):
        """测试完整性评估"""
        query = "学费缴纳政策"
        score = evaluator._evaluate_completeness(sample_results, query)
        assert 0.0 <= score <= 1.0
    
    def test_evaluate_full(self, evaluator, sample_results):
        """测试完整评估"""
        query = "学费缴纳政策"
        quality = evaluator.evaluate(sample_results, query)
        
        assert isinstance(quality, QualityScore)
        assert 0.0 <= quality.similarity <= 1.0
        assert 0.0 <= quality.coverage <= 1.0
        assert 0.0 <= quality.diversity <= 1.0
        assert 0.0 <= quality.completeness <= 1.0
        assert 0.0 <= quality.overall <= 1.0
    
    def test_evaluate_empty_results(self, evaluator):
        """测试空结果评估"""
        quality = evaluator.evaluate([], "测试查询")
        assert quality.overall == 0.0
    
    def test_evaluate_single_result(self, evaluator):
        """测试单个结果评估"""
        results = [{"id": "1", "text": "单个结果", "similarity": 0.9}]
        quality = evaluator.evaluate(results, "测试")
        assert quality.similarity > 0.0
        assert quality.diversity == 0.0  # 单个结果无多样性
    
    def test_evaluate_low_quality_results(self, evaluator):
        """测试低质量结果"""
        results = [
            {"id": "1", "text": "不相关内容", "similarity": 0.3},
            {"id": "2", "text": "另一个不相关", "similarity": 0.2},
        ]
        quality = evaluator.evaluate(results, "学费政策")
        assert quality.overall < 0.5
    
    def test_meets_threshold(self, evaluator, sample_results):
        """测试阈值判断"""
        quality = evaluator.evaluate(sample_results, "学费")
        assert evaluator.meets_threshold(quality, threshold=0.5)
        assert not evaluator.meets_threshold(quality, threshold=0.99)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
