from __future__ import annotations

from collections import Counter

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.return_loop_template import ReturnLoopTemplate


def test_return_loop_repeats_switch_tap_with_safe_spacing() -> None:
    preset = DifficultyService().get_preset("medium")
    generated = ReturnLoopTemplate().generate("level_012", 12, preset, RandomSource(4))
    tap_counts = Counter(action.tapNodeID for action in generated.solution.actions)
    times = [action.timeSeconds for action in generated.solution.actions]

    assert tap_counts["alpha_switch"] == 2
    assert min(b - a for a, b in zip(times, times[1:])) >= preset.min_tap_spacing_seconds
    assert generated.level_document.parTaps == len(generated.solution.actions)
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
