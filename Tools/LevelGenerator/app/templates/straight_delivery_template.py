from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from .base_template import LevelTemplate


class StraightDeliveryTemplate(LevelTemplate):
    name = "straight_delivery"

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name == "tutorial"

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        intermediate_count = rng.randint(0, 2)
        route_ids = ["start"] + [f"node_{chr(ord('a') + index)}" for index in range(intermediate_count)] + [
            "package",
            "destination",
        ]
        base_positions = [
            (-1.0, 0.45),
            (-0.35, 0.15),
            (0.25, -0.25),
            (0.9, -0.65),
            (1.1, -0.95),
        ]
        positions = _spread_positions(route_ids, base_positions)
        layout_variant = self.apply_layout_variant(positions, preset, rng)
        positions = layout_variant.positions

        for node_id in route_ids:
            builder.add_node(node_id, *positions[node_id])
        for from_node, to_node in zip(route_ids, route_ids[1:]):
            builder.add_edge(from_node, to_node)

        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route_ids], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=0,
        )
        solution = self.solution_builder.build_no_tap_solution(level_id)
        return self.generated(level, solution, preset, rng.seed, notes=[f"Layout variant: {layout_variant.name}"])


def _spread_positions(route_ids: list[str], base_positions: list[tuple[float, float]]) -> dict[str, tuple[float, float]]:
    if len(route_ids) == 3:
        selected = [base_positions[0], base_positions[2], base_positions[4]]
    elif len(route_ids) == 4:
        selected = [base_positions[0], base_positions[1], base_positions[3], base_positions[4]]
    else:
        selected = base_positions
    return dict(zip(route_ids, selected))
