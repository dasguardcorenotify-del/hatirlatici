"""Negative and positive fixtures keep documentation filtering honest."""
from pathlib import Path
import tempfile
import unittest
from transport_policy_support import transport_references


class TransportPolicyScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.token = "notify" + "-" + "send"

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_release_note_prose_is_not_a_runtime_dependency(self):
        self.put("docs/RELEASE_NOTES.md", "No " + self.token + " dependency")
        self.assertEqual(transport_references(self.root, self.token), [])

    def test_python_comments_and_module_docstrings_are_not_commands(self):
        self.put("entry.py", '"""Removed ' + self.token + '."""\n# ' + self.token + '\nx=1\n')
        self.assertEqual(transport_references(self.root, self.token), [])

    def test_runtime_literal_is_detected(self):
        self.put("ui_v2/sender.py", "import subprocess\nsubprocess.run([" + repr(self.token) + ", 'test'])\n")
        self.assertEqual(transport_references(self.root, self.token), ["ui_v2/sender.py"])

    def test_constant_concatenation_is_detected(self):
        self.put("entry.py", "command='notify' + '-' + 'send'\n")
        self.assertEqual(transport_references(self.root, self.token), ["entry.py"])

    def test_mail_runtime_reference_is_detected(self):
        token = "m" + "smtp"
        self.put("sender.py", "command='m' + 'smtp'\n")
        self.assertEqual(transport_references(self.root, token), ["sender.py"])

    def test_shell_launcher_is_scanned(self):
        self.put("run.sh", "#!/bin/sh\nexec " + self.token + " test\n")
        self.assertEqual(transport_references(self.root, self.token), ["run.sh"])

    def test_packaging_dependency_is_scanned(self):
        self.put("packaging/manifest.yml", "modules:\n  - name: " + self.token + "\n")
        self.assertEqual(transport_references(self.root, self.token), ["packaging/manifest.yml"])

    def test_tool_script_is_scanned(self):
        self.put("tools/send.py", "command=" + repr(self.token) + "\n")
        self.assertEqual(transport_references(self.root, self.token), ["tools/send.py"])

    def test_malformed_python_is_not_silently_ignored(self):
        self.put("entry.py", "def incomplete(\n")
        with self.assertRaises(SyntaxError):
            transport_references(self.root, self.token)


if __name__ == "__main__":
    unittest.main()
