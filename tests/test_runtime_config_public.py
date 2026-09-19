import os
import tempfile
import unittest
from pathlib import Path

import runtime_config


class RuntimeConfigTests(
    unittest.TestCase
):
    def setUp(self):
        self.tmp = (
            tempfile.TemporaryDirectory()
        )

        self.old = {}

        for key in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
        ):
            self.old[key] = (
                os.environ.get(key)
            )

        base = Path(
            self.tmp.name
        )

        os.environ[
            "XDG_CONFIG_HOME"
        ] = str(
            base / "config"
        )

        os.environ[
            "XDG_DATA_HOME"
        ] = str(
            base / "data"
        )

        os.environ[
            "XDG_STATE_HOME"
        ] = str(
            base / "state"
        )

    def tearDown(self):
        for key, value in (
            self.old.items()
        ):
            if value is None:
                os.environ.pop(
                    key,
                    None,
                )
            else:
                os.environ[
                    key
                ] = value

        self.tmp.cleanup()

    def test_xdg_paths(self):
        self.assertIn(
            "config",
            str(
                runtime_config
                .config_dir()
            ),
        )

        self.assertIn(
            "data",
            str(
                runtime_config
                .data_dir()
            ),
        )

        self.assertIn(
            "state",
            str(
                runtime_config
                .state_dir()
            ),
        )

    def test_atomic_save_load(self):
        payload = {
            "setup_complete":
                True,

            "profile_name":
                "Test",
        }

        runtime_config.save_settings(
            payload
        )

        self.assertEqual(
            runtime_config
            .load_settings(),
            payload,
        )

        mode = (
            runtime_config
            .settings_path()
            .stat()
            .st_mode
            & 0o777
        )

        self.assertEqual(
            mode,
            0o600,
        )

    def test_no_secret_written(self):
        payload = {
            "setup_complete":
                True,

            "profile_name":
                "Test",

            "email_enabled":
                False,
        }

        runtime_config.save_settings(
            payload
        )

        text = (
            runtime_config
            .settings_path()
            .read_text(
                encoding="utf-8"
            )
        )

        forbidden = (
            "pass"
            + "word",
            "api"
            + "_key",
            "access"
            + "_token",
        )

        for term in forbidden:
            self.assertNotIn(
                term,
                text.lower(),
            )


if __name__ == "__main__":
    unittest.main()
