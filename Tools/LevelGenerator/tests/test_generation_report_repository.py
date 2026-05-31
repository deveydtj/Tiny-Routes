from __future__ import annotations

import json

from app.generation_config import GenerationConfig
from app.repositories.generation_report_repository import GenerationReportRepository
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.level_generation_service import LevelGenerationService
from app.random_source import RandomSource
from app.templates.single_switch_template import SingleSwitchTemplate


def test_generation_report_repository_writes_markdown_and_json(tmp_path) -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="tutorial",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [],
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": [],
        },
    )()
    repository = GenerationReportRepository()

    repository.write_markdown(config.report_path, config, result)
    repository.write_json(config.json_report_path, config, result)

    assert "Tiny Routes Generation Report" in config.report_path.read_text(encoding="utf-8")
    assert json.loads(config.json_report_path.read_text(encoding="utf-8"))["difficulty"] == "tutorial"


def test_generation_report_repository_writes_candidate_signatures(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [generated],
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": [],
        },
    )()

    GenerationReportRepository().write_markdown(config.report_path, config, result)
    GenerationReportRepository().write_json(config.json_report_path, config, result)

    payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    signature = payload["acceptedLevels"][0]["signature"]
    assert signature["topologyHashShort"] == generated.candidate_signature.topology_hash[:8]
    assert "Signatures" in config.report_path.read_text(encoding="utf-8")
    assert payload["acceptedLevels"][0]["switchPreview"]
    assert payload["acceptedLevels"][0]["switchPreview"][0]["visualDirectionBuckets"]


def test_generation_report_repository_adds_duplicate_exhaustion_recommendations(tmp_path) -> None:
    config = GenerationConfig(
        start_level_number=29,
        count=1,
        difficulty="hard",
        template_name="mixed",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [],
            "rejected_candidate_count": 100,
            "rejection_reason_counts": {"candidate_too_similar_to_batch": 87},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": ["Could not generate valid level_029 after 100 attempts."],
            "passed": False,
        },
    )()

    GenerationReportRepository().write_markdown(config.report_path, config, result)
    GenerationReportRepository().write_json(config.json_report_path, config, result)

    markdown = config.report_path.read_text(encoding="utf-8")
    payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    assert "## Recommendations" in markdown
    assert payload["recommendations"][0] == "Most common rejection: `candidate_too_similar_to_batch`."


def test_generation_report_repository_writes_recipe_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=12,
            count=1,
            difficulty="easy",
            template_name="single_switch",
            generation_mode="recipe_first",
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    accepted = payload["acceptedLevels"][0]

    assert result.passed is True
    assert accepted["recipeFamily"] == "single_switch"
    assert accepted["recipeVariant"].startswith("single_switch_")
    assert accepted["abstractGraphSignature"]
    assert accepted["selectedLayoutVariant"] == "normal"
    assert accepted["selectedRoadShapeStrategy"] == "auto"
