import unittest

import mail_dispatch


class MailRuntimePolicyTests(
    unittest.TestCase
):
    def test_time_model_matches_core(self):
        value = (
            mail_dispatch
            ._now()
        )

        self.assertIsNone(
            value.tzinfo
        )

        self.assertEqual(
            value.second,
            0,
        )

        self.assertEqual(
            value.microsecond,
            0,
        )

    def test_batch_and_lease_bounds(self):
        self.assertEqual(
            mail_dispatch
            .LEASE_MINUTES,
            10,
        )

        self.assertEqual(
            mail_dispatch
            .MAX_JOBS_PER_CYCLE,
            5,
        )


if __name__ == "__main__":
    unittest.main()
