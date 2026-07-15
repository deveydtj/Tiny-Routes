from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.paths import find_repo_root
from migrate_levels_to_live_routing import (
    MIGRATION_CATEGORY_DEFINITIONS,
    MigrationCategory,
    recommend_migration,
)


SCRIPT = find_repo_root() / "Tools" / "LevelGenerator" / "migrate_levels_to_live_routing.py"


def _recommend(**overrides):
    inputs = {
        "current_solution_passed": True,
        "current_live_passed": True,
        "adjusted_live_passed": True,
        "live_failure_reason": None,
        "decision_quality_issues": [],
        "windows_legalizable": True,
    }
    inputs.update(overrides)
    return recommend_migration(**inputs)


def test_migration_categories_have_stable_definitions_and_precedence() -> None:
    assert set(MIGRATION_CATEGORY_DEFINITIONS) == set(MigrationCategory)
    assert _recommend()[0] == MigrationCategory.AUTOMATIC_CONVERSION
    assert _recommend(
        current_live_passed=False,
        adjusted_live_passed=True,
        live_failure_reason="insufficient_rotation_window",
    )[0] == MigrationCategory.TIMING_LAYOUT_ADJUSTMENT
    assert _recommend(
        decision_quality_issues=["decision_count_outside_difficulty_range:0:2-4"],
    )[0] == MigrationCategory.MANUAL_REDESIGN
    assert _recommend(
        decision_quality_issues=["too_many_multiple_tap_windows"],
    )[0] == MigrationCategory.REGENERATION


def test_window_only_quality_issue_recommends_adjustment() -> None:
    category, reasons = _recommend(
        decision_quality_issues=["decision_window_below_preset_minimum"],
    )

    assert category == MigrationCategory.TIMING_LAYOUT_ADJUSTMENT
    assert reasons == ("decision_window_below_preset_minimum",)


def test_analyzer_fails_cleanly_when_sidecar_is_missing(tmp_path: Path) -> None:
    levels = tmp_path / "levels"
    solutions = tmp_path / "solutions"
    levels.mkdir()
    solutions.mkdir()
    (levels / "level_001.json").write_text('{"id":"level_001"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--levels-dir",
            str(levels),
            "--solutions-dir",
            str(solutions),
            "--json-output",
            str(tmp_path / "out.json"),
            "--markdown-output",
            str(tmp_path / "out.md"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Missing solution sidecar for level_001" in result.stderr


def test_production_report_is_deterministic_and_complete(tmp_path: Path) -> None:
    root = find_repo_root()
    first_json = tmp_path / "first.json"
    first_markdown = tmp_path / "first.md"
    second_json = tmp_path / "second.json"
    second_markdown = tmp_path / "second.md"
    for json_output, markdown_output in (
        (first_json, first_markdown),
        (second_json, second_markdown),
    ):
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--json-output",
                str(json_output),
                "--markdown-output",
                str(markdown_output),
            ],
            cwd=root,
            check=True,
        )

    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_markdown.read_bytes() == second_markdown.read_bytes()
    payload = json.loads(first_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["levelCount"] > 0
    assert set(payload["migrationCategories"]) == {item.value for item in MigrationCategory}
    required = {
        "currentSchemaAndRules",
        "currentSolutionResult",
        "liveRoutingSolution",
        "requiredWindowSizes",
        "repeatedDecisionBehavior",
        "decisionQuality",
        "recommendation",
    }
    assert all(required <= set(level) for level in payload["levels"])
