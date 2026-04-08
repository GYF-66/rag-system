# 人工智能专业智能问答系统 - 产品需求文档 (PRD)

> **文档版本**：v1.0
> **创建日期**：2026-02-03
> **产品名称**：安信工AI小助手
> **文档状态**：待评审

---

## 文档修订历史

| 版本 | 日期 | 作者 | 修订内容 |
|------|------|------|---------|
| v1.0 | 2026-02-03 | 产品团队 | 初版发布 |

---

## 一、产品概述

### 1.1 产品定位
基于人工智能专业知识库的智能问答系统，通过自然语言对话方式，让学生能够快速、准确地获取校规信息。

### 1.2 目标用户
| 用户类型 | 占比 | 核心需求 |
|---------|------|---------|
| 在校学生 | 80% | 快速查询校规、理解条款 |
| 辅导员 | 15% | 查询规则、解答学生疑问 |
| 教务人员 | 5% | 规则管理、数据分析 |

### 1.3 产品目标
- **短期**：完成 Web 端和微信小程序端基础功能
- **中期**：提升检索准确率至 90% 以上
- **长期**：扩展至多所学校，形成 SaaS 平台

---

## 二、功能需求

### 2.1 核心功能模块

#### 2.1.1 智能问答模块

| 功能点 | 描述 | 优先级 | 验收标准 |
|-------|------|--------|---------|
| 自然语言提问 | 支持中文自然语言输入 | P0 | 支持常见问法 |
| 实时回复 | 2秒内返回答案 | P0 | 95%请求 < 2s |
| 上下文对话 | 支持多轮对话，记住上下文 | P0 | 3轮对话准确率 > 85% |
| 答案来源展示 | 显示引用的知识来源和相似度 | P1 | 来源准确率 > 90% |
| 流式输出（可选） | 支持答案流式返回 | P2 | 延迟 < 500ms |

#### 2.1.2 知识库搜索模块

| 功能点 | 描述 | 优先级 | 验收标准 |
|-------|------|--------|---------|
| 关键词搜索 | 支持关键词模糊搜索 | P0 | Top-5 准确率 > 85% |
| 结果排序 | 按相似度排序展示 | P0 | 排序合理 |
| 相似度展示 | 显示每个结果的相似度分数 | P1 | 分数范围 0-1 |
| 章节筛选 | 支持按章节筛选结果 | P2 | 筛选准确 |

#### 2.1.3 会话管理模块

| 功能点 | 描述 | 优先级 | 验收标准 |
|-------|------|--------|---------|
| 会话创建 | 自动/手动创建新会话 | P0 | 创建成功率 > 99% |
| 会话列表 | 展示历史会话 | P0 | 显示完整列表 |
| 会话详情 | 查看会话完整对话历史 | P0 | 历史完整展示 |
| 会话删除 | 删除不需要的会话 | P1 | 删除成功 |
| 会话切换 | 在不同会话间切换 | P1 | 切换流畅 |

#### 2.1.4 用户管理模块

| 功能点 | 描述 | 优先级 | 验收标准 |
|-------|------|--------|---------|
| 用户登录 | 支持微信授权登录 | P0 | 登录成功率 > 98% |
| 用户信息 | 展示用户基本信息 | P1 | 信息准确 |
| 用户画像（扩展） | 记录用户偏好和行为 | P2 | 数据收集完整 |

---

### 2.2 前端界面需求

#### 2.2.1 Web 端界面设计

##### 页面结构

```
┌─────────────────────────────────────────────────────┐
│  顶部导航栏                                          │
│  [Logo] [首页] [历史会话] [用户头像]                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  主内容区                                            │
│  ┌─────────────────────────────────────────────┐   │
│  │  欢迎语 / 空状态提示                         │   │
│  │  "您好，请问有什么可以帮您？"               │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  对话区域（滚动）                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │  [用户] 请假流程是什么？                      │   │
│  │  [AI]   根据培养方案第X章规定...             │   │
│  │        📚 来源：第X章 第X条 (相似度: 0.92)   │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  输入区域                                            │
│  ┌─────────────────────────────────────────────┐   │
│  │  [输入框........................] [发送]    │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

##### 组件规范

| 组件 | 描述 | 交互规范 |
|------|------|---------|
| 消息气泡 | 用户消息（右侧蓝色）、AI消息（左侧灰色） | 支持长文本换行 |
| 来源卡片 | 可展开/折叠的知识来源 | 点击展开详情 |
| 加载状态 | AI思考时的动画 | 3秒后显示加载提示 |
| 输入框 | 多行文本输入 | 支持 Enter 发送，Shift+Enter 换行 |
| 会话列表 | 侧边栏展示历史会话 | 点击切换，右键删除 |

##### 响应式设计

| 断点 | 宽度 | 布局调整 |
|------|------|---------|
| 移动端 | < 768px | 隐藏侧边栏，抽屉式会话列表 |
| 平板 | 768-1024px | 侧边栏可折叠 |
| 桌面端 | > 1024px | 完整布局 |

#### 2.2.2 小程序端界面设计

##### 页面结构

```
┌──────────────────────────────┐
│  顶部：安信工AI小助手  [三]  │
├──────────────────────────────┤
│                              │
│  对话区域（滚动）            │
│  ┌────────────────────────┐ │
│  │  [用户] 请假流程？      │ │
│  │  [AI] 根据手册...       │ │
│  │       📚 来源详情 >     │ │
│  └────────────────────────┘ │
│                              │
│  输入区域                    │
│  ┌────────────────────────┐ │
│  │  [输入框........] [🎤] │ │
│  └────────────────────────┘ │
│                              │
│  底部导航栏                  │
│  [聊天] [历史] [我的]       │
└──────────────────────────────┘
```

##### 小程序专属功能

| 功能 | 描述 | 实现方式 |
|------|------|---------|
| 微信授权登录 | 使用微信用户信息 | wx.getUserProfile |
| 语音输入 | 语音转文字提问 | wx.getRecorderManager |
| 分享功能 | 分享对话给好友 | wx.shareAppMessage |
| 消息通知 | 重要规则变更提醒 | 微信订阅消息 |

---

## 三、API 对接规范（重点）

### 3.1 通用规范

#### 3.1.1 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `http://localhost:8000` (开发) / `https://api.example.com` (生产) |
| 协议 | HTTPS (生产环境) |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |

#### 3.1.2 请求头规范

```typescript
// 所有 API 请求需包含的请求头
const headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  // 可选：用户认证 token
  // 'Authorization': `Bearer ${token}`
}
```

#### 3.1.3 响应状态码

| 状态码 | 含义 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 提示用户检查输入 |
| 401 | 未授权 | 跳转登录页 |
| 404 | 资源不存在 | 提示用户资源不存在 |
| 500 | 服务器错误 | 显示错误提示，记录日志 |
| 503 | 服务不可用 | 显示"服务维护中" |

#### 3.1.4 错误响应格式

```typescript
interface ErrorResponse {
  detail: string;  // 错误详情
  // 可选的其他字段
}
```

### 3.2 API 接口详情

#### 3.2.1 健康检查

```typescript
// GET /health
// 获取系统健康状态

interface HealthResponse {
  status: string;              // "healthy"
  agent_name: string;          // "安信工AI小助手"
  knowledge_base_loaded: boolean;  // true/false
  total_chunks: number;        // 知识块总数
  timestamp: string;           // ISO 8601 格式时间戳
}
```

**前端调用示例：**

```typescript
const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data: HealthResponse = await response.json();
    return data;
  } catch (error) {
    console.error('健康检查失败:', error);
  }
};
```

#### 3.2.2 智能问答

```typescript
// POST /api/chat
// 发送消息并获取 AI 回复

interface ChatRequest {
  message: string;           // 用户消息（必填）
  session_id?: string;       // 会话ID（可选，首次不传）
  user_id?: string;          // 用户ID（可选）
  use_rag: boolean;          // 是否使用RAG（默认true）
}

interface ChatResponse {
  response: string;          // AI 回复内容
  session_id: string;        // 会话ID（首次请求会返回新ID）
  sources: KnowledgeChunk[]; // 引用的知识来源
  timestamp: string;         // 响应时间戳
}

interface KnowledgeChunk {
  id: string;                // 知识块ID
  text: string;              // 知识块文本
  char_count: number;        // 字符数
  similarity: number;        // 相似度分数 0-1
}
```

**前端调用示例：**

```typescript
const sendMessage = async (
  message: string,
  sessionId?: string
): Promise<ChatResponse> => {
  const request: ChatRequest = {
    message,
    session_id: sessionId,
    use_rag: true
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: ChatResponse = await response.json();

    // 保存 session_id 到本地存储
    localStorage.setItem('session_id', data.session_id);

    return data;
  } catch (error) {
    console.error('发送消息失败:', error);
    throw error;
  }
};
```

**Vue 3 组件集成示例：**

```vue
<script setup lang="ts">
import { ref } from 'vue';

const inputMessage = ref('');
const messages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
const sessionId = ref<string | null>(localStorage.getItem('session_id'));
const isLoading = ref(false);

const handleSend = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userMessage = inputMessage.value;
  messages.value.push({ role: 'user', content: userMessage });
  inputMessage.value = '';
  isLoading.value = true;

  try {
    const response = await sendMessage(userMessage, sessionId.value || undefined);
    messages.value.push({ role: 'assistant', content: response.response });
    sessionId.value = response.session_id;
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误，请稍后重试。'
    });
  } finally {
    isLoading.value = false;
  }
};
</script>
```

#### 3.2.3 知识库搜索

```typescript
// POST /api/search
// 搜索知识库

interface SearchRequest {
  query: string;      // 搜索查询（必填）
  top_k: number;      // 返回结果数量（1-20，默认5）
}

interface SearchResult {
  query: string;
  results: KnowledgeChunk[];
  total_results: number;
}
```

**前端调用示例：**

```typescript
const searchKnowledge = async (query: string, topK = 5) => {
  const request: SearchRequest = {
    query,
    top_k: topK
  };

  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  return await response.json() as SearchResult;
};
```

#### 3.2.4 会话管理

##### 创建会话

```typescript
// POST /api/sessions
// 创建新会话或获取现有会话

interface SessionRequest {
  session_id?: string;
  user_id?: string;
}

interface SessionInfo {
  session_id: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}
```

##### 获取会话详情

```typescript
// GET /api/sessions/{session_id}
// 获取会话完整历史

interface SessionDetail {
  session_id: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

interface Message {
  role: string;      // "user" | "assistant"
  content: string;
  timestamp: string;
}
```

##### 删除会话

```typescript
// DELETE /api/sessions/{session_id}
// 删除会话

interface DeleteResponse {
  status: string;
  message: string;
}
```

##### 获取用户会话列表

```typescript
// GET /api/users/{user_id}/sessions
// 获取用户的所有会话

interface UserSessionsResponse {
  user_id: string;
  sessions: SessionInfo[];
  total: number;
}
```

**前端会话管理示例：**

```typescript
// 会话管理类
class SessionManager {
  private sessionId: string | null = null;

  async createSession(userId?: string): Promise<SessionInfo> {
    const response = await fetch(`${API_BASE_URL}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    const session = await response.json() as SessionInfo;
    this.sessionId = session.session_id;
    localStorage.setItem('session_id', session.session_id);
    return session;
  }

  async getSessionDetail(): Promise<SessionDetail | null> {
    if (!this.sessionId) return null;

    const response = await fetch(`${API_BASE_URL}/api/sessions/${this.sessionId}`);
    if (!response.ok) return null;
    return await response.json() as SessionDetail;
  }

  async deleteSession(): Promise<boolean> {
    if (!this.sessionId) return false;

    const response = await fetch(`${API_BASE_URL}/api/sessions/${this.sessionId}`, {
      method: 'DELETE'
    });

    if (response.ok) {
      this.sessionId = null;
      localStorage.removeItem('session_id');
      return true;
    }
    return false;
  }
}
```

### 3.3 小程序端 API 对接

#### 3.3.1 请求封装

```javascript
// utils/request.js
const BASE_URL = 'https://api.example.com';

function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        'Authorization': wx.getStorageSync('token') || ''
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          wx.showToast({
            title: '请求失败',
            icon: 'none'
          });
          reject(res);
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
        reject(err);
      }
    });
  });
}

module.exports = { request };
```

#### 3.3.2 对话服务

```javascript
// services/chat.js
const { request } = require('../utils/request');

// 发送消息
function sendMessage(data) {
  return request('/api/chat', {
    method: 'POST',
    data
  });
}

// 搜索知识库
function searchKnowledge(query, topK = 5) {
  return request('/api/search', {
    method: 'POST',
    data: { query, top_k: topK }
  });
}

module.exports = { sendMessage, searchKnowledge };
```

#### 3.3.3 小程序页面集成

```javascript
// pages/chat/chat.js
const { sendMessage } = require('../../services/chat');

Page({
  data: {
    inputMessage: '',
    messages: [],
    sessionId: '',
    loading: false
  },

  onLoad() {
    // 从本地存储获取 sessionId
    this.setData({
      sessionId: wx.getStorageSync('sessionId') || ''
    });
  },

  onInputChange(e) {
    this.setData({ inputMessage: e.detail.value });
  },

  async handleSend() {
    const { inputMessage, sessionId } = this.data;
    if (!inputMessage.trim() || this.data.loading) return;

    // 添加用户消息
    const messages = [...this.data.messages, { role: 'user', content: inputMessage }];
    this.setData({ messages, inputMessage: '', loading: true });

    try {
      // 调用 API
      const response = await sendMessage({
        message: inputMessage,
        session_id: sessionId || undefined,
        use_rag: true
      });

      // 添加 AI 回复
      this.setData({
        messages: [...messages, { role: 'assistant', content: response.response }],
        sessionId: response.session_id
      });

      // 保存 sessionId
      wx.setStorageSync('sessionId', response.session_id);

    } catch (error) {
      wx.showToast({ title: '发送失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
```

### 3.4 WebSocket 对接（可选扩展）

```typescript
// 未来可升级为 WebSocket 实时连接
class ChatWebSocket {
  private ws: WebSocket | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket 连接成功');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // 处理流式消息
      if (data.type === 'stream') {
        // 更新当前消息内容
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket 连接关闭');
      // 可实现自动重连
    };
  }

  send(message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message }));
    }
  }

  close() {
    this.ws?.close();
  }
}
```

---

## 四、技术实现规范

### 4.1 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | 3.x | 前端框架 |
| TypeScript | 5.x | 类型系统 |
| Vite | 5.x | 构建工具 |
| Tailwind CSS | 3.x | 样式框架 |
| Vercel AI SDK | 3.0.67 | AI 集成 |
| Pinia | 2.x | 状态管理 |
| Vue Router | 4.x | 路由管理 |

### 4.2 小程序技术栈

| 技术 | 用途 |
|------|------|
| 微信小程序原生框架 | 小程序开发 |
| TypeScript | 类型系统 |
| MobX | 状态管理 |

### 4.3 代码规范

#### 4.3.1 Vue 组件命名

```typescript
// 组件文件名：PascalCase
// ChatComponent.vue
// SessionList.vue

// 组件名：PascalCase
export default {
  name: 'ChatComponent'
}
```

#### 4.3.2 API 调用封装

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
});

// 请求拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 统一错误处理
    return Promise.reject(error);
  }
);

export default api;
```

---

## 五、非功能需求

### 5.1 性能要求

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 首屏加载时间 | < 3秒 | Lighthouse |
| API 响应时间 | < 2秒 | 监控工具 |
| 页面切换 | < 500ms | 性能测试 |
| 搜索延迟 | < 1秒 | 用户测试 |

### 5.2 兼容性要求

| 平台 | 版本要求 |
|------|---------|
| Chrome | 90+ |
| Safari | 14+ |
| Edge | 90+ |
| 微信小程序 | 基础库 2.0+ |
| iOS | 12+ |
| Android | 8+ |

### 5.3 安全要求

| 需求 | 实现方案 |
|------|---------|
| HTTPS 强制 | 生产环境强制 HTTPS |
| XSS 防护 | 输入过滤 + CSP |
| CSRF 防护 | Token 验证 |
| 敏感信息加密 | 加密存储 |

---

## 六、测试计划

### 6.1 功能测试

| 模块 | 测试用例数 | 覆盖率目标 |
|------|-----------|-----------|
| 智能问答 | 20+ | 90% |
| 知识库搜索 | 15+ | 85% |
| 会话管理 | 12+ | 90% |
| 用户管理 | 8+ | 80% |

### 6.2 性能测试

| 测试项 | 目标值 |
|--------|--------|
| 并发用户 | 100+ |
| 响应时间 (P95) | < 2秒 |
| 错误率 | < 1% |

### 6.3 兼容性测试

| 测试环境 | 设备/浏览器 |
|---------|------------|
| Web 端 | Chrome, Safari, Edge, Firefox |
| 移动端 | iOS Safari, Android Chrome |
| 小程序 | 微信小程序 |

---

## 七、验收标准

### 7.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| 智能问答 | 能够正确回答 85% 以上的测试问题 |
| 会话管理 | 会话创建、切换、删除功能正常 |
| 知识库搜索 | Top-5 结果准确率 > 85% |
| 界面交互 | 所有交互流畅，无卡顿 |

### 7.2 性能验收

| 指标 | 验收标准 |
|------|---------|
| 响应时间 | 95% 请求 < 2秒 |
| 并发支持 | 支持 100+ 并发用户 |
| 错误率 | < 1% |

### 7.3 用户体验验收

| 指标 | 验收标准 |
|------|---------|
| 首次使用引导 | 新用户能在 30 秒内完成首次问答 |
| 界面美观度 | 符合设计稿，无明显视觉问题 |
| 操作便捷性 | 核心操作不超过 3 步 |

---

## 八、项目计划

### 8.1 里程碑

| 阶段 | 时间 | 交付物 |
|------|------|--------|
| 需求确认 | 第1周 | PRD v1.0 |
| UI 设计 | 第2周 | 设计稿 v1.0 |
| Web 前端开发 | 第3-4周 | Web 端 MVP |
| 小程序开发 | 第5-6周 | 小程序端 MVP |
| 联调测试 | 第7周 | 测试报告 |
| 上线发布 | 第8周 | 生产环境 |

### 8.2 人员分工

| 角色 | 负责人 | 职责 |
|------|--------|------|
| 产品经理 | - | 需求管理、进度把控 |
| UI 设计师 | - | 界面设计、交互设计 |
| 前端开发 | - | Vue.js 前端、小程序开发 |
| 后端开发 | - | API 维护、功能扩展 |
| 测试工程师 | - | 测试用例、质量把控 |

---

## 九、附录

### 9.1 术语表

| 术语 | 含义 |
|------|------|
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| TF-IDF | Term Frequency-Inverse Document Frequency |
| MVP | Minimum Viable Product，最小可行产品 |
| API | Application Programming Interface，应用程序接口 |

### 9.2 参考资料

- FastAPI 官方文档：https://fastapi.tiangolo.com/
- Vue.js 官方文档：https://vuejs.org/
- 微信小程序文档：https://developers.weixin.qq.com/miniprogram/dev/framework/

---

**文档状态**：待评审
**下次更新**：根据评审意见修订
