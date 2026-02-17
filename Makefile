# 安信工AI小助手 - Makefile
# 一键操作命令

.PHONY: help install dev test lint format build docker clean

# 默认显示帮助
help:
	@echo "=================================="
	@echo "  安信工AI小助手 - 项目命令"
	@echo "=================================="
	@echo ""
	@echo "安装与启动:"
	@echo "  make install      - 安装所有依赖"
	@echo "  make dev          - 启动开发服务器"
	@echo "  make dev-backend  - 仅启动后端"
	@echo "  make dev-frontend - 仅启动前端"
	@echo ""
	@echo "测试与质量:"
	@echo "  make test         - 运行所有测试"
	@echo "  make test-backend - 运行后端测试"
	@echo "  make test-frontend- 运行前端测试"
	@echo "  make lint         - 代码风格检查"
	@echo "  make format       - 代码格式化"
	@echo ""
	@echo "构建与部署:"
	@echo "  make build        - 构建项目"
	@echo "  make docker       - 构建 Docker 镜像"
	@echo "  make docker-up    - 使用 Docker Compose 启动"
	@echo "  make docker-down  - 停止 Docker 服务"
	@echo ""
	@echo "清理:"
	@echo "  make clean        - 清理临时文件"

# 安装依赖
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd frontend && npm install

# 开发服务器
dev: dev-backend dev-frontend

dev-backend:
	cd backend && python main.py

dev-frontend:
	cd frontend && npm run dev

# 测试
test: test-backend test-frontend

test-backend:
	pytest tests/ -v --cov=backend --cov-report=term-missing

test-frontend:
	cd frontend && npm run test:ci

# 代码检查
lint:
	black --check backend/ tests/
	isort --check-only backend/ tests/
	flake8 backend/ tests/
	cd frontend && npm run lint

# 代码格式化
format:
	black backend/ tests/
	isort backend/ tests/

# 构建
build:
	cd frontend && npm run build

# Docker
docker:
	docker build -t student-ai-backend .
	cd frontend && docker build -t student-ai-frontend .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	cd frontend && rm -rf node_modules dist
