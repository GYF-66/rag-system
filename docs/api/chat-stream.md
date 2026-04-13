# `/api/chat/stream` SSE 契约

`POST /api/chat/stream`

用于手动问答页的真实流式回答链路。响应类型为 `text/event-stream`，事件顺序允许插入 `token`，但整体遵循以下契约：

1. `metadata`
2. `token` 若干
3. 可选 `answer_replace`
4. 可选 `reflection`
5. 可选 `thinking`
6. `done` 或 `error`

## 事件说明

### `metadata`
- 首个事件
- 必含：
  - `request_id`
  - `contract_version`
  - `event_types`
  - `session_id`
  - `sources`
  - `metadata`
- `metadata.request_id` 必须与顶层 `request_id` 一致

### `token`
- 逐段返回模型生成内容
- 载荷：
  - `content`

### `answer_replace`
- 当后端从 CoT 原始输出中提取出最终答案时，用于替换前端已累计的展示文本
- 载荷：
  - `content`

### `reflection`
- Self-RAG 校验结果
- 载荷：
  - `request_id`
  - `status`
  - `confidence`
  - `issues`
  - `revision_applied`

### `thinking`
- 完整思考过程对象
- 结构与 `ThinkingProcess` 对齐

### `done`
- 流式结束信号
- 载荷：
  - `request_id`
  - `total_duration_ms`

### `error`
- 流式失败信号
- 载荷：
  - `request_id`
  - `message`

## 前端兼容要求

- 前端必须容忍 `reflection` 和 `thinking` 缺失。
- 前端必须支持 `token` 在 `thinking` 之前连续到达。
- 前端必须在收到 `error` 后进入可重试状态，并保留已生成的部分文本用于排障。
