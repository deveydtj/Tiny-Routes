from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_support.production_v3_stress import (
    parse_seed_range,
    resolve_campaign_seeds,
    run_production_v3_stress,
)
from test_support.production_v3_smoke import _SmokeValidationService


def test_seed_ranges_are_inclusive_and_must_match_campaign_count() -> None:
    assert parse_seed_range("1-3") == (1, 2, 3)
    assert resolve_campaign_seeds(3, seed=10) == (10, 11, 12)
    assert resolve_campaign_seeds(3, seed_range="21-23") == (21, 22, 23)

    with pytest.raises(ValueError, match="ascending"):
        parse_seed_range("3-1")
    with pytest.raises(ValueError, match="exactly match"):
        resolve_campaign_seeds(2, seed_range="1-3")
    with pytest.raises(ValueError, match="either seed or seed_range"):
        resolve_campaign_seeds(1, seed=1, seed_range="1-1")
    with pytest.raises(ValueError, match="campaign_count"):
        run_production_v3_stress(
            Path("unused"),
            campaign_count=0,
            levels_per_campaign=30,
            seeds=(),
        )


def test_stress_suite_uses_complete_deterministic_staged_v3_campaigns(tmp_path) -> None:
    evidence = run_production_v3_stress(
        tmp_path,
        campaign_count=1,
        levels_per_campaign=3,
        start_level_number=901,
        difficulty="easy",
        seeds=(12_345,),
    )

    assert evidence.passed
    assert evidence.generator_architecture == "production_v3"
    assert evidence.generator_architecture_version == 3
    assert evidence.requested_level_count == evidence.selected_level_count == 3
    assert evidence.executed_campaign_count == 1
    assert evidence.complete_batch_count == 1
    assert evidence.deterministic_batch_count == 1
    assert evidence.staged_batch_count == 1
    assert evidence.fallback_count == 0
    assert evidence.stage_path_violation_count == 0
    assert evidence.behavior_duplicate_count == 0
    assert evidence.one_tap_or_less_count == 0
    assert evidence.static_policy_solvable_count == 0
    assert evidence.unproven_optimal_count == 0
    assert evidence.parity_error_count == 0
    assert evidence.production_mutation_count == 0
    assert list(tmp_path.iterdir()) == []
    json.dumps(evidence.to_dict(), sort_keys=True)


def test_stress_validation_rejects_any_fallback_stage(tmp_path) -> None:
    levels_dir = tmp_path / "levels"
    solutions_dir = tmp_path / "solutions"
    levels_dir.mkdir()
    solutions_dir.mkdir()
    run_manifest_path = tmp_path / "run_manifest.json"
    run_manifest_path.write_text("{}\n", encoding="utf-8")
    seed_config_snapshot_path = tmp_path / "seed_config_snapshot.json"
    seed_config_snapshot_path.write_text(
        json.dumps(
            {
                "configuration": {
                    "generatorArchitecture": "production_v3",
                    "generatorArchitectureVersion": 3,
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (levels_dir / "level_001.json").write_text("{}\n", encoding="utf-8")
    (solutions_dir / "level_001.solution.json").write_text(
        "{}\n", encoding="utf-8"
    )
    stage_names = (
        "blueprint",
        "composition",
        "strategy",
        "layout",
        "runtime",
        "quality",
    )
    stages = tuple(
        SimpleNamespace(
            stage=name,
            report_fields={
                "fallbackUsed": name == "composition",
                "generatorArchitecture": "production_v3",
                **(
                    {"generatorArchitectureVersion": 3}
                    if name == "blueprint"
                    else {}
                ),
                **(
                    {"execution": "production_v3_composition"}
                    if name == "composition"
                    else {}
                ),
                **(
                    {
                        "parityStatus": "smoke_fixture_passed",
                        "swiftParityRequested": True,
                    }
                    if name == "runtime"
                    else {}
                ),
            },
        )
        for name in stage_names
    )

    with pytest.raises(ValueError, match="fallback path"):
        _SmokeValidationService().validate(
            SimpleNamespace(
                levels_dir=levels_dir,
                solutions_dir=solutions_dir,
                run_manifest_path=run_manifest_path,
                seed_config_snapshot_path=seed_config_snapshot_path,
            ),
            (SimpleNamespace(stage_results=stages),),
            run_swift_tests=True,
        )
