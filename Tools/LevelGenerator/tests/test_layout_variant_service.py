from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.layout_variant_service import LayoutVariantService


def test_layout_variant_service_supports_named_variants() -> None:
    service = LayoutVariantService()
    preset = DifficultyService().get_preset("easy")
    positions = {"start": (-1.0, 0.0), "package": (0.0, 0.4), "destination": (1.0, 0.8)}

    for index, variant_name in enumerate(service.variant_names):
        result = service.apply_variant(variant_name, positions, RandomSource(index), preset)

        assert result.name in service.variant_names
        assert set(result.positions) == set(positions)


def test_layout_variant_service_falls_back_when_variant_would_not_fit() -> None:
    service = LayoutVariantService()
    preset = DifficultyService().get_preset("easy")
    positions = {"a": (-1.2, -1.3), "b": (1.2, 1.0)}

    result = service.apply_variant("offset", positions, RandomSource(1), preset)

    assert result.name in service.variant_names
    assert set(result.positions) == {"a", "b"}
