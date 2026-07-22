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


PHASE4_FAMILIES = ("split_path_rejoin", "fake_shortcut", "hub_choice", "long_detour_gate")
PHASE4_TOPOLOGIES = {"split_rejoin", "detour_gate", "hub_spoke"}


@pytest.mark.parametrize(
    ("family_name", "difficulty_name"),
    [
        ("split_path_rejoin", "medium"),
        ("split_path_rejoin", "hard"),
        ("fake_shortcut", "easy"),
        ("fake_shortcut", "medium"),
        ("fake_shortcut", "hard"),
        ("hub_choice", "medium"),
        ("hub_choice", "hard"),
        ("long_detour_gate", "easy"),
        ("long_detour_gate", "medium"),
        ("long_detour_gate", "hard"),
    ],
)
def test_phase4_families_generate_solve_build_and_validate(family_name: str, difficulty_name: str) -> None:
    difficulty = DifficultyService()
    preset = difficulty.get_preset(difficulty_name)
    family = RecipeFamilyRegistry().get_family(family_name)

    recipe = family.generate_recipe("level_999", preset, RandomSource(11), family.variants[0])
    solved = AbstractPuzzleSolverService().solve(recipe, preset)
    generated = RecipeToLevelBuilderService().build_level(solved, 999, seed=22)
    validation = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)

    assert not validation.has_errors, (family_name, difficulty_name, validation.error_codes)
    assert generated.recipe_family == family_name
    assert generated.topology_class in PHASE4_TOPOLOGIES
    assert generated.mechanic_tags
    assert generated.abstract_solution_metadata is not None
    assert generated.abstract_solution_metadata.minimum_required_decisions in range(
        preset.required_tap_range[0],
        preset.required_tap_range[1] + 1,
    )


def test_split_path_rejoin_has_real_split_and_rejoin() -> None:
    recipe = _solved_recipe("split_path_rejoin", "medium")
    outgoing = _outgoing(recipe)
    incoming_count = Counter(edge.to_node_id for edge in recipe.edges)

    assert recipe.topology_class == "split_rejoin"
    assert {"split_path", "rejoin"}.issubset(recipe.mechanic_tags)
    assert set(outgoing["switch_a"]) == {"lower_shortcut", "upper_branch"}
    assert incoming_count["rejoin"] == 2
    assert "upper_branch" in recipe.required_path
    assert "lower_shortcut" not in recipe.required_path
    assert ("lower_shortcut", "rejoin") in _edge_pairs(recipe)


def test_fake_shortcut_has_false_shortcut_and_longer_correct_route() -> None:
    recipe = _solved_recipe("fake_shortcut", "medium")
    outgoing = _outgoing(recipe)

    assert recipe.topology_class == "detour_gate"
    assert {"fake_shortcut", "detour", "dead_end"}.issubset(recipe.mechanic_tags)
    assert "shortcut_dead_end" in outgoing["choice"]
    assert "shortcut_dead_end" not in recipe.required_path
    assert recipe.required_path.index("package") < recipe.required_path.index("destination")
    assert len(recipe.required_path) - 1 > 2


def test_hub_choice_has_three_way_hub_with_distinct_visual_buckets() -> None:
    recipe = _solved_recipe("hub_choice", "medium")
    outgoing = _outgoing(recipe)

    assert recipe.topology_class == "hub_spoke"
    assert {"hub", "multi_switch"}.issubset(recipe.mechanic_tags)
    assert set(outgoing["hub"]) == {"dead_end_a", "package_branch", "rejoin"}

    generated = RecipeToLevelBuilderService().build_level(recipe, 999, seed=22)
    buckets = generated.road_shape_metadata["switchDirectionBuckets"]["hub"]
    assert len(buckets) == 3
    assert len(set(buckets.values())) == 3


@pytest.mark.parametrize(
    ("difficulty_name", "expected_range"),
    [
        ("easy", range(4, 7)),
        ("medium", range(6, 10)),
        ("hard", range(8, 13)),
    ],
)
def test_long_detour_gate_path_lengths_and_no_generic_filler(
    difficulty_name: str,
    expected_range: range,
) -> None:
    recipe = _solved_recipe("long_detour_gate", difficulty_name)
    required_path_length = len(recipe.required_path) - 1
    filler_nodes = [
        node_id
        for node_id in recipe.required_path[1:-1]
        if not _is_meaningful_long_detour_node(node_id)
    ]

    assert recipe.topology_class == "detour_gate"
    assert {"long_route", "detour", "package_gate"}.issubset(recipe.mechanic_tags)
    assert required_path_length in expected_range
    assert filler_nodes == []


def test_report_includes_phase4_family_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            generator_architecture="v2_legacy",
            start_level_number=90,
            count=1,
            difficulty="medium",
            template_name="hub_choice",
            seed=7,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
            max_attempts_per_level=20,
            candidate_pool_size=1,
            recipe_pool_size=1,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
        )
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    accepted = payload["acceptedLevels"][0]

    assert result.passed is True
    assert accepted["recipeFamily"] == "hub_choice"
    assert accepted["topologyClass"] == "hub_spoke"
    assert accepted["primaryMechanicTag"] == "hub"
    assert {"hub", "multi_switch"}.issubset(set(accepted["mechanicTags"]))
    assert payload["candidateSelection"][0]["acceptedCandidate"]["topologyClass"] == "hub_spoke"


@pytest.mark.parametrize(
    ("difficulty_name", "seed"),
    [
        ("medium", 1),
        ("hard", 3),
    ],
)
def test_mixed_dry_runs_include_phase4_topology_mix_without_writing_levels(
    tmp_path,
    difficulty_name: str,
    seed: int,
) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            generator_architecture="v2_legacy",
            start_level_number=80,
            count=4,
            difficulty=difficulty_name,
            template_name="mixed",
            seed=seed,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / difficulty_name / "levels",
            solutions_output_dir=tmp_path / difficulty_name / "solutions",
            report_path=tmp_path / difficulty_name / "report.md",
            json_report_path=tmp_path / difficulty_name / "report.json",
            max_attempts_per_level=80,
            candidate_pool_size=1,
            recipe_pool_size=3,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
        )
    )
    topology_classes = {level.topology_class for level in result.accepted}

    assert result.passed is True
    assert len(result.accepted) == 4
    assert topology_classes.intersection(PHASE4_TOPOLOGIES)
    assert len(topology_classes) >= 3
    assert not (tmp_path / difficulty_name / "levels").exists()
    assert not (tmp_path / difficulty_name / "solutions").exists()


def _solved_recipe(family_name: str, difficulty_name: str):
    preset = DifficultyService().get_preset(difficulty_name)
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe("level_999", preset, RandomSource(11), family.variants[0])
    return AbstractPuzzleSolverService().solve(recipe, preset)


def _outgoing(recipe) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for edge in recipe.edges:
        grouped.setdefault(edge.from_node_id, []).append(edge.to_node_id)
    return {node_id: tuple(targets) for node_id, targets in grouped.items()}


def _edge_pairs(recipe) -> set[tuple[str, str]]:
    return {(edge.from_node_id, edge.to_node_id) for edge in recipe.edges}


def _is_meaningful_long_detour_node(node_id: str) -> bool:
    return (
        node_id in {"package", "rejoin"}
        or "switch" in node_id
        or "detour" in node_id
        or "gate" in node_id
    )
