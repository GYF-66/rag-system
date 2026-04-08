# Auto Research Program

## Goal
- 以“人工智能专业培养 RAG 系统”为对象，持续优化检索增强生成效果。
- 提升验证集与评测集上的回答准确率、证据一致性与引用可靠性。
- 重点优化以下技术方向：
  - CRAG（Corrective RAG）
  - Self-RAG
  - 查询重写（Query Rewrite）
  - 混合检索（Sparse + Dense + Metadata）
  - 重排序（Rerank）
  - 训练方案（Embedding / Reranker / SFT / 偏好优化）
  - 评测指标体系
- 降低幻觉率，减少“证据不足但仍强行作答”的情况。
- 在效果相近时，优先保留实现更简单、维护成本更低、推理链路更稳定的方案。
- 优化后系统应更适合“专业培养方案、课程体系、毕业要求、能力指标、教学计划、政策文件”等教育场景问答。

## Constraints
- 优先在现有项目结构内迭代，不随意重构整个系统。
- 不修改原始知识库内容，除非任务明确要求新增规范化元数据或构建派生索引。
- 不破坏现有可运行流程；每次改动都应尽量小、可验证、可回滚。
- 不为了追求指标盲目增加复杂度；新增模块必须有明确收益预期。
- 若引入新模型、新索引或新策略，必须说明：
  - 解决什么问题
  - 如何接入现有流程
  - 带来什么成本
  - 如何验证效果
- 若某项优化需要较大训练成本或额外算力，应优先给出轻量级替代方案。
- 对“证据不足、问题模糊、跨文档冲突”的场景，优先增强拒答、澄清和置信提示能力，而不是放任生成。
- 保持面向项目业务目标：
  - 先提升检索质量
  - 再提升证据排序
  - 再提升生成控制
  - 最后再推进训练闭环
- 所有结论尽量以评测结果、对比实验或明确日志证据为依据。

## Setup
1. 阅读项目说明文档与核心源码，理解当前 RAG 流程：
   - 文档导入方式：`backend/indexing/pdf_corpus_builder.py` + `scripts/build_rag_kb.py`
   - chunk 切分方式：`backend/chunking/unified_chunker.py`（基于标题结构）
   - 向量化与索引方式：ChromaDB（BAAI/bge-m3）+ TF-IDF/BM25 混合
   - 检索与生成链路：`backend/agent_v2.py`（主）→ `adaptive_router` → `hybrid_retriever` → `reranker`
   - 当前评测方法：`tests/backend/test_agent.py`，`tests/integration/test_api.py`
2. 识别系统现状（基于代码探索）：
   - ✅ 已有向量检索 `retrieval/chroma_knowledge_base.py`
   - ✅ 已有 BM25/TF-IDF `retrieval/knowledge_base.py`
   - ✅ 已有 metadata filtering（through hybrid_retriever）
   - ✅ 已有重排序 `retrieval/reranker.py`（Cross-Encoder）
   - ✅ 已有 CRAG `retrieval/crag_evaluator.py`
   - ✅ 已有 Self-RAG 风格控制（`agent_v2.py` 中的 evidence self-check）
   - ✅ 已有 GraphRAG `graph/knowledge_graph.py`
   - ✅ 已有 HyDE 增强 `pipeline/hyde_enhancer.py`
   - ✅ 已有引用输出（`_build_citation`）
   - ⚠️ 已有初步拒答机制（CRAG 触发），但阈值和覆盖面可增强
3. 盘点知识库数据与元数据字段：
   - 专业名称、年级、学期、课程名称
   - 毕业要求编号、文档类型、版本年份、标题层级
   - 来源：`database/rag_knowledge_base.json`
4. 先跑一次 baseline，并记录基础指标：
   - Recall@K / MRR / nDCG
   - Answer Accuracy / Faithfulness / Groundedness
   - Hallucination Rate / Refusal Accuracy
   - Latency
5. 初始化实验记录文件（`auto-research/results.tsv`），字段见原 Setup 第 5 条
6. 根据现状建立优化优先级（已实现的技术优先验证效果，未实现的补充接入）：
   1. **查询改写验证**：`pipeline/query_rewriter.py` 是否在所有路径被充分调用
   2. **CRAG 阈值调优**：`retrieval/crag_evaluator.py` 的 `CORRECTNESS_THRESHOLD`
   3. **Self-RAG 增强**：二次检索触发条件、拒答逻辑
   4. **缓存命中率优化**：`SEMANTIC_CACHE_SIMILARITY_THRESHOLD` 从 0.95 降至 0.85-0.90
   5. **重排序效率**：Cross-Encoder 调用开销 vs 效果提升
   6. **GraphRAG 融合**：图谱检索与向量检索的融合策略
   7. **Agent 重构**：拆分 `agent_v2.py`（1068行）和 `main.py`（1084行）
   8. **训练方案**（条件允许时）

## Code Analysis（基于 2026-03-29 探索）

### 关键代码问题

| 文件 | 行数 | 问题 | 优先级 |
|------|------|------|--------|
| `backend/agent_v2.py` | 1068 | 单文件过大，违反单一职责，循环导入风险 | 🔴 高 |
| `backend/main.py` | 1084 | 同上，FastAPI 生命周期与路由混杂 | 🔴 高 |
| `backend/graph/knowledge_graph.py` | 661 | 类过大，可拆分 Node/Edge 操作 | 🟡 中 |
| `backend/retrieval/hybrid_retriever.py` | 490 | 全局单例 `hybrid_retriever`，测试困难 | 🟡 中 |
| `backend/indexing/pdf_corpus_builder.py` | 570 | 职责过多，可拆分解析/清洗/分块 | 🟡 中 |
| `backend/agent_v1.py` + `agent_v2.py` | - | 双版本并存，`AGENT_V2_AVAILABLE` 切换 | 🟡 中 |

### 配置问题

| 配置项 | 当前值 | 问题 | 建议 |
|--------|--------|------|------|
| `SEMANTIC_CACHE_SIMILARITY_THRESHOLD` | 0.95 | 过高，缓存命中率低 | 降至 0.85-0.90 |
| `TOP_K_RESULTS` | 3 | 复杂问题可能不足 | complex 路由增至 5-8 |
| `CORRECTNESS_THRESHOLD` | 未知 | CRAG 阈值未暴露配置 | 提取为可调参数 |

### 功能缺口

1. **增量索引缺失**：知识库更新需全量重建
2. **监控不完善**：`backend/monitoring/` 存在但指标不全
3. **评测自动化**：无定时跑评测机制
4. **拒答阈值未公开配置**：CRAG 阈值硬编码在逻辑中

### 重构路线（长期）

```
Phase 1（安全改进）:
  - 统一到 agent_v2，删除 agent_v1
  - 抽出 CRAG/Self-RAG 配置常量表
  - 调优缓存阈值

Phase 2（架构解耦）:
  - 拆分 agent_v2.py → router/retriever/generator 模块
  - 引入依赖注入替代全局单例
  - 拆分 main.py 生命周期管理

Phase 3（能力增强）:
  - 增量索引
  - 自动化评测 pipeline
  - 监控告警
```

## Run
- 基线运行：先按项目当前默认方式完整跑通一次索引、检索、问答和评测流程。
- 检索实验：分别测试以下方案，并保留独立记录：
  - 纯稠密检索
  - 纯稀疏检索
  - 混合检索
  - 混合检索 + metadata filtering
- 查询重写实验：
  - 原始查询
  - 术语标准化查询
  - 上下文补全查询
  - 多查询扩展
  - 复合问题拆解
- 重排序实验：
  - 无 rerank
  - 轻量 rerank
  - Cross-Encoder rerank
- CRAG 实验：
  - 无质量评估直接生成
  - 质量评估后重检索
  - 质量评估后拒答 / 澄清
- Self-RAG 风格实验：
  - 固定一次检索
  - 检索后证据不足触发二次检索
  - 生成前自检并控制是否回答
- 训练实验（若条件允许）：
  - Embedding 微调
  - Reranker 微调
  - 生成模型 SFT
  - 偏好优化 / 拒答优化
- 每轮实验都必须：
  1. 说明本轮只改一个主变量
  2. 跑完整评测
  3. 输出指标
  4. 记录结论
  5. 与 baseline 或上一最佳方案比较
- 对以下重点方向进行持续试验：
  - 查询重写是否提升召回
  - 混合检索是否提升覆盖率
  - 重排序是否提升 Top1 命中率
  - CRAG 是否降低误答
  - Self-RAG 是否提升复杂问题稳定性
  - 训练是否带来可持续收益

## Success Criteria
- 检索层成功标准：
  - Recall@5 / Recall@10 有稳定提升
  - MRR 或 nDCG 明显优于 baseline
  - 课程名、毕业要求编号、版本敏感问题的检索稳定性提升
- 生成层成功标准：
  - Answer Accuracy 提升
  - Faithfulness / Groundedness 提升
  - Citation Precision 提升
  - Hallucination Rate 下降
  - Refusal Accuracy 提升
- 系统层成功标准：
  - 用户口语化问题的处理能力增强
  - 多文档综合问题更完整
  - 证据不足时更少“硬答”
  - 平均延迟增幅可控
- 预期技术收益：
  - 查询重写：提升非标准表达下的召回质量
  - 混合检索：提升教育知识库的覆盖率与精确定位能力
  - 重排序：提升高质量证据进入生成阶段的概率
  - CRAG：降低低质量检索对答案的污染
  - Self-RAG：提升复杂问题的动态补证与谨慎作答能力
  - 训练方案：让系统逐步适配“人工智能专业培养”场景
- 通过标准：
  - 若某改动在核心指标上明显提升，且复杂度可接受，则保留
  - 若某改动效果有限但实现大幅复杂化，则谨慎采用
  - 若 accuracy / faithfulness 不升反降，则默认回滚
  - 若时延显著变差且收益不足，则默认回滚
  - 若只提升局部样例而无法在评测集上复现，则不视为成功

## Loop
循环执行，直到人工停止：

1. 选择一个小改动，只改一个主变量。
   - 示例：
     - 加入术语标准化查询重写
     - 增加 BM25 并行召回
     - 增加 metadata filtering
     - 接入 reranker
     - 增加 CRAG 质量阈值
     - 增加证据不足拒答逻辑
2. 修改实现或配置，确保改动范围清晰可追踪。
3. 重新运行索引、检索、问答或评测流程。
4. 读取结果并与当前最佳方案比较。
5. 将实验结果记录到实验表中。
6. 若效果变好则保留；若无提升或副作用过大则回滚。
7. 继续下一轮优化，优先尝试以下路线：
   - 先做查询改写
   - 再做混合检索
   - 再做重排序
   - 再做 CRAG
   - 再做 Self-RAG
   - 再做 GPU 加速验证（Embedding/Cross-Encoder 实测对比）
   - 再做本地 LLM 接入（ollama qwen2.5:7b-q4）
   - 最后做训练与偏好优化
8. 每轮都要回答以下问题：
   - 本轮解决了什么具体问题？
   - 指标是否真的变好？
   - 是否引入了新的复杂度或风险？
   - 是否值得保留到主流程？
9. 若当前阶段缺少可靠评测依据，则优先补评测集，不要盲目继续改模型。
10. 持续迭代，直到人工明确停止。

推荐长期循环目标：
- 建立“查询重写 → 混合检索 → 重排序 → CRAG → Self-RAG → 训练闭环 → 持续评测”的稳定优化流程
- 最终把系统从“能回答”提升为“能基于教育知识证据稳定、可解释、低幻觉地回答”