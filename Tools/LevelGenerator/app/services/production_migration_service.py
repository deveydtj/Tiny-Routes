from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .production_manifest_service import ProductionManifestService


class ProductionMigrationError(ValueError):
    """Raised before production files are changed when migration invariants fail."""


@dataclass(frozen=True)
class ProductionMigrationResult:
    migrated_level_ids: tuple[str, ...]
    written_paths: tuple[Path, ...]
    manifest_path: Path


class ProductionMigrationService:
    """Apply reviewed level/sidecar replacements as one recoverable transaction."""

    def __init__(self, manifest_service: ProductionManifestService | None = None) -> None:
        self.manifest_service = manifest_service or ProductionManifestService()

    def apply(
        self,
        replacement_levels_dir: Path,
        replacement_solutions_dir: Path,
        levels_dir: Path,
        solutions_dir: Path,
        manifest_path: Path,
        *,
        reviewed_name_changes: Iterable[str] = (),
    ) -> ProductionMigrationResult:
        levels_dir = Path(levels_dir)
        solutions_dir = Path(solutions_dir)
        manifest_path = Path(manifest_path)
        replacement_levels_dir = Path(replacement_levels_dir)
        replacement_solutions_dir = Path(replacement_solutions_dir)
        reviewed_names = set(reviewed_name_changes)

        current_level_paths = self._level_paths(levels_dir)
        replacement_level_paths = self._level_paths(replacement_levels_dir)
        replacement_solution_paths = sorted(replacement_solutions_dir.glob("level_*.solution.json"))
        if not replacement_level_paths:
            raise ProductionMigrationError("No replacement level files were provided")

        current_by_id = self._current_levels(current_level_paths, solutions_dir)
        replacement_ids = tuple(path.stem for path in replacement_level_paths)
        solution_ids = tuple(path.name.removesuffix(".solution.json") for path in replacement_solution_paths)
        if set(replacement_ids) != set(solution_ids):
            missing = sorted(set(replacement_ids) - set(solution_ids))
            extra = sorted(set(solution_ids) - set(replacement_ids))
            raise ProductionMigrationError(
                f"Replacement level/sidecar sets differ (missing sidecars: {missing}; extra sidecars: {extra})"
            )

        changed_names: set[str] = set()
        replacement_payloads: dict[str, tuple[dict, dict]] = {}
        for level_id in replacement_ids:
            if level_id not in current_by_id:
                raise ProductionMigrationError(
                    f"Replacement {level_id} would add or reorder campaign content; only existing IDs may be migrated"
                )
            level_path = replacement_levels_dir / f"{level_id}.json"
            solution_path = replacement_solutions_dir / f"{level_id}.solution.json"
            level_payload = self._read_object(level_path)
            solution_payload = self._read_object(solution_path)
            current_payload = current_by_id[level_id]
            if level_payload.get("id") != level_id:
                raise ProductionMigrationError(
                    f"Replacement filename {level_path.name} must contain id {level_id!r}"
                )
            if solution_payload.get("levelID") != level_id:
                raise ProductionMigrationError(
                    f"Replacement sidecar {solution_path.name} must target {level_id!r}"
                )
            if level_payload.get("name") != current_payload.get("name"):
                changed_names.add(level_id)
            replacement_payloads[level_id] = (level_payload, solution_payload)

        unreviewed_names = changed_names - reviewed_names
        if unreviewed_names:
            raise ProductionMigrationError(
                "Level names changed without explicit review: " + ", ".join(sorted(unreviewed_names))
            )
        unused_reviews = reviewed_names - changed_names
        if unused_reviews:
            raise ProductionMigrationError(
                "Name-change review was supplied for unchanged levels: " + ", ".join(sorted(unused_reviews))
            )

        with tempfile.TemporaryDirectory(prefix="tiny-routes-migration-") as temporary_root:
            stage_root = Path(temporary_root)
            stage_levels = stage_root / "Levels"
            stage_solutions = stage_root / "LevelSolutions"
            shutil.copytree(levels_dir, stage_levels)
            shutil.copytree(solutions_dir, stage_solutions)
            for level_id, (level_payload, solution_payload) in replacement_payloads.items():
                self._write_json(stage_levels / f"{level_id}.json", level_payload)
                self._write_json(stage_solutions / f"{level_id}.solution.json", solution_payload)

            staged_ids = tuple(path.stem for path in self._level_paths(stage_levels))
            current_ids = tuple(path.stem for path in current_level_paths)
            if staged_ids != current_ids:
                raise ProductionMigrationError("Migration changed campaign progression order")

            staged_manifest = stage_root / "production_manifest.json"
            self.manifest_service.rebuild(stage_levels, stage_solutions, staged_manifest)
            manifest_payload = self._read_object(staged_manifest)
            if manifest_payload.get("warnings"):
                raise ProductionMigrationError(
                    "Staged manifest contains warnings: " + "; ".join(manifest_payload["warnings"])
                )
            manifest_ids = tuple(item["levelID"] for item in manifest_payload.get("levels", []))
            if manifest_ids != current_ids:
                raise ProductionMigrationError("Staged manifest does not preserve campaign progression order")

            writes: dict[Path, bytes] = {}
            for level_id in replacement_ids:
                writes[levels_dir / f"{level_id}.json"] = (stage_levels / f"{level_id}.json").read_bytes()
                writes[solutions_dir / f"{level_id}.solution.json"] = (
                    stage_solutions / f"{level_id}.solution.json"
                ).read_bytes()
            writes[manifest_path] = staged_manifest.read_bytes()
            self._commit_transaction(writes)

        return ProductionMigrationResult(
            migrated_level_ids=replacement_ids,
            written_paths=tuple(writes),
            manifest_path=manifest_path,
        )

    def _current_levels(self, level_paths: list[Path], solutions_dir: Path) -> dict[str, dict]:
        if not level_paths:
            raise ProductionMigrationError("Production corpus contains no levels")
        current: dict[str, dict] = {}
        for path in level_paths:
            payload = self._read_object(path)
            level_id = path.stem
            if payload.get("id") != level_id:
                raise ProductionMigrationError(f"Production filename {path.name} does not match its level id")
            if level_id in current:
                raise ProductionMigrationError(f"Duplicate production level id: {level_id}")
            sidecar = solutions_dir / f"{level_id}.solution.json"
            if not sidecar.is_file():
                raise ProductionMigrationError(f"Missing production sidecar for {level_id}: {sidecar}")
            if self._read_object(sidecar).get("levelID") != level_id:
                raise ProductionMigrationError(f"Production sidecar for {level_id} targets another level")
            current[level_id] = payload
        return current

    def _commit_transaction(self, writes: dict[Path, bytes]) -> None:
        staged: dict[Path, Path] = {}
        backups = {path: path.read_bytes() if path.exists() else None for path in writes}
        replaced: list[Path] = []
        try:
            for destination, payload in writes.items():
                destination.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{destination.name}.migration-",
                    dir=destination.parent,
                )
                temporary_path = Path(temporary_name)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                staged[destination] = temporary_path
            for destination, temporary_path in staged.items():
                os.replace(temporary_path, destination)
                replaced.append(destination)
        except Exception:
            for destination in reversed(replaced):
                backup = backups[destination]
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    self._replace_bytes(destination, backup)
            raise
        finally:
            for temporary_path in staged.values():
                temporary_path.unlink(missing_ok=True)

    def _replace_bytes(self, destination: Path, payload: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.rollback-",
            dir=destination.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _level_paths(directory: Path) -> list[Path]:
        return sorted(
            path for path in Path(directory).glob("level_*.json")
            if not path.name.endswith(".solution.json")
        )

    @staticmethod
    def _read_object(path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProductionMigrationError(f"Could not read {path}: {error}") from error
        if not isinstance(payload, dict):
            raise ProductionMigrationError(f"Expected a JSON object in {path}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
