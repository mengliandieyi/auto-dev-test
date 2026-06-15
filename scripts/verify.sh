#!/usr/bin/env bash
# PRD §8 一键验收：全流程 + 全量单测
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> run-full (project-a / PROJ-001)"
python3 run.py run-full --project project-a --prd prds/project-a/PROJ-001_login.md

echo "==> unit tests"
bash scripts/run-unit-tests.sh

echo "✅ 里程碑验收全部通过"
