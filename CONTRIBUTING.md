# 贡献指南

感谢你对安信工AI小助手项目的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

请使用 GitHub Issues 报告 bug，并包含以下信息：

- Bug 描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（操作系统、Python 版本等）

### 提出新功能

请在提交 Issue 前先确认：

1. 该功能是否已存在
2. 该功能是否符合项目目标
3. 是否有其他相关 Issue

### 提交代码

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 代码规范

### Python 代码

- 遵循 PEP 8 规范
- 使用 Black 格式化代码
- 使用 isort 排序导入
- 添加类型注解
- 编写文档字符串

```bash
# 格式化代码
black backend/
isort backend/

# 检查代码
flake8 backend/
mypy backend/
```

### Vue/TypeScript 代码

- 使用 ESLint 检查代码
- 遵循 Vue 3 组合式 API 风格
- 添加组件文档

```bash
# 检查代码
cd frontend
npm run lint
```

## 测试

### 编写测试

- 为新功能添加单元测试
- 确保测试覆盖率不低于 70%
- 使用清晰的测试描述

```python
@pytest.mark.unit
def test_feature():
    """测试功能描述"""
    # 测试代码
    assert True
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/backend/test_agent.py

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

## Commit 规范

使用语义化提交信息：

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建/工具链变更
```

示例：

```
feat: 添加交叉检索功能
fix: 修复知识库加载问题
docs: 更新 API 文档
```

## Pull Request 流程

1. 确保代码通过所有测试
2. 更新相关文档
3. 添加清晰的 PR 描述
4. 等待代码审查
5. 根据反馈进行修改
6. 合并到主分支

## 行为准则

- 尊重所有贡献者
- 保持友好和专业的态度
- 接受建设性的批评
- 关注对社区最有利的事情

## 获取帮助

如有疑问，请：

1. 查看现有 Issues
2. 阅读项目文档
3. 在 Issue 中提问

## 许可证

通过贡献代码，你同意你的贡献将使用 MIT 许可证。