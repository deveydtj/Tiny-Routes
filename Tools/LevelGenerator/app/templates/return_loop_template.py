from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from .base_template import LevelTemplate


class ReturnLoopTemplate(LevelTemplate):
    name = "return_loop"

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name == "medium" and preset.allow_return_loops and preset.allow_repeated_switch_taps

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        positions = {
            "start": (-1.1, 0.0),
            "alpha_switch": (-0.45, 0.0),
            "package": (0.1, 0.75),
            "beta_switch": (0.75, 0.75),
            "return_a": (0.75, -0.55),
            "destination": (-0.05, -1.05),
            "dead_end_a": (1.15, 0.15),
        }
        if rng.bool(0.5):
            positions = {node_id: (-x, y) for node_id, (x, y) in positions.items()}

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        builder.add_edge("start", "alpha_switch")
        builder.add_edge("alpha_switch", "destination")
        builder.add_edge("alpha_switch", "package")
        builder.add_edge("package", "beta_switch")
        builder.add_edge("beta_switch", "dead_end_a")
        builder.add_edge("beta_switch", "return_a")
        builder.add_edge("return_a", "alpha_switch")

        route = ["start", "alpha_switch", "package", "beta_switch", "return_a", "alpha_switch", "destination"]
        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=3,
        )
        solution = self.solution_builder.build_tap_solution(
            level_id,
            ["alpha_switch", "beta_switch", "alpha_switch"],
            preset,
            "Rotate alpha to collect the package, rotate beta onto the return path, then rotate alpha again for destination.",
            times=[0.4, 1.2, 2.0],
        )
        return self.generated(level, solution, preset, rng.seed)
