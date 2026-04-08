# -*- coding: utf-8 -*-
"""
将 JSON 知识库数据导入 ChromaDB

用法：
    cd 人工智能专业培养rag系统
    python scripts/import_to_chromadb.py [--reset]

参数：
    --reset  清空已有集合后重新导入（默认行为）
"""
import sys
import json
import re
import time
import argparse
from pathlib import Path

# 将 backend 目录加入 sys.path，以便导入 config 等模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from config import (
    KNOWLEDGE_BASE_PATH,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
)

# ── 噪音过滤（与 knowledge_base.py 保持一致） ──────────────────────
NOISE_KEYWORDS = [
    '校徽释义', '校训释义', '校风释义', '教风释义', '学风释义',
    '编制说明', '安徽信息工程学院简介 .'
]


def is_noise_chunk(text: str) -> bool:
    """判断是否为噪音 chunk"""
    if any(kw in text for kw in NOISE_KEYWORDS):
        return True
    # 纯目录 chunk（大量省略号，中文字符占比低）
    if text.count('...') >= 5:
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars < len(text) * 0.3:
            return True
    return False


def load_chunks() -> list:
    """加载并过滤 JSON 知识库"""
    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"❌ 知识库文件不存在: {KNOWLEDGE_BASE_PATH}")
        sys.exit(1)

    with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw_chunks = data.get('chunks', [])
    if not raw_chunks:
        print("❌ 知识库中没有知识块")
        sys.exit(1)

    chunks = [c for c in raw_chunks if not is_noise_chunk(c.get('text', ''))]
    filtered = len(raw_chunks) - len(chunks)
    print(f"📚 加载知识库: {len(raw_chunks)} 个 chunk，过滤噪音 {filtered} 个，有效 {len(chunks)} 个")
    return chunks


def import_to_chromadb(chunks: list, reset: bool = True):
    """将 chunk 列表导入 ChromaDB"""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("❌ 未安装 chromadb，请先运行: pip install chromadb")
        sys.exit(1)

    print(f"🔧 ChromaDB 存储目录: {CHROMA_PERSIST_DIR}")
    print(f"🔧 集合名称: {CHROMA_COLLECTION_NAME}")

    # 初始化客户端
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )

    # 初始化 embedding 函数（必须与 chroma_knowledge_base.py 运行时一致）
    embedding_function = None
    from config import EMBEDDING_MODEL_NAME
    EMBEDDING_MODEL = EMBEDDING_MODEL_NAME
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        print(f"✅ 使用 SentenceTransformer ({EMBEDDING_MODEL}) 生成向量")
    except Exception as e:
        print(f"⚠️  SentenceTransformer 不可用 ({e})，将使用 ChromaDB 默认 embedding")

    # 重置或获取集合
    if reset:
        try:
            client.delete_collection(CHROMA_COLLECTION_NAME)
            print("🗑️  已清空旧集合")
        except Exception:
            pass  # 集合不存在，忽略

    collection_kwargs = {
        "name": CHROMA_COLLECTION_NAME,
        "metadata": {
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 200,
            "hnsw:M": 16,
        }
    }
    if embedding_function:
        collection_kwargs["embedding_function"] = embedding_function

    collection = client.get_or_create_collection(**collection_kwargs)
    print(f"📦 集合就绪，当前文档数: {collection.count()}")

    # ── 分批导入（ChromaDB 单次最多约 5000 条） ──────────────
    BATCH_SIZE = 200
    total = len(chunks)
    start_time = time.time()

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = chunks[batch_start:batch_end]

        ids = [f"chunk_{c.get('id', str(i))}" for i, c in enumerate(batch, start=batch_start)]
        documents = [c['text'] for c in batch]
        metadatas = [
            {
                "section": c.get("section", ""),
                "char_count": c.get("char_count", len(c['text'])),
                "original_id": str(c.get("id", "")),
            }
            for c in batch
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        progress = batch_end / total * 100
        print(f"  ⏳ 已导入 {batch_end}/{total} ({progress:.0f}%)")

    elapsed = time.time() - start_time
    final_count = collection.count()
    print(f"\n✅ 导入完成！共 {final_count} 个文档，耗时 {elapsed:.1f}s")

    # 简单验证：做一次测试查询
    print("\n── 验证查询 ──")
    test_queries = ["奖学金评选条件", "请假流程", "转专业"]
    for q in test_queries:
        results = collection.query(query_texts=[q], n_results=1)
        if results['documents'] and results['documents'][0]:
            doc = results['documents'][0][0]
            dist = results['distances'][0][0] if results.get('distances') else None
            sim = f"(相似度 {1 - dist:.3f})" if dist is not None else ""
            preview = doc[:80].replace('\n', ' ') + "..."
            print(f"  🔍 「{q}」→ {preview} {sim}")
        else:
            print(f"  🔍 「{q}」→ 无结果")


def main():
    parser = argparse.ArgumentParser(description="将知识库导入 ChromaDB")
    parser.add_argument('--no-reset', action='store_true', help="不清空已有集合，追加导入")
    args = parser.parse_args()

    print("=" * 60)
    print("  ChromaDB 知识库导入工具")
    print("=" * 60)

    chunks = load_chunks()
    import_to_chromadb(chunks, reset=not args.no_reset)

    print("\n💡 提示：在 .env 或环境变量中设置以下值以启用 ChromaDB 检索：")
    print("   USE_CHROMADB=true")
    print("   USE_HYBRID_SEARCH=true  (可选，启用混合检索)")


if __name__ == "__main__":
    main()
