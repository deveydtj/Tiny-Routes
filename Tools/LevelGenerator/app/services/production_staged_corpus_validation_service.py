"""Fail-closed validation of the exact corpus selected for promotion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from tiny_routes_core.models import LevelDocument, Solution
from tiny_routes_core.simulation import RuntimeSimulator

from ..level_editor_imports import (
    LevelValidationService,
    SolutionValidationService,
    ValidationSeverity,
)
from ..models.generated_level import GeneratedLevel
from ..models.production_run_manifest import ProductionRunManifest
from ..paths import find_repo_root
from .candidate_signature_service import CandidateSignatureService
from .level_resource_sync_service import LevelResourceSyncService
from .production_staging_service import ProductionStagingWorkspace
from .static_policy_solver_service import StaticPolicySolverService
from .strategy_search_service import StrategySearchService
from .swift_test_service import SwiftTestService
from .unique_optimal_proof_service import UniqueOptimalProofService
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineResult


@dataclass(frozen=True, order=True)
class StagedCorpusValidationIssue:
    """One stable reason that a staged run cannot be promoted."""

    code: str
    detail: str
    level_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "levelID": self.level_id,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class StagedCorpusValidationResult:
    """Complete staged validation evidence retained before promotion."""

    run_id: str
    validated_level_ids: tuple[str, ...]
    issues: tuple[StagedCorpusValidationIssue, ...]
    swift_passed: bool
    project_resource_sync_passed: bool
    report_path: Path
    manifest: ProductionRunManifest

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "runID": self.run_id,
            "passed": self.passed,
            "validatedLevelIDs": list(self.validated_level_ids),
            "swiftPassed": self.swift_passed,
            "projectResourceSyncPassed": self.project_resource_sync_passed,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class ProductionStagedCorpusValidationService:
    """Validate staged bytes and proofs without reading production level bytes.

    The selected pipeline results are deliberately required. A staged JSON file
    can prove schema and replay correctness, but only the retained V3 pipeline
    evidence can prove that all non-compensating quality gates accepted it.
    """

    def __init__(
        self,
        *,
        level_validation_service: LevelValidationService | None = None,
        solution_validation_service: SolutionValidationService | None = None,
        signature_service: CandidateSignatureService | None = None,
        strategy_search_service: StrategySearchService | None = None,
        unique_optimal_proof_service: UniqueOptimalProofService | None = None,
        static_policy_solver_service: StaticPolicySolverService | None = None,
        resource_sync_service: LevelResourceSyncService | None = None,
    ) -> None:
        self.level_validation_service = (
            level_validation_service or LevelValidationService()
        )
        self.solution_validation_service = (
            solution_validation_service or SolutionValidationService()
        )
        self.signature_service = signature_service or CandidateSignatureService()
        self.strategy_search_service = strategy_search_service or StrategySearchService()
        self.unique_optimal_proof_service = (
            unique_optimal_proof_service or UniqueOptimalProofService()
        )
        self.static_policy_solver_service = (
            static_policy_solver_service or StaticPolicySolverService()
        )
        self.resource_sync_service = resource_sync_service or LevelResourceSyncService()

    def validate(
        self,
        workspace: ProductionStagingWorkspace,
        selected_pipeline_results: Iterable[V3CandidatePipelineResult],
        *,
        repo_root: Path | None = None,
        project_file: Path | None = None,
        run_swift_tests: bool = True,
        swift_timeout_seconds: int = 180,
    ) -> StagedCorpusValidationResult:
        if not isinstance(workspace, ProductionStagingWorkspace):
            raise TypeError("workspace must be a ProductionStagingWorkspace")
        workspace.require_path(workspace.root)
        manifest = ProductionRunManifest.read(workspace.run_manifest_path)
        if manifest.run_id != workspace.run_id:
            raise ValueError("production run manifest does not belong to the workspace")
        if manifest.status != "staged":
            raise ValueError("only a staged production run can be validated")

        pipeline_results = tuple(selected_pipeline_results)
        issues: list[StagedCorpusValidationIssue] = []
        self._validate_artifact_integrity(workspace, manifest, issues)
        self._validate_config_snapshot(workspace, manifest, issues)

        staged_levels = self._load_complete_corpus(workspace, issues)
        selected = self._selected_pipeline_map(pipeline_results, manifest, issues)
        self._validate_selected_candidates(
            staged_levels,
            selected,
            manifest,
            issues,
        )
        self._validate_duplicates(staged_levels, manifest, issues)
        self._validate_proposed_manifest(workspace, staged_levels, issues)

        root = Path(repo_root or find_repo_root()).resolve(strict=False)
        sync_result = self.resource_sync_service.check_project_references(
            workspace.levels_dir,
            workspace.solutions_dir,
            project_file=project_file,
        )
        if sync_result.errors:
            issues.extend(
                StagedCorpusValidationIssue("xcode_resource_sync_failed", detail)
                for detail in sync_result.errors
            )
        if sync_result.missing_project_references:
            issues.append(
                StagedCorpusValidationIssue(
                    "xcode_resource_missing_reference",
                    ", ".join(sync_result.missing_project_references),
                )
            )
        if sync_result.stale_project_references:
            issues.append(
                StagedCorpusValidationIssue(
                    "xcode_resource_stale_reference",
                    ", ".join(sync_result.stale_project_references),
                )
            )
        resource_sync_passed = not any(
            issue.code.startswith("xcode_resource_") for issue in issues
        )

        swift_passed = False
        swift_summary = None
        if run_swift_tests:
            swift_summary = SwiftTestService(
                root,
                timeout_seconds=swift_timeout_seconds,
                level_ids=manifest.requested_level_ids,
                levels_output_dir=workspace.levels_dir,
                solutions_output_dir=workspace.solutions_dir,
            ).run()
            swift_passed = swift_summary.passed is True
            if not swift_passed:
                issues.append(
                    StagedCorpusValidationIssue(
                        "swift_staged_parity_failed",
                        swift_summary.summary,
                    )
                )
        else:
            issues.append(
                StagedCorpusValidationIssue(
                    "swift_staged_parity_not_run",
                    "Production staged-corpus validation requires Swift parity.",
                )
            )

        issues = sorted(set(issues))
        report_path = workspace.require_path(
            workspace.validation_logs_dir / "staged_corpus_validation.json"
        )
        report_payload: dict[str, object] = {
            "runID": workspace.run_id,
            "passed": not issues,
            "validatedLevelIDs": sorted(staged_levels),
            "swiftPassed": swift_passed,
            "projectResourceSyncPassed": resource_sync_passed,
            "issues": [issue.to_dict() for issue in issues],
        }
        if swift_summary is not None:
            report_payload["swift"] = {
                "passed": swift_summary.passed,
                "exitCode": swift_summary.exit_code,
                "summary": swift_summary.summary,
                "command": list(swift_summary.command),
                "environment": dict(swift_summary.environment),
                "failureReasons": list(swift_summary.failure_reasons),
            }
        report_path.write_text(
            json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if not issues:
            manifest = replace(manifest, status="validated")
            manifest.write(workspace.run_manifest_path)

        return StagedCorpusValidationResult(
            run_id=workspace.run_id,
            validated_level_ids=tuple(sorted(staged_levels)),
            issues=tuple(issues),
            swift_passed=swift_passed,
            project_resource_sync_passed=resource_sync_passed,
            report_path=report_path,
            manifest=manifest,
        )

    def _validate_artifact_integrity(
        self,
        workspace: ProductionStagingWorkspace,
        manifest: ProductionRunManifest,
        issues: list[StagedCorpusValidationIssue],
    ) -> None:
        snapshot_paths = {item.path for item in manifest.target_snapshots}
        for artifact in manifest.artifacts:
            path = workspace.require_path(workspace.root / artifact.staged_path)
            if path.is_symlink() or not path.is_file():
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_artifact_missing", artifact.staged_path, artifact.level_id
                    )
                )
                continue
            if path.stat().st_size != artifact.byte_count or self._digest(path) != artifact.sha256:
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_artifact_hash_mismatch",
                        artifact.staged_path,
                        artifact.level_id,
                    )
                )
            if (
                artifact.production_path is not None
                and artifact.production_path not in snapshot_paths
            ):
                issues.append(
                    StagedCorpusValidationIssue(
                        "promotion_target_snapshot_missing",
                        artifact.production_path,
                        artifact.level_id,
                    )
                )

    def _validate_config_snapshot(
        self,
        workspace: ProductionStagingWorkspace,
        manifest: ProductionRunManifest,
        issues: list[StagedCorpusValidationIssue],
    ) -> None:
        if (
            not workspace.seed_config_snapshot_path.is_file()
            or self._digest(workspace.seed_config_snapshot_path)
            != manifest.config_snapshot_sha256
        ):
            issues.append(
                StagedCorpusValidationIssue(
                    "config_snapshot_hash_mismatch",
                    "The staged seed/config snapshot no longer matches the run manifest.",
                )
            )

    def _load_complete_corpus(
        self,
        workspace: ProductionStagingWorkspace,
        issues: list[StagedCorpusValidationIssue],
    ) -> dict[str, GeneratedLevel]:
        level_paths = {
            path.stem: path
            for path in sorted(workspace.levels_dir.glob("level_*.json"))
            if not path.name.endswith(".solution.json")
        }
        solution_paths = {
            path.name[: -len(".solution.json")]: path
            for path in sorted(workspace.solutions_dir.glob("level_*.solution.json"))
        }
        # The Swift test bundle deliberately retains solution sidecars for
        # later, not-yet-shipped campaign levels. A shipped level may never be
        # missing its sidecar, but a solution-only test resource is valid.
        for level_id in sorted(set(level_paths).difference(solution_paths)):
            issues.append(
                StagedCorpusValidationIssue(
                    "staged_level_solution_pair_missing",
                    "A level and solution sidecar must both exist.",
                    level_id,
                )
            )

        result: dict[str, GeneratedLevel] = {}
        for level_id in sorted(set(level_paths).intersection(solution_paths)):
            try:
                level = LevelDocument.from_dict(self._read_object(level_paths[level_id]))
                solution = Solution.from_dict(self._read_object(solution_paths[level_id]))
            except Exception as error:
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_json_schema_invalid", str(error), level_id
                    )
                )
                continue
            if level.id != level_id or solution.levelID != level_id:
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_level_id_mismatch",
                        "Filename, level ID, and solution level ID must match.",
                        level_id,
                    )
                )
                continue
            level_messages = self.level_validation_service.validate(level).messages
            solution_messages = self.solution_validation_service.validate(
                level, solution
            ).messages
            for message in (*level_messages, *solution_messages):
                if message.severity == ValidationSeverity.ERROR:
                    issues.append(
                        StagedCorpusValidationIssue(
                            f"staged_validation:{message.code}",
                            message.message,
                            level_id,
                        )
                    )
            generated = GeneratedLevel(
                level_document=level,
                solution=solution,
                template_name="staged",
                difficulty="staged",
                seed=0,
            )
            replay = RuntimeSimulator().simulate(level, solution.actions)
            if not replay.passed or len(replay.taps) != len(solution.actions):
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_runtime_solution_replay_failed",
                        replay.failure_reason or replay.state.outcome.value,
                        level_id,
                    )
                )
            result[level_id] = generated
        return result

    @staticmethod
    def _selected_pipeline_map(
        pipeline_results: tuple[V3CandidatePipelineResult, ...],
        manifest: ProductionRunManifest,
        issues: list[StagedCorpusValidationIssue],
    ) -> dict[str, V3CandidatePipelineResult]:
        result: dict[str, V3CandidatePipelineResult] = {}
        for pipeline in pipeline_results:
            if not isinstance(pipeline, V3CandidatePipelineResult):
                raise TypeError(
                    "selected_pipeline_results must contain V3CandidatePipelineResult values"
                )
            level_id = pipeline.request.level_id
            if level_id in result:
                issues.append(
                    StagedCorpusValidationIssue(
                        "duplicate_selected_pipeline_evidence",
                        "More than one selected pipeline result was provided.",
                        level_id,
                    )
                )
            result[level_id] = pipeline
        requested = set(manifest.requested_level_ids)
        for level_id in sorted(requested.difference(result)):
            issues.append(
                StagedCorpusValidationIssue(
                    "selected_quality_evidence_missing",
                    "The selected candidate requires its accepted V3 pipeline result.",
                    level_id,
                )
            )
        for level_id in sorted(set(result).difference(requested)):
            issues.append(
                StagedCorpusValidationIssue(
                    "unexpected_selected_pipeline_evidence",
                    "Pipeline evidence does not belong to a requested level.",
                    level_id,
                )
            )
        return result

    def _validate_selected_candidates(
        self,
        staged_levels: dict[str, GeneratedLevel],
        selected: dict[str, V3CandidatePipelineResult],
        manifest: ProductionRunManifest,
        issues: list[StagedCorpusValidationIssue],
    ) -> None:
        records = {item.level_id: item for item in manifest.selected_candidates}
        for level_id in manifest.requested_level_ids:
            staged = staged_levels.get(level_id)
            pipeline = selected.get(level_id)
            if staged is None:
                continue
            record = records[level_id]
            staged.difficulty = record.difficulty
            staged.seed = record.seed
            signature = self.signature_service.signature_for(staged)
            expected_signature = (
                record.topology_hash,
                record.layout_hash,
                record.solution_hash,
                record.structural_behavior_signature,
            )
            actual_signature = (
                signature.topology_hash,
                signature.layout_hash,
                signature.solution_hash,
                signature.structural_behavior_signature,
            )
            if actual_signature != expected_signature:
                issues.append(
                    StagedCorpusValidationIssue(
                        "selected_staged_signature_mismatch",
                        "The staged level/solution is not the candidate selected for promotion.",
                        level_id,
                    )
                )

            if pipeline is None:
                continue
            quality = pipeline.quality_result
            if (
                not pipeline.passed
                or quality is None
                or not quality.ranking_eligible
                or quality.generated_level is None
                or pipeline.request.seed != record.seed
                or pipeline.request.difficulty != record.difficulty
                or quality.generated_level.seed != record.seed
            ):
                issues.append(
                    StagedCorpusValidationIssue(
                        "selected_quality_gate_not_proven",
                        "The retained V3 quality stage is missing, rejected, or stale.",
                        level_id,
                    )
                )
            elif quality.generated_level.candidate_signature is None:
                issues.append(
                    StagedCorpusValidationIssue(
                        "selected_quality_signature_missing",
                        "The accepted quality candidate has no production signature.",
                        level_id,
                    )
                )
            else:
                quality_signature = quality.generated_level.candidate_signature
                if (
                    quality_signature.topology_hash,
                    quality_signature.layout_hash,
                    quality_signature.solution_hash,
                    quality_signature.structural_behavior_signature,
                ) != expected_signature:
                    issues.append(
                        StagedCorpusValidationIssue(
                            "selected_quality_evidence_stale",
                            "Quality evidence belongs to different candidate bytes.",
                            level_id,
                        )
                    )

            search = self.strategy_search_service.search(staged.level_document)
            proof = self.unique_optimal_proof_service.prove(staged.level_document, search)
            if not search.exhaustive or not proof.accepted:
                detail = ", ".join((*search.limit_reasons, *proof.rejection_reasons))
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_exact_strategy_proof_failed",
                        detail or "No accepted exhaustive unique optimum.",
                        level_id,
                    )
                )
            static = self.static_policy_solver_service.solve(staged.level_document)
            if not static.accepted_for_production:
                detail = ", ".join(static.limit_reasons) or (
                    "A permanent switch assignment solves the staged level."
                    if static.static_policy_solvable
                    else "Static-policy proof is incomplete."
                )
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_static_policy_rejection_failed", detail, level_id
                    )
                )

    def _validate_duplicates(
        self,
        staged_levels: dict[str, GeneratedLevel],
        manifest: ProductionRunManifest,
        issues: list[StagedCorpusValidationIssue],
    ) -> None:
        requested = set(manifest.requested_level_ids)
        seen: dict[str, str] = {}
        for level_id, generated in sorted(staged_levels.items()):
            signature = self.signature_service.signature_for(generated)
            key = signature.structural_behavior_signature
            prior = seen.get(key)
            if prior is not None and (prior in requested or level_id in requested):
                issues.append(
                    StagedCorpusValidationIssue(
                        "staged_behavior_duplicate",
                        f"Behavior duplicates {prior}.",
                        level_id,
                    )
                )
            else:
                seen[key] = level_id

    def _validate_proposed_manifest(
        self,
        workspace: ProductionStagingWorkspace,
        staged_levels: dict[str, GeneratedLevel],
        issues: list[StagedCorpusValidationIssue],
    ) -> None:
        try:
            payload = self._read_object(workspace.proposed_manifest_path)
            entries = payload["levels"]
            if not isinstance(entries, list):
                raise TypeError("levels must be an array")
            ids = tuple(item["levelID"] for item in entries)
            if len(ids) != len(set(ids)) or set(ids) != set(staged_levels):
                raise ValueError("manifest levels do not exactly match staged levels")
            warnings = payload.get("warnings", [])
            if warnings:
                raise ValueError("manifest contains load warnings: " + "; ".join(warnings))
        except Exception as error:
            issues.append(
                StagedCorpusValidationIssue(
                    "proposed_manifest_invalid", str(error)
                )
            )

    @staticmethod
    def _read_object(path: Path) -> dict:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("expected a top-level JSON object")
        return payload

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


# Concise compatibility name for callers that do not include the production prefix.
StagedCorpusValidationService = ProductionStagedCorpusValidationService
