from __future__ import annotations

import json
import os
from collections import Counter

import pytest

from app.generation_config import GenerationConfig
from app.services.level_generation_service import LevelGenerationService


FULL_STRESS_ENV = "TINY_ROUTES_FULL_GENERATOR_STRESS"


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
                candidate_pool_size=2,
                recipe_pool_size=2,
                layouts_per_recipe=1,
                road_shapes_per_layout=1,
            )
        )

        assert result.passed is True
        assert len(result.accepted) == 2
        assert result.report_path is not None
        assert result.json_report_path is not None


def test_mixed_auto_dry_run_reports_diversity_distribution(tmp_path) -> None:
    result = _run_dry_batch(
        tmp_path,
        start_level_number=1,
        count=8,
        difficulty="auto",
        seed=9001,
        max_attempts_per_level=80,
        candidate_pool_size=4,
        recipe_pool_size=3,
        layouts_per_recipe=1,
        road_shapes_per_layout=2,
    )
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert result.passed is True
    assert len(result.accepted) == 8
    _assert_report_includes_diversity_fields(payload)
    assert len(_distribution(payload, "recipeFamily")) >= 2
    assert len(_distribution(payload, "topologyClass")) >= 2
    assert len(_distribution(payload, "primaryMechanicTag")) >= 2


@pytest.mark.skipif(
    os.environ.get(FULL_STRESS_ENV) != "1",
    reason=f"set {FULL_STRESS_ENV}=1 to run full generator stress dry-runs",
)
def test_full_mixed_auto_50_dry_run_stress_diversity(tmp_path) -> None:
    result = _run_dry_batch(
        tmp_path,
        start_level_number=1,
        count=50,
        difficulty="auto",
        seed=9001,
    )
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert result.passed is True
    assert len(result.accepted) == 50
    _assert_report_includes_diversity_fields(payload)
    assert len(_distribution(payload, "recipeFamily")) >= 5
    assert len(_distribution(payload, "topologyClass")) >= 5
    assert len(_distribution(payload, "primaryMechanicTag")) >= 5
    _assert_duplicate_rejections_not_dominant(payload)


@pytest.mark.skipif(
    os.environ.get(FULL_STRESS_ENV) != "1",
    reason=f"set {FULL_STRESS_ENV}=1 to run full generator stress dry-runs",
)
def test_full_expert_10_dry_run_stress_diversity(tmp_path) -> None:
    result = _run_dry_batch(
        tmp_path,
        start_level_number=41,
        count=10,
        difficulty="expert",
        seed=9101,
    )
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert result.passed is True
    assert len(result.accepted) == 10
    _assert_report_includes_diversity_fields(payload)
    assert len(_distribution(payload, "recipeFamily")) >= 3
    assert len(_distribution(payload, "topologyClass")) >= 3
    assert len(_distribution(payload, "primaryMechanicTag")) >= 3
    _assert_duplicate_rejections_not_dominant(payload)


@pytest.mark.skipif(
    os.environ.get(FULL_STRESS_ENV) != "1",
    reason=f"set {FULL_STRESS_ENV}=1 to run full generator stress dry-runs",
)
def test_full_hard_20_dry_run_stress_diversity(tmp_path) -> None:
    result = _run_dry_batch(
        tmp_path,
        start_level_number=26,
        count=20,
        difficulty="hard",
        seed=9201,
    )
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    topology_counts = _distribution(payload, "topologyClass")
    chain_count = sum(
        count
        for topology, count in topology_counts.items()
        if "chain" in str(topology or "")
    )

    assert result.passed is True
    assert len(result.accepted) == 20
    _assert_report_includes_diversity_fields(payload)
    assert len(_distribution(payload, "recipeFamily")) >= 4
    assert len(topology_counts) >= 4
    assert len(_distribution(payload, "primaryMechanicTag")) >= 4
    assert chain_count / len(payload["acceptedLevels"]) < 0.65
    _assert_duplicate_rejections_not_dominant(payload)


def _run_dry_batch(tmp_path, **overrides):
    return LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=overrides.pop("start_level_number"),
            count=overrides.pop("count"),
            difficulty=overrides.pop("difficulty"),
            template_name="mixed",
            generation_mode="recipe_first",
            seed=overrides.pop("seed"),
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
            **overrides,
        )
    )


def _assert_report_includes_diversity_fields(payload: dict) -> None:
    for accepted in payload["acceptedLevels"]:
        assert accepted["recipeFamily"]
        assert accepted["mechanicTags"]
        assert accepted["topologyClass"]
        assert accepted["layoutOrientation"]
        assert accepted["requiredPathLength"] is not None
        assert accepted["diversityScore"] is not None
        assert accepted["quality"]["diversityScore"] is not None
        assert accepted["signature"]["diversityAudit"]["diversityScore"] is not None

    for selection in payload["candidateSelection"]:
        accepted_candidate = selection["acceptedCandidate"]
        assert accepted_candidate["diversityScore"] is not None
        assert accepted_candidate["nearbyMechanicTagPenalty"] is not None
        assert accepted_candidate["nearbyTopologyClassPenalty"] is not None
        assert accepted_candidate["quality"]["diversityScore"] is not None


def _distribution(payload: dict, field_name: str) -> Counter:
    return Counter(
        accepted.get(field_name)
        for accepted in payload["acceptedLevels"]
        if accepted.get(field_name)
    )


def _assert_duplicate_rejections_not_dominant(payload: dict) -> None:
    rejection_counts = payload.get("rejectionReasonCounts", {})
    total_rejections = sum(rejection_counts.values())
    if total_rejections < 10:
        return
    duplicate_rejections = sum(
        count
        for reason, count in rejection_counts.items()
        if "similar" in reason or "duplicate" in reason
    )
    assert duplicate_rejections / total_rejections < 0.85
