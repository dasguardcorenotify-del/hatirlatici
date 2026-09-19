import unittest
from pathlib import Path

from transport_policy_support import transport_references


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class NotificationTransportPolicyTests(
    unittest.TestCase
):
    def test_legacy_notification_transport_absent(self):
        hits = transport_references(ROOT, "notify" + "-" + "send")
        self.assertEqual(hits, [], hits)

    def test_portal_transport_exists(
        self,
    ):
        self.assertTrue(
            (
                ROOT
                / "portal_notifications.py"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
