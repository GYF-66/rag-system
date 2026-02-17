# -*- coding: utf-8 -*-
"""
简化版测试脚本 - 验证智能推理问答功能
"""
import sys
from pathlib import Path

# 添加 backend 目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 60)
print("智能推理问答功能测试")
print("=" * 60)

# 测试1: 导入测试
print("\n[测试1] 导入模块")
print("-" * 60)

try:
    from cross_retrieval_engine_improved import cross_retrieval_engine_improved
    print("✓ cross_retrieval_engine_improved 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

# 测试2: 查询检测
print("\n[测试2] 交叉查询检测")
print("-" * 60)

test_queries = [
    "挂科对奖学金申请有影响吗？",
    "软件著作权可以加分吗？",
    "转专业需要满足什么条件？",
    "你好",
    "奖学金怎么申请？"
]

for query in test_queries:
    is_cross, pattern_info = cross_retrieval_engine_improved.is_cross_query(query)
    print(f"\n查询: {query}")
    print(f"  是否为交叉查询: {'是' if is_cross else '否'}")
    if is_cross:
        print(f"  模式: {pattern_info['pattern_name']}")
        print(f"  描述: {pattern_info['description']}")
        print(f"  关键词: {', '.join(pattern_info['keywords'])}")

# 测试3: 关键内容提取
print("\n[测试3] 关键内容提取")
print("-" * 60)

test_texts = [
    "这是一段短文本。",
    "这是一段较长的文本，包含多个句子。这是第二句话。这是第三句话。",
    "这是一个很长的文本，包含了很多内容。第一句话在这里。第二句话在这里。第三句话在这里。第四句话在这里结束。",
    ""
]

for i, text in enumerate(test_texts, 1):
    content = cross_retrieval_engine_improved._extract_key_content(text, max_chars=150)
    print(f"\n文本{i}: {text[:30]}...")
    print(f"  提取结果: {content}")
    print(f"  是否截断: {'是' if '...' in content else '否'}")

# 测试4: 模式覆盖
print("\n[测试4] 模式覆盖")
print("-" * 60)

patterns = cross_retrieval_engine_improved.cross_query_patterns
print(f"\n共有 {len(patterns)} 个交叉查询模式:")
for pattern_name, info in patterns.items():
    print(f"\n  {pattern_name}:")
    print(f"    描述: {info['description']}")
    print(f"    关键词: {', '.join(info['keywords'])}")

# 测试5: 完整流程（模拟）
print("\n[测试5] 完整流程模拟")
print("-" * 60)

query = "挂科对奖学金申请有影响吗？"
print(f"\n查询: {query}")
print(f"\n完整流程:")
print("  1. 问题识别")
is_cross, pattern_info = cross_retrieval_engine_improved.is_cross_query(query)
if is_cross:
    print(f"     ✓ 识别为隐含关联问题")
    print(f"     ✓ 模式: {pattern_info['pattern_name']}")
    print(f"     ✓ 关键词: {', '.join(pattern_info['keywords'])}")
else:
    print(f"     ✗ 不是隐含关联问题")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)