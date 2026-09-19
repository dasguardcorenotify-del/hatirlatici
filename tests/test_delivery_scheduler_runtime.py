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


class DeliverySchedulerRuntimeTests(
    unittest.TestCase
):
    def test_scheduler_selftest_fresh_xdg(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)

            env = (
                os.environ.copy()
            )

            env.update(
                {
                    "XDG_CONFIG_HOME":
                        str(
                            tmp
                            / "config"
                        ),

                    "XDG_DATA_HOME":
                        str(
                            tmp
                            / "data"
                        ),

                    "XDG_STATE_HOME":
                        str(
                            tmp
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
                        / "delivery_scheduler.py"
                    ),
                    "--selftest",
                ],
                env=env,
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
                "INTERNAL_SCHEDULER_SELFTEST=PASS",
                result.stdout,
            )


if __name__ == "__main__":
    unittest.main()
