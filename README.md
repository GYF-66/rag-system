# 安信工 AI 助手

基于人工智能专业培养方案与课程资料的 RAG 问答系统，提供专业知识检索、会话问答、来源追踪和基础用户认证能力。

## 当前交付目标

本版本不再只面向单机演示，而是按“企业可落地部署”的思路整理：

- 区分 `development` 与 `production` 运行档位
- `production` 下支持严格模式，关键依赖缺失时直接启动失败
- 提供就绪探针、存活探针、数据库健康检查和 Prometheus 文本指标
- 提供开发编排和生产编排两套 Docker Compose 入口
- 提供独立的生产环境变量模板，支持 MongoDB + Redis + 前后端分离部署

## 技术栈

### 后端

- FastAPI
- MongoDB
- Redis
- SlowAPI
- 可选 ChromaDB

### 前端

- Vue 3
- Vite
- TypeScript
- Tailwind CSS
- Pinia

## 目录结构

```text
backend/                 FastAPI 后端
frontend/                Vue 前端
database/                知识库与索引数据
docs/                    设计与部署文档
tests/                   自动化测试
docker-compose.yml       开发编排
docker-compose.prod.yml  生产编排
.env.example             开发环境模板
.env.production.example  生产环境模板
```

## 运行模式

### 开发模式

特点：

- 允许 `PUBLIC_DEMO_MODE=true`
- 允许文件会话降级
- 关键依赖缺失时可降级启动

### 生产模式

特点：

- `ENVIRONMENT=production`
- `STRICT_PRODUCTION_MODE=true`
- `PUBLIC_DEMO_MODE=false`
- 会校验关键配置、知识库加载、数据库连接、会话后端状态
- 不允许把文件会话当成默认生产方案

## 快速开始

### 1. 准备环境文件

开发环境：

```bash
cp .env.example .env
```

生产环境：

```bash
cp .env.production.example .env.production
```

### 2. 本地开发

后端：

```bash
pip install -r requirements.txt
cd backend
python main.py
```

前端：

```bash
cd frontend
npm install
npm run dev
```

### 3. Docker 开发编排

```bash
docker compose up -d
```

### 4. Docker 生产编排

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## 健康检查与可观测性

- `GET /health/live`：进程存活
- `GET /health/ready`：依赖就绪状态
- `GET /health/db`：数据库健康检查
- `GET /metrics`：Prometheus 文本指标

## 生产部署建议

- 前端、后端、MongoDB、Redis 使用独立容器或独立托管服务
- 使用反向代理或网关统一入口，并启用 HTTPS
- 在 CI/CD 中固定镜像 tag，不直接发布 `latest`
- 使用 `.env.production` 或密钥管理服务注入 `SECRET_KEY`、`LLM_API_KEY`
- 通过 `health/ready` 作为编排平台就绪探针

## 常用命令

```bash
make install
make test
make docker-up
make docker-prod-up
```

## DeepScientist 静默启动

推荐使用项目内的通用静默启动器，而不是旧的多窗口启动方式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_deepscientist_silent.ps1
```

如果要双击启动且不出现黑窗口，直接运行根目录的 `start_deepscientist_silent.vbs`。

说明：

- 不打开浏览器
- 不进入 TUI
- 不额外弹出新的 `cmd` 或 `PowerShell` 黑窗口
- 如果 `DeepScientist` daemon 已经在运行，会直接返回，不重复拉起实例
- 启动日志写入 `.\DeepScientist\logs\silent-launch.log`

停止命令：

```powershell
ds --here --stop
```

跨项目复用方式：

- 复制 `scripts/start_deepscientist_silent.ps1` 到目标项目的 `scripts/` 目录
- 目标项目保持 `项目根/.env`、`项目根/DeepScientist/`、`项目根/scripts/` 结构
- 然后执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_deepscientist_silent.ps1 -ProjectRoot .
```

## 进一步说明

详细部署流程见 [docs/deploy/README.md](docs/deploy/README.md)。
