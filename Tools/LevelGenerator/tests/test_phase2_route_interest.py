from __future__ import annotations

from collections import Counter
from dataclasses import replace

from app.generation_config import GenerationConfig
from app.random_source import RandomSource
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.generation_quality_service import GenerationQualityService
from app.services.level_generation_service import LevelGenerationService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService


def test_fake_shortcut_creates_real_tempting_invalid_shortcut() -> None:
    recipe, generated, score = _solved_generated_scored("fake_shortcut", "medium")
    outgoing = _outgoing(recipe)
    audit = score.details["routeInterest"]

    assert "shortcut_dead_end" in outgoing["choice"]
    assert "shortcut_dead_end" not in recipe.required_path
    assert len(recipe.required_path) - 1 > 2
    assert audit["fakeShortcutPresent"] is True
    assert "fake_shortcut" in audit["tags"]


def test_split_path_rejoin_creates_real_branch_and_rejoin() -> None:
    recipe, _, score = _solved_generated_scored("split_path_rejoin", "medium")
    incoming = Counter(edge.to_node_id for edge in recipe.edges)
    audit = score.details["routeInterest"]

    assert set(_outgoing(recipe)["switch_a"]) == {"lower_shortcut", "upper_branch"}
    assert incoming["rejoin"] == 2
    assert "lower_shortcut" not in recipe.required_path
    assert audit["branchRejoinPresent"] is True


def test_long_detour_gate_requires_longer_valid_route_over_obvious_direct_path() -> None:
    recipe, _, score = _solved_generated_scored("long_detour_gate", "medium")
    outgoing = _outgoing(recipe)
    audit = score.details["routeInterest"]

    assert "direct_bypass" in outgoing["switch_gate"]
    assert ("direct_bypass", "rejoin") in _edge_pairs(recipe)
    assert "direct_bypass" not in recipe.required_path
    assert recipe.required_path.index("package") < recipe.required_path.index("destination")
    assert len(recipe.required_path) - 1 > _shortest_edge_count("direct_bypass", "destination", outgoing)
    assert audit["packageGateTensionPresent"] is True
    assert "correct_detour" in audit["tags"]


def test_hub_choice_creates_true_multi_exit_decision_point() -> None:
    recipe, generated, score = _solved_generated_scored("hub_choice", "medium")
    outgoing = _outgoing(recipe)
    audit = score.details["routeInterest"]

    assert set(outgoing["hub"]) == {"dead_end_a", "package_branch", "rejoin"}
    assert len(outgoing["hub"]) == 3
    assert len(set(generated.road_shape_metadata["switchDirectionBuckets"]["hub"].values())) == 3
    assert "multi_exit_hub" in audit["tags"]


def test_package_inside_loop_places_package_on_loop_path() -> None:
    recipe, _, score = _solved_generated_scored("package_inside_loop", "hard")
    route_counts = Counter(recipe.required_path)
    audit = score.details["routeInterest"]

    assert route_counts["loop_entry_switch"] == 2
    assert recipe.required_path.index("outer_loop") < recipe.required_path.index("package")
    assert recipe.required_path.index("package") < recipe.required_path.index("loop_return")
    assert ("loop_return", "loop_entry_switch") in _edge_pairs(recipe)
    assert audit["loopRevisitPresent"] is True
    assert "loop_or_revisit" in audit["tags"]


def test_two_phase_route_separates_package_collection_from_destination_routing() -> None:
    recipe, _, score = _solved_generated_scored("two_phase_route", "hard")
    audit = score.details["routeInterest"]
    package_index = recipe.required_path.index("package")

    assert recipe.required_path.index("phase_one_switch") < package_index
    assert package_index < recipe.required_path.index("exit_choice")
    assert package_index < recipe.required_path.index("switch_final")
    assert ("early_exit", "exit_choice") in _edge_pairs(recipe)
    assert "two_phase" in recipe.mechanic_tags
    assert audit["branchRejoinPresent"] is True
    assert audit["packageGateTensionPresent"] is True


def test_route_interest_scoring_prefers_phase2_patterns_over_simple_chains() -> None:
    preset = DifficultyService().get_preset("hard")
    chain = _generated_candidate("multi_switch_chain", "hard", "level_901", 901)
    detour = _generated_candidate("two_phase_route", "hard", "level_902", 902)
    quality = GenerationQualityService()

    chain_score = quality.score(chain, preset)
    detour_score = quality.score(detour, preset)

    assert detour_score.route_interest > chain_score.route_interest
    assert "difficulty_from_switch_count_only" in chain_score.penalties
    assert "two_phase" in detour_score.details["routeInterest"]["tags"] or detour_score.details["routeInterest"]["branchRejoinPresent"]


def test_hard_candidates_below_minimum_route_interest_are_rejected() -> None:
    candidate = _scored_candidate("hub_choice", "hard", "level_903", 903)
    quality = candidate.quality_score
    assert quality is not None

    candidate.quality_score = replace(
        quality,
        route_interest=0.10,
        details={
            **quality.details,
            "routeInterest": {
                **quality.details["routeInterest"],
                "score": 0.10,
                "tags": [],
            },
        },
    )

    rejection = LevelGenerationService()._quality_rejection(candidate)

    assert rejection is not None
    assert rejection[0] == "route_interest_below_hard_gate"


def test_expert_candidates_below_minimum_route_interest_are_rejected() -> None:
    candidate = _scored_candidate("four_way_intro", "expert", "level_907", 907)
    quality = candidate.quality_score
    assert quality is not None

    candidate.quality_score = replace(
        quality,
        route_interest=0.10,
        details={
            **quality.details,
            "routeInterest": {
                **quality.details["routeInterest"],
                "score": 0.10,
                "tags": [],
            },
        },
    )

    rejection = LevelGenerationService()._quality_rejection(candidate)

    assert rejection is not None
    assert rejection[0] == "route_interest_below_expert_gate"


def test_hard_multi_switch_chain_two_switch_order_with_weak_interest_is_rejected() -> None:
    candidate = _scored_candidate("multi_switch_chain", "hard", "level_904", 904)
    quality = candidate.quality_score
    assert quality is not None
    assert candidate.topology_class == "two_switch_order"
    assert quality.route_interest < DifficultyService().get_preset("hard").minimum_route_interest_score

    rejection = LevelGenerationService()._quality_rejection(candidate)

    assert rejection is not None
    assert rejection[0] == "boring_topology_for_difficulty"


def test_expert_large_portrait_without_puzzle_need_is_rejected() -> None:
    candidate = _scored_candidate(
        "four_way_intro",
        "expert",
        "level_905",
        905,
        layout_orientation_preference="portrait_vertical",
        layout_size_profile="large_portrait",
    )
    quality = candidate.quality_score
    assert quality is not None
    assert quality.details["presetContentFit"]["largeMapFit"]["penalties"] == (
        "large_portrait_without_puzzle_need",
    )

    rejection = LevelGenerationService()._quality_rejection(candidate)

    assert rejection is not None
    assert rejection[0] == "large_portrait_without_puzzle_need"


def test_large_portrait_with_high_interest_structure_can_still_pass_quality_gate() -> None:
    candidate = _scored_candidate(
        "hub_choice",
        "hard",
        "level_906",
        906,
        layout_orientation_preference="portrait_vertical",
        layout_size_profile="large_portrait",
    )
    quality = candidate.quality_score
    assert quality is not None
    assert quality.route_interest == 1.0
    assert quality.details["presetContentFit"]["largeMapFit"]["penalties"] == ()

    assert LevelGenerationService()._quality_rejection(candidate) is None


def test_recipe_first_generation_is_deterministic_for_fixed_seed(tmp_path) -> None:
    first = _dry_run_auto(tmp_path / "first")
    second = _dry_run_auto(tmp_path / "second")

    first_summary = [
        (level.level_id, level.recipe_family, level.recipe_variant, level.topology_class, level.seed)
        for level in first.accepted
    ]
    second_summary = [
        (level.level_id, level.recipe_family, level.recipe_variant, level.topology_class, level.seed)
        for level in second.accepted
    ]

    assert first.passed is True
    assert second.passed is True
    assert first_summary == second_summary


def test_phase2_families_still_pass_strict_generator_validation() -> None:
    for family_name, difficulty_name in [
        ("fake_shortcut", "medium"),
        ("split_path_rejoin", "medium"),
        ("long_detour_gate", "medium"),
        ("hub_choice", "medium"),
        ("package_inside_loop", "hard"),
        ("two_phase_route", "hard"),
    ]:
        _, generated, _ = _solved_generated_scored(family_name, difficulty_name)
        validation = GeneratedLevelValidationService().validate(
            generated,
            preset=DifficultyService().get_preset(difficulty_name),
            overwrite=True,
        )
        assert not validation.has_errors, (family_name, validation.error_codes)


def _dry_run_auto(base_path):
    return LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=20,
            count=3,
            difficulty="medium",
            template_name="mixed",
            seed=4242,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=base_path / "levels",
            solutions_output_dir=base_path / "solutions",
            report_path=base_path / "report.md",
            json_report_path=base_path / "report.json",
            max_attempts_per_level=50,
            candidate_pool_size=2,
            recipe_pool_size=3,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
        )
    )


def _solved_generated_scored(family_name: str, difficulty_name: str):
    recipe, generated = _solved_recipe_and_generated(family_name, difficulty_name, "level_999", 999)
    preset = DifficultyService().get_preset(difficulty_name)
    score = GenerationQualityService().score(generated, preset)
    return recipe, generated, score


def _generated_candidate(family_name: str, difficulty_name: str, level_id: str, level_number: int):
    _, generated = _solved_recipe_and_generated(family_name, difficulty_name, level_id, level_number)
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    return generated


def _scored_candidate(
    family_name: str,
    difficulty_name: str,
    level_id: str,
    level_number: int,
    *,
    layout_orientation_preference: str = "horizontal",
    layout_size_profile: str = "standard_portrait",
):
    _, generated = _solved_recipe_and_generated(
        family_name,
        difficulty_name,
        level_id,
        level_number,
        layout_orientation_preference=layout_orientation_preference,
        layout_size_profile=layout_size_profile,
    )
    preset = DifficultyService().get_preset(difficulty_name)
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    generated.quality_score = GenerationQualityService().score(generated, preset)
    return generated


def _solved_recipe_and_generated(
    family_name: str,
    difficulty_name: str,
    level_id: str,
    level_number: int,
    *,
    layout_orientation_preference: str = "horizontal",
    layout_size_profile: str = "standard_portrait",
):
    preset = DifficultyService().get_preset(difficulty_name)
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe(level_id, preset, RandomSource(11), family.variants[0])
    recipe = AbstractPuzzleSolverService().solve(recipe, preset)
    generated = RecipeToLevelBuilderService().build_level(
        recipe,
        level_number,
        seed=22,
        layout_orientation_preference=layout_orientation_preference,
        layout_size_profile=layout_size_profile,
    )
    validation_preset = RecipeToLevelBuilderService()._preset_for_layout_size_profile(preset, layout_size_profile)
    validation = GeneratedLevelValidationService().validate(generated, preset=validation_preset, overwrite=True)
    assert not validation.has_errors, (family_name, validation.error_codes)
    return recipe, generated


def _outgoing(recipe) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for edge in recipe.edges:
        grouped.setdefault(edge.from_node_id, []).append(edge.to_node_id)
    return {node_id: tuple(targets) for node_id, targets in grouped.items()}


def _edge_pairs(recipe) -> set[tuple[str, str]]:
    return {(edge.from_node_id, edge.to_node_id) for edge in recipe.edges}


def _shortest_edge_count(start_node_id: str, destination_node_id: str, outgoing: dict[str, tuple[str, ...]]) -> int:
    frontier = [(start_node_id, 0)]
    seen = {start_node_id}
    while frontier:
        node_id, distance = frontier.pop(0)
        if node_id == destination_node_id:
            return distance
        for next_node_id in outgoing.get(node_id, ()):
            if next_node_id in seen:
                continue
            seen.add(next_node_id)
            frontier.append((next_node_id, distance + 1))
    raise AssertionError(f"No route from {start_node_id} to {destination_node_id}")
