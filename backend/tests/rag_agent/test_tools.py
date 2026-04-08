# -*- coding: utf-8 -*-
"""
Agent工具单元测试
测试向量检索、关键词检索、混合检索工具
"""
import pytest
import sys
from pathlib import Path

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from rag_agent.tools import Tool, ToolResult, VectorSearchTool, KeywordSearchTool, HybridSearchTool
from unittest.mock import Mock, MagicMock, patch


class TestToolBase:
    """工具基类测试"""
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = Tool(name="test_tool", description="测试工具")
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.priority == 1
        assert tool.timeout == 30
    
    def test_tool_result_creation(self):
        """测试工具结果创建"""
        result = ToolResult(
            success=True,
            data={"test": "data"},
            error=None,
            duration_ms=100.5
        )
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.error is None
        assert result.duration_ms == 100.5


class TestVectorSearchTool:
    """向量检索工具测试"""
    
    @pytest.fixture
    def mock_kb(self):
        """模拟知识库"""
        kb = Mock()
        kb.search.return_value = [
            {"id": "1", "text": "测试文本1", "similarity": 0.95},
            {"id": "2", "text": "测试文本2", "similarity": 0.85},
        ]
        return kb
    
    def test_vector_search_tool_init(self, mock_kb):
        """测试向量检索工具初始化"""
        tool = VectorSearchTool(mock_kb)
        assert tool.name == "vector_search"
        assert tool.vector_kb == mock_kb
    
    def test_vector_search_execute(self, mock_kb):
        """测试向量检索执行"""
        tool = VectorSearchTool(mock_kb)
        results = tool.execute("测试查询", top_k=2)
        
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["similarity"] == 0.95
        mock_kb.search.assert_called_once_with("测试查询", top_k=2)
    
    def test_vector_search_empty_query(self, mock_kb):
        """测试空查询"""
        tool = VectorSearchTool(mock_kb)
        results = tool.execute("", top_k=5)
        assert results == []
    
    def test_vector_search_exception_handling(self, mock_kb):
        """测试异常处理"""
        mock_kb.search.side_effect = Exception("搜索失败")
        tool = VectorSearchTool(mock_kb)
        results = tool.execute("测试查询")
        assert results == []


class TestKeywordSearchTool:
    """关键词检索工具测试"""
    
    @pytest.fixture
    def mock_kb(self):
        """模拟知识库"""
        kb = Mock()
        kb.keyword_search.return_value = [
            {"id": "1", "text": "包含关键词的文本", "score": 0.9},
            {"id": "2", "text": "另一个匹配文本", "score": 0.7},
        ]
        return kb
    
    def test_keyword_search_tool_init(self, mock_kb):
        """测试关键词检索工具初始化"""
        tool = KeywordSearchTool(mock_kb)
        assert tool.name == "keyword_search"
        assert tool.keyword_kb == mock_kb
    
    def test_keyword_search_execute(self, mock_kb):
        """测试关键词检索执行"""
        tool = KeywordSearchTool(mock_kb)
        results = tool.execute("关键词", top_k=2)
        
        assert len(results) == 2
        assert results[0]["score"] == 0.9
        mock_kb.keyword_search.assert_called_once()


class TestHybridSearchTool:
    """混合检索工具测试"""
    
    @pytest.fixture
    def mock_vector_kb(self):
        """模拟向量知识库"""
        kb = Mock()
        kb.search.return_value = [
            {"id": "1", "text": "向量结果1", "similarity": 0.95},
            {"id": "2", "text": "向量结果2", "similarity": 0.85},
        ]
        return kb
    
    @pytest.fixture
    def mock_keyword_kb(self):
        """模拟关键词知识库"""
        kb = Mock()
        kb.keyword_search.return_value = [
            {"id": "2", "text": "关键词结果1", "score": 0.9},
            {"id": "3", "text": "关键词结果2", "score": 0.8},
        ]
        return kb
    
    def test_hybrid_search_tool_init(self, mock_vector_kb, mock_keyword_kb):
        """测试混合检索工具初始化"""
        tool = HybridSearchTool(mock_vector_kb, mock_keyword_kb)
        assert tool.name == "hybrid_search"
        assert tool.vector_kb == mock_vector_kb
        assert tool.keyword_kb == mock_keyword_kb
    
    def test_hybrid_search_execute(self, mock_vector_kb, mock_keyword_kb):
        """测试混合检索执行"""
        tool = HybridSearchTool(mock_vector_kb, mock_keyword_kb)
        results = tool.execute("测试查询", top_k=3)
        
        assert len(results) <= 3
        # 验证结果包含来自两个来源的文档
        result_ids = [r["id"] for r in results]
        assert "1" in result_ids or "2" in result_ids or "3" in result_ids
    
    def test_hybrid_search_dynamic_weights(self, mock_vector_kb, mock_keyword_kb):
        """测试动态权重调整"""
        tool = HybridSearchTool(
            mock_vector_kb, 
            mock_keyword_kb,
            enable_dynamic_weights=True
        )
        
        # 短查询应该偏向关键词
        results_short = tool.execute("学费", top_k=5)
        
        # 长查询应该偏向向量
        results_long = tool.execute("请问学校的学费缴纳政策是什么？", top_k=5)
        
        assert len(results_short) > 0
        assert len(results_long) > 0
    
    def test_hybrid_search_bm25_mode(self, mock_vector_kb, mock_keyword_kb):
        """测试BM25模式"""
        tool = HybridSearchTool(
            mock_vector_kb,
            mock_keyword_kb,
            use_bm25=True
        )
        
        results = tool.execute("测试查询", top_k=5)
        assert isinstance(results, list)
    
    def test_hybrid_search_fuzzy_matching(self, mock_vector_kb, mock_keyword_kb):
        """测试模糊匹配"""
        tool = HybridSearchTool(
            mock_vector_kb,
            mock_keyword_kb,
            enable_fuzzy=True
        )
        
        # 包含拼写错误的查询
        results = tool.execute("学费缴纳", top_k=5)
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
