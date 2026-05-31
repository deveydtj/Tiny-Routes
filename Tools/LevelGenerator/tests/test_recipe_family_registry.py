from __future__ import annotations

from app.models.recipe_variant_spec import RecipeVariantSpec
from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
from app.services.difficulty_service import DifficultyService


def test_recipe_variant_spec_normalizes_names() -> None:
    variant = RecipeVariantSpec(
        name=" Default ",
        family_name=" Single_Switch ",
        difficulty_names=(" Easy ",),
        legacy_template_name=" Single_Switch ",
    )

    assert variant.name == "default"
    assert variant.family_name == "single_switch"
    assert variant.legacy_template_name == "single_switch"
    assert variant.supports_difficulty("easy")


def test_recipe_family_registry_exposes_current_template_families() -> None:
    registry = RecipeFamilyRegistry()

    assert registry.valid_family_names() == [
        "four_way_intersection",
        "mixed",
        "multi_switch_chain",
        "package_gate",
        "return_loop",
        "ring_route",
        "single_switch",
        "straight_delivery",
    ]
    assert registry.get_family("single_switch").legacy_template_name == "single_switch"


def test_recipe_family_registry_filters_by_difficulty() -> None:
    preset = DifficultyService().get_preset("tutorial")
    supported = {family.name for family in RecipeFamilyRegistry().supported_families(preset)}

    assert supported == {"straight_delivery", "single_switch"}


def test_recipe_family_generates_valid_graph_recipe() -> None:
    preset = DifficultyService().get_preset("easy")
    family = RecipeFamilyRegistry().choose_family("single_switch", preset, RandomSource(1))
    recipe = family.generate_recipe("level_012", preset, RandomSource(1))

    assert recipe.family_name == "single_switch"
    assert recipe.variant_name.startswith("single_switch_")
    assert recipe.required_path[0] == "start"
    assert recipe.required_path[-1] == "destination"
    assert recipe.validate() == []
