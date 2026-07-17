from __future__ import annotations

import pytest

from app.generation_config import GenerationConfig
from app.gui.gui_state import GuiGenerationState, parse_positive_int, parse_probability, to_generation_config


def test_parse_positive_int_accepts_valid_integer() -> None:
    assert parse_positive_int("12", "Start") == 12


def test_parse_positive_int_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Start is required"):
        parse_positive_int("", "Start")


def test_parse_positive_int_rejects_non_numeric_value() -> None:
    with pytest.raises(ValueError, match="Start must be a whole number"):
        parse_positive_int("abc", "Start")


@pytest.mark.parametrize("value", ["0", "-1"])
def test_parse_positive_int_rejects_zero_and_negative_values(value: str) -> None:
    with pytest.raises(ValueError, match="Start must be greater than zero"):
        parse_positive_int(value, "Start")


def test_parse_probability_accepts_probability() -> None:
    assert parse_probability("0.35", "Vertical route probability") == 0.35


@pytest.mark.parametrize("value", ["", "abc", "-0.1", "1.1"])
def test_parse_probability_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_probability(value, "Vertical route probability")


def test_default_gui_state_converts_to_generation_config() -> None:
    config = to_generation_config(GuiGenerationState())

    assert isinstance(config, GenerationConfig)
    assert config.start_level_number == 12
    assert config.count == 1
    assert config.difficulty == "tutorial"
    assert config.template_name == "mixed"
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
    assert config.dry_run is True


def test_blank_seed_becomes_none(tmp_path) -> None:
    config = to_generation_config(_state_with_paths(tmp_path, seed=""))

    assert config.seed is None


def test_numeric_seed_becomes_integer(tmp_path) -> None:
    config = to_generation_config(_state_with_paths(tmp_path, seed="42"))

    assert config.seed == 42


def test_invalid_seed_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="Seed must be a whole number"):
        to_generation_config(_state_with_paths(tmp_path, seed="abc"))


def test_invalid_start_level_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="Start level number must be a whole number"):
        to_generation_config(_state_with_paths(tmp_path, start_level_number="abc"))


def test_invalid_count_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="Count must be greater than zero"):
        to_generation_config(_state_with_paths(tmp_path, count="0"))


def test_invalid_max_attempts_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="Max attempts per level must be greater than zero"):
        to_generation_config(_state_with_paths(tmp_path, max_attempts_per_level="-1"))


def test_gui_state_converts_layout_orientation_controls(tmp_path) -> None:
    config = to_generation_config(
        _state_with_paths(
            tmp_path,
            layout_orientation_preference="vertical",
            layout_size_profile="large_portrait",
            vertical_route_probability="0.8",
            prefer_vertical_for_long_routes=False,
        )
    )

    assert config.layout_orientation_preference == "vertical"
    assert config.layout_size_profile == "large_portrait"
    assert config.vertical_route_probability == 0.8
    assert config.prefer_vertical_for_long_routes is False
    assert "--layout-orientation" in config.command_arguments
    assert "--layout-size-profile" in config.command_arguments
    assert "--no-prefer-vertical-for-long-routes" in config.command_arguments


def _state_with_paths(tmp_path, **kwargs) -> GuiGenerationState:
    state = GuiGenerationState(
        levels_output_dir=str(tmp_path / "levels"),
        solutions_output_dir=str(tmp_path / "solutions"),
        report_path=str(tmp_path / "report.md"),
        json_report_path=str(tmp_path / "report.json"),
    )
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state
