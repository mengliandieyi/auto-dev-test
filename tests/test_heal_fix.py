"""heal/fix apply_patch_dir 单测。"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from heal.fix import apply_patch_dir  # noqa: E402


class TestApplyPatchDir(unittest.TestCase):
    def test_copies_staged_generated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch_dir = Path(tmp) / "patch"
            staged = patch_dir / "tests" / "generated" / "login.spec.ts"
            staged.parent.mkdir(parents=True)
            staged.write_text("export const applied = true;\n", encoding="utf-8")

            gen_root = ROOT / "tests" / "generated" / "_heal_fix_test"
            gen_root.mkdir(parents=True, exist_ok=True)
            target = gen_root / "login.spec.ts"
            if target.exists():
                target.unlink()

            try:
                ok = apply_patch_dir(patch_dir, "_heal_fix_test", "PROJ-001")
                self.assertTrue(ok)
                self.assertEqual(target.read_text(encoding="utf-8"), "export const applied = true;\n")
            finally:
                if target.exists():
                    target.unlink()
                if gen_root.is_dir() and not any(gen_root.iterdir()):
                    gen_root.rmdir()

    def test_business_code_dry_run_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch_dir = Path(tmp) / "patch"
            patch_dir.mkdir()
            (patch_dir / "business_code.TODO.md").write_text("manual review\n", encoding="utf-8")
            self.assertFalse(apply_patch_dir(patch_dir, "project-a", "PROJ-001"))

    def test_missing_patch_dir_returns_false(self):
        self.assertFalse(apply_patch_dir(Path("/nonexistent/patch-dir"), "project-a", "PROJ-001"))

    def test_generate_fallback_returns_false_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch_dir = Path(tmp) / "patch"
            patch_dir.mkdir()
            with patch("heal.fix.subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1
                self.assertFalse(apply_patch_dir(patch_dir, "project-a", "PROJ-001"))


if __name__ == "__main__":
    unittest.main()
