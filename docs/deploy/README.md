# 部署说明

本文档面向“可企业落地”的部署方式，而不是单机演示。

## 1. 部署形态

推荐拆分为 4 个运行单元：

- `frontend`：静态站点与反向代理
- `backend`：FastAPI 服务
- `mongo`：业务数据与会话持久化
- `redis`：会话与缓存加速

如果企业已有托管 MongoDB / Redis，可直接替换容器服务。

## 2. 环境文件

开发环境使用：

```bash
cp .env.example .env
```

生产环境使用：

```bash
cp .env.production.example .env.production
```

生产环境至少确认以下变量：

- `ENVIRONMENT=production`
- `STRICT_PRODUCTION_MODE=true`
- `PUBLIC_DEMO_MODE=false`
- `SECRET_KEY`
- `MONGODB_URL`
- `REDIS_URL`
- `SESSION_BACKEND=redis`
- `CORS_ORIGINS`
- `LLM_API_KEY`

## 3. 本地生产预演

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

检查状态：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl http://localhost:8001/health/live
curl http://localhost:8001/health/ready
curl http://localhost:8001/health/db
```

## 4. 就绪判定

后端提供两类探针：

- 存活探针：`/health/live`
- 就绪探针：`/health/ready`

`/health/ready` 会汇总以下信息：

- 知识库是否加载
- 数据库是否可用
- 会话存储后端是否可用
- 启动期导入失败的模块
- 当前是否处于严格模式 / demo 模式

在 `STRICT_PRODUCTION_MODE=true` 下，如果关键依赖不可用，服务会直接拒绝启动。

## 5. 生产发布流程建议

1. 构建前后端镜像。
2. 通过 CI 运行后端测试与前端测试。
3. 将 `.env.production` 中的密钥由密钥平台注入。
4. 使用 `bash scripts/create_deploy_bundle.sh` 生成发布包。
5. 上传到远端部署根目录，保留当前 `app/` 目录备份。
6. 在远端执行 `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`。
7. 发布后强制校验 `/health`、`/health/ready` 和 `/api/chat/stream`。
8. 发布后接 Prometheus 或日志平台采集 `/metrics` 与容器日志，并记录回滚目录。

## 6. 高可用建议

- MongoDB 建议使用副本集或托管服务
- Redis 建议使用持久化和高可用方案
- 后端服务建议至少双副本，并由网关或负载均衡分发流量
- 镜像发布时固定版本号，避免漂移
- 对 `SECRET_KEY`、`LLM_API_KEY` 做轮换策略

## 7. 安全基线

- 禁止生产启用 `PUBLIC_DEMO_MODE`
- `CORS_ORIGINS` 只允许实际前端域名
- 对外统一走 HTTPS
- JWT 密钥长度至少 32 字符
- 将 MongoDB、Redis 放在内网，不直接暴露公网端口

## 8. 运维排障

知识库未加载：

- 检查 `database/` 下知识库文件是否存在
- 检查容器挂载是否成功
- 访问 `/health/ready` 查看 `knowledge_base` 状态

数据库不可用：

- 检查 `MONGODB_URL`
- 检查 Mongo 容器或托管实例连通性
- 访问 `/health/db`

会话异常：

- 检查 `SESSION_BACKEND`
- 如果是 Redis，会在 `/health/ready` 中显示 `session_store` 状态

指标不可用：

- 检查 `ENABLE_METRICS`
- 确认 `backend/monitoring/metrics.py` 正常加载
