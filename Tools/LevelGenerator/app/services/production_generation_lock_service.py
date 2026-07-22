"""Exclusive, ownership-safe filesystem lock for production generation."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class GenerationLockError(RuntimeError):
    """Raised when a production generation lock cannot be acquired or released."""


class GenerationLockOwnershipError(GenerationLockError):
    """Raised when a lease no longer owns the lock path it acquired."""


@dataclass
class ProductionGenerationLock:
    """One held lock lease.

    The inode and random token are both checked before release. A process can
    therefore never remove a lock that replaced its own lease while it was
    running.
    """

    path: Path
    run_id: str
    owner_token: str
    descriptor: int
    device: int
    inode: int
    _released: bool = field(default=False, init=False, repr=False)

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> None:
        if self._released:
            return

        ownership_error: GenerationLockOwnershipError | None = None
        try:
            try:
                current_stat = self.path.lstat()
            except OSError:
                ownership_error = GenerationLockOwnershipError(
                    f"generation lock ownership was lost before release: {self.path}"
                )
            else:
                owned_inode = (
                    current_stat.st_dev == self.device
                    and current_stat.st_ino == self.inode
                )
                if not owned_inode:
                    ownership_error = GenerationLockOwnershipError(
                        f"generation lock ownership changed before release: {self.path}"
                    )
                else:
                    try:
                        payload = json.loads(self.path.read_text(encoding="utf-8"))
                    except (OSError, ValueError, TypeError):
                        ownership_error = GenerationLockOwnershipError(
                            f"generation lock metadata changed before release: {self.path}"
                        )
                    else:
                        owned_token = (
                            payload.get("runID") == self.run_id
                            and payload.get("ownerToken") == self.owner_token
                        )
                        if not owned_token:
                            ownership_error = GenerationLockOwnershipError(
                                f"generation lock ownership changed before release: {self.path}"
                            )
                        else:
                            self.path.unlink()
        finally:
            os.close(self.descriptor)
            self._released = True

        if ownership_error is not None:
            raise ownership_error

    def __enter__(self) -> ProductionGenerationLock:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.release()
        return False


class ProductionGenerationLockService:
    """Acquire a non-waiting exclusive lock for one production run."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._token_factory = token_factory or (lambda: secrets.token_hex(16))

    def acquire(self, path: Path, run_id: str) -> ProductionGenerationLock:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")

        lock_path = Path(path).resolve(strict=False)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        token = self._token_factory()
        acquired_at = self._clock()
        if acquired_at.tzinfo is None:
            raise ValueError("generation lock clock must return a timezone-aware value")
        payload = {
            "acquiredAtUTC": acquired_at.astimezone(timezone.utc).isoformat(),
            "ownerToken": token,
            "pid": os.getpid(),
            "runID": run_id,
        }
        serialized = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")

        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except FileExistsError as error:
            owner = self._describe_owner(lock_path)
            raise GenerationLockError(
                f"production generation is already locked{owner}: {lock_path}"
            ) from error
        except OSError as error:
            raise GenerationLockError(
                f"could not acquire production generation lock {lock_path}: {error}"
            ) from error

        lock_stat = os.fstat(descriptor)
        lease = ProductionGenerationLock(
            path=lock_path,
            run_id=run_id,
            owner_token=token,
            descriptor=descriptor,
            device=lock_stat.st_dev,
            inode=lock_stat.st_ino,
        )
        try:
            self._write_all(descriptor, serialized)
            os.fsync(descriptor)
        except BaseException:
            self._discard_failed_acquisition(lease)
            raise
        return lease

    @staticmethod
    def _discard_failed_acquisition(lease: ProductionGenerationLock) -> None:
        """Remove an incompletely written lock only when its inode is still ours."""

        try:
            try:
                current_stat = lease.path.lstat()
            except OSError:
                return
            if (
                current_stat.st_dev == lease.device
                and current_stat.st_ino == lease.inode
            ):
                lease.path.unlink()
        finally:
            os.close(lease.descriptor)
            lease._released = True

    @staticmethod
    def _write_all(descriptor: int, payload: bytes) -> None:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("generation lock metadata write made no progress")
            offset += written

    @staticmethod
    def _describe_owner(path: Path) -> str:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ""
        run_id = payload.get("runID")
        pid = payload.get("pid")
        acquired_at = payload.get("acquiredAtUTC")
        details = []
        if isinstance(run_id, str):
            details.append(f"run {run_id}")
        if isinstance(pid, int):
            details.append(f"pid {pid}")
        if isinstance(acquired_at, str):
            details.append(f"since {acquired_at}")
        return " by " + ", ".join(details) if details else ""
