from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from app.services.production_generation_lock_service import (
    GenerationLockError,
    GenerationLockOwnershipError,
    ProductionGenerationLockService,
)


def _service() -> ProductionGenerationLockService:
    return ProductionGenerationLockService(
        clock=lambda: datetime(2026, 7, 21, 18, 30, tzinfo=timezone.utc),
        token_factory=lambda: "fixed-owner-token",
    )


def test_lock_records_owner_and_blocks_a_concurrent_run(tmp_path) -> None:
    lock_path = tmp_path / "production" / ".tiny_routes_generation.lock"
    first = _service().acquire(lock_path, "run-first")

    assert json.loads(lock_path.read_text(encoding="utf-8")) == {
        "acquiredAtUTC": "2026-07-21T18:30:00+00:00",
        "ownerToken": "fixed-owner-token",
        "pid": os.getpid(),
        "runID": "run-first",
    }
    with pytest.raises(GenerationLockError, match="run run-first"):
        _service().acquire(lock_path, "run-second")

    first.release()
    assert not lock_path.exists()


def test_context_manager_releases_lock_after_failure(tmp_path) -> None:
    lock_path = tmp_path / ".generation.lock"

    with pytest.raises(RuntimeError, match="simulated generation failure"):
        with _service().acquire(lock_path, "run-context"):
            raise RuntimeError("simulated generation failure")

    assert not lock_path.exists()
    with _service().acquire(lock_path, "run-next") as next_lock:
        assert next_lock.released is False
    assert next_lock.released is True


def test_release_never_unlinks_a_replacement_lock(tmp_path) -> None:
    lock_path = tmp_path / ".generation.lock"
    lease = _service().acquire(lock_path, "run-original")
    lock_path.unlink()
    replacement = {
        "acquiredAtUTC": "2026-07-21T18:31:00+00:00",
        "ownerToken": "replacement-token",
        "pid": 999,
        "runID": "run-replacement",
    }
    lock_path.write_text(json.dumps(replacement) + "\n", encoding="utf-8")

    with pytest.raises(GenerationLockOwnershipError, match="ownership changed"):
        lease.release()

    assert json.loads(lock_path.read_text(encoding="utf-8")) == replacement
    assert lease.released is True


def test_invalid_owner_metadata_still_fails_closed(tmp_path) -> None:
    lock_path = tmp_path / ".generation.lock"
    lock_path.write_text("not json\n", encoding="utf-8")

    with pytest.raises(GenerationLockError, match="already locked"):
        _service().acquire(lock_path, "run-blocked")

    assert lock_path.read_text(encoding="utf-8") == "not json\n"
