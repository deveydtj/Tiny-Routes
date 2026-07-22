"""Rollback-safe promotion of one validated production staging workspace."""

from __future__ import annotations

import hashlib
import os
import secrets
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from ..models.production_run_manifest import (
    ProductionRunManifest,
    ProductionTargetSnapshot,
)
from ..paths import find_repo_root
from .level_resource_sync_service import LevelResourceSyncService
from .production_staging_service import ProductionStagingWorkspace


@dataclass(frozen=True)
class TransactionalPromotionResult:
    """Terminal result of a promotion attempt; partial success is impossible."""

    run_id: str
    status: str
    promoted_paths: tuple[Path, ...] = ()
    restored_paths: tuple[Path, ...] = ()
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"completed", "failed_no_changes", "rolled_back"}:
            raise ValueError("unsupported transactional promotion status")
        if self.status == "completed" and self.failure_reason is not None:
            raise ValueError("completed promotion cannot have a failure reason")
        if self.status != "completed" and not self.failure_reason:
            raise ValueError("failed promotion requires a failure reason")

    @property
    def completed(self) -> bool:
        return self.status == "completed"


class TransactionalPromotionService:
    """Promote all staged artifacts, or restore the exact preflight corpus."""

    def __init__(
        self,
        *,
        resource_sync_service: LevelResourceSyncService | None = None,
        resource_updater: Callable[[], object] | None = None,
        lightweight_validator: Callable[[ProductionRunManifest], object] | None = None,
    ) -> None:
        self.resource_sync_service = resource_sync_service or LevelResourceSyncService()
        self.resource_updater = resource_updater
        self.lightweight_validator = lightweight_validator

    def promote(
        self,
        workspace: ProductionStagingWorkspace,
        *,
        lock_path: Path | None = None,
        project_file: Path | None = None,
    ) -> TransactionalPromotionResult:
        if not isinstance(workspace, ProductionStagingWorkspace):
            raise TypeError("workspace must be a ProductionStagingWorkspace")
        workspace.require_path(workspace.root)
        manifest = ProductionRunManifest.read(workspace.run_manifest_path)
        if manifest.run_id != workspace.run_id:
            raise ValueError("production run manifest does not belong to the workspace")
        if manifest.status != "validated":
            raise ValueError("atomic promotion requires a validated run manifest")

        project_path = Path(
            project_file
            or find_repo_root() / "TinyRoutes.xcodeproj" / "project.pbxproj"
        ).resolve(strict=False)
        resolved_lock = Path(lock_path or self._default_lock_path(manifest)).resolve(
            strict=False
        )
        lock_fd: int | None = None
        backup_root = workspace.require_path(workspace.root / "promotion_backup")
        prepared: dict[Path, Path] = {}
        backups: dict[Path, Path | None] = {}
        changed: list[Path] = []
        restored: list[Path] = []

        try:
            lock_fd = self._acquire_lock(resolved_lock, workspace.run_id)
        except Exception as error:
            failed = replace(manifest, status="failed_no_changes")
            failed.write(workspace.run_manifest_path)
            return TransactionalPromotionResult(
                workspace.run_id,
                "failed_no_changes",
                failure_reason=str(error),
            )

        try:
            self._verify_preflight_targets(manifest)
            self._verify_staged_artifacts(workspace, manifest)
            project_snapshot = self._snapshot_for(manifest, project_path)
            if project_snapshot is None:
                raise ValueError(
                    "project file is missing from the production preflight snapshots"
                )

            if backup_root.exists():
                raise FileExistsError(f"Promotion backup already exists: {backup_root}")
            backup_root.mkdir()
            target_paths = [
                Path(artifact.production_path).resolve(strict=False)
                for artifact in manifest.artifacts
                if artifact.production_path is not None
            ]
            all_mutable_paths = tuple(dict.fromkeys((*target_paths, project_path)))
            for index, target in enumerate(all_mutable_paths):
                if target.exists():
                    backup = backup_root / f"{index:04d}.backup"
                    shutil.copy2(target, backup)
                    backups[target] = backup
                else:
                    backups[target] = None

            # Copy every source beside its destination before changing any
            # production file. os.replace then makes each individual move atomic,
            # while the backup set makes the multi-file operation recoverable.
            for artifact in manifest.artifacts:
                if artifact.production_path is None:
                    continue
                source = workspace.require_path(workspace.root / artifact.staged_path)
                target = Path(artifact.production_path).resolve(strict=False)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.parent / (
                    f".{target.name}.{workspace.run_id}.{secrets.token_hex(6)}.promoting"
                )
                shutil.copy2(source, temporary)
                prepared[target] = temporary

            for target, temporary in prepared.items():
                os.replace(temporary, target)
                changed.append(target)

            self._update_project_resources(project_path, manifest)
            if self._digest(project_path) != self._digest(backups[project_path]):
                changed.append(project_path)

            self._lightweight_validate(manifest, project_path)
            shutil.rmtree(backup_root)
            completed = replace(manifest, status="completed")
            completed.write(workspace.run_manifest_path)
            return TransactionalPromotionResult(
                workspace.run_id,
                "completed",
                promoted_paths=tuple(dict.fromkeys(changed)),
            )
        except Exception as error:
            for temporary in prepared.values():
                if temporary.exists():
                    temporary.unlink()
            if backups:
                rollback_errors: list[str] = []
                for target, backup in reversed(tuple(backups.items())):
                    try:
                        if backup is None:
                            if target.exists():
                                target.unlink()
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup, target)
                        restored.append(target)
                    except Exception as rollback_error:  # pragma: no cover
                        rollback_errors.append(f"{target}: {rollback_error}")
                if rollback_errors:
                    raise RuntimeError(
                        "Promotion failed and rollback was incomplete: "
                        + "; ".join(rollback_errors)
                    ) from error
                if backup_root.exists():
                    shutil.rmtree(backup_root)
                rolled_back = replace(manifest, status="rolled_back")
                rolled_back.write(workspace.run_manifest_path)
                return TransactionalPromotionResult(
                    workspace.run_id,
                    "rolled_back",
                    promoted_paths=tuple(dict.fromkeys(changed)),
                    restored_paths=tuple(restored),
                    failure_reason=str(error),
                )

            failed = replace(manifest, status="failed_no_changes")
            failed.write(workspace.run_manifest_path)
            return TransactionalPromotionResult(
                workspace.run_id,
                "failed_no_changes",
                failure_reason=str(error),
            )
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
                try:
                    resolved_lock.unlink()
                except FileNotFoundError:
                    pass

    @staticmethod
    def _acquire_lock(path: Path, run_id: str) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        descriptor = os.open(path, flags, 0o600)
        os.write(descriptor, (run_id + "\n").encode("utf-8"))
        os.fsync(descriptor)
        return descriptor

    @staticmethod
    def _default_lock_path(manifest: ProductionRunManifest) -> Path:
        production_targets = [
            Path(item.production_path)
            for item in manifest.artifacts
            if item.production_path is not None
        ]
        if not production_targets:
            raise ValueError("production run manifest has no promotion targets")
        manifest_artifact = next(
            (
                item
                for item in manifest.artifacts
                if item.kind == "proposed_manifest" and item.production_path is not None
            ),
            None,
        )
        parent = (
            Path(manifest_artifact.production_path).parent
            if manifest_artifact is not None
            else production_targets[0].parent
        )
        return parent / ".tiny_routes_generation.lock"

    def _verify_preflight_targets(self, manifest: ProductionRunManifest) -> None:
        for snapshot in manifest.target_snapshots:
            path = Path(snapshot.path).resolve(strict=False)
            if snapshot.existed:
                if path.is_symlink() or not path.is_file():
                    raise RuntimeError(f"production target changed since preflight: {path}")
                if (
                    path.stat().st_size != snapshot.byte_count
                    or self._digest(path) != snapshot.sha256
                ):
                    raise RuntimeError(f"production target changed since preflight: {path}")
            elif path.exists():
                raise RuntimeError(f"production target appeared after preflight: {path}")

    def _verify_staged_artifacts(
        self,
        workspace: ProductionStagingWorkspace,
        manifest: ProductionRunManifest,
    ) -> None:
        for artifact in manifest.artifacts:
            path = workspace.require_path(workspace.root / artifact.staged_path)
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size != artifact.byte_count
                or self._digest(path) != artifact.sha256
            ):
                raise RuntimeError(
                    f"staged artifact changed after validation: {artifact.staged_path}"
                )

    def _update_project_resources(
        self,
        project_file: Path,
        manifest: ProductionRunManifest,
    ) -> None:
        if self.resource_updater is not None:
            result = self.resource_updater()
            if result is False:
                raise RuntimeError("project resource update failed")
            return

        levels_dir = self._target_parent(manifest, "level")
        solutions_dir = self._target_parent(manifest, "solution")
        before = self.resource_sync_service.check_project_references(
            levels_dir, solutions_dir, project_file=project_file
        )
        if before.errors:
            raise RuntimeError("; ".join(before.errors))
        if before.missing_project_references or before.stale_project_references:
            message = self.resource_sync_service.run_xcodegen()
            if not message.startswith("Regenerated "):
                raise RuntimeError(message)

        after = self.resource_sync_service.check_project_references(
            levels_dir, solutions_dir, project_file=project_file
        )
        if (
            after.errors
            or after.missing_project_references
            or after.stale_project_references
        ):
            details = [
                *after.errors,
                *(
                    f"missing project reference: {item}"
                    for item in after.missing_project_references
                ),
                *(
                    f"stale project reference: {item}"
                    for item in after.stale_project_references
                ),
            ]
            raise RuntimeError("; ".join(details))

    def _lightweight_validate(
        self,
        manifest: ProductionRunManifest,
        project_file: Path,
    ) -> None:
        for artifact in manifest.artifacts:
            if artifact.production_path is None:
                continue
            target = Path(artifact.production_path)
            if (
                not target.is_file()
                or target.stat().st_size != artifact.byte_count
                or self._digest(target) != artifact.sha256
            ):
                raise RuntimeError(f"post-promotion artifact mismatch: {target}")
        if not project_file.is_file():
            raise RuntimeError(f"post-promotion project file missing: {project_file}")
        if self.lightweight_validator is not None:
            result = self.lightweight_validator(manifest)
            if result is False:
                raise RuntimeError("lightweight production-corpus validation failed")

    @staticmethod
    def _target_parent(manifest: ProductionRunManifest, kind: str) -> Path:
        artifact = next(
            (
                item
                for item in manifest.artifacts
                if item.kind == kind and item.production_path is not None
            ),
            None,
        )
        if artifact is None:
            raise ValueError(f"production run manifest has no {kind} target")
        return Path(artifact.production_path).parent

    @staticmethod
    def _snapshot_for(
        manifest: ProductionRunManifest,
        path: Path,
    ) -> ProductionTargetSnapshot | None:
        resolved = str(path.resolve(strict=False))
        return next((item for item in manifest.target_snapshots if item.path == resolved), None)

    @staticmethod
    def _digest(path: Path | None) -> str:
        if path is None:
            return ""
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


# Short alias used by orchestration code and tests.
AtomicPromotionService = TransactionalPromotionService
