# Reasoning-RAG 架构设计文档

## 概述

本文档描述了人工智能专业知识库系统的 Reasoning-RAG（推理增强检索）架构。该架构在传统 RAG 的基础上，引入了 ChromaDB 向量数据库、Rerank 重排序和推理引擎，显著提升了检索准确性和回答的可解释性。

---

## 架构演进

### 原有架构（V1）
```
用户查询 → TF-IDF 检索 → 内容合并 → 规则生成 → 回答
```

### 新架构（V2 - Reasoning-RAG）
```
用户查询 → 查询分析 → ChromaDB 检索 → Rerank 重排序 → 推理引擎 → 回答 + 思考过程
```

---

## 核心组件

### 1. ChromaDB 向量知识库 (`chroma_knowledge_base.py`)

**功能**：使用 ChromaDB 替代 TF-IDF 进行向量检索

**特性**：
- 支持多种 Embedding 提供者（OpenAI、HuggingFace、简单 TF-IDF）
- 持久化存储向量索引
- 余弦相似度计算
- 自动降级机制（ChromaDB 不可用时使用 TF-IDF）

### 2. Rerank 重排序器 (`reranker.py`)

**功能**：对向量检索结果进行精排，提升相关性

### 3. 推理引擎 (`reasoning_engine.py`)

**功能**：记录和生成完整的思考过程

### 4. AI 智能体 V2 (`agent_v2.py`)

**功能**：整合所有组件，提供完整的问答服务

---

## 依赖安装

```bash
pip install chromadb jieba
```

---

## 参考资料

- [ChromaDB 官方文档](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)

