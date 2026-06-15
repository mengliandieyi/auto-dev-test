#!/usr/bin/env bash
# PRD §8 一键验收：全流程 + 全量单测
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> run-full (project-a / PROJ-001)"
python3 run.py run-full --project project-a --prd prds/project-a/PROJ-001_login.md

echo "==> unit tests"
python3 -m unittest \
  tests.test_acceptance \
  tests.test_m2 \
  tests.test_path_safety \
  tests.test_m4_vitest \
  tests.test_m5_write_security \
  tests.test_m6_heal \
  tests.test_component_path_resolver \
  tests.test_validator_optional -v

echo "✅ 里程碑验收全部通过"
