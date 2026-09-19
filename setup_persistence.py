"""In-process rollback for the three first-run configuration files.

Only encrypted credential bytes are snapshotted; no credential is decrypted.
This protects handled save exceptions, not power-loss or SIGKILL recovery.
The caller must hold the application's onboarding/reconfiguration ownership.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
import tempfile
from typing import Iterator

import runtime_config


class SetupRollbackError(OSError):
    """A save failed and at least one original file could not be restored."""


_NAMES = ("settings.json", "credentials.v1.json", "secret-portal.v1.json")
_MAX_BYTES = 256 * 1024


def _private_root() -> Path:
    root = runtime_config.config_dir()
    if not root.is_absolute():
        raise OSError("SETUP_CONFIG_PATH_INVALID")
    for item in (root, *root.parents):
        if item.is_symlink():
            raise OSError("SETUP_CONFIG_SYMLINK")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise OSError("SETUP_CONFIG_OWNER_OR_MODE")
    return root


def _read(path: Path) -> bytes | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1:
            raise OSError("SETUP_CONFIG_FILE_TYPE")
        if before.st_size > _MAX_BYTES:
            raise OSError("SETUP_CONFIG_FILE_LIMIT")
        data = handle.read(_MAX_BYTES + 1)
        after = os.fstat(handle.fileno())
    if len(data) > _MAX_BYTES or (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise OSError("SETUP_CONFIG_FILE_CHANGED")
    return data


def _restore(path: Path, data: bytes | None) -> None:
    if _read(path) == data:
        return
    if data is None:
        path.unlink(missing_ok=True)
        return
    fd, temporary = tempfile.mkstemp(prefix=".setup-rollback-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def protect_setup_files() -> Iterator[None]:
    """Restore prior configuration bytes if the enclosed save raises.

Serializes cooperating first-run saves. The lock is not a general runtime
settings lock, and is intentionally not presented as crash-atomic storage.
"""
    root = _private_root()
    fd = os.open(root / ".setup-save.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise OSError("SETUP_SAVE_LOCK_INVALID")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = {name: _read(root / name) for name in _NAMES}
        try:
            yield
        except BaseException:
            failed = False
            for name, data in before.items():
                try:
                    _restore(root / name, data)
                except OSError:
                    failed = True
            if failed:
                raise SetupRollbackError("SETUP_ROLLBACK_FAILED") from None
            raise
    finally:
        os.close(fd)
