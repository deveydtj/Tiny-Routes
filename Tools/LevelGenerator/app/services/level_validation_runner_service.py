from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..level_editor_imports import LevelDocument, SolutionModel
from ..models.generated_level import GeneratedLevel
from ..models.generation_result import SwiftTestSummary
from ..paths import find_repo_root
from ..repositories.generated_level_repository import GeneratedLevelRepository
from .difficulty_service import DifficultyService
from .generated_level_validation_service import GeneratedLevelValidationService
from .swift_test_service import SwiftTestService


@dataclass(frozen=True)
class ExistingLevelValidationConfig:
    level_ids: list[str]
    difficulty: str | None
    run_swift_tests: bool
    levels_output_dir: Path
    solutions_output_dir: Path
    swift_timeout_seconds: int = 180


@dataclass
class ExistingLevelValidationResult:
    passed: bool = True
    validated_level_ids: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    swift_summary: SwiftTestSummary = field(default_factory=SwiftTestSummary)


class LevelValidationRunnerService:
    def __init__(
        self,
        *,
        repository: GeneratedLevelRepository | None = None,
        validation_service: GeneratedLevelValidationService | None = None,
        difficulty_service: DifficultyService | None = None,
    ) -> None:
        self.repository = repository or GeneratedLevelRepository()
        self.validation_service = validation_service or GeneratedLevelValidationService()
        self.difficulty_service = difficulty_service or DifficultyService()

    def validate_existing_levels(self, config: ExistingLevelValidationConfig) -> ExistingLevelValidationResult:
        preset = self.difficulty_service.get_preset(config.difficulty) if config.difficulty else None
        result = ExistingLevelValidationResult()

        for raw_level_id in config.level_ids:
            level_id = normalize_level_id(raw_level_id)
            level_path = self.repository.level_path(level_id, config.levels_output_dir)
            solution_path = self.repository.solution_path(level_id, config.solutions_output_dir)
            try:
                level = LevelDocument.from_dict(json.loads(level_path.read_text(encoding="utf-8")))
                solution = SolutionModel.from_dict(json.loads(solution_path.read_text(encoding="utf-8")))
            except Exception as exc:
                result.failures.append(f"{level_id}: could not load level/solution files: {exc}")
                continue

            generated = GeneratedLevel(
                level_document=level,
                solution=solution,
                template_name="existing",
                difficulty=config.difficulty or "unspecified",
                seed=0,
            )
            validation_result = self.validation_service.validate(
                generated,
                preset=preset,
                overwrite=True,
                enforce_difficulty=preset is not None,
            )
            if validation_result.has_errors:
                details = ", ".join(
                    message.code for message in validation_result.messages if message.severity == "error"
                )
                result.failures.append(f"{level_id}: validation failed ({details})")
            else:
                result.validated_level_ids.append(level_id)

        if config.run_swift_tests and not result.failures:
            result.swift_summary = SwiftTestService(
                find_repo_root(),
                timeout_seconds=config.swift_timeout_seconds,
                level_ids=tuple(result.validated_level_ids),
                levels_output_dir=config.levels_output_dir,
                solutions_output_dir=config.solutions_output_dir,
            ).run()
            if result.swift_summary.passed is not True:
                result.failures.append(result.swift_summary.summary)

        result.passed = not result.failures
        return result


def normalize_level_id(value: str) -> str:
    path = Path(value)
    name = path.name
    if name.endswith(".solution.json"):
        name = name[: -len(".solution.json")]
    elif name.endswith(".json"):
        name = name[: -len(".json")]
    return name
