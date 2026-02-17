# 安信工AI小助手

基于学生手册知识库的智能问答系统，通过自然语言对话方式，让学生能够快速、准确地获取校规信息。

## 项目简介

安信工AI小助手采用 RAG (Retrieval-Augmented Generation) 架构，结合向量检索、重排序和推理引擎，为学生提供准确的规章制度查询服务。

## 技术栈

### 后端
- **框架**: FastAPI 0.104+
- **数据库**: MongoDB 4.4+
- **向量数据库**: ChromaDB 0.4+
- **检索**: TF-IDF + 向量检索 + 重排序
- **LLM**: 支持通义千问、OpenAI 等兼容 API

### 前端
- **框架**: Vue 3.4+
- **构建工具**: Vite 5+
- **语言**: TypeScript 5+
- **样式**: Tailwind CSS 3+
- **状态管理**: Pinia 2+

## 功能特性

- ✅ 智能问答：基于学生手册的自然语言问答
- ✅ 上下文对话：支持多轮对话，记住上下文
- ✅ 交叉推理：自动识别跨章节关联问题
- ✅ 来源追溯：显示答案来源和相似度
- ✅ 会话管理：创建、切换、删除会话
- ✅ 用户认证：注册、登录、Token 刷新
- ✅ 思考过程：显示 AI 的推理过程（可选）

## 快速开始

### 前置要求

- Python 3.8+
- MongoDB 4.4+
- Node.js 16+ (前端开发)

### 后端启动

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
cd backend
python main.py
```

服务将在 `http://localhost:8001` 启动。

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## 项目结构

```
学生手册知识库/
├── backend/              # 后端代码
│   ├── agent.py          # AI 智能体
│   ├── config.py         # 配置文件
│   ├── main.py           # FastAPI 应用入口
│   ├── models.py         # 数据模型
│   ├── knowledge_base.py # 知识库
│   ├── reranker.py       # 重排序
│   ├── reasoning_engine.py # 推理引擎
│   ├── cross_retrieval_engine.py # 交叉检索
│   └── routers/          # API 路由
├── frontend/             # 前端代码
│   ├── src/
│   │   ├── api/          # API 调用
│   │   ├── components/   # 组件
│   │   ├── views/        # 页面
│   │   └── stores/       # 状态管理
├── database/             # 数据库文件
│   ├── rag_knowledge_base_optimized.json
│   └── chroma_db/        # 向量数据库
├── scripts/              # 工具脚本
├── tests/                # 测试文件
├── docs/                 # 文档
│   ├── api/             # API 文档
│   └── deploy/          # 部署文档
└── requirements.txt     # Python 依赖
```

## API 文档

启动后端后，访问 `http://localhost:8001/docs` 查看自动生成的 Swagger 文档。

详细的 API 文档请参考 [docs/api/README.md](docs/api/README.md)。

## 部署文档

详细的部署指南请参考 [docs/deploy/README.md](docs/deploy/README.md)。

## 开发指南

### 运行测试

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=backend --cov-report=html
```

### 代码规范

```bash
# 格式化代码
black backend/
isort backend/

# 检查代码质量
flake8 backend/
mypy backend/
```

## 知识库重建

```bash
cd database
python rebuild_kb.py
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请提交 Issue 或联系开发团队。