# 部署说明

本文档面向“可企业落地”的部署方式，而不是单机演示。

## 1. 部署形态

推荐拆分为 5 个运行单元：

- `caddy`：公网 HTTPS 入口，自动签发证书
- `frontend`：静态站点与反向代理
- `backend`：FastAPI 服务
- `mongo`：业务数据与会话持久化
- `redis`：会话与缓存加速

如果企业已有托管 MongoDB / Redis，可直接替换容器服务。

当前生产编排默认面向 `rag.gyfbest.cn`：

- 公网暴露 `80`、`443` 和用于直连演示的 `18080`
- Caddy 将页面请求转发到内网 `frontend:80`
- Caddy 将 `/api*` 和 `/health*` 直接转发到内网 `backend:8001`，前端 nginx 也保留同源 API 代理作为容器内兜底
- MongoDB、Redis、后端端口不直接暴露到公网
- `http://146.56.208.45:18080/` 保留为前端直连入口，`https://rag.gyfbest.cn/` 保留为正式域名入口

如果同时使用 Cloudflare，目前支持两条生产路线：

- **路线 A：VPS + Caddy + Cloudflare DNS/橙云代理**
- **路线 B：Cloudflare Pages 前端 + 海外后端 API 子域名**

路线 B 详见 `docs/deploy/cloudflare-pages-remote-backend.md`。当使用路线 B 时：

- `rag.gyfbest.cn` 绑定到 Cloudflare Pages
- 建议新增 `api-rag.gyfbest.cn` 指向海外后端
- 前端生产环境设置 `VITE_API_BASE_URL=https://api-rag.gyfbest.cn`
- 后端 `CORS_ORIGINS` 至少允许 `https://rag.gyfbest.cn`

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
- `ADMIN_USERNAMES=<管理员用户名，多个用英文逗号分隔>`
- `CORS_ORIGINS=https://rag.gyfbest.cn,http://rag.gyfbest.cn,http://rag.gyfbest.cn:18080,http://146.56.208.45:18080`
- `FRONTEND_BIND=0.0.0.0`
- `FRONTEND_PORT=18080`
- `CADDY_DOMAIN=rag.gyfbest.cn`
- `LLM_API_KEY`

`ADMIN_USERNAMES` 用来把已有账号提升为知识库管理员。生产环境中，`/api/documents/upload`、`DELETE /api/documents/{document_id}`、`POST /api/documents/rebuild-index`、`/api/learning-events/summary` 和 `/api/learning-events/export.csv` 都应只允许管理员访问；普通学生账号只能问答、检索、查看图谱和上报学习行为。

其中 `FRONTEND_BIND=0.0.0.0` 不要改回 `127.0.0.1`。当前编排需要同时保留 `https://rag.gyfbest.cn/` 和 `http://146.56.208.45:18080/` 两个入口；如果绑定到回环地址，`18080` 的公网直连入口会直接失效。

路线 A（同源反代）下，前端生产构建建议保持：

```env
VITE_API_BASE_URL=
```

这样浏览器会走同源 `/api`，由前端 nginx 内网转发到后端，避免额外 CORS 和公网 API 端口。

路线 B（Cloudflare Pages + 远程后端）下，前端生产环境应设置：

```env
VITE_API_BASE_URL=https://api-rag.gyfbest.cn
``` 

这样浏览器会直接请求远程后端，适合无大陆备案源站的场景。

当前生产前端已暂时关闭 PWA 注册。`frontend/public/sw.js` 只保留为自清理脚本：旧浏览器如果已经安装过 Workbox Service Worker，会更新到这个脚本，清空 Cache Storage，注销自身，并重新加载页面。上线稳定后如需恢复 PWA，必须先确认 `/api*`、`/health*`、`/metrics` 不会被 navigation fallback 或运行时缓存接管。

## 3. DNS 与防火墙

在域名服务商处添加 DNS 记录：

```text
rag.gyfbest.cn A <VPS 公网 IP>
```

如果域名托管在 Cloudflare：

- 保留 `rag.gyfbest.cn` 指向 VPS 公网 IP 的记录
- 可以继续开橙云
- 不要把 `rag.gyfbest.cn` 再绑定到 Cloudflare Pages 自定义域名
- 若刚从 Pages 回切，先移除 Pages 自定义域名绑定，再确认 DNS 记录仍指向 VPS

VPS 防火墙只需要放行：

```text
80/tcp
443/tcp
18080/tcp
```

不要对公网放行 `8001`、`27017`、`6379`。

## 4. 本地生产预演

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production exec backend python database/indexes.py create
```

检查状态：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker logs student-ai-caddy-prod
curl -I http://146.56.208.45:18080
curl -I https://rag.gyfbest.cn
curl https://rag.gyfbest.cn/health
curl https://rag.gyfbest.cn/health/live
curl https://rag.gyfbest.cn/health/ready
curl https://rag.gyfbest.cn/health/db
```

也可以直接运行公网入口验证脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_public_entry.ps1 -BaseUrl https://rag.gyfbest.cn -ExpectedIp <VPS 公网 IP> -NoProxy
```

如果正式域名暂时被 DNSPod webblock 拦截，可先用直连入口验证业务版本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_production_auth.ps1 -BaseUrl http://146.56.208.45:18080 -NoProxy
```

有管理员账号时，补充传入管理员凭据，脚本会完成真实知识库上传、索引、删除清理和学习行为 CSV 字段检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_production_auth.ps1 -BaseUrl http://146.56.208.45:18080 -AdminUsername <admin> -AdminPassword <password> -NoProxy
```

验收信号：

- 匿名或普通用户访问 `/api/documents/upload` 应返回 `401/403`，不能进入文件解析错误。
- 普通用户可调用 `/api/learning-events` 上报学习行为。
- 普通用户访问 `/api/learning-events/summary` 和 `/api/learning-events/export.csv` 应返回 `403`。
- 管理员上传文档应返回 `201`，且包含 `document_id`、`chunk_count > 0`、`indexed=true`、`stages`、`index_status`。
- 管理员导出的 CSV 表头必须包含老师要求字段：`user_id`、`group`、`task_id`、`question_count`、`followup_count`、`total_time_sec`、`retrieved_doc_count`、`citation_click_count`、`graph_node_click_count`、`graph_edge_view_count`、`graph_dwell_time_sec`、`crag_score_mean`、`self_rag_pass_rate`、`retrieve_triggered`、`final_answer_submitted`。

如果 DNS 尚未生效，公网 HTTPS 证书签发通常不会成功。此时先验证容器内链路：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec frontend wget -qO- http://127.0.0.1/health
docker compose -f docker-compose.prod.yml --env-file .env.production exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health/ready', timeout=5).read().decode())"
```

在 VPS 上可运行服务端入口检查：

```bash
bash scripts/verify_server_entry.sh rag.gyfbest.cn
```

如果需要接入定时巡检，可直接运行半小时巡检脚本：

```bash
bash scripts/cron_production_checks.sh
```

如果 `/api/chat/stream` 打开后进入前端 404 页面，说明 `/api*` 没有到达 FastAPI。上传最新部署包后，在 VPS 项目目录运行入口修复脚本：

```bash
bash scripts/repair_public_entry.sh rag.gyfbest.cn
```

脚本会确认线上 Caddyfile 包含 `/api*`、`/health*` 后端转发规则，强制重建 `backend`、`frontend`、`caddy`，重载 Caddy，并验证 `/health/ready` 与 `/api/chat/stream`。

## 5. 就绪判定

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

## 6. 生产发布流程建议

1. 构建前后端镜像。
2. 通过 CI 运行后端测试与前端测试。
3. 将 `.env.production` 中的密钥由密钥平台注入。
4. 使用 `bash scripts/create_deploy_bundle.sh` 生成发布包。
5. 上传到远端部署根目录，保留当前 `app/` 目录备份。
6. 将 `rag.gyfbest.cn` 的 A 记录指向 VPS 公网 IP。
7. 在远端执行 `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`。
8. 执行 `docker compose -f docker-compose.prod.yml --env-file .env.production exec backend python database/indexes.py create`，只迁移索引，不覆盖 MongoDB 数据。
9. 发布后强制校验 `/health`、`/health/ready`、`/api/auth/register`、`/api/chat/stream`、知识库上传权限和学习行为 CSV 导出。
10. 如启用 Dify 外部知识库，配置 `DIFY_EXTERNAL_KB_TOKEN`，并在 Dify 中填写 `/api/dify/retrieval` 所在公网地址。
11. 文档上传会写入 `database/rag_knowledge_base.json` 并重载运行时 TF-IDF 索引；生产环境请确保 `backend` 容器对 `database/` 挂载有写权限。
12. 确认公网仅开放 `80/443/18080`，不要暴露后端、MongoDB、Redis 端口。
13. 首次从旧 PWA 版本升级时，在浏览器 DevTools 清理一次 `rag.gyfbest.cn` 的 Service Worker、Cache Storage 和站点数据；随后新的 `sw.js` 会自动注销旧缓存链路。
14. 发布后接 Prometheus 或日志平台采集 `/metrics` 与容器日志，并记录回滚目录。

推荐再加一个宿主机 cron，每 30 分钟执行一次基础可用性巡检：

```cron
*/30 * * * * cd /srv/student-ai && /usr/bin/env bash scripts/cron_production_checks.sh >> /var/log/student-ai-cron-check.log 2>&1
```

脚本默认检查以下 4 项：

- `docker compose -f docker-compose.prod.yml --env-file .env.production ps`
- `https://rag.gyfbest.cn/health/ready`
- `https://rag.gyfbest.cn/api/chat/stream`
- `http://146.56.208.45:18080`

如果域名、编排文件或直连入口变更，可在 cron 中覆盖 `DOMAIN`、`COMPOSE_FILE`、`ENV_FILE`、`DIRECT_FRONTEND_URL`。

## 7. 高可用建议

- MongoDB 建议使用副本集或托管服务
- Redis 建议使用持久化和高可用方案
- 后端服务建议至少双副本，并由网关或负载均衡分发流量
- 镜像发布时固定版本号，避免漂移
- 对 `SECRET_KEY`、`LLM_API_KEY` 做轮换策略

## 8. 安全基线

- 禁止生产启用 `PUBLIC_DEMO_MODE`
- `CORS_ORIGINS` 只允许实际前端域名
- 对外统一走 HTTPS
- JWT 密钥长度至少 32 字符
- 将 MongoDB、Redis 放在内网，不直接暴露公网端口
- 知识库写操作和学习行为导出只允许管理员账号；学生账号不能上传、删除或重建知识库。

## 9. 运维排障

公网入口 `Failed to fetch`：

- 如果页面仍显示破图校标，先确认线上包已经包含 `assets/jpg/logo-*.jpg`，并确认构建产物中没有 `/logo.jpg` 或 `/校徽.jpg` 根路径引用。若本地构建正确但浏览器仍旧破图，清理该域名的 Service Worker、Cache Storage 和站点数据后刷新。
- 当前 PWA 已暂停。`/sw.js` 应返回自清理脚本，不应包含 `workbox`、`NavigationRoute` 或 `navigateFallback`。如果线上 `/sw.js` 仍是 Workbox 版本，说明旧前端包没有部署成功。
- 如果直接打开 `https://rag.gyfbest.cn/api/chat/stream` 显示前端 404 页面，说明 `/api*` 被静态前端接走了。先运行 `bash scripts/repair_public_entry.sh rag.gyfbest.cn`，再检查 `docker exec student-ai-caddy-prod cat /etc/caddy/Caddyfile` 是否包含 `@backend path /api* /health*`。
- 浏览器请求应为 `https://rag.gyfbest.cn/api/chat/stream`。如果请求到了 `localhost:8001` 或公网 `:8001`，重新构建前端，并保持 `VITE_API_BASE_URL=` 为空。
- 如果 `https://rag.gyfbest.cn/*` 在 TLS 握手阶段被 reset，先在 VPS 上执行 `ss -ltnp | grep -E ':(80|443)\b'`，确认 80/443 是否由 `student-ai-caddy-prod` 绑定。
- 如果宿主机 Nginx 占用 80/443，停止或改造它：`sudo systemctl stop nginx && sudo systemctl disable nginx`，然后重新执行 `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`。
- 查看 `docker logs student-ai-caddy-prod`，确认 Caddy 已加载 `deploy/Caddyfile`，并成功为 `CADDY_DOMAIN` 签发证书。
- 如果 `http://rag.gyfbest.cn/*` 跳转到 `dnspod.qcloud.com/static/webblock.html?d=rag.gyfbest.cn`，这不是应用代码问题，需要在 DNSPod/腾讯云侧解除域名拦截、完成域名解析校验或备案/安全配置。
- 如果 `https://146.56.208.45/*` 直连 IP 能返回应用响应，但 `https://rag.gyfbest.cn/*` 在 TLS/SNI 阶段 reset，说明域名或 SNI 被 DNSPod/腾讯云/CDN/安全策略拦截；继续改前端、Nginx 或后端都不会修复，需要先解除域名侧 webblock/安全拦截。
- 如果 `rag.gyfbest.cn` 之前挂在 Cloudflare Pages，移除 Pages 自定义域名后变成 `522`，优先检查 Cloudflare DNS 记录是否仍正确指向 VPS 公网 IP，而不是残留 Pages 自动创建的旧记录。
- 修复入口后再验证 `/health`、`/health/ready` 和 `/api/chat/stream`。只有 `/health/ready` 返回 `not_ready` 时，才继续排查 MongoDB、Redis、知识库或 LLM 配置。

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


