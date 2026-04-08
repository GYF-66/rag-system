# 安信工 AI 助手 - Makefile

.PHONY: help install dev test lint format build docker docker-up docker-down docker-prod-up docker-prod-down clean

help:
	@echo "=================================="
	@echo "  安信工 AI 助手 - 项目命令"
	@echo "=================================="
	@echo ""
	@echo "安装与启动"
	@echo "  make install         - 安装所有依赖"
	@echo "  make dev             - 启动开发环境"
	@echo "  make dev-backend     - 仅启动后端"
	@echo "  make dev-frontend    - 仅启动前端"
	@echo ""
	@echo "测试与质量"
	@echo "  make test            - 运行全部测试"
	@echo "  make test-backend    - 运行后端测试"
	@echo "  make test-frontend   - 运行前端测试"
	@echo "  make lint            - 代码风格检查"
	@echo "  make format          - 代码格式化"
	@echo ""
	@echo "构建与部署"
	@echo "  make build           - 构建前端"
	@echo "  make docker          - 构建镜像"
	@echo "  make docker-up       - 启动开发编排"
	@echo "  make docker-down     - 关闭开发编排"
	@echo "  make docker-prod-up  - 启动生产编排"
	@echo "  make docker-prod-down - 关闭生产编排"
	@echo ""
	@echo "清理"
	@echo "  make clean           - 清理临时文件"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd frontend && npm install

dev: dev-backend dev-frontend

dev-backend:
	cd backend && python main.py

dev-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	pytest tests/ -v --cov=backend --cov-report=term-missing --cov-fail-under=70

test-frontend:
	cd frontend && npm run test:ci

lint:
	black --check backend/ tests/
	isort --check-only backend/ tests/
	flake8 backend/ tests/
	cd frontend && npm run lint

format:
	black backend/ tests/
	isort backend/ tests/

build:
	cd frontend && npm run build

docker:
	docker build -t student-ai-backend .
	cd frontend && docker build -t student-ai-frontend .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-prod-up:
	docker compose -f docker-compose.prod.yml --env-file .env.production up -d

docker-prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.production down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	cd frontend && rm -rf node_modules dist
