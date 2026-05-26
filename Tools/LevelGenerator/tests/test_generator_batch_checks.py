from __future__ import annotations

from app.generation_config import GenerationConfig
from app.services.level_generation_service import LevelGenerationService


def test_dry_run_batches_for_each_difficulty_pass_validation(tmp_path) -> None:
    for difficulty in ["tutorial", "easy", "medium", "hard"]:
        result = LevelGenerationService().generate(
            GenerationConfig(
                start_level_number=31,
                count=2,
                difficulty=difficulty,
                template_name="mixed",
                seed=123,
                dry_run=True,
                compare_against_existing=False,
                levels_output_dir=tmp_path / difficulty / "levels",
                solutions_output_dir=tmp_path / difficulty / "solutions",
                report_path=tmp_path / difficulty / "report.md",
                json_report_path=tmp_path / difficulty / "report.json",
                max_attempts_per_level=25,
            )
        )

        assert result.passed is True
        assert len(result.accepted) == 2
        assert result.report_path is not None
        assert result.json_report_path is not None
