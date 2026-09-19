import unittest

from setup_model import (
    contains_secret_keys,
    normalize_setup,
    validate_setup,
)


def email(
    local: str,
    domain: str,
) -> str:
    return (
        local
        + "@"
        + domain
    )


class SetupModelTests(
    unittest.TestCase
):
    def base(self):
        return normalize_setup(
            {
                "profile_name":
                    "Test Kullanıcısı",

                "language":
                    "tr",

                "default_channel":
                    "pc",

                "email_enabled":
                    False,

                "smtp_provider":
                    "gmail",
            }
        )

    def test_pc_only_is_valid(self):
        payload = self.base()

        self.assertEqual(
            validate_setup(payload),
            [],
        )

    def test_name_required(self):
        payload = self.base()

        payload[
            "profile_name"
        ] = ""

        self.assertTrue(
            validate_setup(payload)
        )

    def test_email_mode_requires_email_setup(self):
        payload = self.base()

        payload[
            "default_channel"
        ] = "email"

        self.assertTrue(
            validate_setup(payload)
        )

    def test_email_configuration_valid(self):
        payload = normalize_setup(
            {
                "profile_name":
                    "Test",

                "language":
                    "en",

                "default_channel":
                    "both",

                "email_enabled":
                    True,

                "smtp_provider":
                    "gmail",

                "mail_from_email":
                    email(
                        "sender",
                        "example.invalid",
                    ),

                "mail_to_email":
                    email(
                        "receiver",
                        "example.invalid",
                    ),
            }
        )

        self.assertEqual(
            validate_setup(payload),
            [],
        )

    def test_invalid_email_rejected(self):
        payload = normalize_setup(
            {
                "profile_name":
                    "Test",

                "language":
                    "tr",

                "default_channel":
                    "email",

                "email_enabled":
                    True,

                "smtp_provider":
                    "gmail",

                "mail_from_email":
                    "invalid",

                "mail_to_email":
                    "invalid",
            }
        )

        self.assertTrue(
            validate_setup(payload)
        )

    def test_secret_keys_rejected(self):
        payload = self.base()

        payload[
            "smtp_"
            + "password"
        ] = "never-store"

        self.assertTrue(
            contains_secret_keys(
                payload
            )
        )

        self.assertTrue(
            validate_setup(payload)
        )


if __name__ == "__main__":
    unittest.main()
