import unittest

import l10n


class LocalizationCatalogTests(
    unittest.TestCase
):
    def test_exact_language_set(self):
        self.assertEqual(
            tuple(
                l10n.SUPPORTED_LANGUAGES
            ),
            (
                "tr",
                "en",
                "de",
                "es",
                "ru",
            ),
        )

    def test_every_catalog_is_complete(self):
        reference = set(
            l10n.STRINGS["tr"]
        )

        for language in (
            l10n.SUPPORTED_LANGUAGES
        ):
            self.assertEqual(
                set(
                    l10n.STRINGS[
                        language
                    ]
                ),
                reference,
                language,
            )

    def test_native_language_names(self):
        self.assertEqual(
            l10n.LANGUAGE_NAMES[
                "de"
            ],
            "Deutsch",
        )

        self.assertEqual(
            l10n.LANGUAGE_NAMES[
                "es"
            ],
            "Español",
        )

        self.assertEqual(
            l10n.LANGUAGE_NAMES[
                "ru"
            ],
            "Русский",
        )


if __name__ == "__main__":
    unittest.main()
