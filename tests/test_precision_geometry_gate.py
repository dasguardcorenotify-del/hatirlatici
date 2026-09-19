import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "tools" / "precision_geometry_gate.py"


class PrecisionGeometryGateTests(unittest.TestCase):
    def run_gate(self, scale, *extra):
        env = dict(os.environ)
        env.pop("HATIRLATICI_GEOMETRY_CODE_ROOT", None)
        env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "ui_v2")))
        result = subprocess.run(
            [sys.executable, str(GATE), "--scale", scale, *extra],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
            check=False,
        )
        return result

    def test_full_matrix_at_all_required_scales(self):
        for scale in ("1.0", "1.25", "1.5"):
            with self.subTest(scale=scale):
                result = self.run_gate(scale)
                match = re.search(r"^TRUE_FAILURES=(\d+)$", result.stdout, re.MULTILINE)
                self.assertIsNotNone(match, result.stdout)
                self.assertEqual(int(match.group(1)), 0, result.stdout)
                self.assertIn("GEOMETRY_CODE_ROOT_SOURCE=CHECKOUT", result.stdout)
                self.assertIn("PRECISION_GEOMETRY_GATE=PASS", result.stdout)
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_printed_failure_always_exits_nonzero(self):
        result = self.run_gate("1.0", "--inject-failure")
        match = re.search(r"^TRUE_FAILURES=(\d+)$", result.stdout, re.MULTILINE)
        self.assertIsNotNone(match, result.stdout)
        self.assertGreater(int(match.group(1)), 0, result.stdout)
        self.assertIn("PRECISION_GEOMETRY_GATE=FAIL", result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_invalid_installed_code_root_fails_closed(self):
        env = dict(os.environ)
        env["HATIRLATICI_GEOMETRY_CODE_ROOT"] = "/definitely/missing/hatirlatici"
        result = subprocess.run(
            [sys.executable, str(GATE), "--scale", "1.0"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 41, result.stdout)
        self.assertIn("PRECISION_GEOMETRY_GATE=FAIL_INVALID_CODE_ROOT", result.stdout)


if __name__ == "__main__":
    unittest.main()
