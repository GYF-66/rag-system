# -*- coding: utf-8 -*-
"""
知识库测试脚本
验证人工智能专业知识库的加载和检索功能
"""
import sys
sys.path.insert(0, 'backend')

from retrieval.knowledge_base import KnowledgeBase

def test_knowledge_base():
    """测试知识库功能"""
    print("=" * 70)
    print("人工智能专业知识库测试")
    print("=" * 70)
    
    # 1. 加载知识库
    print("\n[1] 测试知识库加载...")
    kb = KnowledgeBase()
    success = kb.load()
    
    if not success:
        print("[FAIL] 知识库加载失败")
        return False
    
    print(f"[OK] 知识库加载成功")
    print(f"  - 知识块数量: {len(kb.chunks)}")
    print(f"  - 数据源: {kb.metadata.get('source', 'N/A')}")
    print(f"  - 总字符数: {kb.metadata.get('total_characters', 0):,}")
    
    # 2. 测试检索功能
    print("\n[2] 测试知识库检索...")
    test_queries = [
        "专业培养目标是什么",
        "机器学习课程内容",
        "核心课程有哪些",
        "实践环节安排"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        results = kb.search(query, top_k=2)
        
        if not results:
            print("  [WARN] 未找到相关结果")
            continue
        
        for i, result in enumerate(results, 1):
            similarity = result.get('similarity', 0)
            text = result.get('text', '')
            preview = text[:100].replace('\n', ' ')
            print(f"  [{i}] 相似度: {similarity:.3f}")
            print(f"      内容: {preview}...")
    
    # 3. 统计信息
    print("\n[3] 知识库统计信息")
    print(f"  - 总块数: {len(kb.chunks)}")
    print(f"  - 平均块大小: {kb.metadata.get('average_chunk_size', 0)} 字符")
    print(f"  - 分块参数: size={kb.metadata.get('chunk_size', 0)}, overlap={kb.metadata.get('chunk_overlap', 0)}")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] 所有测试通过!")
    print("=" * 70)
    return True

if __name__ == '__main__':
    try:
        test_knowledge_base()
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
