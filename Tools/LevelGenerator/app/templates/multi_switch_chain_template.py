from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from .base_template import LevelTemplate


class MultiSwitchChainTemplate(LevelTemplate):
    name = "multi_switch_chain"

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name in {"medium", "hard"}

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        variant = rng.choice(["zigzag", "stair_step", "split_dead_ends"])
        required_switch_count = rng.randint(2, 3) if preset.name == "medium" else rng.randint(3, 4)
        switch_ids = [f"{variant}_switch_{chr(ord('a') + index)}" for index in range(required_switch_count)]
        builder = self.builder()

        core_route = ["start", switch_ids[0], "package"] + switch_ids[1:] + ["destination"]
        x_step = 2.2 / (len(core_route) - 1)
        positions: dict[str, tuple[float, float]] = {}
        for index, node_id in enumerate(core_route):
            y = _route_y_for_variant(variant, index, len(core_route))
            if node_id == "package":
                y = 0.58 if variant != "stair_step" else 0.34
            if node_id == "destination":
                y = _destination_y_for_variant(variant)
            positions[node_id] = (round(-1.1 + (index * x_step), 4), y)
        for index, switch_id in enumerate(switch_ids):
            dead_id = f"{variant}_dead_end_{chr(ord('a') + index)}"
            switch_x, switch_y = positions[switch_id]
            dead_y = _dead_end_y_for_variant(variant, index, switch_y)
            positions[dead_id] = (switch_x, dead_y)

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        builder.add_edge("start", switch_ids[0])
        for index, switch_id in enumerate(switch_ids):
            dead_id = f"{variant}_dead_end_{chr(ord('a') + index)}"
            builder.add_edge(switch_id, dead_id)
            if index == 0:
                builder.add_edge(switch_id, "package")
            else:
                next_node = switch_ids[index + 1] if index + 1 < len(switch_ids) else "destination"
                builder.add_edge(switch_id, next_node)
            if index == 0 and len(switch_ids) > 1:
                builder.add_edge("package", switch_ids[1])

        route_positions = [positions[node_id] for node_id in core_route]
        time_limit = self.calculate_time_limit(route_positions, preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=required_switch_count,
        )
        tap_times = [round(0.4 + (index * preset.min_tap_spacing_seconds), 2) for index in range(required_switch_count)]
        solution = self.solution_builder.build_tap_solution(
            level_id,
            switch_ids,
            preset,
            "Rotate each chain switch once so the route avoids dead ends and completes delivery.",
            times=tap_times,
        )
        return self.generated(level, solution, preset, rng.seed, notes=[f"Template variant: {variant}"])


def _route_y_for_variant(variant: str, index: int, route_length: int) -> float:
    if variant == "stair_step":
        if route_length <= 1:
            return 0.0
        return round(-0.45 + (index * (0.9 / (route_length - 1))), 4)
    if variant == "split_dead_ends":
        return -0.12 if index % 2 == 0 else 0.28
    return 0.18 if index % 2 == 0 else -0.18


def _destination_y_for_variant(variant: str) -> float:
    if variant == "stair_step":
        return 0.52
    if variant == "split_dead_ends":
        return -0.32
    return 0.35


def _dead_end_y_for_variant(variant: str, index: int, switch_y: float) -> float:
    if variant == "split_dead_ends":
        return 0.92 if index % 2 == 0 else -0.92
    if variant == "stair_step":
        return -0.95 if index % 2 == 0 else 0.95
    return -0.95 if switch_y >= 0 else 0.95
