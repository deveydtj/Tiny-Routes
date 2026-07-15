from __future__ import annotations

import json
from pathlib import Path

from app.paths import find_repo_root
from app.services.production_manifest_service import ProductionManifestService
from migrate_levels_to_live_routing import analyze_level
from verify_production_corpus import verify


def test_committed_production_corpus_passes_every_non_swift_gate() -> None:
    root = find_repo_root()
    report = verify(
        root / "TinyRoutes/Resources/Levels",
        root / "TinyRoutesTests/Resources/LevelSolutions",
        root / "docs/generated_levels/production_manifest.json",
        run_swift_tests=False,
    )

    assert report["passed"] is True
    assert report["levelCount"] == 27
    assert report["manifestSynchronized"] is True
    assert report["representativeEditorRoundTripLevelIDs"] == [
        "level_001",
        "level_014",
        "level_027",
    ]
    assert all(item["explicitSchemaV2LiveRules"] for item in report["levels"])
    assert all(item["pythonReplayPassed"] for item in report["levels"])
    assert all(item["zeroTimeSolutionRejected"] for item in report["levels"])
    assert all(item["decisionProfilePassed"] for item in report["levels"])
    assert all(item["visualReadabilityPassed"] for item in report["levels"])
    assert all(item["modelRoundTripPassed"] for item in report["levels"])


def test_zero_time_preconfiguration_fails_the_corpus_gate(tmp_path: Path) -> None:
    root = find_repo_root()
    levels = tmp_path / "Levels"
    solutions = tmp_path / "LevelSolutions"
    levels.mkdir()
    solutions.mkdir()
    level_id = "level_002"
    level_source = root / "TinyRoutes/Resources/Levels" / f"{level_id}.json"
    solution_source = (
        root / "TinyRoutesTests/Resources/LevelSolutions" / f"{level_id}.solution.json"
    )
    (levels / level_source.name).write_bytes(level_source.read_bytes())
    solution_payload = json.loads(solution_source.read_text(encoding="utf-8"))
    for action in solution_payload["actions"]:
        action["timeSeconds"] = 0.0
    (solutions / solution_source.name).write_text(
        json.dumps(solution_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "production_manifest.json"
    ProductionManifestService().rebuild(levels, solutions, manifest)

    report = verify(
        levels,
        solutions,
        manifest,
        run_swift_tests=False,
    )

    assert report["passed"] is False
    assert report["levels"][0]["pythonReplayPassed"] is False
    assert "python_replay:tap_before_activation_window" in report["levels"][0]["issues"]


def test_redesigned_levels_have_phase_and_revisit_evidence() -> None:
    root = find_repo_root()

    def analysis(level_id: str) -> dict:
        level = json.loads(
            (root / "TinyRoutes/Resources/Levels" / f"{level_id}.json").read_text()
        )
        solution = json.loads(
            (
                root
                / "TinyRoutesTests/Resources/LevelSolutions"
                / f"{level_id}.solution.json"
            ).read_text()
        )
        return analyze_level(level, solution)

    phase_intro = analysis("level_005")["decisionQuality"]["profile"]
    assert phase_intro["ordered_dependency_count"] >= 1
    assert phase_intro["package_phase_decisions_before"] >= 1
    assert phase_intro["package_phase_decisions_after"] >= 1
    assert phase_intro["front_loaded_legacy_solution_possible"] is False

    revisit_ring = analysis("level_024")["decisionQuality"]["profile"]
    assert revisit_ring["repeated_switch_decision_count"] >= 1
    assert revisit_ring["route_revisit_count"] >= 1
    assert revisit_ring["switch_state_change_on_revisit_count"] >= 1
    assert revisit_ring["recoverable_mistake_count"] >= 1
    assert revisit_ring["front_loaded_legacy_solution_possible"] is False
