"""No real vault access: these tests use disposable synthetic ciphertext bytes."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import runtime_config
import setup_persistence


class SetupPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "config" / "hatirlatici"
        self.root.mkdir(parents=True, mode=0o700)
        patch = mock.patch.object(runtime_config, "config_dir", return_value=self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def put(self, name, value):
        path = self.root / name
        path.write_bytes(value)
        path.chmod(0o600)
        return path

    def test_success_keeps_new_files(self):
        with setup_persistence.protect_setup_files():
            self.put("settings.json", b'{"new": true}')
        self.assertEqual((self.root / "settings.json").read_bytes(), b'{"new": true}')

    def test_failed_save_restores_all_existing_bytes(self):
        values = {name: ("synthetic prior " + name).encode() for name in setup_persistence._NAMES}
        for name, data in values.items():
            self.put(name, data)
        with self.assertRaisesRegex(OSError, "synthetic"):
            with setup_persistence.protect_setup_files():
                for name in values:
                    self.put(name, b"synthetic replacement")
                raise OSError("synthetic")
        for name, data in values.items():
            path = self.root / name
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(self.root.glob(".setup-rollback-*")))

    def test_failed_save_removes_only_new_configuration_files(self):
        unrelated = self.put("untouched.txt", b"keep")
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                for name in setup_persistence._NAMES:
                    self.put(name, b"synthetic")
                raise OSError("synthetic")
        self.assertTrue(unrelated.exists())
        self.assertTrue(all(not (self.root / name).exists() for name in setup_persistence._NAMES))

    def test_failed_delete_restores_ciphertext(self):
        path = self.put("credentials.v1.json", b"synthetic ciphertext")
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                path.unlink()
                raise OSError("synthetic")
        self.assertEqual(path.read_bytes(), b"synthetic ciphertext")

    def test_snapshot_symlink_is_rejected_without_touching_target(self):
        other = Path(self.temp.name) / "external"
        other.write_bytes(b"safe")
        (self.root / "credentials.v1.json").symlink_to(other)
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                self.fail("Must not enter save")
        self.assertEqual(other.read_bytes(), b"safe")

    def test_hardlinked_snapshot_is_rejected(self):
        path = self.put("settings.json", b"prior")
        os.link(path, self.root / "alias")
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                self.fail("Must not enter save")

    def test_oversized_snapshot_is_rejected(self):
        self.put("settings.json", b"x" * (setup_persistence._MAX_BYTES + 1))
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                self.fail("Must not enter save")

    def test_failed_restoration_is_explicit_and_sanitized(self):
        with mock.patch.object(setup_persistence, "_restore", side_effect=OSError("sensitive details")):
            with self.assertRaises(setup_persistence.SetupRollbackError) as error:
                with setup_persistence.protect_setup_files():
                    raise OSError("sensitive details")
        self.assertEqual(str(error.exception), "SETUP_ROLLBACK_FAILED")
        self.assertIsNone(error.exception.__cause__)
        self.assertTrue(error.exception.__suppress_context__)

    def test_duplicate_save_lock_does_not_wait_forever(self):
        with setup_persistence.protect_setup_files():
            with self.assertRaises(BlockingIOError):
                with setup_persistence.protect_setup_files():
                    self.fail("Must not enter second save")

    def test_lock_is_released_after_error(self):
        with self.assertRaises(OSError):
            with setup_persistence.protect_setup_files():
                raise OSError("synthetic")
        with setup_persistence.protect_setup_files():
            self.put("settings.json", b"retry")
        self.assertEqual((self.root / ".setup-save.lock").stat().st_mode & 0o777, 0o600)

    def test_keyboard_interrupt_also_rolls_back(self):
        path = self.put("settings.json", b"before")
        with self.assertRaises(KeyboardInterrupt):
            with setup_persistence.protect_setup_files():
                self.put("settings.json", b"after")
                raise KeyboardInterrupt()
        self.assertEqual(path.read_bytes(), b"before")


if __name__ == "__main__":
    unittest.main()
