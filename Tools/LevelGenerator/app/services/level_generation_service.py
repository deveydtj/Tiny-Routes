from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..models.generation_result import GenerationResult
from ..paths import find_repo_root
from ..random_source import RandomSource
from ..repositories.generated_level_repository import GeneratedLevelRepository
from ..repositories.generation_report_repository import GenerationReportRepository
from ..templates.template_registry import TemplateRegistry
from .candidate_rejection_service import CandidateRejectionService
from .difficulty_service import DifficultyService
from .generated_level_validation_service import GeneratedLevelValidationService
from .swift_test_service import SwiftTestService


class LevelGenerationService:
    def __init__(self) -> None:
        self.difficulty_service = DifficultyService()
        self.template_registry = TemplateRegistry()
        self.validation_service = GeneratedLevelValidationService()
        self.generated_level_repository = GeneratedLevelRepository()
        self.report_repository = GenerationReportRepository()

    def generate(self, config: GenerationConfig) -> GenerationResult:
        result = GenerationResult()
        try:
            preset = self.difficulty_service.get_preset(config.difficulty)
            self._validate_template(config.template_name, preset, config)
            self._preflight_output_collisions(config)
        except Exception as exc:
            result.passed = False
            result.messages.append(str(exc))
            self._write_reports(config, result)
            return result

        rejection_service = CandidateRejectionService()
        base_rng = RandomSource(config.base_seed)

        for offset in range(config.count):
            level_number = config.start_level_number + offset
            level_id = format_level_id(level_number)
            accepted_candidate = None

            for attempt in range(config.max_attempts_per_level):
                candidate_seed = base_rng.child_seed(config.difficulty, config.template_name, level_id, attempt)
                rng = RandomSource(candidate_seed)
                try:
                    include_swift_required = config.run_swift_tests or config.dry_run
                    template = self.template_registry.choose(
                        config.template_name,
                        preset,
                        rng,
                        include_swift_required=include_swift_required,
                    )
                    candidate = template.generate(level_id, level_number, preset, rng)
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
                    accepted_candidate = candidate
                    break

                rejection_service.record_rejection(candidate, validation_result, config.debug_failures_dir)

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

    def _validate_template(self, template_name: str, preset, config: GenerationConfig) -> None:
        if template_name not in self.template_registry.valid_names:
            raise ValueError(f"Unknown template: {template_name}")
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
        repo_root = find_repo_root()
        if not self._uses_default_output_dirs(config):
            return []

        project_file = repo_root / "TinyRoutes.xcodeproj" / "project.pbxproj"
        if not project_file.exists():
            return ["TinyRoutes.xcodeproj was not found, so generated resource inclusion could not be checked."]

        project_text = project_file.read_text(encoding="utf-8")
        missing: list[str] = []
        for generated_level in result.accepted:
            for filename in [f"{generated_level.level_id}.json", f"{generated_level.level_id}.solution.json"]:
                if filename not in project_text:
                    missing.append(filename)

        if not missing:
            return []
        return [
            "Generated files are not referenced by TinyRoutes.xcodeproj: "
            f"{', '.join(missing)}. Run `xcodegen generate` before relying on Swift solvability for these files."
        ]
