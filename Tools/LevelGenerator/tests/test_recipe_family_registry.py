from __future__ import annotations

import pytest

from app.models.recipe_lifecycle import RecipeLifecycleStatus
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.models.recipe_variant_spec import RecipeVariantSpec
from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry, expanded_recipe_family as expanded_recipe_family_module
from app.recipes.expanded_recipe_family import expanded_recipe_family_definitions
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService


def test_recipe_variant_spec_normalizes_names() -> None:
    variant = RecipeVariantSpec(
        name=" Default ",
        family_name=" Single_Switch ",
        difficulty_names=(" Easy ",),
        topology_rules=_simple_topology_rules(),
        mechanic_tags=(" Single_Switch ",),
        topology_class=" Single_Branch ",
    )

    assert variant.name == "default"
    assert variant.family_name == "single_switch"
    assert variant.supports_difficulty("easy")
    assert variant.mechanic_tags == ("single_switch",)
    assert variant.primary_mechanic_tag == "single_switch"
    assert variant.topology_class == "single_branch"
    assert variant.topology_rules.allowsCycles is False
    assert variant.mechanic_metadata()["topologyRules"]["allowsCycles"] is False


def test_recipe_variant_spec_requires_topology_rules() -> None:
    with pytest.raises(ValueError, match="topology rules are required"):
        RecipeVariantSpec(
            name="missing_rules",
            family_name="single_switch",
            difficulty_names=("easy",),
            topology_rules=None,
        )


def test_recipe_family_registry_exposes_current_template_families() -> None:
    registry = RecipeFamilyRegistry()

    family_names = registry.valid_family_names()
    assert "mixed" in family_names
    assert {
        "four_way_intersection",
        "multi_switch_chain",
        "package_gate",
        "return_loop",
        "ring_route",
        "single_switch",
        "straight_delivery",
    }.issubset(family_names)
    assert {
        "straight_delivery_intro",
        "single_switch_intro",
        "single_switch_wrong_dead_end",
        "package_before_destination_intro",
        "single_switch_package_choice",
        "two_switch_order_intro",
        "short_detour_gate",
        "safe_dead_end_choice",
        "package_gate_simple",
        "multi_switch_order",
        "package_gate_double_choice",
        "return_loop_intro",
        "split_path_rejoin",
        "fake_shortcut",
        "hub_choice",
        "long_detour_gate",
        "return_loop_with_gate",
        "ring_route_gate",
        "multi_switch_revisit",
        "package_inside_loop",
        "two_phase_route",
        "branch_then_rejoin_with_wrong_order",
        "four_way_intro",
        "four_way_package_gate",
        "four_way_ring",
        "multi_four_way_route",
        "controlled_repeated_taps",
        "late_route_reversal",
    }.issubset(family_names)


def test_expanded_families_remove_behavior_isomorphic_alternates() -> None:
    registry = RecipeFamilyRegistry()

    assert not hasattr(expanded_recipe_family_module, "_swap_dead_end_order")
    for definition in expanded_recipe_family_definitions():
        variants = registry.get_family(definition.name).variants
        assert tuple(variant.name for variant in variants) == (
            f"{definition.name}_primary",
        )


def test_every_fixed_recipe_family_and_variant_has_explicit_lifecycle_status() -> None:
    registry = RecipeFamilyRegistry()
    records = registry.lifecycle_records()
    expected_record_count = sum(
        1 + len(registry.get_family(family_name).variants)
        for family_name in registry.valid_family_names()
        if family_name != "mixed"
    )

    assert len(records) == expected_record_count
    assert len(
        {(record.family_name, record.variant_name) for record in records}
    ) == len(records)
    assert {record.status for record in records} == {
        RecipeLifecycleStatus.FIXTURE_ONLY,
        RecipeLifecycleStatus.DEPRECATED,
    }
    assert registry.production_v3_families() == ()

    for record in records:
        assert record.reason
        assert record.to_dict()["status"] == record.status.value
        if record.family_name in registry.quarantined_family_names():
            assert record.status is RecipeLifecycleStatus.DEPRECATED
        else:
            assert record.status is RecipeLifecycleStatus.FIXTURE_ONLY


def test_recipe_family_registry_filters_by_difficulty() -> None:
    preset = DifficultyService().get_preset("tutorial")
    supported = {family.name for family in RecipeFamilyRegistry().supported_families(preset)}

    assert {
        "straight_delivery",
        "single_switch",
        "straight_delivery_intro",
        "single_switch_intro",
        "single_switch_wrong_dead_end",
        "package_before_destination_intro",
    } == supported


def test_every_registered_recipe_family_exposes_mechanic_and_topology_metadata() -> None:
    registry = RecipeFamilyRegistry()

    for family_name in registry.valid_family_names():
        if family_name == "mixed":
            continue
        family = registry.get_family(family_name)

        assert family.mechanic_tags, family_name
        assert family.primary_mechanic_tag, family_name
        assert family.topology_class, family_name
        assert family.topology_rules, family_name
        for variant in family.variants:
            assert variant.mechanic_tags, (family_name, variant.name)
            assert variant.primary_mechanic_tag, (family_name, variant.name)
            assert variant.topology_class, (family_name, variant.name)
            assert variant.topology_rules, (family_name, variant.name)
            assert variant.mechanic_metadata()["topologyRules"]["requiresUniqueSolution"] is True


def test_tutorial_and_easy_recipe_families_disallow_cycles() -> None:
    registry = RecipeFamilyRegistry()
    difficulty = DifficultyService()

    for difficulty_name in ("tutorial", "easy"):
        preset = difficulty.get_preset(difficulty_name)
        for family in registry.supported_families(preset):
            for variant in family.variants_for_difficulty(preset):
                assert variant.topology_rules.allows_cycles is False, (difficulty_name, family.name, variant.name)
                assert variant.topology_rules.allowed_cycle_count == 0, (difficulty_name, family.name, variant.name)


def test_advanced_loop_ring_and_revisit_families_declare_topology_permissions() -> None:
    registry = RecipeFamilyRegistry()

    revisit_families = {
        "return_loop",
        "return_loop_with_gate",
        "multi_switch_revisit",
        "package_inside_loop",
        "four_way_intro",
        "controlled_repeated_taps",
        "late_route_reversal",
    }
    for family_name in revisit_families:
        rules = registry.get_family(family_name).topology_rules
        assert rules.allows_cycles is True, family_name
        assert rules.allows_revisit is True, family_name
        assert rules.allows_return_path is True, family_name

    ring_families = {"ring_route", "four_way_ring"}
    for family_name in ring_families:
        rules = registry.get_family(family_name).topology_rules
        assert rules.allows_cycles is True, family_name
        assert rules.allows_ring is True, family_name
        assert rules.requires_swift_runtime_validation is True, family_name


def test_topology_name_mismatches_do_not_claim_loop_permissions() -> None:
    registry = RecipeFamilyRegistry()

    for family_name in ("return_loop_intro", "ring_route_gate", "branch_then_rejoin_with_wrong_order"):
        rules = registry.get_family(family_name).topology_rules
        assert rules.allows_cycles is False, family_name
        assert rules.allows_ring is False, family_name


def test_recipe_family_generates_valid_graph_recipe() -> None:
    preset = DifficultyService().get_preset("easy")
    family = RecipeFamilyRegistry().choose_family("single_switch", preset, RandomSource(1))
    recipe = family.generate_recipe("level_012", preset, RandomSource(1))

    assert recipe.family_name == "single_switch"
    assert recipe.variant_name.startswith("single_switch_")
    assert recipe.required_path[0] == "start"
    assert recipe.required_path[-1] == "destination"
    assert recipe.mechanic_tags
    assert recipe.primary_mechanic_tag == "single_switch"
    assert recipe.topology_class == "single_branch"
    assert recipe.mechanic_metadata["primaryMechanicTag"] == "single_switch"
    assert recipe.mechanic_metadata["topologyClass"] == "single_branch"
    assert recipe.mechanic_metadata["topologyRules"]["allowsCycles"] is False
    assert recipe.topology_rules is not None
    assert recipe.validate() == []


def test_expanded_recipe_families_solve_layout_and_validate() -> None:
    difficulty = DifficultyService()
    solver = AbstractPuzzleSolverService()
    builder = RecipeToLevelBuilderService()
    validator = GeneratedLevelValidationService()
    registry = RecipeFamilyRegistry()

    for index, definition in enumerate(expanded_recipe_family_definitions()):
        preset = difficulty.get_preset(definition.difficulty_names[0])
        family = registry.get_family(definition.name)
        recipe = family.generate_recipe("level_999", preset, RandomSource(100 + index), family.variants[0])
        solved = solver.solve(recipe, preset)
        generated = builder.build_level(solved, 999, seed=200 + index)
        result = validator.validate(generated, preset=preset, overwrite=True)

        assert not result.has_errors, (definition.name, result.error_codes)
        assert generated.recipe_family == definition.name
        assert generated.mechanic_tags
        assert generated.primary_mechanic_tag
        assert generated.topology_class
        assert generated.mechanic_metadata["intendedMechanic"]
        assert generated.mechanic_metadata["primaryMechanicTag"] == generated.primary_mechanic_tag
        assert generated.mechanic_metadata["topologyClass"] == generated.topology_class
        assert generated.unlock_requirement is not None


def _simple_topology_rules() -> RecipeTopologyRules:
    return RecipeTopologyRules(
        allows_cycles=False,
        allows_rejoin=False,
        allows_revisit=False,
        allows_return_path=False,
        allows_ring=False,
        allowed_cycle_count=0,
        requires_package_gate=False,
        requires_unique_solution=True,
        requires_swift_runtime_validation=False,
    )
