import unittest
from unittest import mock

import l10n
import portal_notifications as portal


class PortalNotificationTests(
    unittest.TestCase
):
    def test_id_is_sanitized(self):
        value = portal.sanitize_id(
            "pair / 12:34"
        )

        self.assertEqual(
            value,
            "pair-12-34",
        )

    def test_action_spec(self):
        spec = portal.build_spec(
            "Başlık",
            "Gövde",
            action_buttons=True,
        )

        self.assertEqual(
            spec["category"],
            "alarm.ringing",
        )

        buttons = spec[
            "buttons"
        ]

        self.assertEqual(
            len(buttons),
            2,
        )

        self.assertEqual(
            buttons[0]["action"],
            "complete",
        )

        self.assertEqual(
            buttons[1]["action"],
            "snooze",
        )

    def test_non_action_test_notification(self):
        spec = portal.build_spec(
            "Başlık",
            "Gövde",
            action_buttons=False,
        )

        self.assertNotIn(
            "buttons",
            spec,
        )

    def test_action_labels_are_localized_for_every_locale(
        self,
    ):
        for language in (
            l10n.SUPPORTED_LANGUAGES
        ):
            with self.subTest(
                language=language
            ):
                spec = portal.build_spec(
                    "Title",
                    "Body",
                    action_buttons=True,
                    language=language,
                    snooze_minutes=25,
                )

                buttons = spec[
                    "buttons"
                ]

                self.assertEqual(
                    buttons[0][
                        "label"
                    ],
                    l10n.text(
                        "notification_complete",
                        language,
                    ),
                )

                self.assertEqual(
                    buttons[1][
                        "label"
                    ],
                    l10n.text(
                        "notification_snooze_minutes",
                        language,
                        minutes=25,
                    ),
                )

    def test_saved_language_is_default(self):
        with mock.patch.object(
            portal.runtime_config,
            "load_settings",
            return_value={
                "language": "de",
            },
        ):
            spec = portal.build_spec(
                "Title",
                "Body",
            )

        self.assertEqual(
            spec["buttons"][0]["label"],
            l10n.text(
                "notification_complete",
                "de",
            ),
        )

    def test_selftest_notification_uses_saved_language(
        self,
    ):
        for language in (
            l10n.SUPPORTED_LANGUAGES
        ):
            with self.subTest(
                language=language
            ):
                with (
                    mock.patch.object(
                        portal,
                        "portal_version",
                        return_value=2,
                    ),
                    mock.patch.object(
                        portal,
                        "_current_language",
                        return_value=language,
                    ),
                    mock.patch.object(
                        portal,
                        "add_notification",
                    ) as add,
                    mock.patch.object(
                        portal,
                        "remove_notification",
                    ),
                ):
                    self.assertEqual(
                        portal.selftest(),
                        0,
                    )

                self.assertEqual(
                    add.call_args.args[1:3],
                    (
                        l10n.text(
                            "portal_test_title",
                            language,
                        ),
                        l10n.text(
                            "portal_test_message",
                            language,
                        ),
                    ),
                )
                self.assertEqual(
                    add.call_args.kwargs[
                        "language"
                    ],
                    language,
                )

    def test_manual_action_notification_uses_saved_language(
        self,
    ):
        for language in (
            l10n.SUPPORTED_LANGUAGES
        ):
            with self.subTest(
                language=language
            ):
                with (
                    mock.patch.object(
                        portal,
                        "_current_language",
                        return_value=language,
                    ),
                    mock.patch.object(
                        portal,
                        "notify_and_wait",
                        return_value=(
                            portal
                            .ACTION_COMPLETE
                        ),
                    ) as notify,
                ):
                    self.assertEqual(
                        portal
                        .manual_action_test(),
                        0,
                    )

                self.assertEqual(
                    notify.call_args.args[1:3],
                    (
                        l10n.text(
                            "portal_action_test_title",
                            language,
                        ),
                        l10n.text(
                            "portal_action_test_message",
                            language,
                        ),
                    ),
                )
                self.assertEqual(
                    notify.call_args.kwargs[
                        "language"
                    ],
                    language,
                )

    def test_portal_variant_build(self):
        spec = portal.build_spec(
            "Başlık",
            "Gövde",
            action_buttons=True,
        )

        payload = (
            portal
            ._to_portal_vardict(
                spec
            )
        )

        self.assertIn(
            "title",
            payload,
        )

        self.assertIn(
            "buttons",
            payload,
        )

        self.assertEqual(
            payload[
                "buttons"
            ].get_type_string(),
            "aa{sv}",
        )


if __name__ == "__main__":
    unittest.main()
