# Cloudflare 域名部署指南（`rag.gyfbest.cn`）

本文档说明如何把当前项目部署到 `rag.gyfbest.cn`，并使用 Cloudflare 负责 DNS 与公网代理。

> 结论先说：
>
> - **当前项目最合适的方案不是 Cloudflare Pages 直出整站**
> - **最稳妥方案是：Cloudflare 负责 DNS/HTTPS 代理，VPS 上继续运行 `docker-compose.prod.yml` + `Caddy`**
> - 原因是本项目是 **前后端分离**，并且后端依赖 FastAPI、MongoDB、Redis，不适合直接迁移成纯 Pages 静态站

## 1. 架构说明

推荐线上架构：

```text
浏览器
  -> Cloudflare（DNS + Proxy）
  -> 你的 VPS 公网 IP
  -> Caddy :443/:80
     -> /api* /health* 转发到 backend:8001
     -> 其他路径转发到 frontend:80
```

当前仓库已经具备这套结构：

- `docker-compose.prod.yml`
- `deploy/Caddyfile`
- `.env.production`

其中：

- 前端生产环境建议保持 `VITE_API_BASE_URL=` 为空
- 浏览器会直接请求同域名下的 `/api/*`
- `Caddy` 会把 `/api*` 和 `/health*` 转发给后端

## 2. 部署前确认

先确认以下条件：

1. 你有一台可公网访问的 Linux VPS
2. 该 VPS 已安装 Docker 和 Docker Compose
3. 你可以修改 `gyfbest.cn` 的 Cloudflare DNS
4. `rag.gyfbest.cn` 最终应指向你的 VPS 公网 IP
5. VPS 的安全组/防火墙已放行 `80` 和 `443`

> 不建议直接暴露 `8001`、MongoDB、Redis 端口到公网。

## 3. Cloudflare 控制台配置

在 Cloudflare 中进入你的站点 `gyfbest.cn`：

### 3.1 添加 DNS 记录

添加一条记录：

- 类型：`A`
- 名称：`rag`
- IPv4 地址：`你的 VPS 公网 IP`
- Proxy status：`Proxied`（橙色云）

如果已经存在旧记录，先检查它是不是还指向旧机器、旧 Pages 记录或错误 IP。

### 3.2 SSL/TLS 模式

Cloudflare -> `SSL/TLS` -> `Overview`：

- 推荐设置为：`Full (strict)`

如果你的源站证书暂时还没完全准备好，可临时用 `Full`，但最终建议切回 `Full (strict)`。

### 3.3 加速/缓存建议

先保持默认即可，不要一开始就对 `/api/*` 做缓存规则。

建议：

- 不缓存 `/api/*`
- 不缓存 `/health*`

## 4. 服务器端配置

### 4.1 上传项目

把项目上传到服务器，例如：

```bash
/srv/student-ai
```

### 4.2 准备生产环境变量

在服务器项目目录中准备：

```bash
cp .env.production.example .env.production
```

重点检查以下字段：

```env
ENVIRONMENT=production
STRICT_PRODUCTION_MODE=true
PUBLIC_DEMO_MODE=false

CADDY_DOMAIN=rag.gyfbest.cn

CORS_ORIGINS=https://rag.gyfbest.cn,http://rag.gyfbest.cn,http://rag.gyfbest.cn:18080,http://146.56.208.45:18080

VITE_API_BASE_URL=
```

另外必须替换：

- `SECRET_KEY`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGODB_URL`
- `LLM_API_KEY`

### 4.3 检查 Caddy 配置

当前仓库中的 `deploy/Caddyfile` 已包含关键规则：

- `/api*`、`/health*` -> `backend:8001`
- 其他请求 -> `frontend:80`

这正是 `rag.gyfbest.cn` 所需行为。

## 5. 启动生产服务

在服务器项目根目录执行：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

查看状态：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

查看日志：

```bash
docker logs student-ai-caddy-prod --tail 200
docker logs student-ai-backend-prod --tail 200
docker logs student-ai-frontend-prod --tail 200
```

## 6. 验证链路

### 6.1 源站本机验证

在 VPS 上先验证容器是否正常：

```bash
curl -I http://127.0.0.1:18080
curl http://127.0.0.1:8001/health/ready
```

### 6.2 域名验证

再验证公网域名：

```bash
curl -I https://rag.gyfbest.cn
curl https://rag.gyfbest.cn/health/ready
```

浏览器验证重点：

1. 打开 `https://rag.gyfbest.cn`
2. 页面能正常加载
3. 打开浏览器开发者工具 -> Network
4. 确认接口请求发往：

```text
https://rag.gyfbest.cn/api/...
```

而不是：

- `http://localhost:8001`
- `https://rag.gyfbest.cn:8001`
- 某个其它独立 API 域名

## 7. 常见问题

### 7.1 Cloudflare 返回 522

说明 Cloudflare 连不到你的源站，常见原因：

- VPS 没开放 `80/443`
- Docker 没起来
- `Caddy` 没绑定成功
- DNS 记录指向错 IP

排查：

```bash
ss -ltnp | grep -E ':(80|443|18080|8001)\b'
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker logs student-ai-caddy-prod --tail 200
```

### 7.2 打开 `/api/*` 返回前端 404 页面

说明 `/api` 没有被反向代理到后端，而是被前端静态站接走了。

当前仓库里正确规则应该是：

```text
@backend path /api* /health*
reverse_proxy @backend backend:8001
```

### 7.3 浏览器请求跑到了 `localhost:8001`

说明前端构建时写死了 API 地址。

修复方式：

- 保持 `.env.production` 中 `VITE_API_BASE_URL=` 为空
- 重新构建前端镜像并重启：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build frontend caddy
```

### 7.4 Cloudflare 开启代理后证书报错

优先检查：

- Cloudflare SSL 模式是否为 `Full` 或 `Full (strict)`
- 源站 `443` 是否可访问
- `Caddy` 证书路径是否有效

### 7.5 之前挂过 Cloudflare Pages

如果 `rag.gyfbest.cn` 之前绑定过 Pages：

- 删除 Pages 上的自定义域名绑定
- 再检查 DNS 中是否残留 Pages 自动生成记录
- 确保最终只有一条指向当前 VPS 的 `A` 记录在工作

## 8. 不推荐的当前方案

当前仓库 **不推荐直接部署到 Cloudflare Pages 作为完整生产架构**，原因：

1. Pages 适合纯静态前端或配合轻量 Functions
2. 你的后端是 FastAPI，不是 Cloudflare Workers 原生架构
3. MongoDB / Redis / Python 服务仍然需要独立运行环境
4. 直接拆成 Pages + 独立 API 域名会增加跨域、鉴权、流式接口与运维复杂度

如果你只是想“让前端先上线”，可以后续再单独评估：

- 前端放 Cloudflare Pages
- 后端放 VPS 或其它 Python 托管平台
- 前端通过 `VITE_API_BASE_URL=https://api.xxx` 访问 API

但这不是当前仓库的最低风险路径。

## 9. 最短上线步骤

如果你现在就要把 `rag.gyfbest.cn` 挂起来，按下面做即可：

1. Cloudflare 添加 `rag -> VPS_IP` 的 `A` 记录并开启代理
2. Cloudflare SSL 设为 `Full (strict)`
3. VPS 放通 `80/443`
4. 服务器上配置好 `.env.production`
5. 确认 `VITE_API_BASE_URL=` 为空
6. 执行：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

7. 验证：

```bash
curl -I https://rag.gyfbest.cn
curl https://rag.gyfbest.cn/health/ready
```

8. 浏览器打开 `https://rag.gyfbest.cn` 测试聊天与检索
