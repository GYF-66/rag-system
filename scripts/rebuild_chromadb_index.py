# -*- coding: utf-8 -*-
"""
重建ChromaDB索引脚本
使用新的BGE中文embedding模型和统一分块器重建索引
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加backend到路径
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / 'backend'
sys.path.insert(0, str(BASE_DIR))  # 项目根目录（config.py 在此处不存在，但 backend/config.py 可通过 backend. 前缀导入）
sys.path.insert(0, str(BACKEND_DIR))  # backend/ 目录（使 from config import 能找到 backend/config.py）

# Import config first to init env
from config import KNOWLEDGE_BASE_PATH, EMBEDDING_MODEL_NAME, USE_CHROMADB

# Import chroma knowledge base after path setup
from backend.retrieval.chroma_knowledge_base import chroma_knowledge_base  # noqa: E402
from backend.chunking.unified_chunker import UnifiedChunker  # noqa: E402

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_knowledge_base():
    """加载原始知识库数据"""
    logger.info(f"加载知识库: {KNOWLEDGE_BASE_PATH}")
    
    if not KNOWLEDGE_BASE_PATH.exists():
        raise FileNotFoundError(f"知识库文件不存在: {KNOWLEDGE_BASE_PATH}")
    
    with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"知识库加载完成: {len(data.get('chunks', []))} 个分块")
    return data


def rebuild_with_unified_chunker(original_data):
    """
    使用统一分块器重新分块原始文本

    Args:
        original_data: 原始知识库数据

    Returns:
        新的分块列表
    """
    logger.info("使用统一分块器重新分块...")

    # 初始化统一分块器
    chunker = UnifiedChunker(
        chunk_size=800,
        chunk_overlap=150,
        respect_sentence_boundary=True,
        min_chunk_size=50
    )

    # 合并所有原始文本
    all_text = ""
    for chunk in original_data.get('chunks', []):
        all_text += chunk.get('text', '') + "\n\n"

    # 重新分块
    new_chunks = chunker.chunk_text(
        text=all_text,
        metadata={
            'source': original_data.get('metadata', {}).get('source', '人工智能专业知识库'),
            'rebuild_date': datetime.now().isoformat()
        }
    )

    logger.info(f"重新分块完成: {len(new_chunks)} 个分块")
    return new_chunks


def rebuild_from_kb_json():
    """
    直接从 KB JSON 重建 ChromaDB 索引（不重新分块，避免引入重复处理）
    KB JSON 中的 chunks 已经是 pdf_corpus_builder + UnifiedChunker 处理好的数据
    """
    logger.info("直接从 KB JSON 加载 chunks...")

    kb_path = KNOWLEDGE_BASE_PATH
    with open(kb_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data.get('chunks', [])
    logger.info(f"从 KB JSON 加载了 {len(chunks)} 个 chunks")
    return chunks


def rebuild_chromadb_index(chunks):
    """
    重建ChromaDB索引

    Args:
        chunks: 分块列表（来自 UnifiedChunker.chunk_text 的 Dict）
    """
    logger.info("开始重建ChromaDB索引...")

    # 重置现有集合（删除并重建）
    logger.info("重置现有集合...")
    try:
        chroma_knowledge_base.reset()
        logger.info("现有集合已重置")
    except Exception as e:
        logger.warning(f"重置集合失败（可能不存在）: {e}")

    # 批量添加文档（使用正确的 add_documents API）
    batch_size = 50
    total_chunks = len(chunks)

    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]

        documents = []
        metadatas = []
        ids = []

        for chunk in batch:
            # KB JSON chunk metadata structure:
            # - id, text, char_count, section, title, document_id, source_path, page_start, page_end, keywords, chunk_type, metadata
            # - metadata sub-dict may contain: document_id, title, source_path, section_title, section_path, etc.
            chunk_id = chunk.get('id', f"chunk_{chunk.get('chunk_index', 0)}")
            raw_meta = chunk.get('metadata', {})
            # ChromaDB rejects empty lists → strip them
            clean_meta = {k: v for k, v in raw_meta.items() if not (isinstance(v, list) and len(v) == 0)}

            # Top-level fields take precedence, fall back to metadata sub-dict
            doc_id = chunk.get('document_id') or clean_meta.get('document_id', '')
            src_path = chunk.get('source_path') or clean_meta.get('source_path', '')
            doc_title = chunk.get('title') or clean_meta.get('title', '')

            documents.append(chunk.get('text', ''))
            metadatas.append({
                **clean_meta,
                'document_id': doc_id,
                'source_path': src_path,
                'section': chunk.get('section', ''),
                'title': doc_title,
                'char_count': chunk.get('char_count', 0),
                'chunk_type': clean_meta.get('chunk_type', ''),
                'section_path_text': clean_meta.get('section_path_text', ''),
            })
            ids.append(chunk_id)

        chroma_knowledge_base.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        progress = min(i + batch_size, total_chunks)
        logger.info(f"进度: {progress}/{total_chunks} ({progress/total_chunks*100:.1f}%)")

    logger.info("ChromaDB索引重建完成")


def save_new_knowledge_base(chunks, original_data, output_path=None):
    """
    保存新的知识库文件（可选）
    
    Args:
        chunks: 新分块列表
        original_data: 原始数据
        output_path: 输出路径（默认覆盖原文件）
    """
    if output_path is None:
        output_path = KNOWLEDGE_BASE_PATH
    
    logger.info(f"保存新知识库: {output_path}")
    
    # 构建新的知识库数据
    new_data = {
        'version': '2.0',
        'created_at': original_data.get('created_at'),
        'rebuilt_at': datetime.now().isoformat(),
        'metadata': {
            **original_data.get('metadata', {}),
            'total_chunks': len(chunks),
            'chunk_size': 800,
            'chunk_overlap': 150,
            'chunker': 'UnifiedChunker',
            'embedding_model': 'BAAI/bge-small-zh-v1.5'
        },
        'chunks': [
            {
                'id': str(chunk['chunk_index']),
                'text': chunk['text'],
                'metadata': chunk.get('metadata', {})
            }
            for chunk in chunks
        ]
    }
    
    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    logger.info("新知识库已保存")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("ChromaDB索引重建工具")
    logger.info("=" * 60)

    try:
        # 1. 直接从 KB JSON 加载已处理好的 chunks（避免重新分块引入误差）
        chunks = rebuild_from_kb_json()

        # 2. 重建 ChromaDB 索引
        rebuild_chromadb_index(chunks)

        logger.info("=" * 60)
        logger.info("索引重建成功！")
        logger.info("=" * 60)
        logger.info(f"总分块数: {len(chunks)}")
        logger.info(f"Embedding模型: {EMBEDDING_MODEL_NAME}")
        logger.info(f"分块策略: 800字符, 150重叠 (来自 KB JSON)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"索引重建失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
