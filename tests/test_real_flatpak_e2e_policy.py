import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "real_flatpak_e2e.py"


class RealFlatpakE2EPolicyTests(unittest.TestCase):
    def _run(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_real_send_requires_explicit_confirmation(self):
        result = self._run()
        self.assertEqual(result.returncode, 41)
        self.assertEqual(
            result.stdout.strip(),
            "REAL_BOTH_E2E=REFUSED_MISSING_EXPLICIT_CONFIRMATION",
        )
        self.assertEqual(result.stderr, "")

    def test_confirmed_send_refuses_non_flatpak_host(self):
        result = self._run("--confirm-real-send-to-configured-owner")
        self.assertEqual(result.returncode, 41)
        self.assertEqual(
            result.stdout.strip(),
            "REAL_BOTH_E2E=REFUSED_NOT_FLATPAK",
        )
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
