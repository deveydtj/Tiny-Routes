from __future__ import annotations

from dataclasses import dataclass

from ..models.difficulty_preset import DifficultyPreset
from ..random_source import RandomSource
from .graph_layout_service import BoundingBox, GraphLayoutService


@dataclass(frozen=True)
class LayoutVariantResult:
    name: str
    positions: dict[str, tuple[float, float]]


class LayoutVariantService:
    variant_names = ["normal", "mirrored", "wide", "tall", "offset", "jittered"]

    def apply_random_variant(
        self,
        positions: dict[str, tuple[float, float]],
        rng: RandomSource,
        preset: DifficultyPreset,
    ) -> LayoutVariantResult:
        return self.apply_variant(rng.choice(self.variant_names), positions, rng, preset)

    def apply_variant(
        self,
        variant_name: str,
        positions: dict[str, tuple[float, float]],
        rng: RandomSource,
        preset: DifficultyPreset,
    ) -> LayoutVariantResult:
        layout = GraphLayoutService(
            bounds=BoundingBox(*preset.coordinate_bounds),
            minimum_node_distance=preset.minimum_node_distance,
        )
        variant = variant_name if variant_name in self.variant_names else "normal"
        transformed = dict(positions)

        if variant == "mirrored":
            transformed = (
                layout.mirror_horizontally(positions)
                if rng.bool(0.5)
                else layout.mirror_vertically(positions)
            )
        elif variant == "wide":
            transformed = layout.scale_positions(positions, scale_x=1.06, scale_y=0.96)
        elif variant == "tall":
            transformed = layout.scale_positions(positions, scale_x=0.96, scale_y=1.06)
        elif variant == "offset":
            transformed = layout.translate_positions(
                positions,
                rng.choice([-0.08, -0.04, 0.04, 0.08]),
                rng.choice([-0.08, -0.04, 0.04, 0.08]),
            )
        elif variant == "jittered":
            transformed = layout.apply_safe_jitter(positions, rng, amount=0.045)

        if layout.validate_positions(transformed):
            normalized = layout.normalize_positions(transformed, padding=0.08)
            if not layout.validate_positions(normalized):
                return LayoutVariantResult(name=variant, positions=normalized)
            return LayoutVariantResult(name="normal", positions=dict(positions))
        return LayoutVariantResult(name=variant, positions=transformed)
