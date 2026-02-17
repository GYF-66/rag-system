# -*- coding: utf-8 -*-
"""
测试智能推理问答功能
验证交叉检索引擎和隐含关联问题处理
"""
import sys
from pathlib import Path

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from cross_retrieval_engine import cross_retrieval_engine


def test_cross_query_detection():
    """测试交叉查询检测"""
    print("=" * 60)
    print("测试 1: 交叉查询检测")
    print("=" * 60)

    test_queries = [
        "挂科对奖学金申请有影响吗？",
        "软件著作权可以加分吗？",
        "转专业需要满足什么条件？",
        "补考对绩点有影响吗？",
        "你好",
        "奖学金怎么申请？"
    ]

    for query in test_queries:
        is_cross, pattern_info = cross_retrieval_engine.is_cross_query(query)
        print(f"\n查询: {query}")
        print(f"  是否为交叉查询: {'是' if is_cross else '否'}")
        if is_cross:
            print(f"  模式: {pattern_info['pattern_name']}")
            print(f"  描述: {pattern_info['description']}")
            print(f"  关键词: {', '.join(pattern_info['keywords'])}")


def test_cross_retrieval():
    """测试交叉检索"""
    print("\n" + "=" * 60)
    print("测试 2: 交叉检索")
    print("=" * 60)

    query = "挂科对奖学金申请有影响吗？"
    print(f"\n查询: {query}")

    is_cross, pattern_info = cross_retrieval_engine.is_cross_query(query)
    if is_cross:
        result = cross_retrieval_engine.process_cross_query(query)

        if result:
            print(f"\n交叉检索成功！")
            print(f"  检索文档数: {result['total_documents']}")
            print(f"  最终文档数: {len(result['documents'])}")
            print(f"  检索耗时: {result['retrieval_duration_ms']:.2f}ms")
            print(f"  比对耗时: {result['comparison_duration_ms']:.2f}ms")
            print(f"  总耗时: {result['total_duration_ms']:.2f}ms")

            print(f"\n生成的 Thinking 内容:")
            print("-" * 60)
            print(result['thinking_content'])
            print("-" * 60)
        else:
            print("交叉检索失败")
    else:
        print("不是交叉查询")


def test_soft_patent_query():
    """测试软著加分查询"""
    print("\n" + "=" * 60)
    print("测试 3: 软著加分查询")
    print("=" * 60)

    query = "软件著作权可以在综合素质测评中加分吗？"
    print(f"\n查询: {query}")

    is_cross, pattern_info = cross_retrieval_engine.is_cross_query(query)
    if is_cross:
        result = cross_retrieval_engine.process_cross_query(query)

        if result:
            print(f"\n交叉检索成功！")
            print(f"  最终文档数: {len(result['documents'])}")
            print(f"  总耗时: {result['total_duration_ms']:.2f}ms")

            print(f"\n生成的 Thinking 内容:")
            print("-" * 60)
            print(result['thinking_content'][:500] + "...")  # 只显示前500字符
            print("-" * 60)
        else:
            print("交叉检索失败")


def test_pattern_coverage():
    """测试所有模式覆盖"""
    print("\n" + "=" * 60)
    print("测试 4: 模式覆盖检查")
    print("=" * 60)

    print(f"\n共有 {len(cross_retrieval_engine.cross_query_patterns)} 个交叉查询模式:")
    for pattern_name, info in cross_retrieval_engine.cross_query_patterns.items():
        print(f"\n  {pattern_name}:")
        print(f"    描述: {info['description']}")
        print(f"    关键词: {', '.join(info['keywords'])}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("智能推理问答功能测试")
    print("=" * 60)

    # 测试1: 交叉查询检测
    test_cross_query_detection()

    # 测试2: 交叉检索
    test_cross_retrieval()

    # 测试3: 软著加分查询
    test_soft_patent_query()

    # 测试4: 模式覆盖
    test_pattern_coverage()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()