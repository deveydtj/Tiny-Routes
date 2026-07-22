"""Write a selected V3 campaign into staging without touching production."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Iterable

from ..models.generated_level import GeneratedLevel
from ..models.production_run_manifest import (
    ProductionArtifact,
    ProductionCandidateRecord,
    ProductionRunManifest,
    ProductionTargetSnapshot,
)
from ..paths import find_repo_root
from ..repositories.generated_level_repository import GeneratedLevelRepository
from .preview_image_service import PreviewImageService
from .production_manifest_service import ProductionManifestService
from .production_staging_service import ProductionStagingWorkspace


class ProductionStagedOutputService:
    """Materialize the complete proposed corpus behind the staging boundary."""

    def __init__(
        self,
        generated_level_repository: GeneratedLevelRepository | None = None,
        production_manifest_service: ProductionManifestService | None = None,
        preview_image_service: PreviewImageService | None = None,
    ) -> None:
        self.generated_level_repository = (
            generated_level_repository or GeneratedLevelRepository()
        )
        self.production_manifest_service = (
            production_manifest_service or ProductionManifestService()
        )
        self.preview_image_service = preview_image_service or PreviewImageService()

    def write_selected_candidates(
        self,
        workspace: ProductionStagingWorkspace,
        selected_candidates: Iterable[GeneratedLevel],
        *,
        production_levels_dir: Path,
        production_solutions_dir: Path,
        production_manifest_path: Path,
        production_project_file: Path | None = None,
    ) -> ProductionRunManifest:
        """Stage a full corpus overlay and publish its integrity manifest last."""

        if not isinstance(workspace, ProductionStagingWorkspace):
            raise TypeError("workspace must be a ProductionStagingWorkspace")
        candidates = tuple(selected_candidates)
        if not candidates:
            raise ValueError("selected_candidates cannot be empty")
        if any(not isinstance(candidate, GeneratedLevel) for candidate in candidates):
            raise TypeError("selected_candidates must contain GeneratedLevel values")
        level_ids = tuple(candidate.level_id for candidate in candidates)
        if len(level_ids) != len(set(level_ids)):
            raise ValueError("selected candidate level IDs must be unique")
        for candidate in candidates:
            if candidate.candidate_signature is None:
                raise ValueError(
                    f"selected candidate {candidate.level_id} requires a complete signature"
                )

        production_levels_dir = Path(production_levels_dir).resolve(strict=False)
        production_solutions_dir = Path(production_solutions_dir).resolve(strict=False)
        production_manifest_path = Path(production_manifest_path).resolve(strict=False)
        production_project_file = Path(
            production_project_file
            or find_repo_root() / "TinyRoutes.xcodeproj" / "project.pbxproj"
        ).resolve(strict=False)
        self._require_clean_workspace(workspace)
        snapshot = self._read_seed_snapshot(workspace)

        artifacts: list[ProductionArtifact] = []
        target_paths: list[Path] = []
        try:
            self._copy_json_corpus(production_levels_dir, workspace.levels_dir)
            self._copy_json_corpus(production_solutions_dir, workspace.solutions_dir)

            for candidate in candidates:
                level_path = workspace.require_path(
                    self.generated_level_repository.level_path(
                        candidate.level_id,
                        workspace.levels_dir,
                    )
                )
                solution_path = workspace.require_path(
                    self.generated_level_repository.solution_path(
                        candidate.level_id,
                        workspace.solutions_dir,
                    )
                )
                level_target = self.generated_level_repository.level_path(
                    candidate.level_id,
                    production_levels_dir,
                ).resolve(strict=False)
                solution_target = self.generated_level_repository.solution_path(
                    candidate.level_id,
                    production_solutions_dir,
                ).resolve(strict=False)
                self.generated_level_repository.write_level(
                    candidate.level_document,
                    level_path,
                    overwrite=True,
                )
                self.generated_level_repository.write_solution(
                    candidate.solution,
                    solution_path,
                    overwrite=True,
                )
                artifacts.extend(
                    (
                        self._artifact(
                            workspace,
                            level_path,
                            kind="level",
                            production_path=level_target,
                            level_id=candidate.level_id,
                        ),
                        self._artifact(
                            workspace,
                            solution_path,
                            kind="solution",
                            production_path=solution_target,
                            level_id=candidate.level_id,
                        ),
                    )
                )
                target_paths.extend((level_target, solution_target))

                preview_path = workspace.require_path(
                    self.preview_image_service.write_preview(
                        candidate,
                        workspace.previews_dir,
                    )
                )
                preview_target = (
                    production_manifest_path.parent / "previews" / preview_path.name
                ).resolve(strict=False)
                artifacts.append(
                    self._artifact(
                        workspace,
                        preview_path,
                        kind="preview",
                        production_path=preview_target,
                        level_id=candidate.level_id,
                    )
                )
                target_paths.append(preview_target)

            proposed_manifest_path = workspace.require_path(
                workspace.proposed_manifest_path
            )
            self.production_manifest_service.rebuild(
                workspace.levels_dir,
                workspace.solutions_dir,
                proposed_manifest_path,
            )
            artifacts.append(
                self._artifact(
                    workspace,
                    proposed_manifest_path,
                    kind="proposed_manifest",
                    production_path=production_manifest_path,
                )
            )
            target_paths.append(production_manifest_path)

            # The project file is a derived production target. Atomic promotion
            # may regenerate it after moving resources, so its preflight state
            # must be protected by the same optimistic-concurrency check.
            target_paths.append(production_project_file)

            snapshot_path = workspace.require_path(workspace.seed_config_snapshot_path)
            artifacts.append(
                self._artifact(
                    workspace,
                    snapshot_path,
                    kind="seed_config_snapshot",
                )
            )
            manifest = ProductionRunManifest(
                run_id=workspace.run_id,
                status="staged",
                generator_architecture="production_v3",
                generator_architecture_version=3,
                seed=snapshot["seed"],
                config_snapshot_sha256=self._file_digest(snapshot_path),
                requested_level_ids=level_ids,
                selected_candidates=tuple(
                    self._candidate_record(candidate) for candidate in candidates
                ),
                artifacts=tuple(artifacts),
                target_snapshots=tuple(
                    self._target_snapshot(path)
                    for path in self._deduplicated_paths(target_paths)
                ),
            )
            workspace.require_path(manifest.write(workspace.run_manifest_path))
            return manifest
        except Exception:
            # An incomplete stage must never look promotable. Keep the workspace
            # for diagnostics, but ensure no stale run manifest can authorize it.
            if workspace.run_manifest_path.exists():
                workspace.run_manifest_path.unlink()
            raise

    def write_report(
        self,
        workspace: ProductionStagingWorkspace,
        filename: str,
        content: str | bytes,
    ) -> Path:
        """Write later report evidence through the same containment boundary."""

        safe_name = self._safe_filename(filename)
        path = workspace.require_path(workspace.reports_dir / safe_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            raise TypeError("report content must be text or bytes")
        return path

    def write_validation_log(
        self,
        workspace: ProductionStagingWorkspace,
        filename: str,
        content: str | bytes,
    ) -> Path:
        """Write validation evidence without accepting an external path."""

        safe_name = self._safe_filename(filename)
        path = workspace.require_path(workspace.validation_logs_dir / safe_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            raise TypeError("validation log content must be text or bytes")
        return path

    def _require_clean_workspace(self, workspace: ProductionStagingWorkspace) -> None:
        workspace.require_path(workspace.root)
        if workspace.run_manifest_path.exists():
            raise FileExistsError(
                f"Production run manifest already exists: {workspace.run_manifest_path}"
            )
        for directory in (
            workspace.levels_dir,
            workspace.solutions_dir,
            workspace.previews_dir,
        ):
            workspace.require_path(directory)
            if not directory.is_dir():
                raise FileNotFoundError(f"Staging directory is missing: {directory}")
            if any(directory.iterdir()):
                raise FileExistsError(f"Staging directory is not empty: {directory}")
        if workspace.proposed_manifest_path.exists():
            raise FileExistsError(
                f"Proposed manifest already exists: {workspace.proposed_manifest_path}"
            )

    @staticmethod
    def _copy_json_corpus(source: Path, destination: Path) -> None:
        if not source.exists():
            return
        if not source.is_dir():
            raise NotADirectoryError(f"Production corpus path is not a directory: {source}")
        for path in sorted(source.glob("*.json"), key=lambda item: item.name):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Production corpus entries must be regular files: {path}")
            shutil.copyfile(path, destination / path.name)

    @staticmethod
    def _read_seed_snapshot(workspace: ProductionStagingWorkspace) -> dict:
        payload = json.loads(
            workspace.seed_config_snapshot_path.read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            raise ValueError("seed/config snapshot must be a JSON object")
        if payload.get("runID") != workspace.run_id:
            raise ValueError("seed/config snapshot run ID does not match workspace")
        seed = payload.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed/config snapshot requires an integer seed")
        configuration = payload.get("configuration")
        if not isinstance(configuration, dict):
            raise ValueError("seed/config snapshot requires a configuration object")
        architecture = configuration.get("generatorArchitecture") or configuration.get("mode")
        if architecture != "production_v3":
            raise ValueError("staged production output requires production_v3 configuration")
        return payload

    @staticmethod
    def _candidate_record(candidate: GeneratedLevel) -> ProductionCandidateRecord:
        signature = candidate.candidate_signature
        assert signature is not None
        return ProductionCandidateRecord(
            level_id=candidate.level_id,
            difficulty=candidate.difficulty,
            seed=candidate.seed,
            candidate_id=f"{candidate.level_id}:{candidate.seed}",
            topology_hash=signature.topology_hash,
            layout_hash=signature.layout_hash,
            solution_hash=signature.solution_hash,
            structural_behavior_signature=signature.structural_behavior_signature,
        )

    @classmethod
    def _artifact(
        cls,
        workspace: ProductionStagingWorkspace,
        path: Path,
        *,
        kind: str,
        production_path: Path | None = None,
        level_id: str | None = None,
    ) -> ProductionArtifact:
        staged_path = workspace.require_path(path)
        relative_path = staged_path.relative_to(workspace.root).as_posix()
        return ProductionArtifact(
            kind=kind,
            staged_path=relative_path,
            production_path=(
                str(production_path.resolve(strict=False))
                if production_path is not None
                else None
            ),
            level_id=level_id,
            sha256=cls._file_digest(staged_path),
            byte_count=staged_path.stat().st_size,
        )

    @classmethod
    def _target_snapshot(cls, path: Path) -> ProductionTargetSnapshot:
        resolved = path.resolve(strict=False)
        if not resolved.exists():
            return ProductionTargetSnapshot(path=str(resolved), existed=False)
        if resolved.is_symlink() or not resolved.is_file():
            raise ValueError(f"Production target must be a regular file: {resolved}")
        return ProductionTargetSnapshot(
            path=str(resolved),
            existed=True,
            sha256=cls._file_digest(resolved),
            byte_count=resolved.stat().st_size,
        )

    @staticmethod
    def _file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _deduplicated_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
        result: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            resolved = path.resolve(strict=False)
            key = str(resolved)
            if key not in seen:
                seen.add(key)
                result.append(resolved)
        return tuple(result)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename cannot be empty")
        path = Path(filename)
        if path.name != filename or filename in {".", ".."}:
            raise ValueError("filename must be a single path component")
        return filename
