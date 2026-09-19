import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('hat_manifest_contract', ROOT / 'tools/manifest_contract.py')
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)

gate_spec = importlib.util.spec_from_file_location(
    'hat_release_gate',
    ROOT / 'packaging/flatpak/release_gate.py',
)
release_gate = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(release_gate)


class ManifestContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.development = mc.read_source(ROOT, mc.DEVEL_NAME).decode()
        for name in mc.FIXED_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        (self.root / mc.DEVEL_NAME).write_text(self.development)
        for subdir in ('ui_v2', 'tools', 'tests'):
            (self.root / subdir).mkdir(exist_ok=True)
            (self.root / subdir / 'fixture.py').write_text('VALUE = 1\n')
        (self.root / 'fixture.py').write_text('VALUE = 2\n')
        self.archive = Path(self.temp.name) / mc.ASSET

    def tearDown(self):
        self.temp.cleanup()

    def write_pair(self, digest='a' * 64):
        content = mc.render_production(self.development, digest)
        (self.root / mc.PRODUCTION_NAME).write_text(content)
        return content

    def publish_fixture(self):
        info = mc.write_archive(self.root, self.archive)
        self.write_pair(info['sha256'])
        return info

    def test_real_recipe_pair_is_synchronized(self):
        self.assertEqual(mc.check_pair(ROOT)['recipe_pair'], 'PASS')

    def test_render_preserves_entire_dependency_recipe(self):
        production = self.write_pair()
        self.assertEqual(mc.check_pair(self.root)['recipe_pair'], 'PASS')
        self.assertNotIn('type: dir', production)
        self.assertIn(mc.RELEASE_URL, production)
        self.assertEqual(production.count('name: qtbase\n'), 1)

    def test_no_claim_of_remote_publication(self):
        self.write_pair()
        status = mc.check_pair(self.root)
        self.assertEqual(status['remote_archive'], 'NOT_CHECKED')
        self.assertEqual(status['compiled_build'], 'NOT_RUN')

    def test_finish_args_parser_is_linear_and_exact(self):
        source = (ROOT / 'packaging/flatpak/release_gate.py').read_text()
        self.assertNotIn('(?ms)^finish-args', source)
        manifest = (
            'id: example\n'
            'finish-args:\n'
            '  # comment\n'
            '  - --share=ipc\n'
            '  - --share=network\n'
            '\n'
            'modules:\n'
            '  - name: app\n'
        )
        self.assertEqual(
            release_gate.finish_args(manifest),
            {'--share=ipc', '--share=network'},
        )

    def test_dependency_version_drift_rejected(self):
        production = self.write_pair()
        (self.root / mc.PRODUCTION_NAME).write_text(production.replace("'25.08'", "'other'", 1))
        with self.assertRaises(mc.ContractError):
            mc.check_pair(self.root)

    def test_permission_drift_rejected(self):
        production = self.write_pair()
        (self.root / mc.PRODUCTION_NAME).write_text(production.replace('--device=dri', '--device=all'))
        with self.assertRaises(mc.ContractError):
            mc.check_pair(self.root)

    def test_build_command_drift_rejected(self):
        production = self.write_pair()
        (self.root / mc.PRODUCTION_NAME).write_text(production.replace('--no-index', '--index-url=invalid', 1))
        with self.assertRaises(mc.ContractError):
            mc.check_pair(self.root)

    def test_missing_license_step_rejected(self):
        production = self.write_pair()
        (self.root / mc.PRODUCTION_NAME).write_text(production.replace('      - install -Dm644 LICENSE ', '      - echo LICENSE ', 1))
        with self.assertRaises(mc.ContractError):
            mc.check_pair(self.root)

    def test_malformed_digest_rejected(self):
        for value in ('', 'abc', 'g' * 64, 'A' * 64, '1' * 65):
            with self.subTest(value=value), self.assertRaises(mc.ContractError):
                mc.render_production(self.development, value)

    def test_wrong_release_destination_rejected(self):
        prod = self.write_pair()
        (self.root / mc.PRODUCTION_NAME).write_text(prod.replace('releases/download/v2.0.0', 'releases/download/latest'))
        with self.assertRaises(mc.ContractError):
            mc.check_pair(self.root)

    def test_wrong_development_tail_rejected(self):
        for altered in (self.development + '# extra\n', self.development.replace('path: .\n', 'path: ../\n')):
            with self.assertRaises(mc.ContractError):
                mc.render_production(altered, 'a' * 64)

    def test_duplicate_application_module_rejected(self):
        text = self.development.replace('  - name: hatirlatici\n', '  - name: hatirlatici\n  - name: hatirlatici\n')
        with self.assertRaises(mc.ContractError):
            mc.render_production(text, 'a' * 64)

    def test_crlf_development_is_not_silently_rewritten(self):
        with self.assertRaises(mc.ContractError):
            mc.render_production(self.development.replace('\n', '\r\n'), 'a' * 64)

    def test_archive_reproducible_across_modes_and_mtimes(self):
        first = mc.archive_bytes(self.root)
        for p in self.root.rglob('*'):
            if p.is_file():
                p.chmod(0o755)
                os.utime(p, (1, 1))
        second = mc.archive_bytes(self.root)
        self.assertEqual(first, second)

    def test_archive_roundtrip_hash_and_source_members(self):
        info = self.publish_fixture()
        result = mc.check_pair(self.root, self.archive)
        self.assertEqual(result['archive']['status'], 'PASS')
        self.assertEqual(result['archive']['sha256'], info['sha256'])
        with tarfile.open(self.archive) as archive:
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual(member.mtime, mc.SOURCE_DATE_EPOCH)
                self.assertEqual(member.mode, 0o755 if member.name.endswith('.sh') else 0o644)

    def test_production_is_excluded_preventing_checksum_cycle(self):
        self.write_pair()
        first = mc.archive_bytes(self.root)
        (self.root / mc.PRODUCTION_NAME).write_text('totally different production')
        self.assertEqual(first, mc.archive_bytes(self.root))

    def test_private_runtime_and_git_are_not_archived(self):
        for rel in ('.git/config', 'settings.json', 'credentials.v1.json', 'data/history.csv', 'logs/run.log', 'data_backups/state.json'):
            p = self.root / rel
            p.parent.mkdir(exist_ok=True)
            p.write_text('private fixture')
        blob = mc.archive_bytes(self.root)
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            names = archive.getnames()
        self.assertFalse(any('credentials.v1.json' in n or n.endswith('settings.json') or '/.git/' in n for n in names))

    def test_source_edit_invalidates_old_archive(self):
        info = self.publish_fixture()
        (self.root / 'fixture.py').write_text('VALUE = 3\n')
        with self.assertRaises(mc.ContractError):
            mc.verify_archive(self.root, self.archive, info['sha256'])

    def test_tampered_archive_digest_is_rejected(self):
        info = self.publish_fixture()
        with self.archive.open('ab') as stream:
            stream.write(b'tamper')
        with self.assertRaises(mc.ContractError):
            mc.verify_archive(self.root, self.archive, info['sha256'])

    def test_missing_fixed_source_is_rejected(self):
        (self.root / 'LICENSE').unlink()
        with self.assertRaises(FileNotFoundError):
            mc.archive_bytes(self.root)

    def test_symlink_file_is_rejected_without_reading_target(self):
        (self.root / 'fixture.py').unlink()
        (self.root / 'fixture.py').symlink_to('/does-not-exist')
        with self.assertRaises(mc.ContractError):
            mc.archive_bytes(self.root)

    def test_symlink_directory_is_rejected(self):
        (self.root / 'tools' / 'other').symlink_to(self.root / 'tests', target_is_directory=True)
        with self.assertRaises(mc.ContractError):
            mc.archive_bytes(self.root)

    def test_hardlink_is_rejected(self):
        os.link(self.root / 'fixture.py', self.root / 'linked.py')
        with self.assertRaises(mc.ContractError):
            mc.archive_bytes(self.root)

    def test_output_is_not_overwritten(self):
        self.archive.write_bytes(b'keep')
        with self.assertRaises(mc.ContractError):
            mc.write_archive(self.root, self.archive)
        self.assertEqual(self.archive.read_bytes(), b'keep')

    def test_output_symlink_is_not_followed(self):
        target = Path(self.temp.name) / 'keep'
        target.write_bytes(b'keep')
        self.archive.symlink_to(target)
        with self.assertRaises(mc.ContractError):
            mc.write_archive(self.root, self.archive)
        self.assertEqual(target.read_bytes(), b'keep')

    def test_changed_source_during_archive_is_rejected(self):
        original = mc.source_map(self.root)
        changed = dict(original, **{'fixture.py': b'change'})
        with mock.patch.object(mc, 'source_map', side_effect=[original, changed]):
            with self.assertRaises(mc.ContractError):
                mc.archive_bytes(self.root)

    def test_source_limit_is_enforced(self):
        with mock.patch.object(mc, 'MAX_TOTAL', 4):
            with self.assertRaises(mc.ContractError):
                mc.archive_bytes(self.root)

    def test_cli_failure_has_nonzero_exit(self):
        (self.root / mc.PRODUCTION_NAME).write_text('broken')
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'tools/manifest_contract.py'), 'check', '--root', str(self.root)], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('MANIFEST_CONTRACT=FAIL', result.stderr)

    def test_cli_archive_does_not_mutate_source(self):
        expected = mc.source_map(self.root)
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'tools/manifest_contract.py'), 'archive', '--root', str(self.root), '--output', str(self.archive)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(mc.source_map(self.root), expected)


if __name__ == '__main__':
    unittest.main()
