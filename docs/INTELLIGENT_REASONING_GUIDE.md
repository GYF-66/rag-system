# 智能推理问答功能文档

## 功能概述

智能推理问答功能允许 AI 处理隐含关联问题，如"挂科与奖学金"、"软著加分"等。系统会自动识别此类问题，检索多项相关规章，在 `<thinking>` 标签内完成交叉比对，最后输出总结性回答。

---

## 核心组件

### 1. 交叉检索引擎 (`cross_retrieval_engine.py`)

**功能**：识别隐含关联问题并执行交叉检索

**关键方法**：
```python
class CrossRetrievalEngine:
    def is_cross_query(query: str) -> Tuple[bool, Optional[Dict]]
    def cross_retrieve(query: str, pattern_info: Dict) -> Dict
    def compare_and_merge(retrieval_results: Dict, query: str) -> Dict
    def generate_thinking_block(...) -> str
    def process_cross_query(query: str) -> Optional[Dict]
```

**支持的问题模式**：
- 挂科与奖学金
- 软著加分
- 专利加分
- 竞赛获奖加分
- 转专业条件
- 延期毕业影响
- 重修费用
- 补考与绩点
- 处分与评优
- 宿舍违规与处分

---

### 2. 推理引擎增强 (`reasoning_engine.py`)

**新增功能**：支持交叉推理内容

```python
def end(self, is_cross_query: bool = False, cross_thinking_content: str = None) -> ThinkingProcess
```

---

### 3. 智能体增强 (`agent_v2.py`)

**新增功能**：自动识别和处理隐含关联问题

```python
def process_query(
    query: str,
    session_history: Optional[List[Dict]] = None,
    use_rag: bool = True,
    enable_thinking: bool = True
) -> Dict:
    # 返回值包含：
    # - 'is_cross_query': 是否为交叉查询
    # - 'cross_reasoning': 交叉推理内容
    # - 'cross_result': 完整的交叉检索结果
```

---

### 4. 数据模型更新 (`models_v2.py`)

**ChatResponse 新增字段**：
```python
cross_reasoning: Optional[str] = Field(None, description="交叉推理内容（<thinking>标签内的内容）")
is_cross_query: bool = Field(False, description="是否为交叉查询")
```

---

## API 使用示例

### 请求

```http
POST /api/chat
Content-Type: application/json

{
  "message": "挂科对奖学金申请有影响吗？",
  "session_id": "optional",
  "user_id": "optional",
  "use_rag": true,
  "enable_thinking": true
}
```

---

## 扩展新问题模式

如需添加新的隐含关联问题模式，编辑 `cross_retrieval_engine.py`：

```python
self.cross_query_patterns = {
    # 现有模式...
    '新模式': {
        'keywords': ['关键词1', '关键词2', '关键词3'],
        'query_type': 'cross_reference',
        'description': '问题描述'
    }
}
```

同时更新 `_analyze_regulation_correlation()` 方法，添加相应的关联分析逻辑。

---

## 故障排查

### 问题1: 交叉查询未被识别

**原因**：关键词匹配规则过于严格

**解决方案**：
- 降低匹配阈值（从 2 个关键词降到 1.5 个）
- 扩展关键词列表

### 问题2: 交叉检索耗时过长

**原因**：关键词过多或检索结果过多

**解决方案**：
- 减少关键词数量
- 限制每个关键词的检索结果数
- 使用缓存

### 问题3: Thinking 内容为空

**原因**：知识库未加载或检索失败

**解决方案**：
- 检查知识库是否正常加载
- 查看日志中的错误信息
- 验证 ChromaDB 连接

---

## 参考资料

- 交叉检索引擎实现：`backend/cross_retrieval_engine.py`
- 推理引擎增强：`backend/reasoning_engine.py`
- 智能体增强：`backend/agent_v2.py`
- Reasoning-RAG 架构：`docs/REASONING_RAG_ARCHITECTURE.md`
