# AI Specialty Frontend

人工智能专业智能助手 - Vue 3 前端应用

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 下一代前端构建工具
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Vue Router** - Vue.js 官方路由
- **Pinia** - Vue 3 状态管理库
- **AI SDK (Vue)** - Vercel AI SDK Vue 集成

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── assets/         # 资源文件
│   ├── components/     # 可复用组件
│   ├── composables/    # 组合式函数
│   ├── router/         # 路由配置
│   ├── stores/         # Pinia 状态管理
│   ├── styles/         # 全局样式
│   ├── types/          # TypeScript 类型定义
│   ├── utils/          # 工具函数
│   ├── views/          # 页面组件
│   ├── App.vue         # 根组件
│   └── main.ts         # 入口文件
├── index.html          # HTML 模板
├── package.json        # 项目配置
├── vite.config.ts      # Vite 配置
├── tailwind.config.js  # Tailwind CSS 配置
└── tsconfig.json       # TypeScript 配置
```

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 功能特性

- **双模式界面**: 搜索模式与对话模式自动切换
- **智能推荐**: 常见问题快速点击
- **实时交互**: 流式响应支持
- **响应式设计**: 完美适配移动端和桌面端
- **无障碍访问**: 遵循 WCAG AA 标准

## API 集成

前端通过 `/api/chat` 端点与后端通信，支持：

- 发送用户消息
- 接收 AI 响应
- 维护对话上下文
- 引用数据源

## 样式设计

- **主色调**: Emerald Green (#10b981)
- **字体**: Playfair Display (标题), Inter (正文)
- **设计风格**: 现代简约，卡片式布局
- **动画效果**: 平滑过渡，流畅交互

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)