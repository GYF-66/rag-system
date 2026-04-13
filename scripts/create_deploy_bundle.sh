#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="${ROOT_DIR}/release-artifacts"
DATE_STAMP="$(date +%Y%m%d)"
BUNDLE_PATH="${1:-${RELEASE_DIR}/deploy_bundle_${DATE_STAMP}.tar.gz}"

mkdir -p "${RELEASE_DIR}"

cd "${ROOT_DIR}"

tar -czf "${BUNDLE_PATH}" \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/dist' \
  --exclude='frontend/dev-dist' \
  --exclude='frontend/test-results' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.venv' \
  --exclude='logs' \
  --exclude='output' \
  --exclude='evaluation_results' \
  --exclude='paper' \
  --exclude='paper-photo' \
  --exclude='DeepScientist' \
  --exclude='.idea' \
  --exclude='.vscode' \
  --exclude='.cursor' \
  --exclude='.claude' \
  --exclude='.zed' \
  --exclude='.zcf' \
  --exclude='docs' \
  --exclude='tests' \
  --exclude='auto-research' \
  --exclude='ui-design' \
  --exclude='doctor' \
  --exclude='*.log' \
  --exclude='*.tar' \
  --exclude='*.tar.gz' \
  --exclude='.env' \
  --exclude='.env.production' \
  --exclude='scripts' \
  --exclude='backend/data' \
  --exclude='backend/tests' \
  --exclude='backend/benchmark' \
  --exclude='frontend/.storybook' \
  --exclude='frontend/scripts' \
  --exclude='frontend/src/stories' \
  --exclude='frontend/**/*.spec.ts' \
  --exclude='frontend/tmp_utf8_test.txt' \
  Dockerfile \
  docker-compose.prod.yml \
  requirements-prod.txt \
  .dockerignore \
  backend \
  frontend \
  database

echo "Created deploy bundle at ${BUNDLE_PATH}"
