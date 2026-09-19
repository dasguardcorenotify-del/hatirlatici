import unittest
from unittest import mock

import background_portal


class BackgroundPortalTests(
    unittest.TestCase
):
    def test_option_model(self):
        options = (
            background_portal
            .build_options(
                reason=(
                    "Hatırlatmalar için"
                ),
                autostart=True,
                handle_token=(
                    "hatirlatici_test"
                ),
            )
        )

        self.assertEqual(
            options[
                "handle_token"
            ],
            "hatirlatici_test",
        )

        self.assertTrue(
            options[
                "autostart"
            ]
        )

        self.assertEqual(
            options[
                "reason"
            ],
            "Hatırlatmalar için",
        )

    def test_host_request_is_fail_closed(self):
        with mock.patch.object(
            background_portal,
            "is_flatpak",
            return_value=False,
        ):
            with self.assertRaises(
                background_portal
                .BackgroundPortalRequiresFlatpak
            ):
                (
                    background_portal
                    .request_background(
                        reason="Test",
                        autostart=True,
                    )
                )

    def test_result_success(self):
        result = (
            background_portal
            .BackgroundResult(
                response=0,
                background=True,
                autostart=True,
                handle="/request/test",
            )
        )

        self.assertTrue(
            result.success
        )


if __name__ == "__main__":
    unittest.main()
