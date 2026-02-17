# -*- coding: utf-8 -*-
"""
系统测试脚本
验证前后端连接和核心功能
"""
import sys
from pathlib import Path

# 在模块级别导入
from config import *
from models import *
from knowledge_base import knowledge_base
from agent import agent
from session_manager import session_manager, memory_manager

def test_imports():
    """测试模块导入"""
    print("[测试 1/6] 测试模块导入...")
    try:
        # 模块已在顶部导入
        print("  ✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"  ✗ 模块导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("\n[测试 2/6] 测试配置...")
    try:
        from config import (
            KNOWLEDGE_BASE_PATH, API_HOST, API_PORT,
            TOP_K_RESULTS, MIN_SIMILARITY, AGENT_NAME
        )
        print(f"  ✓ API: {API_HOST}:{API_PORT}")
        print(f"  ✓ 知识库路径: {KNOWLEDGE_BASE_PATH}")
        print(f"  ✓ 知识库文件存在: {KNOWLEDGE_BASE_PATH.exists()}")
        print(f"  ✓ 智能体名称: {AGENT_NAME}")
        print(f"  ✓ TOP_K: {TOP_K_RESULTS}, MIN_SIMILARITY: {MIN_SIMILARITY}")
        return True
    except Exception as e:
        print(f"  ✗ 配置测试失败: {e}")
        return False

def test_knowledge_base():
    """测试知识库加载"""
    print("\n[测试 3/6] 测试知识库加载...")
    try:
        from knowledge_base import knowledge_base

        if not knowledge_base.load():
            print("  ✗ 知识库加载失败")
            return False

        print(f"  ✓ 知识库加载成功")
        print(f"  ✓ 知识块数量: {len(knowledge_base.chunks)}")

        stats = knowledge_base.get_statistics()
        print(f"  ✓ 总字符数: {stats.get('total_characters', 0):,}")
        print(f"  ✓ 平均块大小: {stats.get('average_chunk_size', 0):.0f}")
        print(f"  ✓ 关键词数: {len(stats.get('keywords', []))}")

        return True
    except Exception as e:
        print(f"  ✗ 知识库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search():
    """测试搜索功能"""
    print("\n[测试 4/6] 测试搜索功能...")
    try:
        from knowledge_base import knowledge_base

        if not knowledge_base.is_loaded():
            print("  ✗ 知识库未加载，跳过搜索测试")
            return False

        test_queries = [
            "奖学金",
            "考试",
            "宿舍"
        ]

        for query in test_queries:
            results = knowledge_base.search(query, top_k=3)
            print(f"  ✓ 搜索 '{query}' 找到 {len(results)} 个结果")

        return True
    except Exception as e:
        print(f"  ✗ 搜索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent():
    """测试智能体"""
    print("\n[测试 5/6] 测试智能体...")
    try:
        from agent import agent

        test_query = "奖学金怎么申请？"
        result = agent.process_query(test_query, session_history=None, use_rag=True)

        print(f"  ✓ 智能体回复生成成功")
        print(f"  ✓ 回复长度: {len(result['response'])} 字符")
        print(f"  ✓ 引用来源数: {len(result.get('sources', []))}")
        print(f"  ✓ 回复预览: {result['response'][:100]}...")

        return True
    except Exception as e:
        print(f"  ✗ 智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_manager():
    """测试会话管理"""
    print("\n[测试 6/6] 测试会话管理...")
    try:
        from session_manager import session_manager

        # 创建会话
        session_id = session_manager.create_session(user_id="test_user")
        print(f"  ✓ 创建会话: {session_id}")

        # 获取会话
        session_data = session_manager.get_session(session_id)
        print(f"  ✓ 获取会话成功: {session_data is not None}")

        # 更新会话
        success = session_manager.update_session(
            session_id,
            "测试消息",
            "测试回复"
        )
        print(f"  ✓ 更新会话成功: {success}")

        # 获取历史
        history = session_manager.get_session_history(session_id)
        print(f"  ✓ 获取历史成功: {len(history)} 条消息")

        # 删除会话
        success = session_manager.delete_session(session_id)
        print(f"  ✓ 删除会话成功: {success}")

        return True
    except Exception as e:
        print(f"  ✗ 会话管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=" * 70)
    print("安信工AI小助手 - 系统测试")
    print("=" * 70)

    tests = [
        test_imports,
        test_config,
        test_knowledge_base,
        test_search,
        test_agent,
        test_session_manager
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"总计: {total} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")

    if all(results):
        print("\n✓ 所有测试通过！系统可以正常启动。")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查上述错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())