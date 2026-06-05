from __future__ import annotations

import json
from types import SimpleNamespace

from app.generation_config import GenerationConfig
from app.models.generation_quality import GenerationQualityScore
from app.map_import.osm_seed_importer import MapSeedEdge, MapSeedGraph, MapSeedNode
from app.random_source import RandomSource
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult
from app.services.level_generation_service import LevelGenerationService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService
from app.templates.single_switch_template import SingleSwitchTemplate


def _config(tmp_path, **kwargs) -> GenerationConfig:
    return GenerationConfig(
        start_level_number=kwargs.pop("start_level_number", 12),
        count=kwargs.pop("count", 1),
        difficulty=kwargs.pop("difficulty", "tutorial"),
        template_name=kwargs.pop("template_name", "straight_delivery"),
        recipe_pool_size=kwargs.pop("recipe_pool_size", 1),
        layouts_per_recipe=kwargs.pop("layouts_per_recipe", 1),
        road_shapes_per_layout=kwargs.pop("road_shapes_per_layout", 1),
        candidate_pool_size=kwargs.pop("candidate_pool_size", 1),
        seed=kwargs.pop("seed", 1),
        dry_run=kwargs.pop("dry_run", False),
        overwrite=kwargs.pop("overwrite", False),
        run_swift_tests=False,
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        **kwargs,
    )


def test_generation_service_generates_one_level_and_solution(tmp_path) -> None:
    result = LevelGenerationService().generate(_config(tmp_path))

    assert result.passed is True
    assert (tmp_path / "levels" / "level_012.json").exists()
    assert (tmp_path / "solutions" / "level_012.solution.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.json").exists()


def test_generation_service_dry_run_writes_no_levels(tmp_path) -> None:
    result = LevelGenerationService().generate(_config(tmp_path, dry_run=True))

    assert result.passed is True
    assert not (tmp_path / "levels").exists()
    assert not (tmp_path / "solutions").exists()
    assert (tmp_path / "report.md").exists()


def test_generation_service_dry_run_ignores_existing_output_files(tmp_path) -> None:
    (tmp_path / "levels").mkdir()
    (tmp_path / "solutions").mkdir()
    (tmp_path / "levels" / "level_012.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "solutions" / "level_012.solution.json").write_text("{}\n", encoding="utf-8")

    result = LevelGenerationService().generate(_config(tmp_path, dry_run=True))

    assert result.passed is True
    assert result.accepted[0].level_id == "level_012"


def test_generation_service_refuses_collision_without_overwrite(tmp_path) -> None:
    (tmp_path / "levels").mkdir()
    (tmp_path / "solutions").mkdir()
    (tmp_path / "levels" / "level_012.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "solutions" / "level_012.solution.json").write_text("{}\n", encoding="utf-8")

    result = LevelGenerationService().generate(_config(tmp_path))

    assert result.passed is False
    assert "Refusing to overwrite" in result.messages[0]


def test_generation_service_is_deterministic_for_seed(tmp_path) -> None:
    first = LevelGenerationService().generate(_config(tmp_path / "a", dry_run=True, seed=42))
    second = LevelGenerationService().generate(_config(tmp_path / "b", dry_run=True, seed=42))

    assert first.accepted[0].level_document.to_dict() == second.accepted[0].level_document.to_dict()
    assert first.accepted[0].solution.to_dict() == second.accepted[0].solution.to_dict()


def test_generation_service_defaults_to_portrait_vertical_profile(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
        )
    )

    assert result.passed is True
    metadata = result.accepted[0].layout_metadata
    assert metadata["layoutProfile"] == "portrait_vertical"
    assert metadata["orientationPreference"] == "portrait_vertical"
    assert metadata["orientationSelectionReason"] == "portrait_profile_default"
    assert metadata["portraitChecksPassed"] is True


def test_generation_service_accepts_taller_than_wide_portrait_layouts(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
        )
    )

    assert result.passed is True
    metrics = result.accepted[0].layout_metadata["portraitMetrics"]
    assert metrics["height"] > metrics["width"]
    assert metrics["aspectRatio"] <= 0.95
    assert result.accepted[0].layout_metadata["portraitChecksPassed"] is True


def test_generation_service_large_portrait_profile_generates_taller_readable_layouts(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="medium",
            template_name="return_loop",
            dry_run=True,
            compare_against_existing=False,
            layout_size_profile="large_portrait",
        )
    )

    assert result.passed is True, result.messages
    metadata = result.accepted[0].layout_metadata
    metrics = metadata["portraitMetrics"]
    assert metadata["layoutSizeProfile"] == "large_portrait"
    assert metadata["portraitChecksPassed"] is True
    assert metrics["height"] >= 2.75
    assert metrics["height"] > metrics["width"]


def test_generation_service_keeps_start_below_destination_for_portrait_default(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
        )
    )

    assert result.passed is True
    nodes = {node.id: node for node in result.accepted[0].level_document.graph.nodes}
    assert nodes["start"].y > nodes[result.accepted[0].level_document.destinationNodeID].y


def test_generation_service_portrait_default_is_deterministic_for_fixed_seed(tmp_path) -> None:
    first = LevelGenerationService().generate(
        _config(
            tmp_path / "a",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=20260603,
            compare_against_existing=False,
        )
    )
    second = LevelGenerationService().generate(
        _config(
            tmp_path / "b",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=20260603,
            compare_against_existing=False,
        )
    )

    assert first.passed is True
    assert second.passed is True
    assert first.accepted[0].level_document.to_dict() == second.accepted[0].level_document.to_dict()
    assert first.accepted[0].layout_metadata["portraitMetrics"] == second.accepted[0].layout_metadata["portraitMetrics"]


def test_generation_service_retries_after_rejected_candidate(tmp_path) -> None:
    service = LevelGenerationService()
    calls = {"count": 0}
    quality_calls = {"count": 0}

    def fake_validate(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return GeneratorValidationResult(
                [GeneratorValidationMessage(severity="error", code="forced_failure", message="forced")]
            )
        return GeneratorValidationResult([])

    class FakeQualityService:
        def score(self, candidate, preset, comparison_signatures):
            quality_calls["count"] += 1
            return GenerationQualityScore(
                total=0.8,
                readability=1,
                uniqueness=1,
                difficulty_fit=1,
                route_interest=1,
                switch_clarity=1,
            )

    service.validation_service.validate = fake_validate
    service.quality_service = FakeQualityService()
    result = service.generate(_config(tmp_path, dry_run=True, candidate_pool_size=1))

    assert result.passed is True
    assert result.rejection_reason_counts["forced_failure"] == 1
    assert calls["count"] == 2
    assert quality_calls["count"] == 1


def test_generation_service_rejects_duplicate_batch_candidates(tmp_path) -> None:
    service = LevelGenerationService()

    class FixedSingleSwitchTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(2))

    service.template_registry.choose = lambda *args, **kwargs: FixedSingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            count=2,
            max_attempts_per_level=2,
            dry_run=True,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is False
    assert result.accepted[0].level_id == "level_012"
    assert result.rejection_reason_counts["candidate_too_similar_to_batch"] == 2


def test_generation_service_requires_swift_tests_for_hard_mixed_production_writes(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="hard",
            template_name="mixed",
            dry_run=False,
        )
    )

    assert result.passed is False
    assert "--swift-tests" in result.messages[0]


def test_generation_service_requires_swift_tests_for_hard_production_writes(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="hard",
            template_name="multi_switch_chain",
            dry_run=False,
        )
    )

    assert result.passed is False
    assert "--swift-tests" in result.messages[0]
    assert not (tmp_path / "levels").exists()


def test_generation_service_warns_when_production_uses_pool_size_one(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=False,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=1,
            sync_xcode_project=False,
        )
    )

    assert result.passed is True
    assert any("candidate_pool_size=1" in message for message in result.messages)


def test_generation_service_generates_unique_medium_mixed_batch(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="medium",
            template_name="mixed",
            count=8,
            seed=20260525,
            dry_run=True,
        )
    )
    signatures = {
        (
            level.candidate_signature.topology_hash,
            level.candidate_signature.layout_hash,
            level.candidate_signature.solution_hash,
        )
        for level in result.accepted
    }

    assert result.passed is True
    assert len(result.accepted) == 8
    assert len(signatures) == len(result.accepted)


def test_mixed_recipe_family_weights_penalize_recent_family_and_topology_repeats(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("medium")
    supported = service.recipe_family_registry.supported_families(preset, include_swift_required=True)
    accepted = [
        SimpleNamespace(
            recipe_family="multi_switch_order",
            template_name="multi_switch_order",
            topology_class="two_switch_order",
        ),
        SimpleNamespace(
            recipe_family="multi_switch_order",
            template_name="multi_switch_order",
            topology_class="two_switch_order",
        ),
        SimpleNamespace(
            recipe_family="multi_switch_order",
            template_name="multi_switch_order",
            topology_class="two_switch_order",
        ),
    ]

    weighted, decision = service._diversity_adjusted_family_weights(
        supported=supported,
        preset=preset,
        weights_override=None,
        accepted_candidates=accepted,
        level_id="level_020",
    )
    weights = {family.name: weight for family, weight in weighted}

    assert weights["multi_switch_order"] < weights["package_gate_double_choice"]
    assert weights["multi_switch_order"] < weights["split_path_rejoin"]
    repeated = next(item for item in decision["families"] if item["family"] == "multi_switch_order")
    assert "last_family_repeat_penalty" in repeated["reasons"]
    assert "last_topology_repeat_penalty" in repeated["reasons"]


def test_mixed_recipe_family_weights_are_deterministic_for_fixed_context(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("hard")
    supported = service.recipe_family_registry.supported_families(preset, include_swift_required=True)
    accepted = [
        SimpleNamespace(recipe_family="ring_route_gate", template_name="ring_route_gate", topology_class="ring"),
        SimpleNamespace(recipe_family="two_phase_route", template_name="two_phase_route", topology_class="two_phase"),
    ]

    first, first_decision = service._diversity_adjusted_family_weights(
        supported=supported,
        preset=preset,
        weights_override=None,
        accepted_candidates=accepted,
        level_id="level_030",
    )
    second, second_decision = service._diversity_adjusted_family_weights(
        supported=supported,
        preset=preset,
        weights_override=None,
        accepted_candidates=accepted,
        level_id="level_030",
    )

    assert [(family.name, weight) for family, weight in first] == [(family.name, weight) for family, weight in second]
    assert first_decision == second_decision


def test_mixed_recipe_family_weights_penalize_recent_topology_repeats_across_families(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("medium")
    supported = service.recipe_family_registry.supported_families(preset, include_swift_required=True)
    accepted = [
        SimpleNamespace(
            recipe_family="package_gate",
            template_name="package_gate",
            topology_class="package_gate",
            mechanic_tags=("package_gate",),
            layout_metadata={"layoutSizeProfile": "standard_portrait"},
        ),
        SimpleNamespace(
            recipe_family="package_gate",
            template_name="package_gate",
            topology_class="package_gate",
            mechanic_tags=("package_gate",),
            layout_metadata={"layoutSizeProfile": "standard_portrait"},
        ),
        SimpleNamespace(
            recipe_family="package_gate",
            template_name="package_gate",
            topology_class="package_gate",
            mechanic_tags=("package_gate",),
            layout_metadata={"layoutSizeProfile": "large_portrait"},
        ),
    ]

    weighted, decision = service._diversity_adjusted_family_weights(
        supported=supported,
        preset=preset,
        weights_override=None,
        accepted_candidates=accepted,
        level_id="level_021",
    )
    weights = {family.name: weight for family, weight in weighted}
    repeated_topology = next(item for item in decision["families"] if item["family"] == "package_gate_double_choice")

    assert weights["package_gate_double_choice"] < weights["split_path_rejoin"]
    assert "last_topology_repeat_penalty" in repeated_topology["reasons"]
    assert decision["familyCounts"] == {"package_gate": 3}
    assert decision["topologyCounts"] == {"package_gate": 3}
    assert decision["recentMechanicTags"] == ["package_gate", "package_gate", "package_gate"]
    assert decision["recentLayoutSizeProfiles"] == ["standard_portrait", "standard_portrait", "large_portrait"]
    assert decision["recentTopologyPenalties"]
    assert decision["chosenFamilyWeightsAfterDiversityAdjustment"][0]["adjustedWeight"] >= (
        decision["chosenFamilyWeightsAfterDiversityAdjustment"][-1]["adjustedWeight"]
    )


def test_mixed_recipe_family_selection_spreads_topologies_within_candidate_pool(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("medium")
    config = _config(
        tmp_path,
        difficulty="medium",
        template_name="mixed",
        dry_run=True,
        compare_against_existing=False,
    )
    decisions = []

    families = service._recipe_family_candidates(
        config=config,
        preset=preset,
        rng=RandomSource(20260605),
        include_swift_required=True,
        plan_template_weights={},
        count=4,
        accepted_candidates=[],
        level_id="level_021",
        diversity_decisions=decisions,
    )
    topologies = [service._family_topology_classes(family, preset)[0] for family in families]

    assert len(topologies) == len(set(topologies))
    assert decisions[0]["selectedFamilies"]


def test_explicit_recipe_family_selection_ignores_batch_diversity_context(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("medium")
    config = _config(
        tmp_path,
        difficulty="medium",
        template_name="package_gate",
        dry_run=True,
        compare_against_existing=False,
    )
    accepted = [
        SimpleNamespace(
            recipe_family="package_gate",
            template_name="package_gate",
            topology_class="package_gate",
            mechanic_tags=("package_gate",),
            layout_metadata={"layoutSizeProfile": "large_portrait"},
        )
        for _ in range(5)
    ]
    decisions = []

    families = service._recipe_family_candidates(
        config=config,
        preset=preset,
        rng=RandomSource(20260605),
        include_swift_required=True,
        plan_template_weights={},
        count=3,
        accepted_candidates=accepted,
        level_id="level_021",
        diversity_decisions=decisions,
    )

    assert [family.name for family in families] == ["package_gate", "package_gate", "package_gate"]
    assert decisions == []


def test_generation_service_rejects_candidates_similar_to_existing_levels(tmp_path) -> None:
    preset_result = LevelGenerationService()
    preset = preset_result.difficulty_service.get_preset("easy")
    existing = SingleSwitchTemplate().generate("level_001", 1, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    writer.write_level(existing.level_document, tmp_path / "levels" / "level_001.json")
    writer.write_solution(existing.solution, tmp_path / "solutions" / "level_001.solution.json")

    service = LevelGenerationService()

    class FixedSingleSwitchTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(2))

    service.template_registry.choose = lambda *args, **kwargs: FixedSingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            max_attempts_per_level=1,
            dry_run=True,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is False
    assert result.rejection_reason_counts["candidate_too_similar_to_existing"] == 1
    assert "matches level_001" in result.messages[-2]


def test_generation_service_can_skip_existing_similarity_check(tmp_path) -> None:
    preset_result = LevelGenerationService()
    preset = preset_result.difficulty_service.get_preset("easy")
    existing = SingleSwitchTemplate().generate("level_001", 1, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    writer.write_level(existing.level_document, tmp_path / "levels" / "level_001.json")
    writer.write_solution(existing.solution, tmp_path / "solutions" / "level_001.solution.json")

    service = LevelGenerationService()
    service.template_registry.choose = lambda *args, **kwargs: SingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            seed=2,
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is True
    assert result.rejection_reason_counts.get("candidate_too_similar_to_existing") is None


def test_generation_service_selects_highest_quality_candidate_from_pool(tmp_path) -> None:
    service = LevelGenerationService()
    seeds = iter([2, 3])

    class SequenceTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(next(seeds)))

    class FakeQualityService:
        def score(self, candidate, preset, comparison_signatures):
            total = 0.9 if candidate.seed == 3 else 0.1
            return GenerationQualityScore(
                total=total,
                readability=total,
                uniqueness=1,
                difficulty_fit=1,
                route_interest=total,
            )

    service.template_registry.choose = lambda *args, **kwargs: SequenceTemplate()
    service.quality_service = FakeQualityService()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=2,
        )
    )

    assert result.passed is True
    assert result.accepted[0].seed == 3
    assert result.accepted[0].quality_score.total == 0.9
    selection = result.candidate_selection_summaries[0]
    assert selection["acceptedCandidate"]["seed"] == 3
    assert selection["scoreStats"] == {"minimum": 0.1, "average": 0.5, "maximum": 0.9}
    assert selection["topRejectedNearMisses"][0]["seed"] == 2
    assert "highest deterministic quality score" in selection["selectionRationale"]


def test_generation_service_can_select_diverse_candidate_with_slightly_lower_base_quality(tmp_path) -> None:
    service = LevelGenerationService()

    def fake_generate_raw_candidates(**kwargs):
        preset = kwargs["preset"]
        level_id = kwargs["level_id"]
        level_number = kwargs["level_number"]
        repeated = _recipe_generated_candidate("single_switch", level_id, level_number, preset, seed=20)
        distinct = _recipe_generated_candidate("package_gate", level_id, level_number, preset, seed=21)
        return [repeated, distinct]

    class FakeQualityService:
        def score(self, candidate, preset, comparison_signatures, *, accepted_signatures=None):
            if candidate.topology_class == "package_gate":
                return GenerationQualityScore(
                    total=0.85,
                    readability=1,
                    uniqueness=1,
                    difficulty_fit=1,
                    route_interest=1,
                    switch_clarity=1,
                    diversity_score=1.0,
                    topology_diversity_score=1.0,
                    details={"baseQualityScore": 0.82},
                )
            return GenerationQualityScore(
                total=0.84,
                readability=1,
                uniqueness=1,
                difficulty_fit=1,
                route_interest=1,
                switch_clarity=1,
                diversity_score=0.35,
                topology_diversity_score=0.35,
                nearby_topology_class_penalty=0.65,
                details={"baseQualityScore": 0.86},
            )

    service._generate_raw_candidates = fake_generate_raw_candidates
    service.quality_service = FakeQualityService()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="mixed",
            dry_run=True,
            compare_against_existing=False,
            candidate_pool_size=2,
            generation_mode="recipe_first",
        )
    )

    assert result.passed is True
    assert result.accepted[0].topology_class == "package_gate"
    selection = result.candidate_selection_summaries[0]
    assert selection["acceptedCandidate"]["quality"]["baseQualityScore"] == 0.82
    assert selection["topRejectedNearMisses"][0]["quality"]["baseQualityScore"] == 0.86
    assert "after diversity scoring" in selection["selectionRationale"]


def test_generation_service_rejects_low_switch_clarity_after_scoring(tmp_path) -> None:
    service = LevelGenerationService()
    seeds = iter([2, 3])

    class SequenceTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(next(seeds)))

    class FakeQualityService:
        def score(self, candidate, preset, comparison_signatures):
            if candidate.seed == 2:
                return GenerationQualityScore(
                    total=0.95,
                    readability=1,
                    uniqueness=1,
                    difficulty_fit=1,
                    route_interest=1,
                    switch_clarity=0.1,
                    diversity_score=1,
                    topology_diversity_score=1,
                )
            return GenerationQualityScore(
                total=0.8,
                readability=1,
                uniqueness=1,
                difficulty_fit=1,
                route_interest=1,
                switch_clarity=1,
            )

    service.template_registry.choose = lambda *args, **kwargs: SequenceTemplate()
    service.quality_service = FakeQualityService()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is True
    assert result.accepted[0].seed == 3
    assert result.rejection_reason_counts["quality_switch_clarity_below_threshold"] == 1
    near_miss = result.candidate_selection_summaries[0]["topRejectedNearMisses"][0]
    assert near_miss["status"] == "quality_switch_clarity_below_threshold"


def test_generation_service_pool_selection_is_deterministic_for_same_seed(tmp_path) -> None:
    first = LevelGenerationService().generate(
        _config(
            tmp_path / "a",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=44,
            compare_against_existing=False,
            candidate_pool_size=3,
            max_attempts_per_level=20,
        )
    )
    second = LevelGenerationService().generate(
        _config(
            tmp_path / "b",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=44,
            compare_against_existing=False,
            candidate_pool_size=3,
            max_attempts_per_level=20,
        )
    )

    assert first.passed is True
    assert second.passed is True
    assert first.accepted[0].seed == second.accepted[0].seed
    assert first.candidate_selection_summaries[0]["scoreStats"] == second.candidate_selection_summaries[0]["scoreStats"]
    assert (
        first.candidate_selection_summaries[0]["acceptedCandidate"]["diversityAudit"]
        == second.candidate_selection_summaries[0]["acceptedCandidate"]["diversityAudit"]
    )


def test_recipe_first_mixed_orientation_includes_vertical_candidates(tmp_path) -> None:
    service = LevelGenerationService()
    config = _config(
        tmp_path,
        difficulty="easy",
        template_name="single_switch",
        dry_run=True,
        compare_against_existing=False,
        generation_mode="recipe_first",
        layout_orientation_preference="mixed",
        vertical_route_probability=1.0,
    )
    preset = service.difficulty_service.get_preset("easy")

    candidates = service._generate_raw_candidates(
        config=config,
        level_id="level_012",
        level_number=12,
        preset=preset,
        rng=RandomSource(12),
        plan_template_weights={},
    )

    assert {candidate.layout_metadata["orientation"] for candidate in candidates} == {"horizontal", "vertical"}
    assert {candidate.layout_metadata["strategy"] for candidate in candidates} >= {
        "horizontal_route_progression",
        "vertical_route_progression",
    }


def test_recipe_first_auto_orientation_can_include_vertical_by_probability(tmp_path) -> None:
    service = LevelGenerationService()
    config = _config(
        tmp_path,
        difficulty="medium",
        template_name="package_gate",
        dry_run=True,
        compare_against_existing=False,
        generation_mode="recipe_first",
        layout_orientation_preference="auto",
        vertical_route_probability=1.0,
        prefer_vertical_for_long_routes=False,
    )
    preset = service.difficulty_service.get_preset("medium")

    candidates = service._generate_raw_candidates(
        config=config,
        level_id="level_012",
        level_number=12,
        preset=preset,
        rng=RandomSource(12),
        plan_template_weights={},
    )

    assert candidates[0].layout_metadata["orientation"] == "vertical"
    assert candidates[0].layout_metadata["orientationSelectionReason"] == "probability"


def test_recipe_first_long_routes_can_prefer_vertical_when_configured(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("hard")
    recipe = type(
        "Recipe",
        (),
        {
            "required_path": tuple(f"node_{index}" for index in range(12)),
            "mechanic_tags": (),
            "topology_class": "long_chain",
        },
    )()
    config = _config(
        tmp_path,
        difficulty="hard",
        template_name="multi_switch_chain",
        dry_run=True,
        compare_against_existing=False,
        generation_mode="recipe_first",
        layout_orientation_preference="auto",
        vertical_route_probability=0.0,
        prefer_vertical_for_long_routes=True,
    )

    requests = service._layout_orientation_requests(config, recipe, preset, RandomSource(1), layout_index=0)

    assert requests == [{"orientation": "vertical", "reason": "long_route_preference"}]


def test_generation_service_vertical_orientation_is_deterministic_for_same_seed(tmp_path) -> None:
    first = LevelGenerationService().generate(
        _config(
            tmp_path / "a",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=44,
            compare_against_existing=False,
            layout_orientation_preference="vertical",
        )
    )
    second = LevelGenerationService().generate(
        _config(
            tmp_path / "b",
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            seed=44,
            compare_against_existing=False,
            layout_orientation_preference="vertical",
        )
    )

    assert first.passed is True
    assert second.passed is True
    assert first.accepted[0].level_document.to_dict() == second.accepted[0].level_document.to_dict()
    assert first.accepted[0].layout_metadata == second.accepted[0].layout_metadata


def test_generation_service_auto_difficulty_reports_actual_difficulty(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            start_level_number=9,
            count=4,
            difficulty="auto",
            template_name="mixed",
            dry_run=True,
            compare_against_existing=False,
        )
    )

    assert result.passed is True
    assert [level.difficulty for level in result.accepted] == ["easy", "easy", "medium", "medium"]


def test_generation_service_recipe_first_mode_generates_recipe_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            generation_mode="recipe_first",
        )
    )

    assert result.passed is True
    assert result.accepted[0].recipe_family == "single_switch"
    assert result.accepted[0].recipe_variant is not None
    assert result.accepted[0].mechanic_tags
    assert result.accepted[0].primary_mechanic_tag == "single_switch"
    assert result.accepted[0].topology_class == "single_branch"
    assert result.accepted[0].candidate_signature.topology_class == "single_branch"
    assert "single_switch" in result.accepted[0].candidate_signature.mechanic_tags
    assert result.accepted[0].candidate_signature.required_path_length is not None
    assert result.accepted[0].abstract_graph_signature is not None
    assert result.accepted[0].selected_layout_variant is not None
    assert result.accepted[0].selected_road_shape_strategy == "auto"
    assert result.accepted[0].road_shape_metadata is not None
    assert "score" in result.accepted[0].road_shape_metadata
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "roadShapeMetadata" in report["acceptedLevels"][0]
    assert report["acceptedLevels"][0]["primaryMechanicTag"] == "single_switch"
    assert report["acceptedLevels"][0]["topologyClass"] == "single_branch"
    assert report["acceptedLevels"][0]["requiredPathLength"] is not None
    assert report["acceptedLevels"][0]["diversityAudit"]["topologyDiversityScore"] == 1.0
    assert report["candidateSelection"][0]["acceptedCandidate"]["diversityScore"] == 1.0
    assert "roadShapeScore" in report["acceptedLevels"][0]["quality"]["details"]


def test_generation_service_recipe_first_supports_current_recipe_families(tmp_path) -> None:
    specs = [
        ("tutorial", "straight_delivery"),
        ("easy", "single_switch"),
        ("easy", "package_gate"),
        ("medium", "return_loop"),
        ("medium", "fake_shortcut"),
        ("hard", "ring_route"),
        ("expert", "four_way_intersection"),
    ]

    for index, (difficulty, template_name) in enumerate(specs):
        result = LevelGenerationService().generate(
            _config(
                tmp_path / template_name,
                start_level_number=90 + index,
                difficulty=difficulty,
                template_name=template_name,
                generation_mode="recipe_first",
                recipe_pool_size=2,
                layouts_per_recipe=2,
                road_shapes_per_layout=2,
                dry_run=True,
                compare_against_existing=False,
            )
        )

        assert result.passed is True, (difficulty, template_name, result.rejection_reason_counts, result.messages)
        assert result.accepted[0].recipe_family == template_name


def test_generation_service_hybrid_mode_keeps_legacy_templates_available(tmp_path) -> None:
    service = LevelGenerationService()
    config = _config(
        tmp_path,
        difficulty="easy",
        template_name="single_switch",
        generation_mode="hybrid",
        recipe_pool_size=1,
        layouts_per_recipe=1,
        road_shapes_per_layout=1,
        dry_run=True,
        compare_against_existing=False,
    )
    preset = service.difficulty_service.get_preset("easy")
    candidates = service._generate_raw_candidates(
        config=config,
        level_id="level_012",
        level_number=12,
        preset=preset,
        rng=RandomSource(12),
        plan_template_weights={},
    )

    assert len(candidates) == 2
    assert {candidate.recipe_family for candidate in candidates} == {"single_switch", None}


def test_generation_service_applies_map_seed_path(tmp_path) -> None:
    map_seed_path = tmp_path / "seed.json"
    seed_graph = MapSeedGraph(
        nodes=[
            MapSeedNode("a", 0, 0),
            MapSeedNode("b", 1, 0),
            MapSeedNode("c", 2, 1),
            MapSeedNode("d", 3, 1),
            MapSeedNode("e", 4, 0),
            MapSeedNode("f", 5, 0),
        ],
        edges=[
            MapSeedEdge("e1", "a", "b"),
            MapSeedEdge("e2", "b", "c"),
            MapSeedEdge("e3", "c", "d"),
            MapSeedEdge("e4", "d", "e"),
            MapSeedEdge("e5", "e", "f"),
        ],
        attribution="test map",
    )
    map_seed_path.write_text(json.dumps(seed_graph.to_dict()) + "\n", encoding="utf-8")

    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            map_seed_path=map_seed_path,
        )
    )

    assert result.passed is True
    assert any("Map attribution" in note for note in result.accepted[0].generation_notes)


def _recipe_generated_candidate(family_name: str, level_id: str, level_number: int, preset, seed: int):
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe(level_id, preset, RandomSource(seed), family.variants[0])
    recipe = AbstractPuzzleSolverService().solve(recipe, preset)
    return RecipeToLevelBuilderService().build_level(recipe, level_number, seed=seed)
