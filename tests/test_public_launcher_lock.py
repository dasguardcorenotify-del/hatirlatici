import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


import app_identity
import public_launcher


class PublicLauncherLockTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        self.old_state = os.environ.get(
            "XDG_STATE_HOME"
        )

        os.environ[
            "XDG_STATE_HOME"
        ] = str(
            Path(self.temp.name)
            / "state"
        )

    def tearDown(self):
        if self.old_state is None:
            os.environ.pop(
                "XDG_STATE_HOME",
                None,
            )
        else:
            os.environ[
                "XDG_STATE_HOME"
            ] = self.old_state

        self.temp.cleanup()

    def test_namespace_is_derived_from_permanent_app_id(
        self,
    ):
        self.assertTrue(
            public_launcher
            .ONBOARDING_LOCK_NAMESPACE
            .startswith(
                app_identity.APP_ID
            )
        )

        self.assertIn(
            app_identity.APP_ID,
            public_launcher
            .onboarding_lock_path()
            .name,
        )

        self.assertEqual(
            public_launcher
            .owner_lock_path()
            .name,
            app_identity
            .SINGLE_INSTANCE_OWNER_LOCK,
        )

    def test_second_onboarding_owner_is_rejected(
        self,
    ):
        with (
            public_launcher
            .try_onboarding_lock()
        ) as first:
            self.assertTrue(first)

            with (
                public_launcher
                .try_onboarding_lock()
            ) as second:
                self.assertFalse(
                    second
                )

        self.assertEqual(
            public_launcher
            .onboarding_lock_path()
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )

    def test_contending_setup_does_not_spawn_second_dialog(
        self,
    ):
        with (
            public_launcher
            .try_onboarding_lock()
        ) as acquired:
            self.assertTrue(
                acquired
            )

            with mock.patch.object(
                public_launcher,
                "run_setup",
            ) as run_setup:
                second, rc = (
                    public_launcher
                    .run_setup_exclusive(
                        force=True
                    )
                )

        self.assertFalse(second)
        self.assertEqual(rc, 0)
        run_setup.assert_not_called()

    def test_state_is_rechecked_after_lock_acquisition(
        self,
    ):
        with (
            mock.patch.object(
                public_launcher,
                "setup_complete",
                return_value=True,
            ),
            mock.patch.object(
                public_launcher,
                "run_setup",
            ) as run_setup,
        ):
            acquired, rc = (
                public_launcher
                .run_setup_exclusive(
                    force=False
                )
            )

        self.assertTrue(acquired)
        self.assertEqual(rc, 0)
        run_setup.assert_not_called()

    def test_running_application_blocks_forced_reconfiguration(
        self,
    ):
        with (
            public_launcher
            .try_owner_coordination_lock()
        ) as owner:
            self.assertTrue(owner)

            with mock.patch.object(
                public_launcher,
                "run_setup",
            ) as run_setup:
                acquired, rc = (
                    public_launcher
                    .run_setup_exclusive(
                        force=True
                    )
                )

        self.assertFalse(acquired)
        self.assertEqual(rc, 12)
        run_setup.assert_not_called()

        self.assertEqual(
            public_launcher
            .owner_lock_path()
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )


if __name__ == "__main__":
    unittest.main()
