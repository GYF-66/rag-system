# -*- coding: utf-8 -*-
"""
基于 ChromaDB 的知识库实现
支持向量检索和混合检索
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging

from config import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    USE_CHROMADB
)

logger = logging.getLogger(__name__)


class ChromaKnowledgeBase:
    """ChromaDB 知识库"""

    def __init__(
        self,
        persist_directory: str = None,
        collection_name: str = None
    ):
        self.persist_directory = persist_directory or str(CHROMA_PERSIST_DIR)
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 初始化 Embedding 函数
        self.embedding_function = None
        self._init_embedding_function()

        # 获取或创建集合
        self.collection = None
        self._init_collection()

        self._loaded = False
        logger.info(f"ChromaDB 知识库初始化完成: {self.collection_name}")

    def _init_embedding_function(self):
        """初始化 Embedding 函数"""
        try:
            from chromadb.utils import embedding_functions

            if EMBEDDING_MODEL['provider'] == 'openai':
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=EMBEDDING_MODEL['api_key'],
                    model_name=EMBEDDING_MODEL['model']
                )
                logger.info(f"使用 OpenAI Embedding: {EMBEDDING_MODEL['model']}")
            else:
                # 使用默认的 sentence-transformers
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                logger.info("使用 Sentence Transformer Embedding")
        except Exception as e:
            logger.warning(f"初始化 Embedding 函数失败: {e}，将使用默认函数")

    def _init_collection(self):
        """初始化集合"""
        try:
            if self.embedding_function:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={
                        "hnsw:space": "cosine",  # 使用余弦相似度
                        "hnsw:construction_ef": 200,
                        "hnsw:M": 16
                    }
                )
            else:
                # 不使用 embedding 函数，使用外部向量
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        "hnsw:space": "cosine"
                    }
                )
                logger.info("集合创建成功（不使用内部 Embedding 函数）")
        except Exception as e:
            logger.error(f"初始化集合失败: {e}")
            raise

    def load(self) -> bool:
        """加载知识库"""
        try:
            count = self.collection.count()
            self._loaded = True
            logger.info(f"知识库加载成功: {count} 个文档")
            return True
        except Exception as e:
            logger.error(f"加载知识库失败: {e}")
            return False

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict],
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> bool:
        """
        添加文档到知识库

        Args:
            documents: 文档列表
            metadatas: 元数据列表
            ids: 文档ID列表（可选）
            embeddings: 向量列表（可选，如果不提供则使用内部 Embedding）

        Returns:
            是否成功
        """
        try:
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]

            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            logger.info(f"成功添加 {len(documents)} 个文档")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None,
        query_embeddings: Optional[List[float]] = None
    ) -> List[Dict]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            query_embeddings: 查询向量（可选）

        Returns:
            搜索结果列表
        """
        try:
            results = self.collection.query(
                query_texts=[query] if query_embeddings is None else None,
                query_embeddings=[query_embeddings] if query_embeddings else None,
                n_results=top_k,
                where=where,
                where_document=where_document
            )

            # 格式化结果
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        'id': doc_id,
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity': 1 - results['distances'][0][i] if 'distances' in results and results['distances'] else 0
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """获取单个文档"""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=['documents', 'metadatas']
            )

            if results['ids'] and results['ids'][0]:
                return {
                    'id': results['ids'][0],
                    'text': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            return None

        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"文档已删除: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def update_document(
        self,
        doc_id: str,
        document: str = None,
        metadata: Dict = None,
        embeddings: List[float] = None
    ) -> bool:
        """更新文档"""
        try:
            self.collection.update(
                ids=[doc_id],
                documents=[document] if document else None,
                metadatas=[metadata] if metadata else None,
                embeddings=[embeddings] if embeddings else None
            )
            logger.info(f"文档已更新: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            return False

    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'embedding_model': EMBEDDING_MODEL.get('model', 'unknown'),
                'embedding_provider': EMBEDDING_MODEL.get('provider', 'unknown')
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def reset(self) -> bool:
        """重置知识库"""
        try:
            self.client.delete_collection(self.collection_name)
            self._init_collection()
            self._loaded = False
            logger.info("知识库已重置")
            return True
        except Exception as e:
            logger.error(f"重置知识库失败: {e}")
            return False

    def is_loaded(self) -> bool:
        """检查是否已加载"""
        return self._loaded


# 全局实例
chroma_knowledge_base = ChromaKnowledgeBase() if USE_CHROMADB else None

if USE_CHROMADB and chroma_knowledge_base:
    logger.info("ChromaDB 知识库已启用")
else:
    logger.info("ChromaDB 知识库未启用，使用 TF-IDF 检索")