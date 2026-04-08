# -*- coding: utf-8 -*-
"""
Agent集成测试
测试完整的Agent工作流程
"""
import pytest
import sys
import asyncio
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from rag_agent.rag_agent import RAGAgent, AgentResult
from rag_agent.tools import VectorSearchTool, KeywordSearchTool, HybridSearchTool
from rag_agent.evaluator import ResultEvaluator
from rag_agent.reranker import CrossEncoderReranker
from rag_agent.approval_manager import ApprovalManager
from unittest.mock import Mock, MagicMock, patch


class TestRAGAgentIntegration:
    """RAG Agent集成测试"""
    
    @pytest.fixture
    def mock_vector_kb(self):
        """模拟向量知识库"""
        kb = Mock()
        kb.search.return_value = [
            {"id": "1", "text": "学费缴纳政策：每学期开学前缴纳", "similarity": 0.92},
            {"id": "2", "text": "学费标准：本科生每年8000元", "similarity": 0.88},
            {"id": "3", "text": "学费减免政策：困难学生可申请", "similarity": 0.85},
        ]
        return kb
    
    @pytest.fixture
    def mock_keyword_kb(self):
        """模拟关键词知识库"""
        kb = Mock()
        kb.keyword_search.return_value = [
            {"id": "2", "text": "学费标准：本科生每年8000元", "score": 0.9},
            {"id": "4", "text": "学费缴纳方式：支持银行转账", "score": 0.85},
        ]
        return kb
    
    @pytest.fixture
    def agent(self, mock_vector_kb, mock_keyword_kb):
        """创建Agent实例"""
        tools = [
            VectorSearchTool(mock_vector_kb),
            KeywordSearchTool(mock_keyword_kb),
            HybridSearchTool(mock_vector_kb, mock_keyword_kb)
        ]
        evaluator = ResultEvaluator()
        
        return RAGAgent(
            tools=tools,
            evaluator=evaluator,
            max_iterations=3,
            quality_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_simple_query_workflow(self, agent):
        """测试简单查询工作流"""
        result = await agent.process_query("学费缴纳政策")
        
        assert isinstance(result, AgentResult)
        assert result.success
        assert len(result.final_results) > 0
        assert result.final_quality.overall > 0.0
        assert len(result.iteration_records) > 0
    
    @pytest.mark.asyncio
    async def test_complex_query_workflow(self, agent):
        """测试复杂查询工作流"""
        result = await agent.process_query(
            "请详细说明学费缴纳的时间、方式和减免政策"
        )
        
        assert result.success
        assert len(result.iteration_records) >= 1
        # 复杂查询可能需要多次迭代
        assert result.total_iterations >= 1
    
    @pytest.mark.asyncio
    async def test_low_quality_results_refinement(self, agent, mock_vector_kb):
        """测试低质量结果的改进"""
        # 模拟低质量结果
        mock_vector_kb.search.return_value = [
            {"id": "1", "text": "不太相关的内容", "similarity": 0.5},
        ]
        
        result = await agent.process_query("学费政策")
        
        # Agent应该尝试改进查询
        assert result.total_iterations > 1 or result.final_strategy != "vector_search"
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, agent):
        """测试最大迭代次数限制"""
        result = await agent.process_query("测试查询")
        
        assert result.total_iterations <= agent.max_iterations
    
    @pytest.mark.asyncio
    async def test_quality_threshold_achievement(self, agent):
        """测试质量阈值达成"""
        result = await agent.process_query("学费缴纳")
        
        if result.success:
            assert result.final_quality.overall >= agent.quality_threshold
    
    @pytest.mark.asyncio
    async def test_tool_selection_strategy(self, agent):
        """测试工具选择策略"""
        # 短查询应该优先使用关键词搜索
        result_short = await agent.process_query("学费")
        
        # 长查询应该优先使用向量搜索
        result_long = await agent.process_query("请问学校的学费缴纳政策是什么？")
        
        assert result_short.success
        assert result_long.success
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, agent):
        """测试空查询处理"""
        result = await agent.process_query("")
        
        assert not result.success
        assert "查询不能为空" in result.error or len(result.final_results) == 0


class TestAgentWithReranker:
    """带重排序的Agent测试"""
    
    @pytest.fixture
    def agent_with_reranker(self, mock_vector_kb, mock_keyword_kb):
        """创建带重排序的Agent"""
        tools = [
            VectorSearchTool(mock_vector_kb),
            HybridSearchTool(mock_vector_kb, mock_keyword_kb)
        ]
        evaluator = ResultEvaluator()
        
        # 模拟重排序器
        mock_reranker = Mock()
        mock_reranker.rerank.return_value = [
            {"id": "1", "text": "最相关的结果", "rerank_score": 0.95},
            {"id": "2", "text": "次相关的结果", "rerank_score": 0.85},
        ]
        
        return RAGAgent(
            tools=tools,
            evaluator=evaluator,
            reranker=mock_reranker,
            max_iterations=3
        )
    
    @pytest.mark.asyncio
    async def test_reranking_improves_quality(self, agent_with_reranker):
        """测试重排序提升质量"""
        result = await agent_with_reranker.process_query("学费政策")
        
        assert result.success
        # 检查是否使用了重排序
        if len(result.final_results) > 0:
            assert any('rerank_score' in r for r in result.final_results)


class TestAgentWithApproval:
    """带审批机制的Agent测试"""
    
    @pytest.fixture
    def agent_with_approval(self, mock_vector_kb, mock_keyword_kb):
        """创建带审批的Agent"""
        tools = [VectorSearchTool(mock_vector_kb)]
        evaluator = ResultEvaluator()
        approval_manager = ApprovalManager(
            min_results=3,
            min_quality=0.8
        )
        
        return RAGAgent(
            tools=tools,
            evaluator=evaluator,
            approval_manager=approval_manager,
            max_iterations=2
        )
    
    @pytest.mark.asyncio
    async def test_approval_triggered_for_low_quality(self, agent_with_approval, mock_vector_kb):
        """测试低质量结果触发审批"""
        # 模拟低质量结果
        mock_vector_kb.search.return_value = [
            {"id": "1", "text": "不太相关", "similarity": 0.6},
        ]
        
        result = await agent_with_approval.process_query("测试查询")
        
        # 应该触发审批
        assert result.needs_approval or result.final_quality.overall < 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
