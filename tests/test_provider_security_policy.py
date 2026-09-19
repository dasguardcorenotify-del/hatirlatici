import unittest

import setup_model


class ProviderSecurityPolicyTests(
    unittest.TestCase
):
    def test_password_provider_set(self):
        self.assertEqual(
            setup_model.PROVIDERS,
            {
                "gmail",
                "custom",
            },
        )

    def test_microsoft_password_mode_rejected(self):
        payload = (
            setup_model
            .normalize_setup(
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
                        "outlook",

                    "mail_from_email":
                        (
                            "sender"
                            + "@"
                            + "example.invalid"
                        ),

                    "mail_to_email":
                        (
                            "receiver"
                            + "@"
                            + "example.invalid"
                        ),
                }
            )
        )

        self.assertTrue(
            setup_model
            .validate_setup(
                payload
            )
        )


if __name__ == "__main__":
    unittest.main()
