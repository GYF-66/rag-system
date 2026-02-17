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

### 响应

```json
{
  "response": "关于挂科对奖学金申请的影响，根据学生手册的相关规定：\n\n**主要申请条件**\n\n• 国家奖学金要求智育成绩排名在班级前50%\n• 不得有不及格课程\n• 综合测评成绩优秀\n\n**关于挂科的影响**\n\n• 挂科（不及格）会直接影响你的智育成绩和综合测评排名\n• 大部分奖学金都要求成绩排名在班级前50%左右\n• 建议通过补考或重修来改善成绩\n\n**给你的建议**\n\n1. 优先处理挂科课程：关注补考时间，认真准备补考\n2. 了解重修政策：如果补考仍不及格，需要申请重修\n3. 提升综合素质：参加课外活动、竞赛等提升综合素质分\n4. 咨询辅导员：了解具体的奖学金评定细则和补救措施",
  "session_id": "xxx",
  "sources": [...],
  "thinking_process": {
    "query_analysis": {...},
    "retrieval": {...},
    "reranking": {...},
    "reasoning": {...},
    "summary": "【交叉推理】## 问题识别\n识别到隐含关联问题：挂科对奖学金申请有影响吗？...",
    "total_duration_ms": 148.7
  },
  "cross_reasoning": "## 问题识别\n识别到隐含关联问题：挂科对奖学金申请有影响吗？\n问题类型：挂科对奖学金申请的影响\n关联关键词：挂科, 不及格, 奖学金, 评选, 条件\n\n## 检索策略\n采用交叉检索策略，对以下 5 个关键词分别检索：\n- 「挂科」：检索到 15 个相关文档\n- 「不及格」：检索到 12 个相关文档\n- 「奖学金」：检索到 20 个相关文档\n- 「评选」：检索到 8 个相关文档\n- 「条件」：检索到 18 个相关文档\n\n## 交叉比对\n发现 2 个章节同时涉及多个关键词：\n\n1. 《安徽信息工程学院国家奖学金、励志奖学金评选办法》\n   - 涉及关键词：奖学金, 评选, 条件\n   - 文档数量：5\n   - 关键内容：国家奖学金的基本申请条件...\n\n2. 《安徽信息工程学院学生学业成绩管理规定》\n   - 涉及关键词：挂科, 不及格, 评选, 条件\n   - 文档数量：8\n   - 关键内容：不及格课程的处理...\n\n## 规章关联分析\n相关规章关联分析：\n1. 奖学金评选规定：通常要求成绩排名在班级前50%，无不及格课程\n2. 成绩管理规定：补考成绩如实记载，可能影响综合测评排名\n3. 综合素质测评：智育成绩是重要组成部分，挂科会直接影响\n4. 关联结论：挂科对奖学金申请有显著负面影响，建议通过补考或重修改善\n\n## 结论总结\n通过交叉检索，发现 2 个章节同时涉及多个相关主题：\n\n1. 《安徽信息工程学院国家奖学金、励志奖学金评选办法》：同时涉及「奖学金, 评选, 条件」等内容（5 个相关文档）\n\n2. 《安徽信息工程学院学生学业成绩管理规定》：同时涉及「挂科, 不及格, 评选, 条件」等内容（8 个相关文档）\n\n检索范围：共检索 5 个关键词，获取 73 个相关文档。",
  "is_cross_query": true,
  "timestamp": "2026-02-04T20:00:00",
  "metadata": {
    "retrieval_method": "chromadb",
    "rerank_method": "rule_based",
    "is_cross_query": true
  }
}
```

---

## 前端适配

### 1. 更新 API 客户端

```typescript
// services/api.ts
export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  use_rag?: boolean;
  enable_thinking?: boolean;  // 新增
}

export interface ChatResponse {
  response: string;
  session_id: string;
  sources: KnowledgeChunk[];
  thinking_process?: ThinkingProcess;
  cross_reasoning?: string;  // 新增
  is_cross_query?: boolean;  // 新增
  timestamp: string;
  metadata?: {
    retrieval_method: string;
    rerank_method: string;
    is_cross_query?: boolean;
  };
}
```

### 2. 显示交叉推理内容

```vue
<template>
  <div class="chat-message">
    <div class="message-content">
      {{ response }}
    </div>

    <!-- 显示交叉推理内容 -->
    <div v-if="is_cross_query && cross_reasoning" class="cross-reasoning">
      <div class="cross-reasoning-header">
        <span class="icon">🔍</span>
        <span>已进行交叉推理分析</span>
        <button @click="toggleReasoning" class="toggle-btn">
          {{ showReasoning ? '收起' : '展开' }}
        </button>
      </div>

      <div v-if="showReasoning" class="cross-reasoning-content">
        <pre>{{ cross_reasoning }}</pre>
      </div>
    </div>

    <!-- 显示知识来源 -->
    <div class="sources">
      <div v-for="source in sources" :key="source.id" class="source-item">
        <span class="source-section">{{ source.section }}</span>
        <span class="source-score">
          相似度: {{ (source.similarity * 100).toFixed(1) }}%
          <span v-if="source.rerank_score" class="rerank-score">
            (重排序: {{ (source.rerank_score * 100).toFixed(1) }}%)
          </span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  response: String,
  sources: Array,
  is_cross_query: Boolean,
  cross_reasoning: String
});

const showReasoning = ref(false);

const toggleReasoning = () => {
  showReasoning.value = !showReasoning.value;
};
</script>

<style scoped>
.cross-reasoning {
  margin-top: 12px;
  padding: 12px;
  background: #f0f9ff;
  border-left: 4px solid #3b82f6;
  border-radius: 4px;
}

.cross-reasoning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1e40af;
}

.toggle-btn {
  margin-left: auto;
  padding: 4px 12px;
  background: #e0e7ff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.cross-reasoning-content {
  margin-top: 12px;
  padding: 12px;
  background: white;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
}

.cross-reasoning-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: inherit;
}

.rerank-score {
  color: #059669;
  font-weight: 500;
}
</style>
```

---

## 测试

### 运行测试脚本

```bash
cd backend
python test_cross_retrieval.py
```

### 测试覆盖

1. **交叉查询检测测试**
   - 验证各种查询能否正确识别为交叉查询
   - 检查模式匹配准确性

2. **交叉检索测试**
   - 验证多关键词检索功能
   - 检查文档去重和合并

3. **交叉比对测试**
   - 验证章节分组功能
   - 检查关键章节识别

4. **思考内容生成测试**
   - 验证 `<thinking>` 内容格式
   - 检查推理逻辑完整性

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

## 性能优化建议

1. **限制检索关键词数量**
   - 每个模式最多 5 个关键词
   - 按重要性排序关键词

2. **缓存交叉检索结果**
   - 对常见查询进行缓存
   - 使用 Redis 或内存缓存

3. **并行检索**
   - 使用异步并发检索多个关键词
   - 减少总检索时间

4. **限制返回文档数量**
   - 每个关键词最多检索 10 个文档
   - 最终去重后保留 10 个文档

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
- 测试脚本：`backend/test_cross_retrieval.py`
- Reasoning-RAG 架构：`backend/REASONING_RAG_ARCHITECTURE.md`