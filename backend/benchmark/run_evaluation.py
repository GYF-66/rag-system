# -*- coding: utf-8 -*-
"""
RAG 系统评测脚本
在 test_dataset 上跑检索指标，返回 Precision@K、Recall@K、MRR、nDCG、Latency
"""
import sys
import json
import time
from pathlib import Path

# Add project root to path (parent of backend/)
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

# Import config first to init env
from config import (
    TOP_K_RESULTS, SEARCH_TOP_K, USE_CHROMADB, USE_HYBRID_SEARCH,
    EMBEDDING_MODEL_NAME, EMBEDDING_DEVICE,
)
from evaluation.rag_evaluator import RAGEvaluator

# Import retrieval components
try:
    from retrieval import hybrid_retriever, chroma_knowledge_base, knowledge_base
    from retrieval.hybrid_retriever import HybridRetriever
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def load_test_dataset(path: str):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def run_retrieval_evaluation():
    """运行检索评测。"""
    print("=" * 60)
    print("RAG 检索评测")
    print("=" * 60)

    # Init retriever
    print(f"\n初始化检索器...")
    print(f"  USE_CHROMADB={USE_CHROMADB}")
    print(f"  USE_HYBRID_SEARCH={USE_HYBRID_SEARCH}")
    print(f"  EMBEDDING_MODEL={EMBEDDING_MODEL_NAME}")
    print(f"  EMBEDDING_DEVICE={EMBEDDING_DEVICE}")
    print(f"  TOP_K={TOP_K_RESULTS}, SEARCH_TOP_K={SEARCH_TOP_K}")

    retriever = hybrid_retriever
    if retriever is None:
        print("ERROR: hybrid_retriever 初始化失败")
        sys.exit(1)

    # Load test dataset - file is at backend/evaluation/test_dataset.json
    dataset_path = Path(__file__).parent.parent / "evaluation" / "test_dataset.json"
    if not dataset_path.exists():
        dataset_path = _project_root / "backend" / "evaluation" / "test_dataset.json"
    test_cases = load_test_dataset(str(dataset_path))
    print(f"\n测试集: {len(test_cases)} 条评测用例")

    # Ensure knowledge base is loaded (needed for evaluator corpus)
    from retrieval.knowledge_base import knowledge_base as tfidf_kb
    if not getattr(tfidf_kb, '_loaded', False):
        loaded = tfidf_kb.load()
        print(f"TF-IDF KB {'loaded' if loaded else 'FAILED to load'} ({len(tfidf_kb.chunks)} chunks)")

    # Run evaluation
    print("\n开始评测（检索层）...")
    evaluator = RAGEvaluator(test_dataset_path=str(dataset_path))
    results = evaluator.evaluate_retrieval(
        test_cases=test_cases,
        retriever=retriever,
        top_k_values=(1, 3, 5, 10),
    )

    # Print summary
    print("\n" + "=" * 60)
    print("评测结果摘要")
    print("=" * 60)

    metrics_to_show = [
        'precision_at_1', 'precision_at_3', 'precision_at_5',
        'recall_at_3', 'recall_at_5', 'recall_at_10',
        'mrr', 'ndcg_at_3', 'ndcg_at_5',
        'latency_ms', 'irrelevant_doc_rate', 'context_duplication_rate',
    ]

    for metric in metrics_to_show:
        val = results.get(metric)
        std = results.get(f'{metric}_std')
        if val is not None:
            if 'latency' in metric:
                print(f"  {metric:30s}: {val:7.2f} ms  (std={std:.2f})" if std else f"  {metric:30s}: {val:7.2f} ms")
            else:
                print(f"  {metric:30s}: {val:.4f}  (std={std:.4f})" if std else f"  {metric:30s}: {val:.4f}")

    # Per-case results
    print("\n各用例检索结果:")
    print(f"  {'ID':30s} {'Query':20s} {'P@3':6s} {'R@3':6s} {'MRR':6s} {'Latency':8s}")
    print("  " + "-" * 80)
    for case in results.get('per_case', []):
        q = case['query'][:18] + '..' if len(case['query']) > 20 else case['query']
        print(f"  {case['id']:30s} {q:20s} "
              f"{case.get('precision_at_3', 0):6.3f} "
              f"{case.get('recall_at_3', 0):6.3f} "
              f"{case.get('mrr', 0):6.3f} "
              f"{case['latency_ms']:7.1f}ms")

    # Save results
    output_path = _project_root / "auto-research" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evaluator.save_evaluation_results(results, str(output_path))
    print(f"\n结果已保存: {output_path}")

    return results


if __name__ == '__main__':
    run_retrieval_evaluation()
