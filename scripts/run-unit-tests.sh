#!/usr/bin/env bash
# PRD §8 单元测试集合（verify.sh 与 CI 共用）
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m unittest \
  tests.test_acceptance \
  tests.test_m2 \
  tests.test_path_safety \
  tests.test_m4_vitest \
  tests.test_m5_write_security \
  tests.test_m6_heal \
  tests.test_env_store \
  tests.test_ai_resolver \
  tests.test_skills_api \
  tests.test_dev_layer \
  tests.test_dev_ai \
  tests.test_heal_fix \
  tests.test_prd_project_binding \
  tests.test_job_cancel \
  tests.test_job_events \
  tests.test_job_event_persistence \
  tests.test_job_insights \
  tests.test_project_settings \
  tests.test_create_project \
  tests.test_artifacts_api \
  tests.test_component_path_resolver \
  tests.test_validator_optional -v
