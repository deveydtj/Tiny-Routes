from __future__ import annotations

import json

from app.random_source import RandomSource
from app.repositories.existing_level_repository import ExistingLevelRepository
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.difficulty_service import DifficultyService
from app.services.production_manifest_service import ProductionManifestService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_existing_level_repository_loads_levels_and_matching_solutions(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    writer.write_level(generated.level_document, levels_dir / "level_012.json", overwrite=False)
    writer.write_solution(generated.solution, solutions_dir / "level_012.solution.json", overwrite=False)

    result = ExistingLevelRepository().load_existing_levels(levels_dir, solutions_dir)

    assert result.warnings == []
    assert [record.level_id for record in result.records] == ["level_012"]
    assert result.signatures[0].level_id == "level_012"


def test_existing_level_repository_warns_for_missing_solution(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    writer.write_level(generated.level_document, levels_dir / "level_012.json", overwrite=False)

    result = ExistingLevelRepository().load_existing_levels(levels_dir, solutions_dir)

    assert result.records[0].level_id == "level_012"
    assert "Missing existing solution sidecar" in result.warnings[0]


def test_existing_level_repository_warns_for_malformed_level(tmp_path) -> None:
    levels_dir = tmp_path / "levels"
    levels_dir.mkdir()
    (levels_dir / "level_012.json").write_text(json.dumps({"id": "level_012"}) + "\n", encoding="utf-8")

    result = ExistingLevelRepository().load_existing_levels(levels_dir, tmp_path / "solutions")

    assert result.records == []
    assert "Could not load existing level" in result.warnings[0]


def test_existing_level_repository_uses_fresh_manifest_signatures(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    writer.write_level(generated.level_document, levels_dir / "level_012.json", overwrite=False)
    writer.write_solution(generated.solution, solutions_dir / "level_012.solution.json", overwrite=False)
    manifest_path = ProductionManifestService().rebuild(levels_dir, solutions_dir, tmp_path / "manifest.json")

    result = ExistingLevelRepository().load_existing_levels(levels_dir, solutions_dir, manifest_path)

    assert result.records == []
    assert result.signatures[0].level_id == "level_012"
