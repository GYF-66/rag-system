# -*- coding: utf-8 -*-
"""
性能指标收集器
用于追踪RAG系统的查询、检索和生成性能
"""
import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_history: int = 10000):
        """
        初始化指标收集器
        
        Args:
            max_history: 保留的历史记录数量
        """
        self.max_history = max_history
        
        # 查询指标
        self.query_metrics = deque(maxlen=max_history)
        
        # 检索指标
        self.retrieval_metrics = deque(maxlen=max_history)
        
        # 生成指标
        self.generation_metrics = deque(maxlen=max_history)
        
        # 缓存指标
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 错误计数
        self.error_counts = defaultdict(int)
        
        logger.info("MetricsCollector initialized")
    
    def track_query(self, 
                   query: str,
                   total_latency: float,
                   num_results: int,
                   cache_hit: bool,
                   success: bool = True,
                   error_type: Optional[str] = None):
        """
        追踪查询指标
        
        Args:
            query: 查询文本
            total_latency: 总延迟（秒）
            num_results: 返回结果数量
            cache_hit: 是否命中缓存
            success: 是否成功
            error_type: 错误类型（如果失败）
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],  # 只保留前100字符
            'query_length': len(query),
            'total_latency': total_latency,
            'num_results': num_results,
            'cache_hit': cache_hit,
            'success': success,
            'error_type': error_type
        }
        
        self.query_metrics.append(metric)
        
        # 更新缓存统计
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # 更新错误统计
        if not success and error_type:
            self.error_counts[error_type] += 1
        
        # 记录慢查询
        if total_latency > 3.0:
            logger.warning(f"慢查询检测: {query[:50]}... 耗时 {total_latency:.2f}秒")
    
    def track_retrieval(self,
                       query: str,
                       retrieval_time: float,
                       vector_time: Optional[float] = None,
                       keyword_time: Optional[float] = None,
                       num_candidates: int = 0,
                       num_final: int = 0):
        """
        追踪检索性能
        
        Args:
            query: 查询文本
            retrieval_time: 总检索时间（秒）
            vector_time: 向量检索时间（秒）
            keyword_time: 关键词检索时间（秒）
            num_candidates: 候选结果数量
            num_final: 最终结果数量
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],
            'retrieval_time': retrieval_time,
            'vector_time': vector_time,
            'keyword_time': keyword_time,
            'num_candidates': num_candidates,
            'num_final': num_final
        }
        
        self.retrieval_metrics.append(metric)
        
        # 记录慢检索
        if retrieval_time > 1.5:
            logger.warning(f"慢检索检测: {query[:50]}... 耗时 {retrieval_time:.2f}秒")
    
    def track_generation(self,
                        query: str,
                        generation_time: float,
                        answer_length: int,
                        context_length: int,
                        model: str = "unknown"):
        """
        追踪生成性能
        
        Args:
            query: 查询文本
            generation_time: 生成时间（秒）
            answer_length: 答案长度
            context_length: 上下文长度
            model: 使用的模型
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],
            'generation_time': generation_time,
            'answer_length': answer_length,
            'context_length': context_length,
            'model': model
        }
        
        self.generation_metrics.append(metric)
        
        # 记录慢生成
        if generation_time > 2.0:
            logger.warning(f"慢生成检测: {query[:50]}... 耗时 {generation_time:.2f}秒")
    
    def get_statistics(self, time_range: str = "1h") -> Dict:
        """
        获取统计数据
        
        Args:
            time_range: 时间范围 (1h, 24h, 7d, all)
        
        Returns:
            统计数据字典
        """
        # 计算时间窗口
        now = datetime.now()
        if time_range == "1h":
            cutoff = now - timedelta(hours=1)
        elif time_range == "24h":
            cutoff = now - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = now - timedelta(days=7)
        else:
            cutoff = datetime.min
        
        # 过滤指标
        recent_queries = [m for m in self.query_metrics 
                         if datetime.fromisoformat(m['timestamp']) >= cutoff]
        recent_retrievals = [m for m in self.retrieval_metrics 
                            if datetime.fromisoformat(m['timestamp']) >= cutoff]
        recent_generations = [m for m in self.generation_metrics 
                             if datetime.fromisoformat(m['timestamp']) >= cutoff]
        
        stats = {
            'time_range': time_range,
            'timestamp': now.isoformat(),
            'query_stats': self._calculate_query_stats(recent_queries),
            'retrieval_stats': self._calculate_retrieval_stats(recent_retrievals),
            'generation_stats': self._calculate_generation_stats(recent_generations),
            'cache_stats': self._calculate_cache_stats(),
            'error_stats': dict(self.error_counts)
        }
        
        return stats
    
    def _calculate_query_stats(self, metrics: List[Dict]) -> Dict:
        """计算查询统计"""
        if not metrics:
            return {}
        
        latencies = [m['total_latency'] for m in metrics]
        successes = [m for m in metrics if m['success']]
        
        return {
            'total_queries': len(metrics),
            'successful_queries': len(successes),
            'success_rate': len(successes) / len(metrics) if metrics else 0,
            'avg_latency': sum(latencies) / len(latencies),
            'min_latency': min(latencies),
            'max_latency': max(latencies),
            'p50_latency': self._percentile(latencies, 50),
            'p95_latency': self._percentile(latencies, 95),
            'p99_latency': self._percentile(latencies, 99),
            'avg_query_length': sum(m['query_length'] for m in metrics) / len(metrics),
            'avg_results': sum(m['num_results'] for m in metrics) / len(metrics)
        }
    
    def _calculate_retrieval_stats(self, metrics: List[Dict]) -> Dict:
        """计算检索统计"""
        if not metrics:
            return {}
        
        retrieval_times = [m['retrieval_time'] for m in metrics]
        vector_times = [m['vector_time'] for m in metrics if m['vector_time'] is not None]
        keyword_times = [m['keyword_time'] for m in metrics if m['keyword_time'] is not None]
        
        stats = {
            'total_retrievals': len(metrics),
            'avg_retrieval_time': sum(retrieval_times) / len(retrieval_times),
            'p95_retrieval_time': self._percentile(retrieval_times, 95),
            'avg_candidates': sum(m['num_candidates'] for m in metrics) / len(metrics),
            'avg_final_results': sum(m['num_final'] for m in metrics) / len(metrics)
        }
        
        if vector_times:
            stats['avg_vector_time'] = sum(vector_times) / len(vector_times)
        
        if keyword_times:
            stats['avg_keyword_time'] = sum(keyword_times) / len(keyword_times)
        
        return stats
    
    def _calculate_generation_stats(self, metrics: List[Dict]) -> Dict:
        """计算生成统计"""
        if not metrics:
            return {}
        
        generation_times = [m['generation_time'] for m in metrics]
        
        return {
            'total_generations': len(metrics),
            'avg_generation_time': sum(generation_times) / len(generation_times),
            'p95_generation_time': self._percentile(generation_times, 95),
            'avg_answer_length': sum(m['answer_length'] for m in metrics) / len(metrics),
            'avg_context_length': sum(m['context_length'] for m in metrics) / len(metrics)
        }
    
    def _calculate_cache_stats(self) -> Dict:
        """计算缓存统计"""
        total = self.cache_hits + self.cache_misses
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / total if total > 0 else 0,
            'total_cache_queries': total
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_summary(self) -> str:
        """获取摘要信息"""
        stats = self.get_statistics("1h")
        
        query_stats = stats.get('query_stats', {})
        cache_stats = stats.get('cache_stats', {})
        
        summary = f"""
=== RAG系统性能摘要 (最近1小时) ===
总查询数: {query_stats.get('total_queries', 0)}
成功率: {query_stats.get('success_rate', 0):.2%}
平均延迟: {query_stats.get('avg_latency', 0):.3f}秒
P95延迟: {query_stats.get('p95_latency', 0):.3f}秒
缓存命中率: {cache_stats.get('cache_hit_rate', 0):.2%}
错误数: {sum(self.error_counts.values())}
"""
        return summary.strip()
    
    def save_metrics(self, output_path: str):
        """保存指标到文件"""
        try:
            stats = self.get_statistics("all")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"指标已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存指标失败: {e}")
    
    def reset_metrics(self):
        """重置所有指标"""
        self.query_metrics.clear()
        self.retrieval_metrics.clear()
        self.generation_metrics.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.error_counts.clear()
        logger.info("所有指标已重置")


# 全局单例
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
