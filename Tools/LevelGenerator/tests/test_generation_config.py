from __future__ import annotations

from app.generation_config import GenerationConfig


def test_generation_config_defaults_use_recipe_first_breadth() -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
    )

    assert config.generation_mode == "recipe_first"
    assert config.recipe_pool_size == 4
    assert config.layouts_per_recipe == 3
    assert config.road_shapes_per_layout == 3
    assert config.candidate_pool_size == 25
    assert config.max_attempts_per_level == 300


def test_generation_config_still_accepts_explicit_legacy_template_mode() -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
        generation_mode="legacy-template",
    )

    assert config.generation_mode == "legacy_template"
    assert config.uses_legacy_templates is True
