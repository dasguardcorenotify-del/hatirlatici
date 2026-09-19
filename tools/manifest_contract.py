#!/usr/bin/env python3
"""One development recipe, a generated immutable-source recipe, and a source archive.

This module does not build, download, install or publish a Flatpak.  A locally
verified source pin is not evidence that the URL has been published.  Production
is excluded from its own archive to avoid a circular checksum dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import tempfile

APP_ID = 'io.github.dasguardcorenotify_del.hatirlatici'
VERSION = '2.0.0'
# Preserve the existing archive-format epoch, not a claim about release date.
SOURCE_DATE_EPOCH = 1787270400
ASSET = f'hatirlatici-{VERSION}.tar.xz'
RELEASE_URL = f'https://github.com/dasguardcorenotify-del/hatirlatici/releases/download/v{VERSION}/{ASSET}'
DEVEL_NAME = APP_ID + '.Devel.yml'
PRODUCTION_NAME = APP_ID + '.yml'
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_MEMBERS = 1000
DEV_TAIL = '    sources:\n      - type: dir\n        path: .\n'
GENERATED_HEADER = (
    '# GENERATED production recipe; do not maintain a second dependency list.\n'
    '# Canonical dependency/build recipe: ' + DEVEL_NAME + '\n'
    '# Regenerate with tools/manifest_contract.py after changing the source.\n'
    '# The archive pin is verified locally; remote publication is a separate gate.\n'
)
FIXED_SOURCES = (
    'assets/hatirlatici.svg',
    'packaging/flatpak/hatirlatici-flatpak-launcher.sh',
    f'packaging/flatpak/{APP_ID}.desktop',
    f'packaging/flatpak/{APP_ID}.metainfo.xml',
    f'packaging/flatpak/{APP_ID}.svg',
    'packaging/flatpak/cargo-sources-cryptography.json',
    'packaging/flatpak/cargo-sources-maturin.json',
    'packaging/flatpak/create-release-source.sh',
    'packaging/flatpak/install-cargo-license-inventory.py',
    DEVEL_NAME, 'LICENSE', 'README.md', 'README_TR.md', 'SECURITY.md',
    'PRIVACY.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'SUPPORT.md',
    'THIRD_PARTY_NOTICES.md',
)


class ContractError(ValueError):
    """A source, path or manifest contract is not satisfied."""


def _root_check(root: Path) -> None:
    if not root.is_absolute():
        raise ContractError('ROOT_MUST_BE_ABSOLUTE')
    if not root.is_dir() or root.is_symlink():
        raise ContractError('ROOT_NOT_REGULAR_DIRECTORY')
    if any(p.is_symlink() for p in root.parents):
        raise ContractError('ROOT_ANCESTOR_SYMLINK')


def read_source(root: Path, relative: str) -> bytes:
    _root_check(root)
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or str(rel) != relative or not rel.parts:
        raise ContractError('UNSAFE_SOURCE_PATH')
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ContractError('SYMLINK_SOURCE')
    fd = os.open(current, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE:
            raise ContractError('SOURCE_TYPE_LINK_OR_SIZE')
        content = handle.read(MAX_FILE + 1)
        final = os.fstat(handle.fileno())
    if len(content) > MAX_FILE or any(getattr(info, key) != getattr(final, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
        raise ContractError('SOURCE_CHANGED_DURING_READ')
    return content


def source_names(root: Path) -> list[str]:
    _root_check(root)
    names = set(FIXED_SOURCES)
    names.update(p.name for p in root.glob('*.py'))
    for directory, suffixes in [('ui_v2', {'.py'}), ('tools', {'.py'}), ('tests', {'.py', '.sh'})]:
        base = root / directory
        if base.is_symlink() or not base.is_dir():
            raise ContractError('SOURCE_DIRECTORY_MISSING_OR_LINK')
        for current, dirs, files in os.walk(base, followlinks=False):
            for dirname in dirs:
                if (Path(current) / dirname).is_symlink():
                    raise ContractError('SOURCE_DIRECTORY_LINK')
            dirs[:] = [x for x in dirs if x != '__pycache__']
            for name in files:
                p = Path(current) / name
                rel = p.relative_to(root)
                if p.suffix in suffixes or (directory == 'tests' and 'fixtures' in rel.parts):
                    names.add(rel.as_posix())
    if len(names) > MAX_MEMBERS:
        raise ContractError('TOO_MANY_SOURCE_FILES')
    return sorted(names)


def source_map(root: Path) -> dict[str, bytes]:
    result = {}
    total = 0
    for rel in source_names(root):
        content = read_source(root, rel)
        total += len(content)
        if total > MAX_TOTAL:
            raise ContractError('SOURCE_SIZE_LIMIT')
        result[rel] = content
    return result


def canonical_mode(relative: str) -> int:
    return 0o755 if relative.endswith('.sh') else 0o644


def archive_bytes(root: Path) -> bytes:
    before = source_map(root)
    output = io.BytesIO()
    with lzma.LZMAFile(output, 'w', format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
            for rel, content in before.items():
                item = tarfile.TarInfo(f'hatirlatici-{VERSION}/{rel}')
                item.size = len(content)
                item.uid = item.gid = 0
                item.uname = item.gname = ''
                item.mtime = SOURCE_DATE_EPOCH
                item.mode = canonical_mode(rel)
                archive.addfile(item, io.BytesIO(content))
    if source_map(root) != before:
        raise ContractError('SOURCE_CHANGED_WHILE_ARCHIVING')
    return output.getvalue()


def write_archive(root: Path, output: Path) -> dict:
    _root_check(output.parent)
    if output.name != ASSET:
        raise ContractError('WRONG_ARCHIVE_NAME')
    if output.exists() or output.is_symlink():
        raise ContractError('OUTPUT_ALREADY_EXISTS_NO_OVERWRITE')
    content = archive_bytes(root)
    temporary = None
    published = False
    try:
        fd, name = tempfile.mkstemp(prefix='.archive-', dir=output.parent)
        temporary = Path(name)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic no-clobber publication; never follow or replace an existing file.
        os.link(temporary, output, follow_symlinks=False)
        published = True
        temporary.unlink()
        temporary = None
        dfd = os.open(output.parent, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if not published:
        raise ContractError('ARCHIVE_NOT_WRITTEN')
    return {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'members': len(source_names(root))}


def development_body(text: str) -> str:
    if '\r' in text:
        raise ContractError('NONCANONICAL_LINE_ENDINGS')
    marker = f'id: {APP_ID}\n'
    if text.count(marker) != 1:
        raise ContractError('DEVELOPMENT_ID_COUNT')
    prefix, body = text.split(marker)
    if any(line.strip() and not line.lstrip().startswith('#') for line in prefix.splitlines()):
        raise ContractError('UNEXPECTED_DEVELOPMENT_HEADER')
    body = marker + body
    if not body.endswith(DEV_TAIL) or body.count(DEV_TAIL) != 1:
        raise ContractError('MAIN_DIRECTORY_SOURCE_NOT_LAST_OR_UNIQUE')
    if body.count('  - name: hatirlatici\n') != 1:
        raise ContractError('MAIN_MODULE_NOT_UNIQUE')
    if body.count('type: dir') != 1:
        raise ContractError('UNEXPECTED_DIRECTORY_SOURCE')
    return body


def render_production(development: str, digest: str) -> str:
    if not re.fullmatch('[0-9a-f]{64}', digest):
        raise ContractError('INVALID_ARCHIVE_DIGEST')
    body = development_body(development)
    return GENERATED_HEADER + body[:-len(DEV_TAIL)] + (
        '    sources:\n      - type: archive\n'
        f'        url: {RELEASE_URL}\n        sha256: {digest}\n'
    )


def production_digest(production: str) -> str:
    pattern = r'    sources:\n      - type: archive\n        url: ' + re.escape(RELEASE_URL) + r'\n        sha256: ([0-9a-f]{64})\n\Z'
    found = re.search(pattern, production)
    if found is None:
        raise ContractError('PRODUCTION_MAIN_SOURCE_CONTRACT')
    return found.group(1)


def check_pair(root: Path, archive: Path | None = None) -> dict:
    development = read_source(root, DEVEL_NAME).decode('utf-8')
    production = read_source(root, PRODUCTION_NAME).decode('utf-8')
    digest = production_digest(production)
    if production != render_production(development, digest):
        raise ContractError('PRODUCTION_DEVELOPMENT_RECIPE_DRIFT')
    report = {'recipe_pair': 'PASS', 'archive_sha256': digest, 'remote_archive': 'NOT_CHECKED', 'compiled_build': 'NOT_RUN'}
    if archive is not None:
        report['archive'] = verify_archive(root, archive, digest)
    return report


def verify_archive(root: Path, path: Path, digest: str) -> dict:
    content = read_source(path.parent, path.name)
    if path.name != ASSET or hashlib.sha256(content).hexdigest() != digest:
        raise ContractError('ARCHIVE_NAME_OR_DIGEST_MISMATCH')
    expected = source_map(root)
    prefix = f'hatirlatici-{VERSION}/'
    names = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(content), mode='r:xz') as archive:
        for member in archive:
            if len(names) >= MAX_MEMBERS or not member.name.startswith(prefix):
                raise ContractError('ARCHIVE_MEMBER_LIMIT_OR_PATH')
            rel = member.name[len(prefix):]
            if rel not in expected or rel in names or not member.isfile():
                raise ContractError('ARCHIVE_UNEXPECTED_DUPLICATE_OR_LINK')
            if (member.uid, member.gid, member.uname, member.gname, member.mtime, member.mode) != (0, 0, '', '', SOURCE_DATE_EPOCH, canonical_mode(rel)):
                raise ContractError('ARCHIVE_NONCANONICAL_METADATA')
            total += member.size
            if member.size != len(expected[rel]) or total > MAX_TOTAL:
                raise ContractError('ARCHIVE_SIZE_MISMATCH')
            stream = archive.extractfile(member)
            if stream is None or stream.read(MAX_FILE + 1) != expected[rel]:
                raise ContractError('ARCHIVE_SOURCE_BYTES_MISMATCH')
            names.add(rel)
    if names != set(expected):
        raise ContractError('ARCHIVE_SOURCE_SET_MISMATCH')
    return {'status': 'PASS', 'members': len(names), 'bytes': len(content), 'sha256': digest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('check', 'archive', 'render'))
    parser.add_argument('--root', type=Path, default=Path(__file__).absolute().parent.parent)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sha256')
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        if args.operation == 'check':
            result = check_pair(root, args.archive.absolute() if args.archive else None)
        elif args.operation == 'archive':
            if args.output is None:
                raise ContractError('OUTPUT_REQUIRED')
            result = write_archive(root, args.output.absolute())
        else:
            if args.sha256 is None:
                raise ContractError('DIGEST_REQUIRED')
            print(render_production(read_source(root, DEVEL_NAME).decode('utf-8'), args.sha256), end='')
            return 0
        print('MANIFEST_CONTRACT=' + json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, tarfile.TarError, lzma.LZMAError) as exc:
        message = str(exc) if isinstance(exc, ContractError) else type(exc).__name__
        print('MANIFEST_CONTRACT=FAIL: ' + message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
