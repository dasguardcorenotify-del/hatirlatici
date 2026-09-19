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


class PublicPathIsolationTests(
    unittest.TestCase
):
    def test_fresh_process_uses_only_xdg_runtime_paths(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)

            env = os.environ.copy()

            env.update(
                {
                    "XDG_CONFIG_HOME":
                        str(
                            tmp / "config"
                        ),

                    "XDG_DATA_HOME":
                        str(
                            tmp / "data"
                        ),

                    "XDG_STATE_HOME":
                        str(
                            tmp / "state"
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

            code = r'''
import runtime_config
import core_v2 as core

runtime_config.ensure_runtime_dirs()

assert core.ROOT == runtime_config.data_dir()
assert core.MAIL_CSV == runtime_config.mail_csv_path()
assert core.PC_CSV == runtime_config.pc_csv_path()
assert core.HISTORY_CSV == runtime_config.history_path()
assert core.SETTINGS_JSON == runtime_config.app_settings_path()
assert core.DATA_BACKUPS == runtime_config.data_backups_dir()

core.migrate_mail_schema()
core.ensure_pc_schema()
core.ensure_history_schema()

assert core.MAIL_CSV.exists()
assert core.PC_CSV.exists()
assert core.HISTORY_CSV.exists()

print("FRESH_XDG_CORE=PASS")
'''

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code,
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
                "FRESH_XDG_CORE=PASS",
                result.stdout,
            )

            self.assertTrue(
                (
                    tmp
                    / "data"
                    / "hatirlatici"
                    / "hatirlatmalar.csv"
                ).exists()
            )

            self.assertTrue(
                (
                    tmp
                    / "state"
                    / "hatirlatici"
                    / "hatirlatici_history.csv"
                ).exists()
            )

    def test_public_code_tree_gets_no_runtime_csv(
        self,
    ):
        forbidden = (
            ROOT
            / "hatirlatmalar.csv",
            ROOT
            / "pc_hatirlatmalar.csv",
            ROOT
            / "hatirlatici_history.csv",
            ROOT
            / "settings_v2.json",
        )

        for path in forbidden:
            self.assertFalse(
                path.exists(),
                str(path),
            )


if __name__ == "__main__":
    unittest.main()
