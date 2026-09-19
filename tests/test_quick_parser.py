import datetime as dt
import unittest

from quick_parser import parse_quick


NOW = dt.datetime(
    2026,
    8,
    20,
    14,
    0,
)


class ParserTests(unittest.TestCase):
    def test_minutes(self):
        result = parse_quick(
            "30 dakika sonra çayı kontrol et",
            now=NOW,
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                8,
                20,
                14,
                30,
            ),
        )

    def test_tomorrow(self):
        result = parse_quick(
            "yarın saat 9'da Ahmet'i ara",
            now=NOW,
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                8,
                21,
                9,
                0,
            ),
        )

    def test_every_friday(self):
        result = parse_quick(
            "her cuma 14:00 raporu gönder",
            now=NOW,
        )

        self.assertEqual(
            result.repeat,
            "weekly",
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                8,
                21,
                14,
                0,
            ),
        )

    def test_daily(self):
        result = parse_quick(
            "her gün 08:30 ilacı al",
            now=NOW,
        )

        self.assertEqual(
            result.repeat,
            "daily",
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                8,
                21,
                8,
                30,
            ),
        )

    def test_translated_visible_tomorrow_examples(self):
        examples = (
            ("call Alex tomorrow at 9", "call Alex"),
            ("Alex morgen um 9 anrufen", "Alex anrufen"),
            ("llamar a Alex mañana a las 9", "llamar a Alex"),
            ("позвонить Алексу завтра в 9", "позвонить Алексу"),
        )

        for phrase, subject in examples:
            with self.subTest(phrase=phrase):
                result = parse_quick(phrase, now=NOW)
                self.assertIsNotNone(result)
                self.assertEqual(result.subject, subject)
                self.assertEqual(
                    result.run_at,
                    dt.datetime(2026, 8, 21, 9, 0),
                )

    def test_translated_visible_relative_examples(self):
        examples = (
            ("Check the tea in 30 minutes", "Check the tea"),
            ("In 30 Minuten nach dem Tee sehen", "nach dem Tee sehen"),
            ("Comprobar el té dentro de 30 minutos", "Comprobar el té"),
            ("Проверить чай через 30 минут", "Проверить чай"),
        )

        for phrase, subject in examples:
            with self.subTest(phrase=phrase):
                result = parse_quick(phrase, now=NOW)
                self.assertIsNotNone(result)
                self.assertEqual(result.subject, subject)
                self.assertEqual(
                    result.run_at,
                    dt.datetime(2026, 8, 20, 14, 30),
                )

    def test_translated_daily_and_weekly_recurrence(self):
        examples = (
            ("every Friday at 14:00 send report", "weekly", 21),
            ("jeden Freitag um 14:00 Bericht senden", "weekly", 21),
            ("cada viernes a las 14:00 enviar informe", "weekly", 21),
            ("каждую пятницу в 14:00 отправить отчёт", "weekly", 21),
            ("every day at 08:30 take medicine", "daily", 21),
            ("jeden Tag um 08:30 Medizin nehmen", "daily", 21),
            ("cada día a las 08:30 tomar medicina", "daily", 21),
            ("каждый день в 08:30 принять лекарство", "daily", 21),
        )

        for phrase, repeat, day in examples:
            with self.subTest(phrase=phrase):
                result = parse_quick(phrase, now=NOW)
                self.assertIsNotNone(result)
                self.assertEqual(result.repeat, repeat)
                self.assertEqual(result.run_at.day, day)

    def test_invalid_clock_is_a_normal_parse_failure(self):
        for phrase in (
            "yarın saat 24'te ara",
            "call Alex tomorrow at 24",
            "Alex morgen um 24 anrufen",
            "llamar a Alex mañana a las 24",
            "позвонить Алексу завтра в 24",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(
                    parse_quick(
                        phrase,
                        now=NOW,
                    )
                )

    def test_unbounded_relative_value_is_a_normal_parse_failure(self):
        self.assertIsNone(
            parse_quick(
                "Check tea in 999999999999999999999999 days",
                now=NOW,
            )
        )

    def test_punctuation_only_subject_is_not_a_turkish_fallback(self):
        self.assertIsNone(
            parse_quick(
                "... in 1 hour",
                now=NOW,
            )
        )


if __name__ == "__main__":
    unittest.main()
