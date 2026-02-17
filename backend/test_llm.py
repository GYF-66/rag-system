# -*- coding: utf-8 -*-
"""
测试 LLM 集成
"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_llm():
    """测试 LLM 服务"""
    from llm_service import llm_service
    from knowledge_base import knowledge_base
    
    print("=" * 60)
    print("LLM 集成测试")
    print("=" * 60)
    
    # 1. 检查 LLM 服务状态
    print(f"\n[1] LLM 服务状态检查")
    print(f"    - API Key 配置: {'✅ 已配置' if llm_service.is_available() else '❌ 未配置'}")
    print(f"    - API Base URL: {llm_service.base_url}")
    print(f"    - Model: {llm_service.model}")
    
    # 2. 加载知识库
    print(f"\n[2] 知识库加载")
    if knowledge_base.load():
        stats = knowledge_base.get_statistics()
        print(f"    - 知识块数量: {stats['total_chunks']}")
        print(f"    - 总字符数: {stats['total_characters']}")
    else:
        print("    - ❌ 知识库加载失败")
        return
    
    # 3. 测试检索
    print(f"\n[3] 知识库检索测试")
    test_query = "奖学金申请条件是什么"
    results = knowledge_base.search(test_query, top_k=3)
    print(f"    查询: {test_query}")
    print(f"    结果数量: {len(results)}")
    if results:
        print(f"    最高相似度: {results[0].get('similarity', 0):.4f}")
    
    # 4. 测试 LLM 调用
    print(f"\n[4] LLM 调用测试")
    if llm_service.is_available():
        # 构建上下文
        context = "\n\n".join([r.get('text', '')[:500] for r in results[:3]])
        
        print(f"    发送请求到 LLM...")
        response = await llm_service.chat(test_query, context, None)
        
        if response:
            print(f"    ✅ LLM 回复成功！")
            print(f"\n    回复内容（前500字）:")
            print("-" * 40)
            print(response[:500])
            print("-" * 40)
        else:
            print(f"    ❌ LLM 回复失败")
    else:
        print("    ⚠️  LLM 服务未配置，跳过")
    
    # 5. 测试完整 Agent 流程
    print(f"\n[5] 完整 Agent 流程测试")
    from agent import agent
    
    result = await agent.process_query_async(
        query="挂科了还能申请奖学金吗？",
        session_history=None,
        use_rag=True,
        use_llm=True
    )
    
    print(f"    - 使用 LLM: {'✅' if result.get('used_llm') else '❌ 使用规则回复'}")
    print(f"    - 知识来源数量: {len(result.get('sources', []))}")
    print(f"\n    回复内容（前500字）:")
    print("-" * 40)
    print(result['response'][:500])
    print("-" * 40)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_llm())
