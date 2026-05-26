from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..map_import.map_seed_to_template_adapter import MapSeedToTemplateAdapter
from ..map_import.osm_seed_importer import MapSeedGraph
from ..models.generation_result import GenerationResult
from ..paths import find_repo_root, get_default_reports_directory
from ..random_source import RandomSource
from ..repositories.existing_level_repository import ExistingLevelRepository
from ..repositories.generated_level_repository import GeneratedLevelRepository
from ..repositories.generation_report_repository import GenerationReportRepository
from ..templates.template_registry import TemplateRegistry
from .candidate_rejection_service import CandidateRejectionService
from .candidate_signature_service import CandidateSignatureService
from .candidate_uniqueness_service import CandidateUniquenessService
from .difficulty_curve_service import DifficultyCurveService
from .difficulty_service import DifficultyService
from .generated_level_validation_service import GeneratedLevelValidationService
from .generation_quality_service import GenerationQualityService
from .level_resource_sync_service import LevelResourceSyncService
from .swift_test_service import SwiftTestService


class LevelGenerationService:
    def __init__(self) -> None:
        self.difficulty_service = DifficultyService()
        self.difficulty_curve_service = DifficultyCurveService()
        self.template_registry = TemplateRegistry()
        self.validation_service = GeneratedLevelValidationService()
        self.generated_level_repository = GeneratedLevelRepository()
        self.report_repository = GenerationReportRepository()
        self.signature_service = CandidateSignatureService()
        self.existing_level_repository = ExistingLevelRepository(self.signature_service)
        self.uniqueness_service = CandidateUniquenessService()
        self.quality_service = GenerationQualityService()
        self.map_seed_adapter = MapSeedToTemplateAdapter()
        self.resource_sync_service = LevelResourceSyncService()

    def generate(self, config: GenerationConfig) -> GenerationResult:
        result = GenerationResult()
        try:
            batch_plan = self.difficulty_curve_service.build_plan(
                config.start_level_number,
                config.count,
                config.difficulty,
            )
            self._validate_template(config.template_name, config)
            self._preflight_output_collisions(config)
        except Exception as exc:
            result.passed = False
            result.messages.append(str(exc))
            self._write_reports(config, result)
            return result

        rejection_service = CandidateRejectionService()
        base_rng = RandomSource(config.base_seed)
        accepted_signatures = []
        target_level_ids = {
            format_level_id(config.start_level_number + offset)
            for offset in range(config.count)
        }
        existing_signatures = self._load_existing_signatures(config, result, target_level_ids)
        map_seed_graph = self._load_map_seed_graph(config, result)
        if config.map_seed_path is not None and map_seed_graph is None:
            result.passed = False
            self._write_reports(config, result)
            return result

        for offset in range(config.count):
            plan_entry = batch_plan.entries[offset]
            level_number = plan_entry.level_number
            level_id = plan_entry.level_id
            preset = self.difficulty_service.get_preset(plan_entry.difficulty)
            accepted_candidate = None
            candidate_pool = []
            candidate_pool_signatures = []

            for attempt in range(config.max_attempts_per_level):
                candidate_seed = base_rng.child_seed(plan_entry.difficulty, config.template_name, level_id, attempt)
                rng = RandomSource(candidate_seed)
                try:
                    include_swift_required = config.run_swift_tests or config.dry_run
                    template = self.template_registry.choose(
                        config.template_name,
                        preset,
                        rng,
                        include_swift_required=include_swift_required,
                        weights_override=plan_entry.template_weights if config.difficulty == "auto" else None,
                    )
                    candidate = template.generate(level_id, level_number, preset, rng)
                    if map_seed_graph is not None:
                        candidate = self.map_seed_adapter.apply_to_generated_level(map_seed_graph, candidate, rng)
                except Exception as exc:
                    rejection_service.reason_counts["candidate_generation_error"] += 1
                    result.messages.append(f"Rejected candidate {level_id} attempt={attempt}: {exc}")
                    continue

                level_path = self.generated_level_repository.level_path(level_id, config.levels_output_dir)
                solution_path = self.generated_level_repository.solution_path(level_id, config.solutions_output_dir)
                validation_result = self.validation_service.validate(
                    candidate,
                    preset=preset,
                    level_output_path=level_path,
                    solution_output_path=solution_path,
                    overwrite=config.overwrite or config.dry_run,
                )
                if rejection_service.can_save(validation_result):
                    candidate_signature = self.signature_service.signature_for(candidate)
                    duplicate_result = self.uniqueness_service.check_duplicate(
                        candidate_signature,
                        [*accepted_signatures, *candidate_pool_signatures],
                    )
                    if duplicate_result.is_duplicate:
                        message = rejection_service.record_custom_rejection(
                            candidate,
                            "candidate_too_similar_to_batch",
                            duplicate_result.message,
                            config.debug_failures_dir,
                        )
                        result.messages.append(message)
                        continue

                    if config.compare_against_existing:
                        existing_duplicate_result = self.uniqueness_service.check_duplicate(
                            candidate_signature,
                            existing_signatures,
                        )
                        if existing_duplicate_result.is_duplicate:
                            message = rejection_service.record_custom_rejection(
                                candidate,
                                "candidate_too_similar_to_existing",
                                existing_duplicate_result.message,
                                config.debug_failures_dir,
                            )
                            result.messages.append(message)
                            continue

                    candidate.candidate_signature = candidate_signature
                    candidate.quality_score = self.quality_service.score(
                        candidate,
                        preset,
                        [
                            *accepted_signatures,
                            *candidate_pool_signatures,
                            *(existing_signatures if config.compare_against_existing else []),
                        ],
                    )
                    candidate_pool.append(candidate)
                    candidate_pool_signatures.append(candidate_signature)
                    if len(candidate_pool) >= config.candidate_pool_size:
                        break
                    continue

                rejection_service.record_rejection(candidate, validation_result, config.debug_failures_dir)

            if candidate_pool:
                accepted_candidate = max(
                    candidate_pool,
                    key=lambda candidate: candidate.quality_score.total if candidate.quality_score is not None else 0,
                )
                accepted_signatures.append(accepted_candidate.candidate_signature)

            if accepted_candidate is None:
                result.passed = False
                result.messages.append(
                    f"Could not generate valid {level_id} after {config.max_attempts_per_level} attempts."
                )
                break
            result.accepted.append(accepted_candidate)

        result.add_rejections(dict(rejection_service.reason_counts))

        if result.passed and not config.dry_run:
            self._write_generated_files(config, result)
            result.messages.extend(self._sync_xcode_project(config))

        if result.passed and config.run_swift_tests and not config.dry_run:
            result.messages.extend(self._resource_reference_warnings(config, result))
            swift_summary = SwiftTestService(find_repo_root(), timeout_seconds=config.swift_timeout_seconds).run()
            result.swift_test_summary = swift_summary
            if swift_summary.passed is not True:
                result.passed = False
                result.messages.append(swift_summary.summary)

        self._write_reports(config, result)
        return result

    def _validate_template(self, template_name: str, config: GenerationConfig) -> None:
        if template_name not in self.template_registry.valid_names:
            raise ValueError(f"Unknown template: {template_name}")
        if config.difficulty != "auto":
            preset = self.difficulty_service.get_preset(config.difficulty)
        elif template_name != "mixed":
            return
        else:
            return
        if template_name != "mixed":
            include_swift_required = config.run_swift_tests or config.dry_run
            self.template_registry.choose(template_name, preset, RandomSource(config.base_seed), include_swift_required)

    def _preflight_output_collisions(self, config: GenerationConfig) -> None:
        if config.overwrite or config.dry_run:
            return
        collisions: list[Path] = []
        for offset in range(config.count):
            level_id = format_level_id(config.start_level_number + offset)
            for path in [
                self.generated_level_repository.level_path(level_id, config.levels_output_dir),
                self.generated_level_repository.solution_path(level_id, config.solutions_output_dir),
            ]:
                if path.exists():
                    collisions.append(path)
        if collisions:
            formatted = "\n".join(str(path) for path in collisions)
            raise FileExistsError(f"Refusing to overwrite existing output files:\n{formatted}")

    def _load_existing_signatures(
        self,
        config: GenerationConfig,
        result: GenerationResult,
        target_level_ids: set[str],
    ):
        if not config.compare_against_existing:
            return []

        existing_result = self.existing_level_repository.load_existing_levels(
            config.levels_output_dir,
            config.solutions_output_dir,
            get_default_reports_directory() / "production_manifest.json",
        )
        result.messages.extend(existing_result.warnings)
        signatures = [
            signature
            for signature in existing_result.signatures
            if signature.level_id not in target_level_ids
        ]
        if signatures:
            result.messages.append(f"Loaded {len(signatures)} existing level signatures for similarity checks.")
        return signatures

    def _load_map_seed_graph(self, config: GenerationConfig, result: GenerationResult) -> MapSeedGraph | None:
        if config.map_seed_path is None:
            return None
        import json

        try:
            payload = json.loads(config.map_seed_path.read_text(encoding="utf-8"))
            graph_payload = payload.get("simplifiedGraph", payload)
            graph = MapSeedGraph.from_dict(graph_payload)
        except Exception as exc:
            result.messages.append(f"Could not load map seed {config.map_seed_path}: {exc}")
            return None
        result.messages.append(f"Loaded map seed from {config.map_seed_path}.")
        return graph

    def _write_generated_files(self, config: GenerationConfig, result: GenerationResult) -> None:
        for generated_level in result.accepted:
            level_path = self.generated_level_repository.level_path(generated_level.level_id, config.levels_output_dir)
            solution_path = self.generated_level_repository.solution_path(generated_level.level_id, config.solutions_output_dir)
            result.written_level_paths.append(
                self.generated_level_repository.write_level(
                    generated_level.level_document,
                    level_path,
                    overwrite=config.overwrite,
                )
            )
            result.written_solution_paths.append(
                self.generated_level_repository.write_solution(
                    generated_level.solution,
                    solution_path,
                    overwrite=config.overwrite,
                )
            )

    def _sync_xcode_project(self, config: GenerationConfig) -> list[str]:
        if not config.sync_xcode_project:
            return []
        if not self._uses_default_output_dirs(config):
            return []

        repo_root = find_repo_root()
        project_yml = repo_root / "project.yml"
        if not project_yml.exists():
            return ["Skipped xcodegen because project.yml was not found."]
        if shutil.which("xcodegen") is None:
            return ["Skipped xcodegen because the xcodegen command was not found."]

        completed = subprocess.run(
            ["xcodegen", "generate"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return ["Regenerated TinyRoutes.xcodeproj with xcodegen."]

        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit code {completed.returncode}"
        return [f"xcodegen generate failed: {detail}"]

    def _uses_default_output_dirs(self, config: GenerationConfig) -> bool:
        repo_root = find_repo_root()
        try:
            return (
                config.levels_output_dir.resolve() == (repo_root / "TinyRoutes" / "Resources" / "Levels").resolve()
                and config.solutions_output_dir.resolve()
                == (repo_root / "TinyRoutesTests" / "Resources" / "LevelSolutions").resolve()
            )
        except FileNotFoundError:
            return False

    def _write_reports(self, config: GenerationConfig, result: GenerationResult) -> None:
        if config.report_path is not None:
            result.report_path = self.report_repository.write_markdown(config.report_path, config, result)
        if config.json_report_path is not None:
            result.json_report_path = self.report_repository.write_json(config.json_report_path, config, result)

    def _resource_reference_warnings(self, config: GenerationConfig, result: GenerationResult) -> list[str]:
        if not self._uses_default_output_dirs(config):
            return []

        sync_result = self.resource_sync_service.check_project_references(
            config.levels_output_dir,
            config.solutions_output_dir,
        )
        return [*sync_result.errors, *sync_result.warnings]
