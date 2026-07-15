from __future__ import annotations

import json

import pytest

from app.services.production_migration_service import ProductionMigrationError, ProductionMigrationService


def _write_pair(levels, solutions, level_id: str, *, name: str = "Stable Name", taps: int = 0) -> None:
    levels.mkdir(parents=True, exist_ok=True)
    solutions.mkdir(parents=True, exist_ok=True)
    level = {
        "id": level_id,
        "name": name,
        "graph": {
            "nodes": [
                {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["edge"]},
                {"id": "finish", "x": 0, "y": 1, "outgoingEdgeIDs": []},
            ],
            "edges": [{"id": "edge", "fromNodeID": "start", "toNodeID": "finish"}],
        },
        "startNodeID": "start",
        "packageNodeID": "start",
        "destinationNodeID": "finish",
        "timeLimitSeconds": 10,
        "parTaps": taps,
    }
    solution = {
        "levelID": level_id,
        "description": "test",
        "expectedOutcome": "completed",
        "maxTaps": 0,
        "requiresWithinTimeLimit": True,
        "actions": [],
    }
    (levels / f"{level_id}.json").write_text(json.dumps(level), encoding="utf-8")
    (solutions / f"{level_id}.solution.json").write_text(json.dumps(solution), encoding="utf-8")


def test_migration_preserves_ids_order_and_writes_pair_with_fresh_manifest(tmp_path) -> None:
    levels = tmp_path / "production" / "levels"
    solutions = tmp_path / "production" / "solutions"
    replacements = tmp_path / "replacements"
    replacement_solutions = tmp_path / "replacement-solutions"
    _write_pair(levels, solutions, "level_001")
    _write_pair(levels, solutions, "level_002")
    _write_pair(replacements, replacement_solutions, "level_002", taps=1)

    manifest = tmp_path / "production" / "manifest.json"
    result = ProductionMigrationService().apply(
        replacements, replacement_solutions, levels, solutions, manifest
    )

    assert result.migrated_level_ids == ("level_002",)
    assert json.loads((levels / "level_002.json").read_text())["parTaps"] == 1
    assert json.loads((solutions / "level_002.solution.json").read_text())["levelID"] == "level_002"
    assert [item["levelID"] for item in json.loads(manifest.read_text())["levels"]] == [
        "level_001",
        "level_002",
    ]


def test_migration_rejects_new_ids_and_leaves_production_untouched(tmp_path) -> None:
    levels = tmp_path / "production" / "levels"
    solutions = tmp_path / "production" / "solutions"
    replacements = tmp_path / "replacements"
    replacement_solutions = tmp_path / "replacement-solutions"
    _write_pair(levels, solutions, "level_001")
    _write_pair(replacements, replacement_solutions, "level_002")
    before = (levels / "level_001.json").read_bytes()

    with pytest.raises(ProductionMigrationError, match="add or reorder campaign content"):
        ProductionMigrationService().apply(
            replacements,
            replacement_solutions,
            levels,
            solutions,
            tmp_path / "manifest.json",
        )

    assert (levels / "level_001.json").read_bytes() == before
    assert not (tmp_path / "manifest.json").exists()


def test_migration_requires_explicit_review_for_name_changes(tmp_path) -> None:
    levels = tmp_path / "production" / "levels"
    solutions = tmp_path / "production" / "solutions"
    replacements = tmp_path / "replacements"
    replacement_solutions = tmp_path / "replacement-solutions"
    _write_pair(levels, solutions, "level_001", name="Original")
    _write_pair(replacements, replacement_solutions, "level_001", name="Renamed")

    with pytest.raises(ProductionMigrationError, match="without explicit review"):
        ProductionMigrationService().apply(
            replacements,
            replacement_solutions,
            levels,
            solutions,
            tmp_path / "manifest.json",
        )

    ProductionMigrationService().apply(
        replacements,
        replacement_solutions,
        levels,
        solutions,
        tmp_path / "manifest.json",
        reviewed_name_changes=("level_001",),
    )
    assert json.loads((levels / "level_001.json").read_text())["name"] == "Renamed"
