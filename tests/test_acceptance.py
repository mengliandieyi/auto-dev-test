#!/usr/bin/env python3
"""PRD §8 里程碑自动化验收（M1–M6）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bootstrap import ROOT


class TestMilestoneAcceptance(unittest.TestCase):
  """关键验收项；完整 E2E 需 npm + playwright 已安装。"""

  def test_m1_validate_exit_code_2(self):
    bad = ROOT / "prds/project-a/_bad_prd_validate_test.md"
    bad.write_text("# 无章节\n", encoding="utf-8")
    try:
      r = subprocess.run(
        [
          sys.executable,
          str(ROOT / "run.py"),
          "validate",
          "--project",
          "project-a",
          "--prd",
          "prds/project-a/_bad_prd_validate_test.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
      )
      self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
    finally:
      bad.unlink(missing_ok=True)

  def test_m1_intermediate_exists(self):
    p = ROOT / "tests/intermediate/project-a/PROJ-001_test-cases.json"
    self.assertTrue(p.is_file())
    data = json.loads(p.read_text(encoding="utf-8"))
    self.assertIn("e2e_test_cases", data)
    self.assertIn("component_test_cases", data)
    self.assertTrue(any(c.get("m1_gate") for c in data["e2e_test_cases"]))
    self.assertTrue(any(c.get("m1_gate") for c in data["component_test_cases"]))

  def test_m1_generated_specs_exist(self):
    e2e = list((ROOT / "tests/generated/project-a/e2e").glob("PROJ-001_*.spec.ts"))
    comp = list((ROOT / "tests/generated/project-a/component").glob("PROJ-001_*.test.tsx"))
    self.assertTrue(e2e and comp)

  def test_m1_msw_in_it_only(self):
    spec = list((ROOT / "tests/generated/project-a/component").glob("PROJ-001_*.test.tsx"))[0]
    text = spec.read_text(encoding="utf-8")
    self.assertIn("server.use", text)
    self.assertNotIn("beforeAll(() => server.use", text)

  def test_m1_auth_helper_skip(self):
    auth = (ROOT / "test-generator/base/AuthHelper.ts").read_text(encoding="utf-8")
    self.assertIn("AUTH_MODE", auth)
    self.assertIn("return", auth)

  def test_m2_content_hash_in_intermediate(self):
    data = json.loads(
      (ROOT / "tests/intermediate/project-a/PROJ-001_test-cases.json").read_text(encoding="utf-8")
    )
    self.assertIn("prd_content_hash", data)

  def test_m2_skeleton_report_support(self):
    from report import generate_report

    config = __import__("config_loader", fromlist=["load_project_config"]).load_project_config("project-a")
    generate_report(config, "project-a", skeleton=True)
    sk = ROOT / "reports/project-a/PROJ-001_traceability.skeleton.txt"
    self.assertTrue(sk.is_file())

  def test_m2_version_drift_skip(self):
    from spec_idempotency import decide_generation

    with tempfile.TemporaryDirectory() as tmp:
      spec = Path(tmp) / "s.spec.ts"
      spec.write_text("/** PRD: PROJ-001 v1.0.0 (p) */\n/** Hash: abc */\n", encoding="utf-8")
      d = decide_generation("p", "PROJ-001", "e2e", "1.1.0", "abc", spec)
      self.assertEqual(d.action, "skip")

  def test_m2_content_drift_ci(self):
    from spec_idempotency import decide_generation

    with tempfile.TemporaryDirectory() as tmp:
      spec = Path(tmp) / "s.spec.ts"
      spec.write_text("/** PRD: PROJ-001 v1.0.0 (p) */\n/** Hash: old */\n", encoding="utf-8")
      os.environ["CI"] = "true"
      try:
        with self.assertRaises(SystemExit):
          decide_generation("p", "PROJ-001", "e2e", "1.0.0", "new", spec)
      finally:
        os.environ.pop("CI", None)

  def test_m1_project_b_path_isolation(self):
    from config_loader import load_project_config

    a = load_project_config("project-a")
    b = load_project_config("project-b")
    self.assertIn("project-a", a["intermediate_dir"])
    self.assertIn("project-b", b["intermediate_dir"])
    self.assertNotEqual(a["intermediate_dir"], b["intermediate_dir"])

  def test_m3_api_modules(self):
    self.assertTrue((ROOT / "api/main.py").is_file())
    self.assertTrue((ROOT / "api/routers/pipeline.py").is_file())

  def test_m4_vitest_forks_config(self):
    cfg = (ROOT / "vitest.config.ts").read_text(encoding="utf-8")
    self.assertIn("forks", cfg)
    self.assertIn("VITEST_SINGLE_THREAD", cfg)

  def test_m5_ci_templates(self):
    for name in ("github-actions.yml", "gitlab-ci.yml", "Jenkinsfile"):
      self.assertTrue((ROOT / "ci" / name).is_file(), name)
    self.assertIn("[skip ci]", (ROOT / "ci/github-actions.yml").read_text(encoding="utf-8"))

  def test_m1_generate_pipeline_no_test(self):
    src = (ROOT / "run.py").read_text(encoding="utf-8")
    gp = src.split("def cmd_generate_pipeline")[1].split("def cmd_run_full")[0]
    self.assertNotIn("cmd_test", gp)
    self.assertIn("cmd_report", gp)

  def test_m5_write_api(self):
    prds = (ROOT / "api/routers/prds.py").read_text(encoding="utf-8")
    projects = (ROOT / "api/routers/projects.py").read_text(encoding="utf-8")
    self.assertIn("@router.put", prds)
    self.assertIn("@router.put", projects)

  def test_m6_heal_modules(self):
    self.assertTrue((ROOT / "heal/loop.py").is_file())
    self.assertTrue((ROOT / "heal/store.py").is_file())
    self.assertTrue((ROOT / "api/routers/heal.py").is_file())

  def test_m6_dev_runs(self):
    r = subprocess.run(
      [sys.executable, str(ROOT / "run.py"), "dev", "--project", "project-a", "--prd", "prds/project-a/PROJ-001_login.md"],
      cwd=ROOT,
      capture_output=True,
      text=True,
    )
    self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
  unittest.main(verbosity=2)
