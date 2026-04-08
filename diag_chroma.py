"""诊断 ChromaDB 搜索失败的原因"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

from retrieval.chroma_knowledge_base import chroma_knowledge_base as ckb

print(f"Collection count: {ckb.collection.count()}")
print(f"Embedding function type: {type(ckb.embedding_function)}")

# Test 1: normal search
try:
    r = ckb.search("人工智能专业核心课程", top_k=5)
    print(f"Test 1 (top_k=5): {len(r)} results, ok")
except Exception as e:
    print(f"Test 1 FAILED: {e}")

# Test 2: larger top_k
try:
    r = ckb.search("人工智能专业核心课程", top_k=16)
    print(f"Test 2 (top_k=16): {len(r)} results, ok")
except Exception as e:
    print(f"Test 2 FAILED: {e}")

# Test 3: with min_similarity kwarg (should TypeError)
try:
    r = ckb.search("人工智能专业核心课程", top_k=16, min_similarity=0.03)
    print(f"Test 3 (min_similarity): {len(r)} results, ok")
except TypeError as e:
    print(f"Test 3 TypeError (expected): {e}")
except Exception as e:
    print(f"Test 3 FAILED: {type(e).__name__}: {e}")

# Test 4: long query text (HyDE doc)
hyde_text = "在安徽信息工程学院人工智能专业中，学生需要学习以下核心课程：机器学习、深度学习、自然语言处理、计算机视觉等。这些课程涵盖从基础理论到实际应用的全方位知识体系。"
try:
    r = ckb.search(hyde_text[:500], top_k=3)
    print(f"Test 4 (HyDE text, top_k=3): {len(r)} results, ok")
except Exception as e:
    print(f"Test 4 FAILED: {type(e).__name__}: {e}")

# Test 5: direct chromadb collection.query
try:
    r = ckb.collection.query(query_texts=["人工智能"], n_results=5)
    print(f"Test 5 (direct query): {len(r['ids'][0])} results, ok")
except Exception as e:
    print(f"Test 5 FAILED: {type(e).__name__}: {e}")

# Test 6: query with top_k > count
try:
    r = ckb.search("测试", top_k=1000)
    print(f"Test 6 (top_k=1000): {len(r)} results, ok")
except Exception as e:
    print(f"Test 6 FAILED: {type(e).__name__}: {e}")
