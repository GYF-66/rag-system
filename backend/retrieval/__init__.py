# -*- coding: utf-8 -*-
"""检索模块 — 知识库、向量检索、混合检索、重排序"""
from .knowledge_base import KnowledgeBase, knowledge_base
from .reranker import reranker

__all__ = ['KnowledgeBase', 'knowledge_base', 'reranker']

# 可选组件（依赖 chromadb）
try:
    from .chroma_knowledge_base import ChromaKnowledgeBase, chroma_knowledge_base
    __all__ += ['ChromaKnowledgeBase', 'chroma_knowledge_base']
except ImportError:
    chroma_knowledge_base = None

try:
    from .hybrid_retriever import HybridRetriever, hybrid_retriever
    __all__ += ['HybridRetriever', 'hybrid_retriever']
except ImportError:
    hybrid_retriever = None

try:
    from .cross_retrieval_engine import cross_retrieval_engine_improved
    __all__ += ['cross_retrieval_engine_improved']
except ImportError:
    cross_retrieval_engine_improved = None
