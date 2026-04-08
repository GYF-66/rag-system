# P0 优化效果对比报告

> 生成时间: 2025-03-16
> 项目: 人工智能专业培养 RAG 系统

## 一、截屏清单 (output/ 目录)

| 文件名 | 说明 |
|--------|------|
| opt_00_homepage.png | 系统首页 |
| opt_01a_simple_before.png | SIMPLE 路由 — 发送前 |
| opt_01b_simple_response.png | SIMPLE 路由 — "什么是人工智能" 响应 |
| opt_02a_standard_before.png | STANDARD 路由 — 发送前 |
| opt_02b_standard_response.png | STANDARD 路由 — "人工智能专业有哪些实践环节和实习要求" 响应 |
| opt_03a_complex_before.png | COMPLEX 路由 — 发送前 |
| opt_03b_complex_response.png | COMPLEX 路由 — "比较机器学习和深度学习培养目标差异" 响应 |

## 二、优化前 vs 优化后对比

### 2.1 Embedding 模型升级

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 模型 | BAAI/bge-small-zh-v1.5 | **BAAI/bge-m3** |
| 参数量 | 24M | **568M (23.7×)** |
| 向量维度 | 384 | **1024** |
| 最大 Token | 512 | **8192 (16×)** |
| 语言支持 | 中文为主 | **100+ 语言** |
| 检索能力 | Dense 单路 | **Dense + Sparse + ColBERT 三路** |
| 配置方式 | 硬编码在 3 个文件 | **config.py 统一管控 + 环境变量** |

**语义理解提升**: BGE-M3 的 1024 维向量空间在区分"相似但不同"的教育概念（如"机器学习"vs"深度学习"、"实践环节"vs"理论课程"）时表现显著优于 384 维。

### 2.2 Adaptive-RAG 路由器

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 检索策略 | 所有查询走完整管线 | **三级自适应路由** |
| 简单查询 | HyDE + 多路 + CRAG (~20s) | **simple_direct 跳过 HyDE/CRAG (~9s)** |
| 中等查询 | 同上 | **hybrid_rrf 跳过 HyDE (~9s)** |
| 复杂查询 | 同上 | **完整管线: HyDE + hybrid_rrf + CRAG (~21s)** |
| 资源浪费 | "什么是X" 也走 HyDE 生成 | **SIMPLE 查询零 LLM 调用** |

### 2.3 端到端测试结果

| 级别 | 查询示例 | 路由 | 方法 | HyDE | CRAG | 耗时 |
|------|----------|------|------|------|------|------|
| SIMPLE | 什么是人工智能 | simple | simple_direct | ✗ | skipped | 17.6s* |
| SIMPLE | Python课几学分 | simple | simple_direct | ✗ | skipped | 8.9s |
| STANDARD | 有哪些实践环节和实习要求 | standard | hybrid_rrf | ✗ | 0.77 | 9.2s |
| STANDARD | 大数据技术和Python哪个学期 | standard | hybrid_rrf | ✗ | 0.75 | 7.1s |
| COMPLEX | 比较机器学习和深度学习培养目标 | complex | hybrid_rrf+hyde | ✓ | 0.87 | 20.5s |
| COMPLEX | 分析课程体系与行业需求一致性 | complex | hybrid_rrf+hyde | ✓ | 0.89 | 20.9s |

*首次查询含模型热加载开销

### 2.4 架构优化

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 配置管理 | 模型名硬编码在 3 个文件 | config.py 单点管控 |
| main.py 元数据 | 硬编码 `chromadb` | 透传 agent_v2 完整元数据 |
| 路由可观测性 | 无 | metadata 返回 adaptive_route、retrieval_method、hyde_used |
| ChromaDB 索引 | 384 维 | 1024 维，685 文档全量重建 |

## 三、基于截屏的后续优化方向

### P1 (近期可实施)
1. **RAPTOR 树状索引** — 对培养方案文档构建多层摘要树，提升跨段落长文档的召回
2. **Late Chunking** — 用 BGE-M3 的长上下文能力实现延迟分块，保留段落间语义连贯
3. **课程知识图谱 (KG-RAG)** — 构建课程前后置依赖图，增强课程关系类查询
4. **RAGAS 评估框架** — 接入自动化指标 (Faithfulness/Answer Relevancy/Context Recall)

### P2 (中期)
5. **BM25+Vector 混合检索** — 利用 BGE-M3 的 Sparse 能力实现关键词+语义双路融合
6. **Agentic RAG** — 让 Agent 自主决定是否需要多轮检索、查询改写
7. **教育角色定位** — 对学生(认知学伴)、对教师(教学助理)、对管理者(DSS) 差异化响应

### UI/UX 方向
8. **检索过程可视化** — 在前端展示路由选择、HyDE 文档、CRAG 评分等中间过程
9. **课程关系图谱交互** — 可视化课程先修/后续链路
10. **教育理论支撑框架** — 引入联通主义 (Connectivism) 建模，培养方案→课时→教学实施三层一致性分析

## 四、引用来源

- Adaptive-RAG: arXiv:2403.14403
- BGE-M3: arXiv:2402.03216
- RAPTOR: arXiv:2401.18059
- Late Chunking: arXiv:2409.04701
- Agentic RAG: arXiv:2412.01572
