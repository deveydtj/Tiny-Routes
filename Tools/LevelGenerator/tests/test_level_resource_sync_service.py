from __future__ import annotations

from app.services.level_resource_sync_service import (
    LevelResourceSyncService,
    normalize_level_id_or_number,
    parse_level_selectors,
)


def test_parse_level_selectors_supports_ids_numbers_and_ranges() -> None:
    assert parse_level_selectors(["level_001", "2", "4-6"]) == [
        "level_001",
        "level_002",
        "level_004",
        "level_005",
        "level_006",
    ]
    assert normalize_level_id_or_number("7") == "level_007"


def test_resource_sync_detects_missing_and_stale_project_references(tmp_path) -> None:
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    levels_dir.mkdir()
    solutions_dir.mkdir()
    (levels_dir / "level_001.json").write_text("{}\n", encoding="utf-8")
    (solutions_dir / "level_001.solution.json").write_text("{}\n", encoding="utf-8")
    project_file = tmp_path / "project.pbxproj"
    project_file.write_text("level_001.json level_999.json\n", encoding="utf-8")

    result = LevelResourceSyncService().check_project_references(levels_dir, solutions_dir, project_file)

    assert result.missing_project_references == ["level_001.solution.json"]
    assert result.stale_project_references == ["level_999.json"]


def test_delete_levels_deletes_level_and_solution(tmp_path) -> None:
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    levels_dir.mkdir()
    solutions_dir.mkdir()
    level_path = levels_dir / "level_001.json"
    solution_path = solutions_dir / "level_001.solution.json"
    level_path.write_text("{}\n", encoding="utf-8")
    solution_path.write_text("{}\n", encoding="utf-8")

    result = LevelResourceSyncService().delete_levels(
        ["level_001"],
        levels_dir,
        solutions_dir,
        dry_run=False,
        run_xcodegen=False,
    )

    assert result.deleted_paths == [level_path, solution_path]
    assert not level_path.exists()
    assert not solution_path.exists()
