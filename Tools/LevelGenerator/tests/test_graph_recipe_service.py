from __future__ import annotations

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.graph_recipe_service import GraphRecipeService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService


def test_graph_recipe_validate_requires_start_package_destination_order() -> None:
    recipe = GraphRecipe(
        level_id="level_001",
        difficulty="easy",
        nodes=(
            GraphRecipeNode("start"),
            GraphRecipeNode("destination"),
            GraphRecipeNode("package"),
        ),
        edges=(GraphRecipeEdge("start", "destination"), GraphRecipeEdge("destination", "package")),
        required_path=("start", "destination", "package"),
        tap_node_ids=(),
    )

    assert "required_path_must_end_at_destination" in recipe.validate()
    assert "required_path_must_visit_package_before_destination" in recipe.validate()


def test_graph_recipe_service_generates_difficulty_recipe() -> None:
    preset = DifficultyService().get_preset("medium")
    recipe = GraphRecipeService().generate_recipe("level_012", preset, RandomSource(4))

    assert recipe.required_path[0] == "start"
    assert recipe.required_path[-1] == "destination"
    assert "package" in recipe.required_path
    assert recipe.validate() == []


def test_recipe_to_level_builder_builds_valid_generated_level() -> None:
    preset = DifficultyService().get_preset("easy")
    recipe = GraphRecipeService().generate_recipe("level_012", preset, RandomSource(2))
    generated = RecipeToLevelBuilderService().build_level(recipe, level_number=12, seed=2)

    assert generated.template_name == "graph_recipe"
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
