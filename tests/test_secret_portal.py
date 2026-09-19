import unittest
from unittest import mock

import secret_portal


class FakeConnection:
    def get_unique_name(
        self,
    ):
        return ":1.234"


class SecretPortalTests(
    unittest.TestCase
):
    def test_options_with_token(self):
        value = (
            secret_portal
            .build_options(
                handle_token=(
                    "hatirlatici_test"
                ),
                previous_token=(
                    "opaque"
                ),
            )
        )

        self.assertEqual(
            value[
                "handle_token"
            ],
            "hatirlatici_test",
        )

        self.assertEqual(
            value[
                "token"
            ],
            "opaque",
        )

    def test_expected_request_path(self):
        value = (
            secret_portal
            ._expected_request_path(
                FakeConnection(),
                "abc123",
            )
        )

        self.assertEqual(
            value,
            (
                "/org/freedesktop/portal/"
                "desktop/request/"
                "1_234/abc123"
            ),
        )

    def test_host_retrieve_fails_closed(self):
        with mock.patch.object(
            secret_portal,
            "is_flatpak",
            return_value=False,
        ):
            with self.assertRaises(
                secret_portal
                .SecretPortalRequiresFlatpak
            ):
                (
                    secret_portal
                    .retrieve_secret()
                )


if __name__ == "__main__":
    unittest.main()
