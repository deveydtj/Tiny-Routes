from __future__ import annotations

from app.generation_config import GenerationConfig
from app.services.generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult
from app.services.level_generation_service import LevelGenerationService
from app.services.level_validation_runner_service import (
    ExistingLevelValidationConfig,
    LevelValidationRunnerService,
    normalize_level_id,
)


def test_validation_runner_validates_written_level(tmp_path) -> None:
    _write_level(tmp_path)

    result = LevelValidationRunnerService().validate_existing_levels(_validation_config(tmp_path))

    assert result.passed is True
    assert result.validated_level_ids == ["level_012"]


def test_validation_runner_reports_missing_level_file(tmp_path) -> None:
    result = LevelValidationRunnerService().validate_existing_levels(_validation_config(tmp_path))

    assert result.passed is False
    assert "level_012: could not load level/solution files" in result.failures[0]


def test_validation_runner_reports_validation_failure(tmp_path) -> None:
    _write_level(tmp_path)
    service = LevelValidationRunnerService(validation_service=FakeFailingValidationService())

    result = service.validate_existing_levels(_validation_config(tmp_path))

    assert result.passed is False
    assert result.failures == ["level_012: validation failed (forced_failure)"]


def test_normalize_level_id_strips_paths_and_suffixes() -> None:
    assert normalize_level_id("/tmp/level_012.solution.json") == "level_012"
    assert normalize_level_id("level_013.json") == "level_013"


class FakeFailingValidationService:
    def validate(self, *args, **kwargs) -> GeneratorValidationResult:
        return GeneratorValidationResult(
            [GeneratorValidationMessage(severity="error", code="forced_failure", message="forced")]
        )


def _validation_config(tmp_path) -> ExistingLevelValidationConfig:
    return ExistingLevelValidationConfig(
        level_ids=["level_012"],
        difficulty=None,
        run_swift_tests=False,
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
    )


def _write_level(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=12,
            count=1,
            difficulty="tutorial",
            template_name="straight_delivery",
            seed=1,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    )
    assert result.passed is True
