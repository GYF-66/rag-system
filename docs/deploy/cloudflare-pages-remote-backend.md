# Cloudflare Pages + 海外后端部署指南

适用目标：

- 前端托管到 Cloudflare Pages
- 域名使用 `rag.gyfbest.cn`
- 后端部署到海外 Python 平台
- 前端通过 `VITE_API_BASE_URL` 直连远程后端

## 1. 推荐域名规划

- 前端：`https://rag.gyfbest.cn`
- 后端：`https://api-rag.gyfbest.cn`

## 2. 前端部署

Cloudflare Pages 构建参数：

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`

前端生产环境变量：

- `VITE_API_BASE_URL=https://api-rag.gyfbest.cn`
- `VITE_PUBLIC_DEMO_MODE=false`

## 3. 后端部署

后端可直接用仓库根目录 `Dockerfile` 部署到 Render / Railway / Fly.io / 海外 VPS。

核心环境变量：

- `ENVIRONMENT=production`
- `STRICT_PRODUCTION_MODE=true`
- `PUBLIC_DEMO_MODE=false`
- `CORS_ORIGINS=https://rag.gyfbest.cn,https://api-rag.gyfbest.cn`
- `MONGODB_URL=<remote mongodb>`
- `REDIS_URL=<remote redis>`
- `SECRET_KEY=<strong random secret>`
- `LLM_API_KEY=<provider key>`

## 4. DNS

Cloudflare 中配置：

- `rag` -> Cloudflare Pages
- `api-rag` -> 海外后端平台目标

## 5. 验证

- `https://rag.gyfbest.cn` 可打开页面
- `https://api-rag.gyfbest.cn/health/ready` 返回就绪结果
- 浏览器请求实际命中 `https://api-rag.gyfbest.cn/api/chat/stream`
