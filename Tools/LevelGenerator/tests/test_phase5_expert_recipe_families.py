from __future__ import annotations

import json
from collections import Counter

import pytest

from app.generation_config import GenerationConfig
from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.level_generation_service import LevelGenerationService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService


PHASE5_FAMILIES = ("controlled_repeated_taps", "four_way_package_gate", "four_way_ring")
PHASE5_TOPOLOGIES = {"revisit", "four_way_gate", "four_way_ring"}
ADVANCED_EXPERT_TAGS = {
    "four_way",
    "repeated_tap",
    "ring",
    "route_reversal",
    "two_phase",
    "revisit",
    "package_inside_loop",
}


@pytest.mark.parametrize("family_name", PHASE5_FAMILIES)
def test_phase5_expert_families_generate_solve_build_and_validate(family_name: str) -> None:
    preset = DifficultyService().get_preset("expert")
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe("level_999", preset, RandomSource(11), family.variants[0])
    solved = AbstractPuzzleSolverService().solve(recipe, preset)
    generated = RecipeToLevelBuilderService().build_level(solved, 999, seed=22)
    validation = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)

    assert not validation.has_errors, (family_name, validation.error_codes)
    assert generated.recipe_family == family_name
    assert generated.topology_class in PHASE5_TOPOLOGIES
    assert set(generated.mechanic_tags).intersection(ADVANCED_EXPERT_TAGS)
    assert 2 <= generated.required_tap_count <= 6
    assert generated.abstract_solution_metadata is not None


def test_controlled_repeated_taps_has_actual_revisit_and_fair_timing() -> None:
    recipe, generated = _solved_and_generated("controlled_repeated_taps")
    route_counts = Counter(recipe.required_path)
    tap_counts = Counter(recipe.tap_node_ids)
    repeat_visits = [index for index, node_id in enumerate(recipe.required_path) if node_id == "repeat_switch"]
    repeat_tap_times = [
        float(action.timeSeconds)
        for action in generated.solution.actions
        if action.tapNodeID == "repeat_switch"
    ]

    assert recipe.topology_class == "revisit"
    assert {"repeated_tap", "revisit", "two_phase", "loop"}.issubset(recipe.mechanic_tags)
    assert route_counts["repeat_switch"] == 2
    assert tap_counts["repeat_switch"] == 2
    assert repeat_visits[0] < recipe.required_path.index("package") < repeat_visits[1]
    assert repeat_tap_times[1] - repeat_tap_times[0] >= 1.5


def test_four_way_package_gate_has_four_way_plus_separate_gate_not_intro_clone() -> None:
    recipe, generated = _solved_and_generated("four_way_package_gate")
    outgoing = _outgoing(recipe)
    intro = _solved_recipe("four_way_intro")

    assert recipe.topology_class == "four_way_gate"
    assert {"four_way", "package_gate", "two_phase"}.issubset(recipe.mechanic_tags)
    assert len(outgoing["four_way_switch"]) == 4
    assert len(outgoing["switch_exit"]) == 2
    assert "switch_exit" not in outgoing["four_way_switch"]
    assert recipe.required_path.count("four_way_switch") == 1
    assert len(_switch_ids(recipe)) > len(_switch_ids(intro))
    assert "central_switch" not in {node.id for node in recipe.nodes}

    buckets = generated.road_shape_metadata["switchDirectionBuckets"]["four_way_switch"]
    assert set(buckets.values()) == {"north", "east", "south", "west"}


def test_four_way_ring_has_four_way_and_loop_with_package_on_ring() -> None:
    recipe, generated = _solved_and_generated("four_way_ring")
    outgoing = _outgoing(recipe)

    assert recipe.topology_class == "four_way_ring"
    assert {"four_way", "ring", "loop", "package_inside_loop"}.issubset(recipe.mechanic_tags)
    assert len(outgoing["four_way_switch"]) == 4
    assert set(outgoing["ring_b"]) == {"ring_c", "switch_exit"}
    assert ("ring_c", "four_way_switch") in _edge_pairs(recipe)
    assert recipe.required_path.index("ring_a") < recipe.required_path.index("package")
    assert recipe.required_path.index("package") < recipe.required_path.index("switch_exit")

    four_way_buckets = generated.road_shape_metadata["switchDirectionBuckets"]["four_way_switch"]
    ring_exit_buckets = generated.road_shape_metadata["switchDirectionBuckets"]["ring_b"]
    assert set(four_way_buckets.values()) == {"north", "east", "south", "west"}
    assert len(set(ring_exit_buckets.values())) == 2


def test_phase5_swift_required_policy_for_four_way_and_ring_families(tmp_path) -> None:
    registry = RecipeFamilyRegistry()
    preset = DifficultyService().get_preset("expert")

    assert registry.get_family("four_way_package_gate").requires_swift_validation is True
    assert registry.get_family("four_way_ring").requires_swift_validation is True
    assert registry.get_family("controlled_repeated_taps").requires_swift_validation is False
    without_swift = {
        family.name
        for family in registry.supported_families(preset, include_swift_required=False)
    }
    assert "four_way_package_gate" not in without_swift
    assert "four_way_ring" not in without_swift
    with pytest.raises(ValueError, match="requires Swift validation"):
        registry.choose_family("four_way_package_gate", preset, RandomSource(1), include_swift_required=False)

    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=90,
            count=1,
            difficulty="expert",
            template_name="four_way_ring",
            seed=1,
            dry_run=False,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    )
    assert result.passed is False
    assert "--swift-tests" in result.messages[0]
    assert not (tmp_path / "levels").exists()
    assert not (tmp_path / "solutions").exists()


def test_expert_mixed_dry_run_accepts_phase5_topology_mix_and_reports_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=90,
            count=4,
            difficulty="expert",
            template_name="mixed",
            seed=2,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
            max_attempts_per_level=60,
            candidate_pool_size=1,
            recipe_pool_size=3,
            layouts_per_recipe=1,
            road_shapes_per_layout=2,
            layout_orientation_preference="horizontal",
        )
    )
    phase5_accepted = [
        level
        for level in result.accepted
        if level.recipe_family in {"four_way_package_gate", "four_way_ring", "controlled_repeated_taps"}
    ]
    topology_classes = {level.topology_class for level in phase5_accepted}
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    accepted_by_family = {
        level["recipeFamily"]: level
        for level in payload["acceptedLevels"]
    }

    assert result.passed is True
    assert len(result.accepted) == 4
    assert len(topology_classes) >= 2
    assert {"four_way_package_gate", "four_way_ring"}.issubset(accepted_by_family)
    assert accepted_by_family["four_way_package_gate"]["requiresSwiftValidation"] is True
    assert accepted_by_family["four_way_ring"]["requiresSwiftValidation"] is True
    assert accepted_by_family["four_way_ring"]["topologyClass"] == "four_way_ring"
    assert accepted_by_family["four_way_package_gate"]["topologyClass"] == "four_way_gate"
    assert accepted_by_family["four_way_ring"]["layoutOrientation"]
    assert not (tmp_path / "levels").exists()
    assert not (tmp_path / "solutions").exists()


def _solved_recipe(family_name: str):
    preset = DifficultyService().get_preset("expert")
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe("level_999", preset, RandomSource(11), family.variants[0])
    return AbstractPuzzleSolverService().solve(recipe, preset)


def _solved_and_generated(family_name: str):
    recipe = _solved_recipe(family_name)
    generated = RecipeToLevelBuilderService().build_level(recipe, 999, seed=22)
    validation = GeneratedLevelValidationService().validate(
        generated,
        preset=DifficultyService().get_preset("expert"),
        overwrite=True,
    )
    assert not validation.has_errors, validation.error_codes
    return recipe, generated


def _outgoing(recipe) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for edge in recipe.edges:
        grouped.setdefault(edge.from_node_id, []).append(edge.to_node_id)
    return {node_id: tuple(targets) for node_id, targets in grouped.items()}


def _edge_pairs(recipe) -> set[tuple[str, str]]:
    return {(edge.from_node_id, edge.to_node_id) for edge in recipe.edges}


def _switch_ids(recipe) -> set[str]:
    outgoing = _outgoing(recipe)
    return {node_id for node_id, targets in outgoing.items() if len(targets) > 1}
