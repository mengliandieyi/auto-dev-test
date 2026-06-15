"""tool_path 单测。"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tool_path import augment_path_env, which_tool


class TestToolPath(unittest.TestCase):
    def test_augment_path_env_prepends_local_bin(self):
        home_bin = str(Path.home() / ".local" / "bin")
        env = augment_path_env({"PATH": "/usr/bin"})
        self.assertTrue(env["PATH"].startswith(home_bin + os.pathsep) or home_bin in env["PATH"].split(os.pathsep)[:3])

    def test_which_tool_finds_openhands_when_in_local_bin(self):
        fake = Path("/tmp/fake-local-bin-test")
        fake.mkdir(parents=True, exist_ok=True)
        binary = fake / "openhands"
        binary.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
        binary.chmod(0o755)
        with patch("tool_path.augment_path_env", return_value={"PATH": str(fake)}):
            self.assertEqual(which_tool("openhands"), str(binary))
        binary.unlink(missing_ok=True)
        fake.rmdir()


if __name__ == "__main__":
    unittest.main()
