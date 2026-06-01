from __future__ import annotations

from app.models.recipe_variant_spec import RecipeVariantSpec
from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
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
        legacy_template_name=" Single_Switch ",
        mechanic_tags=(" Single_Switch ",),
        topology_class=" Single_Branch ",
    )

    assert variant.name == "default"
    assert variant.family_name == "single_switch"
    assert variant.legacy_template_name == "single_switch"
    assert variant.supports_difficulty("easy")
    assert variant.mechanic_tags == ("single_switch",)
    assert variant.primary_mechanic_tag == "single_switch"
    assert variant.topology_class == "single_branch"


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
    assert registry.get_family("single_switch").legacy_template_name == "single_switch"


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
        for variant in family.variants:
            assert variant.mechanic_tags, (family_name, variant.name)
            assert variant.primary_mechanic_tag, (family_name, variant.name)
            assert variant.topology_class, (family_name, variant.name)


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
