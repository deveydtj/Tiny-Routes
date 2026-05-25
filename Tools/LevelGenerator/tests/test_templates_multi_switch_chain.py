from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.multi_switch_chain_template import MultiSwitchChainTemplate


def test_multi_switch_chain_medium_and_hard_variants_validate() -> None:
    template = MultiSwitchChainTemplate()
    validator = GeneratedLevelValidationService()
    for difficulty, seed in [("medium", 5), ("hard", 6)]:
        preset = DifficultyService().get_preset(difficulty)
        generated = template.generate("level_012", 12, preset, RandomSource(seed))

        assert preset.required_tap_range[0] <= len(generated.solution.actions) <= preset.required_tap_range[1]
        assert generated.level_document.parTaps == len(generated.solution.actions)
        assert not validator.validate(generated, preset=preset, overwrite=True).has_errors
