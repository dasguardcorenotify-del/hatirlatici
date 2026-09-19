import unittest
from pathlib import Path

from transport_policy_support import transport_references


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class MailTransportPolicyTests(
    unittest.TestCase
):
    def test_legacy_mail_binary_absent(self):
        hits = transport_references(ROOT, "m" + "smtp")
        self.assertEqual(hits, [], hits)

    def test_obsolete_mail_stack_absent(self):
        for rel in (
            "hatirlat_locked.sh",
            "mail_post_harden.py",
            "sync_mail_history.py",
        ):
            self.assertFalse(
                (
                    ROOT
                    / rel
                ).exists(),
                rel,
            )

    def test_native_stack_present(self):
        for rel in (
            "smtp_transport.py",
            "mail_dispatch.py",
            "mail_scheduler.py",
        ):
            self.assertTrue(
                (
                    ROOT
                    / rel
                ).is_file(),
                rel,
            )


if __name__ == "__main__":
    unittest.main()
