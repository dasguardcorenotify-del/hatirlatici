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


class ExtendedParserTests(unittest.TestCase):
    def test_days_later(self):
        result = parse_quick(
            "3 gün sonra aboneliği iptal et",
            now=NOW,
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                8,
                23,
                14,
                0,
            ),
        )

    def test_month_day(self):
        result = parse_quick(
            "ayın 1'inde saat 09:00 kirayı öde",
            now=NOW,
        )

        self.assertEqual(
            result.run_at,
            dt.datetime(
                2026,
                9,
                1,
                9,
                0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
