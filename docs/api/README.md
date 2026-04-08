# API 文档

本文档描述安信工AI小助手的所有 API 接口。

## 基础信息

- **Base URL**: `http://localhost:8001` (开发环境)
- **协议**: HTTPS (生产环境)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

部分 API 需要认证，使用 Bearer Token：

```http
Authorization: Bearer <access_token>
```

## 接口列表

### 健康检查

#### GET `/`

获取系统健康状态。

**响应示例**:
```json
{
  "status": "healthy",
  "agent_name": "安信工AI小助手",
  "knowledge_base_loaded": true,
  "total_chunks": 1234,
  "timestamp": "2026-02-05T12:00:00"
}
```

### 智能问答

#### POST `/api/chat`

发送消息并获取 AI 回复。

**请求体**:
```json
{
  "message": "请假流程是什么？",
  "session_id": "optional-session-id",
  "user_id": "optional-user-id",
  "use_rag": true,
  "enable_thinking": true
}
```

**响应示例**:
```json
{
  "response": "根据培养方案，请假流程如下...",
  "session_id": "session-uuid",
  "sources": [
    {
      "id": "123",
      "text": "相关规定内容",
      "char_count": 50,
      "similarity": 0.85
    }
  ],
  "thinking_process": {...},
  "cross_reasoning": "...",
  "is_cross_query": false,
  "timestamp": "2026-02-05T12:00:00"
}
```

### 知识库搜索

#### POST `/api/search`

搜索知识库。

**请求体**:
```json
{
  "query": "奖学金",
  "top_k": 5
}
```

**响应示例**:
```json
{
  "query": "奖学金",
  "results": [...],
  "total_results": 5
}
```

### 会话管理

#### POST `/api/sessions`

创建新会话。

**请求体**:
```json
{
  "session_id": "optional-session-id",
  "user_id": "optional-user-id"
}
```

#### GET `/api/sessions/{session_id}`

获取会话详情。

#### DELETE `/api/sessions/{session_id}`

删除会话。

### 用户认证

#### POST `/api/auth/register`

用户注册。

**请求体**:
```json
{
  "username": "testuser",
  "password": "password123",
  "nickname": "测试用户"
}
```

#### POST `/api/auth/login`

用户登录。

**请求体**:
```json
{
  "username": "testuser",
  "password": "password123"
}
```

#### POST `/api/auth/refresh`

刷新访问令牌。

**请求体**:
```json
{
  "refresh_token": "refresh-token-here"
}
```

## 错误响应

所有错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

常见状态码：
- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权
- `404`: 资源不存在
- `500`: 服务器错误
- `503`: 服务不可用

## 详细文档

请访问 `/docs` 查看自动生成的 Swagger/OpenAPI 文档。
