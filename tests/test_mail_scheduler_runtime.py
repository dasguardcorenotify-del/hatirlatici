import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class MailSchedulerRuntimeTests(
    unittest.TestCase
):
    def test_fresh_xdg_selftest(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)

            env = os.environ.copy()

            env.update(
                {
                    "XDG_CONFIG_HOME":
                        str(
                            base
                            / "config"
                        ),

                    "XDG_DATA_HOME":
                        str(
                            base
                            / "data"
                        ),

                    "XDG_STATE_HOME":
                        str(
                            base
                            / "state"
                        ),

                    "PYTHONPATH":
                        os.pathsep.join(
                            [
                                str(ROOT),
                                str(
                                    ROOT
                                    / "ui_v2"
                                ),
                            ]
                        ),
                }
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "mail_scheduler.py"
                    ),
                ],
                env=env,
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=(
                    result.stdout
                    + "\n"
                    + result.stderr
                ),
            )

            self.assertIn(
                "MAIL_SCHEDULER_SELFTEST=PASS",
                result.stdout,
            )

            self.assertIn(
                "MAIL_TRANSPORT_READY=NO",
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()
