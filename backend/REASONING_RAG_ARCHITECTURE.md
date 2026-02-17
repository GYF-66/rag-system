# Reasoning-RAG 架构设计文档

## 概述

本文档描述了学生手册知识库系统的 Reasoning-RAG（推理增强检索）架构。该架构在传统 RAG 的基础上，引入了 ChromaDB 向量数据库、Rerank 重排序和推理引擎，显著提升了检索准确性和回答的可解释性。

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

**配置** (`config.py`)：
```python
CHROMA_PERSIST_DIR = BASE_DIR / "database" / "chroma_db"
CHROMA_COLLECTION_NAME = "student_manual_kb"

EMBEDDING_MODEL = {
    'provider': 'openai',  # openai / huggingface / local
    'model': 'text-embedding-ada-002',
    'api_key': os.getenv('OPENAI_API_KEY', ''),
    'dimension': 1536
}
```

**接口**：
```python
class ChromaKnowledgeBase:
    def load() -> bool
    def search(query, top_k, min_similarity) -> List[Dict]
    def get_chunk_by_id(chunk_id) -> Optional[Dict]
    def get_statistics() -> Dict
```

---

### 2. Rerank 重排序器 (`reranker.py`)

**功能**：对向量检索结果进行精排，提升相关性

**重排序方法**：
1. **交叉编码器（CrossEncoder）**（可选）
   - 使用 `sentence-transformers` 的 `CrossEncoder`
   - 模型：`BAAI/bge-reranker-base`
   - 更高的准确性，但需要额外依赖

2. **基于规则的重排序**（默认）
   - 关键词重叠度
   - 精确短语匹配
   - 章节相关性
   - 文本长度惩罚
   - 句子完整性
   - 内容唯一性

**特征权重**：
```python
weights = {
    'vector_similarity': 0.40,      # 向量相似度权重
    'keyword_overlap': 0.25,       # 关键词重叠权重
    'exact_match': 0.15,           # 精确匹配权重
    'phrase_match': 0.10,          # 短语匹配权重
    'length_penalty': 0.05,        # 长度惩罚权重
    'section_score': 0.03,         # 章节相关性权重
    'sentence_completeness': 0.01, # 句子完整性权重
    'uniqueness': 0.01             # 唯一性权重
}
```

**接口**：
```python
class Reranker:
    def rerank(query, documents, top_k) -> List[Dict]
    def get_statistics() -> Dict
```

---

### 3. 推理引擎 (`reasoning_engine.py`)

**功能**：记录和生成完整的思考过程

**思考过程结构**：
```python
class ThinkingProcess:
    query_analysis: ThinkingStep      # 查询分析
    retrieval: ThinkingStep           # 检索
    reranking: ThinkingStep           # 重排序
    reasoning: ThinkingStep           # 推理
    summary: str                      # 总结
    total_duration_ms: float          # 总耗时
```

**核心功能**：
1. **查询分析**
   - 提取关键词
   - 识别查询类型（奖学金、考试、纪律等）
   - 识别实体（奖学金类型、考试类型等）
   - 分析上下文依赖

2. **上下文合并**
   - 按章节分组
   - 合并同一章节内容
   - 去重和过滤

3. **推理生成**
   - 根据查询类型选择生成策略
   - 生成推理过程说明

**接口**：
```python
class ReasoningEngine:
    def start()
    def add_step(step_id, step_name, description, reasoning, ...)
    def end() -> ThinkingProcess
    def analyze_query(query, session_history) -> Tuple[str, Dict]
    def generate_reasoning(query, context, sources, analysis) -> str
    def merge_context(sources) -> str
```

---

### 4. AI 智能体 V2 (`agent_v2.py`)

**功能**：整合所有组件，提供完整的问答服务

**处理流程**：
```
1. 开始推理
2. 查询分析（推理引擎）
   - 提取关键词和意图
   - 识别实体
   - 分析上下文依赖
3. 向量检索（ChromaDB）
   - 生成查询向量
   - 检索 Top-K 文档
4. 重排序（Reranker）
   - 对检索结果精排
   - 保留最相关的文档
5. 推理生成（推理引擎）
   - 合并上下文
   - 生成推理说明
   - 生成回答
6. 结束推理，返回完整思考过程
```

**接口**：
```python
class StudentManualAgentV2:
    def process_query(
        query,
        session_history=None,
        use_rag=True,
        enable_thinking=True
    ) -> Dict
```

---

## 数据模型 (`models_v2.py`)

### 请求模型
```python
class ChatRequest:
    message: str
    session_id: Optional[str]
    user_id: Optional[str]
    use_rag: bool
    enable_thinking: bool  # 新增：是否显示思考过程

class SearchRequest:
    query: str
    top_k: int              # 检索结果数量
    rerank_top_k: int       # 最终返回数量
```

### 响应模型
```python
class ThinkingStep:
    step_id: int
    step_name: str
    description: str
    reasoning: str
    input_data: Optional[Dict]
    output_data: Optional[Dict]
    duration_ms: Optional[float]

class ThinkingProcess:
    query_analysis: ThinkingStep
    retrieval: ThinkingStep
    reranking: ThinkingStep
    reasoning: ThinkingStep
    summary: str
    total_duration_ms: float

class ChatResponse:
    response: str
    session_id: str
    sources: List[KnowledgeChunk]  # 包含 rerank_score
    thinking_process: Optional[ThinkingProcess]  # 新增
    timestamp: datetime
    metadata: Dict
```

---

## API 端点

### 聊天接口（更新）
```http
POST /api/chat
Content-Type: application/json

{
  "message": "奖学金怎么申请？",
  "session_id": "optional",
  "user_id": "optional",
  "use_rag": true,
  "enable_thinking": true  // 新增：是否返回思考过程
}
```

**响应**：
```json
{
  "response": "...",
  "session_id": "...",
  "sources": [
    {
      "id": "...",
      "text": "...",
      "char_count": 123,
      "similarity": 0.85,
      "rerank_score": 0.92,  // 新增：重排序分数
      "section": "第一章"
    }
  ],
  "thinking_process": {  // 新增：完整思考过程
    "query_analysis": {
      "step_id": 1,
      "step_name": "查询分析",
      "description": "分析用户查询意图和关键信息",
      "reasoning": "识别查询类型为「奖学金申请」，提取关键词「奖学金, 申请」",
      "input_data": {"query": "奖学金怎么申请？"},
      "output_data": {
        "query_type": "奖学金申请",
        "keywords": ["奖学金", "申请"],
        "entities": []
      },
      "duration_ms": 12.5
    },
    "retrieval": {
      "step_id": 2,
      "step_name": "向量检索",
      "description": "从知识库检索相关文档",
      "reasoning": "使用 ChromaDB 检索到 10 个相关文档",
      "input_data": {"query": "奖学金怎么申请？", "top_k": 10},
      "output_data": {"retrieved_count": 10},
      "duration_ms": 45.3
    },
    "reranking": {
      "step_id": 3,
      "step_name": "重排序",
      "description": "对检索结果进行精排",
      "reasoning": "使用基于规则的方法对检索结果进行重排序",
      "input_data": {"query": "奖学金怎么申请？", "documents_count": 10},
      "output_data": {"reranked_count": 5},
      "duration_ms": 23.1
    },
    "reasoning": {
      "step_id": 4,
      "step_name": "推理生成",
      "description": "基于检索结果生成回答",
      "reasoning": "根据查询「奖学金怎么申请？」，识别意图为 奖学金申请。从知识库检索到 10 个相关文档，经过关键词匹配、章节相关性等特征评估。对检索结果进行内容合并和去重，提取关键信息。采用奖学金专用生成策略，重点突出申请条件、流程和注意事项。",
      "input_data": {"query": "奖学金怎么申请？", "context_length": 1234},
      "output_data": {"sources_count": 5},
      "duration_ms": 67.8
    },
    "summary": "1. 查询分析：识别查询类型为「奖学金申请」，提取关键词「奖学金, 申请」 | 2. 检索到 10 个相关文档 | 3. 重排序后保留 5 个最相关文档 | 4. 基于检索结果生成回答",
    "total_duration_ms": 148.7
  },
  "timestamp": "2026-02-04T20:00:00",
  "metadata": {}
}
```

### 搜索接口（更新）
```http
POST /api/search
Content-Type: application/json

{
  "query": "奖学金",
  "top_k": 10,
  "rerank_top_k": 5
}
```

**响应**：
```json
{
  "query": "奖学金",
  "retrieved_results": [...],  // 检索结果（重排序前）
  "reranked_results": [...],   // 重排序后结果
  "total_results": 5,
  "metadata": {
    "retrieval_method": "chromadb",
    "rerank_method": "rule_based"
  }
}
```

---

## 依赖安装

### 基础依赖
```bash
pip install chromadb jieba
```

### OpenAI Embedding（可选）
```bash
pip install openai
```

### HuggingFace Embedding（可选）
```bash
pip install sentence-transformers
```

### CrossEncoder Reranker（可选）
```bash
pip install sentence-transformers
```

### 完整依赖
```bash
pip install -r requirements.txt
```

---

## 配置说明

### 环境变量
```bash
# ChromaDB
USE_CHROMADB=true

# Embedding 配置
EMBEDDING_PROVIDER=openai  # openai / huggingface / local
OPENAI_API_KEY=your-api-key

# Reranker 配置
RERANKER_USE_CROSS_ENCODER=false
RERANKER_CROSS_ENCODER_MODEL=BAAI/bge-reranker-base
```

---

## 性能优化

### 1. 向量检索优化
- 使用 HNSW 索引（ChromaDB 默认）
- 调整 `hnsw:construction_ef` 和 `hnsw:M` 参数
- 使用更快的 Embedding 模型

### 2. 重排序优化
- 仅对 Top-20 结果进行重排序
- 使用更轻量的 CrossEncoder 模型
- 调整特征权重

### 3. 缓存策略
- 缓存常见查询的向量
- 缓存重排序结果
- 使用 Redis 缓存思考过程

---

## 监控指标

### 检索指标
- 检索耗时（ms）
- 检索结果数量
- 平均相似度分数

### 重排序指标
- 重排序耗时（ms）
- 重排序分数分布
- Top-K 准确率

### 推理指标
- 总推理耗时（ms）
- 各步骤耗时占比
- 上下文使用率

---

## 故障排查

### ChromaDB 无法启动
```python
# 检查 ChromaDB 是否安装
import chromadb
print(chromadb.__version__)

# 检查持久化目录
import os
print(os.path.exists(CHROMA_PERSIST_DIR))
```

### Embedding 失败
```python
# 降级到简单 Embedding
EMBEDDING_MODEL = {
    'provider': 'simple',
    'dimension': 5000
}
```

### 重排序失败
```python
# 降级到基于规则的重排序
reranker = Reranker(config={'use_cross_encoder': False})
```

---

## 未来改进

1. **混合检索**
   - 结合向量检索和 BM25 关键词检索
   - 动态权重调整

2. **多轮对话推理**
   - 基于对话历史的上下文理解
   - 引用前文内容

3. **知识图谱增强**
   - 构建学生手册知识图谱
   - 基于图谱的推理

4. **实时学习**
   - 用户反馈收集
   - 持续优化重排序权重

---

## 参考资料

- [ChromaDB 官方文档](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [RAG 最佳实践](https://www.langchain.com/)
- [CrossEncoder 论文](https://arxiv.org/abs/1911.03363)