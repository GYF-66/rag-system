# 测试指南

## 概述

本目录包含RAG系统的完整测试套件，包括单元测试、集成测试和性能基准测试。

## 测试结构

```
tests/
├── agent/              # Agent组件单元测试
│   ├── test_tools.py           # 工具测试
│   ├── test_cache.py           # 缓存测试
│   └── test_evaluator.py       # 评估器测试
├── integration/        # 集成测试
│   └── test_agent_workflow.py  # Agent工作流测试
└── benchmark/          # 性能基准测试
    └── test_performance.py     # 性能测试
```

## 安装测试依赖

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/agent/test_tools.py
```

### 运行特定测试类
```bash
pytest tests/agent/test_tools.py::TestVectorSearchTool
```

### 运行特定测试函数
```bash
pytest tests/agent/test_tools.py::TestVectorSearchTool::test_vector_search_execute
```

### 按标记运行测试

#### 只运行单元测试
```bash
pytest -m unit
```

#### 只运行集成测试
```bash
pytest -m integration
```

#### 只运行性能测试
```bash
pytest -m benchmark
```

#### 跳过慢速测试
```bash
pytest -m "not slow"
```

### 生成覆盖率报告

```bash
# 生成终端报告
pytest --cov=. --cov-report=term-missing

# 生成HTML报告
pytest --cov=. --cov-report=html

# 生成XML报告（用于CI）
pytest --cov=. --cov-report=xml
```

### 详细输出

```bash
# 显示print输出
pytest -s

# 显示详细信息
pytest -v

# 显示更详细的信息
pytest -vv
```

### 并行运行测试

```bash
# 安装pytest-xdist
pip install pytest-xdist

# 使用多个CPU核心
pytest -n auto
```

## 测试类型说明

### 1. 单元测试 (tests/agent/)

测试单个组件的功能，使用Mock对象隔离依赖。

**覆盖范围：**
- 工具（向量检索、关键词检索、混合检索）
- 缓存（语义缓存、TTL、LRU淘汰）
- 评估器（质量评分、阈值判断）
- 重排序器
- 查询改进器
- 审批管理器

**运行示例：**
```bash
pytest tests/agent/ -v
```

### 2. 集成测试 (tests/integration/)

测试多个组件协同工作的完整流程。

**覆盖范围：**
- Agent完整工作流
- 工具选择策略
- 质量评估和改进循环
- 重排序集成
- 审批机制触发

**运行示例：**
```bash
pytest tests/integration/ -v
```

### 3. 性能基准测试 (tests/benchmark/)

测试系统在不同负载下的性能表现。

**覆盖范围：**
- 单次查询延迟
- 批量查询吞吐量
- 并发查询性能
- 缓存性能
- 指标收集开销
- 持续负载测试

**运行示例：**
```bash
pytest tests/benchmark/ -v -s
```

## 编写新测试

### 单元测试模板

```python
import pytest
from unittest.mock import Mock

class TestYourComponent:
    @pytest.fixture
    def component(self):
        """创建组件实例"""
        return YourComponent()
    
    def test_basic_functionality(self, component):
        """测试基本功能"""
        result = component.do_something()
        assert result is not None
```

### 异步测试模板

```python
import pytest

class TestAsyncComponent:
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """测试异步操作"""
        result = await async_function()
        assert result is not None
```

### 性能测试模板

```python
import time

class TestPerformance:
    def test_operation_latency(self):
        """测试操作延迟"""
        start_time = time.time()
        
        # 执行操作
        perform_operation()
        
        latency = (time.time() - start_time) * 1000
        assert latency < 100  # 应在100ms内完成
```

## 持续集成

### GitHub Actions示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 最佳实践

1. **测试隔离**：每个测试应该独立，不依赖其他测试的状态
2. **使用Fixtures**：复用测试设置代码
3. **Mock外部依赖**：使用Mock对象隔离外部系统
4. **清晰的断言**：使用明确的断言消息
5. **测试边界条件**：测试空输入、极大值、异常情况
6. **性能基准**：为关键操作设置性能基准
7. **定期运行**：在CI/CD中自动运行测试

## 故障排查

### 测试失败

1. 查看详细错误信息：`pytest -vv`
2. 查看完整堆栈：`pytest --tb=long`
3. 只运行失败的测试：`pytest --lf`

### 导入错误

确保backend目录在Python路径中：
```python
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))
```

### 异步测试问题

确保安装了pytest-asyncio：
```bash
pip install pytest-asyncio
```

## 测试覆盖率目标

- **单元测试覆盖率**：> 80%
- **集成测试覆盖率**：> 60%
- **关键路径覆盖率**：100%

## 联系方式

如有测试相关问题，请联系开发团队。
