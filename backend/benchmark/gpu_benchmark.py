# -*- coding: utf-8 -*-
"""
GPU Benchmark 工具
测试 Embedding 和 Reranker 在 CPU vs GPU 模式下的性能
"""
import argparse
import time
import torch
from typing import List, Tuple


def benchmark_embedding(
    model_name: str,
    texts: List[str],
    device: str,
    warmup: int = 2,
    runs: int = 5
) -> Tuple[float, float]:
    """Benchmark embedding model. Returns (mean_ms, std_ms)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device=device)

    # Warmup
    for _ in range(warmup):
        _ = model.encode(texts)

    # Benchmark
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        _ = model.encode(texts)
        if device == 'cuda':
            torch.cuda.synchronize()
        times.append(time.perf_counter() - start)

    del model
    if device == 'cuda':
        torch.cuda.empty_cache()

    mean_ms = (sum(times) / len(times)) * 1000
    std_ms = (max(times) - min(times)) * 500  # half-range approximation
    return mean_ms, std_ms


def benchmark_cross_encoder(
    model_name: str,
    query: str,
    documents: List[str],
    device: str,
    warmup: int = 1,
    runs: int = 3
) -> Tuple[float, float]:
    """Benchmark cross-encoder reranker. Returns (mean_ms, std_ms)."""
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(model_name, device=device)
    pairs = [[query, doc] for doc in documents]

    # Warmup
    for _ in range(warmup):
        _ = model.predict(pairs)

    # Benchmark
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        _ = model.predict(pairs)
        if device == 'cuda':
            torch.cuda.synchronize()
        times.append(time.perf_counter() - start)

    del model
    if device == 'cuda':
        torch.cuda.empty_cache()

    mean_ms = (sum(times) / len(times)) * 1000
    std_ms = (max(times) - min(times)) * 500
    return mean_ms, std_ms


def run_gpu_benchmark(model_name: str, embedding_model: str, reranker_model: str):
    """运行完整 GPU Benchmark。"""
    print("=" * 60)
    print(f"GPU Benchmark — {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("=" * 60)

    texts = [
        "人工智能专业培养方案",
        "计算机视觉课程教学大纲",
        "深度学习模型训练方法",
        "安徽信息工程学院学生管理规定",
        "毕业要求达成情况评价",
    ] * 4  # 20 texts

    query = "人工智能专业的培养目标是什么"

    # ── Embedding ──────────────────────────────────────────────
    print("\n## Embedding (BGE-M3 / all-MiniLM-L6-v2)")

    for m in [embedding_model, 'all-MiniLM-L6-v2']:
        for device in ['cuda', 'cpu']:
            try:
                mean, std = benchmark_embedding(m, texts, device)
                print(f"  {m:35s} {device:4s}: {mean:7.2f} ± {std:.2f} ms")
            except Exception as e:
                print(f"  {m:35s} {device:4s}: FAILED ({e})")

    # ── Cross-Encoder Reranker ─────────────────────────────────
    print(f"\n## Cross-Encoder Reranker ({reranker_model})")

    docs = [f"文档{i}：人工智能专业相关课程内容" for i in range(20)]
    for device in ['cuda', 'cpu']:
        try:
            mean, std = benchmark_cross_encoder(reranker_model, query, docs, device)
            print(f"  {reranker_model:35s} {device:4s}: {mean:7.2f} ± {std:.2f} ms")
        except Exception as e:
            print(f"  {reranker_model:35s} {device:4s}: FAILED ({e})")

    # ── Matmul Baseline ────────────────────────────────────────
    print("\n## Matmul Baseline (1024x1024)")
    a = torch.randn(1024, 1024, device='cuda')
    b = torch.randn(1024, 1024, device='cuda')
    for _ in range(3):
        _ = torch.matmul(a, b)
    torch.cuda.synchronize()

    times = []
    for _ in range(10):
        start = time.perf_counter()
        for _ in range(10):
            _ = torch.matmul(a, b)
        torch.cuda.synchronize()
        times.append(time.perf_counter() - start)

    mean_ms = (sum(times) / len(times)) * 100
    print(f"  1024x1024 matmul (x10): {mean_ms:.2f} ms")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GPU Benchmark Tool')
    parser.add_argument('--embedding-model', default='BAAI/bge-m3',
                        help='Embedding model name')
    parser.add_argument('--reranker-model', default='BAAI/bge-reranker-base',
                        help='Reranker model name')
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("CUDA not available, running CPU-only benchmark")
        import sys
        sys.exit(0)

    run_gpu_benchmark(
        model_name='benchmark',
        embedding_model=args.embedding_model,
        reranker_model=args.reranker_model,
    )
