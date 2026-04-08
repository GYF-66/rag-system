# -*- coding: utf-8 -*-
"""
性能基准测试
测试系统在不同负载下的性能表现
"""
import pytest
import sys
import time
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from rag_agent.rag_agent import RAGAgent
from rag_agent.tools import VectorSearchTool, HybridSearchTool
from rag_agent.evaluator import ResultEvaluator
from utils.cache import SemanticCache
from utils.metrics import MetricsCollector
from unittest.mock import Mock


class TestPerformanceBenchmark:
    """性能基准测试"""
    
    @pytest.fixture
    def mock_kb(self):
        """模拟知识库"""
        kb = Mock()
        kb.search.return_value = [
            {"id": str(i), "text": f"测试文本{i}", "similarity": 0.9 - i*0.05}
            for i in range(10)
        ]
        return kb
    
    @pytest.fixture
    def agent(self, mock_kb):
        """创建Agent实例"""
        tools = [VectorSearchTool(mock_kb)]
        evaluator = ResultEvaluator()
        
        return RAGAgent(
            tools=tools,
            evaluator=evaluator,
            max_iterations=2,
            quality_threshold=0.7
        )
    
    def test_single_query_latency(self, agent):
        """测试单次查询延迟"""
        start_time = time.time()
        
        result = asyncio.run(agent.process_query("测试查询"))
        
        latency = (time.time() - start_time) * 1000  # 毫秒
        
        assert result.success
        assert latency < 5000  # 单次查询应在5秒内完成
        print(f"\n单次查询延迟: {latency:.2f}ms")
    
    def test_batch_query_throughput(self, agent):
        """测试批量查询吞吐量"""
        queries = [f"测试查询{i}" for i in range(10)]
        
        start_time = time.time()
        
        for query in queries:
            asyncio.run(agent.process_query(query))
        
        total_time = time.time() - start_time
        throughput = len(queries) / total_time
        
        print(f"\n批量查询吞吐量: {throughput:.2f} queries/sec")
        assert throughput > 0.5  # 至少每秒0.5个查询
    
    def test_concurrent_query_performance(self, agent):
        """测试并发查询性能"""
        queries = [f"并发查询{i}" for i in range(20)]
        
        async def run_queries():
            tasks = [agent.process_query(q) for q in queries]
            return await asyncio.gather(*tasks)
        
        start_time = time.time()
        results = asyncio.run(run_queries())
        total_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r.success)
        throughput = len(queries) / total_time
        
        print(f"\n并发查询吞吐量: {throughput:.2f} queries/sec")
        print(f"成功率: {success_count}/{len(queries)}")
        
        assert success_count >= len(queries) * 0.9  # 至少90%成功率
        assert throughput > 1.0  # 并发应提升吞吐量


class TestCachePerformance:
    """缓存性能测试"""
    
    def test_cache_hit_performance(self):
        """测试缓存命中性能"""
        cache = SemanticCache(max_size=1000, default_ttl=3600)
        
        # 预填充缓存
        for i in range(100):
            cache.set(f"query{i}", {"data": f"result{i}"})
        
        # 测试缓存命中延迟
        start_time = time.time()
        
        for i in range(100):
            result = cache.get(f"query{i}")
            assert result is not None
        
        total_time = (time.time() - start_time) * 1000
        avg_latency = total_time / 100
        
        print(f"\n缓存命中平均延迟: {avg_latency:.4f}ms")
        assert avg_latency < 1.0  # 缓存命中应小于1ms
    
    def test_cache_miss_performance(self):
        """测试缓存未命中性能"""
        cache = SemanticCache(max_size=1000, default_ttl=3600)
        
        start_time = time.time()
        
        for i in range(100):
            result = cache.get(f"nonexistent{i}")
            assert result is None
        
        total_time = (time.time() - start_time) * 1000
        avg_latency = total_time / 100
        
        print(f"\n缓存未命中平均延迟: {avg_latency:.4f}ms")
        assert avg_latency < 2.0  # 缓存未命中应小于2ms
    
    def test_cache_scalability(self):
        """测试缓存可扩展性"""
        sizes = [100, 500, 1000, 5000]
        
        for size in sizes:
            cache = SemanticCache(max_size=size, default_ttl=3600)
            
            # 填充缓存
            start_time = time.time()
            for i in range(size):
                cache.set(f"query{i}", {"data": f"result{i}"})
            fill_time = time.time() - start_time
            
            # 测试查询性能
            start_time = time.time()
            for i in range(min(100, size)):
                cache.get(f"query{i}")
            query_time = (time.time() - start_time) * 1000 / min(100, size)
            
            print(f"\n缓存大小: {size}, 填充时间: {fill_time:.2f}s, 查询延迟: {query_time:.4f}ms")


class TestMetricsCollectorPerformance:
    """指标收集器性能测试"""
    
    def test_metrics_collection_overhead(self):
        """测试指标收集开销"""
        collector = MetricsCollector(window_size=1000)
        
        # 不收集指标的基准
        start_time = time.time()
        for i in range(1000):
            _ = i * 2
        baseline_time = time.time() - start_time
        
        # 收集指标
        start_time = time.time()
        for i in range(1000):
            collector.record_latency("test_operation", i * 0.1)
            _ = i * 2
        with_metrics_time = time.time() - start_time
        
        overhead = (with_metrics_time - baseline_time) / baseline_time * 100
        
        print(f"\n指标收集开销: {overhead:.2f}%")
        assert overhead < 10  # 开销应小于10%
    
    def test_metrics_export_performance(self):
        """测试指标导出性能"""
        collector = MetricsCollector(window_size=10000)
        
        # 记录大量指标
        for i in range(10000):
            collector.record_latency("operation", i * 0.1)
            collector.record_throughput("requests", 1)
        
        # 测试导出性能
        start_time = time.time()
        metrics = collector.export_metrics()
        export_time = (time.time() - start_time) * 1000
        
        print(f"\n指标导出时间: {export_time:.2f}ms")
        assert export_time < 100  # 导出应在100ms内完成
        assert len(metrics) > 0


class TestLoadTest:
    """负载测试"""
    
    @pytest.fixture
    def agent(self):
        """创建Agent实例"""
        mock_kb = Mock()
        mock_kb.search.return_value = [
            {"id": "1", "text": "测试结果", "similarity": 0.9}
        ]
        
        tools = [VectorSearchTool(mock_kb)]
        evaluator = ResultEvaluator()
        
        return RAGAgent(
            tools=tools,
            evaluator=evaluator,
            max_iterations=2
        )
    
    @pytest.mark.slow
    def test_sustained_load(self, agent):
        """测试持续负载"""
        duration = 10  # 秒
        query_count = 0
        errors = 0
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                result = asyncio.run(agent.process_query(f"查询{query_count}"))
                if not result.success:
                    errors += 1
                query_count += 1
            except Exception as e:
                errors += 1
                print(f"错误: {e}")
        
        total_time = time.time() - start_time
        throughput = query_count / total_time
        error_rate = errors / query_count if query_count > 0 else 0
        
        print(f"\n持续负载测试:")
        print(f"  总查询数: {query_count}")
        print(f"  吞吐量: {throughput:.2f} queries/sec")
        print(f"  错误率: {error_rate*100:.2f}%")
        
        assert error_rate < 0.05  # 错误率应小于5%
        assert throughput > 0.5  # 吞吐量应大于0.5 qps


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
