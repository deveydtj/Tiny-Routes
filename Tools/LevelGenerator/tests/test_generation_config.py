from __future__ import annotations

from app.generation_config import GenerationConfig


def test_generation_config_defaults_use_recipe_pipeline_breadth() -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
    )

    assert not hasattr(config, "generation_mode")
    assert config.recipe_pool_size == 4
    assert config.layouts_per_recipe == 2
    assert config.road_shapes_per_layout == 2
    assert config.layout_orientation_preference == "portrait_vertical"
    assert config.layout_size_profile == "difficulty_curve"
    assert config.vertical_route_probability == 0.35
    assert config.prefer_vertical_for_long_routes is True
    assert config.candidate_pool_size == 4
    assert config.max_attempts_per_level == 120
    assert config.playtest_portfolio is False
    assert config.playtest_uniqueness_window == 6


def test_generation_config_validates_layout_orientation() -> None:
    try:
        GenerationConfig(start_level_number=12, count=1, difficulty="easy", layout_orientation_preference="diagonal")
    except ValueError as exc:
        assert "layout_orientation_preference" in str(exc)
    else:
        raise AssertionError("Expected invalid orientation to raise ValueError")


def test_generation_config_accepts_large_portrait_layout_size_profile() -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
        layout_size_profile="large-portrait",
    )

    assert config.layout_size_profile == "large_portrait"


def test_generation_config_validates_layout_size_profile() -> None:
    try:
        GenerationConfig(start_level_number=12, count=1, difficulty="easy", layout_size_profile="giant")
    except ValueError as exc:
        assert "layout_size_profile" in str(exc)
    else:
        raise AssertionError("Expected invalid layout size profile to raise ValueError")


def test_generation_config_validates_vertical_route_probability() -> None:
    try:
        GenerationConfig(start_level_number=12, count=1, difficulty="easy", vertical_route_probability=1.2)
    except ValueError as exc:
        assert "vertical_route_probability" in str(exc)
    else:
        raise AssertionError("Expected invalid probability to raise ValueError")


def test_generation_config_accepts_playtest_portfolio_mode() -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=50,
        difficulty="auto",
        playtest_portfolio=True,
        playtest_uniqueness_window=12,
    )

    assert config.playtest_portfolio is True
    assert config.playtest_uniqueness_window == 12
