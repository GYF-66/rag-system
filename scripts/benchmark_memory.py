#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存基准测试脚本
用于对比优化前后的内存使用情况
"""
import sys
import time
import psutil
import argparse
from pathlib import Path

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from retrieval.knowledge_base import knowledge_base
from agent import agent


def get_memory_mb():
    """获取当前进程内存使用（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def benchmark_baseline():
    """基准测试：优化前"""
    print("=" * 60)
    print("内存基准测试 - 优化前")
    print("=" * 60)
    
    # 1. 启动内存
    mem_start = get_memory_mb()
    print(f"\n1. 启动内存: {mem_start:.2f} MB")
    
    # 2. 加载知识库
    print("\n2. 加载知识库...")
    knowledge_base.load()
    mem_after_load = get_memory_mb()
    print(f"   加载后内存: {mem_after_load:.2f} MB")
    print(f"   增长: {mem_after_load - mem_start:.2f} MB")
    
    # 3. 空闲内存
    time.sleep(2)
    mem_idle = get_memory_mb()
    print(f"\n3. 空闲内存: {mem_idle:.2f} MB")
    
    # 4. 执行查询测试
    print("\n4. 执行查询测试...")
    test_queries = [
        "人工智能专业的培养目标是什么？",
        "有哪些核心课程？",
        "机器学习课程的主要内容是什么？",
        "实践环节包括哪些？",
        "毕业要求有哪些？"
    ] * 10  # 50次查询
    
    mem_before_queries = get_memory_mb()
    for i, query in enumerate(test_queries):
        result = agent.process_query(query)
        if (i + 1) % 10 == 0:
            mem_current = get_memory_mb()
            print(f"   查询 {i+1}/{len(test_queries)}: {mem_current:.2f} MB")
    
    mem_after_queries = get_memory_mb()
    print(f"\n   查询前内存: {mem_before_queries:.2f} MB")
    print(f"   查询后内存: {mem_after_queries:.2f} MB")
    print(f"   查询峰值增长: {mem_after_queries - mem_before_queries:.2f} MB")
    
    # 5. 1000次查询后
    print("\n5. 执行1000次查询...")
    for i in range(950):  # 已经执行了50次
        query = test_queries[i % len(test_queries)]
        agent.process_query(query)
        if (i + 1) % 100 == 0:
            mem_current = get_memory_mb()
            print(f"   查询 {i+51}/{1000}: {mem_current:.2f} MB")
    
    mem_final = get_memory_mb()
    print(f"\n   1000次查询后内存: {mem_final:.2f} MB")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"启动内存:     {mem_start:.2f} MB")
    print(f"空闲内存:     {mem_idle:.2f} MB")
    print(f"查询峰值:     {mem_after_queries:.2f} MB")
    print(f"1000次查询后: {mem_final:.2f} MB")
    print(f"总增长:       {mem_final - mem_start:.2f} MB")
    
    return {
        'startup': mem_start,
        'idle': mem_idle,
        'query_peak': mem_after_queries,
        'after_1000': mem_final
    }


def benchmark_optimized():
    """基准测试：优化后"""
    print("=" * 60)
    print("内存基准测试 - 优化后")
    print("=" * 60)
    
    # 与baseline相同的测试流程
    return benchmark_baseline()


def compare_results(baseline, optimized):
    """对比测试结果"""
    print("\n" + "=" * 60)
    print("优化效果对比")
    print("=" * 60)
    
    metrics = [
        ('启动内存', 'startup'),
        ('空闲内存', 'idle'),
        ('查询峰值', 'query_peak'),
        ('1000次查询后', 'after_1000')
    ]
    
    print(f"\n{'指标':<15} {'优化前':<12} {'优化后':<12} {'改善':<10}")
    print("-" * 60)
    
    for name, key in metrics:
        before = baseline[key]
        after = optimized[key]
        improvement = (before - after) / before * 100 if before > 0 else 0
        print(f"{name:<15} {before:>10.2f}MB {after:>10.2f}MB {improvement:>8.1f}%")


def main():
    parser = argparse.ArgumentParser(description='内存基准测试')
    parser.add_argument(
        '--mode',
        choices=['baseline', 'optimized', 'compare'],
        default='baseline',
        help='测试模式: baseline(优化前), optimized(优化后), compare(对比)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'baseline':
        benchmark_baseline()
    elif args.mode == 'optimized':
        benchmark_optimized()
    elif args.mode == 'compare':
        print("执行对比测试...\n")
        baseline = benchmark_baseline()
        print("\n\n")
        optimized = benchmark_optimized()
        compare_results(baseline, optimized)


if __name__ == '__main__':
    main()
