from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.ring_route_template import RingRouteTemplate


def test_ring_route_fixed_seed_validates_and_requires_swift() -> None:
    preset = DifficultyService().get_preset("hard")
    generated = RingRouteTemplate().generate("level_012", 12, preset, RandomSource(7))

    assert generated.requires_swift_validation is True
    assert generated.switch_count >= 3
    assert generated.level_document.parTaps == 3
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
