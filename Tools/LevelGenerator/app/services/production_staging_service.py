"""Create isolated filesystem workspaces for transactional production runs."""

from __future__ import annotations

import json
import re
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..paths import get_default_production_staging_directory


_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


@dataclass(frozen=True)
class ProductionStagingWorkspace:
    """All filesystem targets owned by one unpromoted production run."""

    run_id: str
    root: Path
    levels_dir: Path
    solutions_dir: Path
    previews_dir: Path
    reports_dir: Path
    validation_logs_dir: Path
    proposed_manifest_path: Path
    run_manifest_path: Path
    seed_config_snapshot_path: Path

    def contains(self, path: Path) -> bool:
        candidate = Path(path).resolve(strict=False)
        return candidate == self.root or self.root in candidate.parents

    def require_path(self, path: Path) -> Path:
        candidate = Path(path).resolve(strict=False)
        if not self.contains(candidate):
            raise ValueError(
                f"Path is outside production staging workspace {self.run_id}: {candidate}"
            )
        return candidate

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "runID": self.run_id,
            "root": str(self.root),
            "levelsDirectory": str(self.levels_dir),
            "solutionsDirectory": str(self.solutions_dir),
            "previewsDirectory": str(self.previews_dir),
            "reportsDirectory": str(self.reports_dir),
            "validationLogsDirectory": str(self.validation_logs_dir),
            "proposedManifestPath": str(self.proposed_manifest_path),
            "runManifestPath": str(self.run_manifest_path),
            "seedConfigSnapshotPath": str(self.seed_config_snapshot_path),
        }


class ProductionStagingService:
    """Allocate a complete staging tree without overwriting prior run evidence."""

    _DIRECTORIES = (
        "levels",
        "solutions",
        "previews",
        "reports",
        "validation_logs",
    )

    def __init__(self, staging_root: Path | None = None) -> None:
        self.staging_root = Path(
            staging_root or get_default_production_staging_directory()
        ).resolve(strict=False)

    def create_workspace(
        self,
        run_id: str,
        *,
        seed: int,
        config_snapshot: Mapping[str, Any],
    ) -> ProductionStagingWorkspace:
        normalized_run_id = self._validate_run_id(run_id)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("production staging seed must be an integer")
        if not isinstance(config_snapshot, Mapping):
            raise TypeError("config_snapshot must be a mapping")

        snapshot_payload = {
            "runID": normalized_run_id,
            "seed": seed,
            "configuration": dict(config_snapshot),
        }
        serialized_snapshot = json.dumps(
            snapshot_payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"

        self.staging_root.mkdir(parents=True, exist_ok=True)
        final_root = (self.staging_root / normalized_run_id).resolve(strict=False)
        self._require_child(final_root)
        if final_root.exists():
            raise FileExistsError(
                f"Production staging workspace already exists: {final_root}"
            )

        temporary_root = (
            self.staging_root
            / f".{normalized_run_id}.{secrets.token_hex(8)}.creating"
        ).resolve(strict=False)
        self._require_child(temporary_root)
        try:
            temporary_root.mkdir(parents=False, exist_ok=False)
            for directory_name in self._DIRECTORIES:
                (temporary_root / directory_name).mkdir()
            (temporary_root / "seed_config_snapshot.json").write_text(
                serialized_snapshot,
                encoding="utf-8",
            )
            temporary_root.replace(final_root)
        except Exception:
            if temporary_root.exists():
                shutil.rmtree(temporary_root)
            raise

        return self._workspace(normalized_run_id, final_root)

    def open_workspace(self, run_id: str) -> ProductionStagingWorkspace:
        normalized_run_id = self._validate_run_id(run_id)
        root = (self.staging_root / normalized_run_id).resolve(strict=False)
        self._require_child(root)
        workspace = self._workspace(normalized_run_id, root)
        missing = [
            path
            for path in (
                workspace.levels_dir,
                workspace.solutions_dir,
                workspace.previews_dir,
                workspace.reports_dir,
                workspace.validation_logs_dir,
                workspace.seed_config_snapshot_path,
            )
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError(
                "Production staging workspace is missing required paths: "
                + ", ".join(str(path) for path in missing)
            )
        return workspace

    def _workspace(self, run_id: str, root: Path) -> ProductionStagingWorkspace:
        return ProductionStagingWorkspace(
            run_id=run_id,
            root=root,
            levels_dir=root / "levels",
            solutions_dir=root / "solutions",
            previews_dir=root / "previews",
            reports_dir=root / "reports",
            validation_logs_dir=root / "validation_logs",
            proposed_manifest_path=root / "proposed_manifest.json",
            run_manifest_path=root / "production_run_manifest.json",
            seed_config_snapshot_path=root / "seed_config_snapshot.json",
        )

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError(
                "run_id must be 1-128 characters using only letters, digits, '.', "
                "'_', or '-', and must begin with a letter or digit"
            )
        if run_id in {".", ".."}:
            raise ValueError("run_id cannot be '.' or '..'")
        return run_id

    def _require_child(self, path: Path) -> None:
        if path.parent != self.staging_root:
            raise ValueError(f"Staging workspace escaped its configured root: {path}")
