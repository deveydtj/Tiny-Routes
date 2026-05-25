from __future__ import annotations

import json

from app.generation_config import GenerationConfig
from app.repositories.generation_report_repository import GenerationReportRepository


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
