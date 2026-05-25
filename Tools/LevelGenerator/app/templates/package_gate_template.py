from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from .base_template import LevelTemplate


class PackageGateTemplate(LevelTemplate):
    name = "package_gate"

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name in {"easy", "medium"}

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        positions = {
            "start": (-1.1, 0.25),
            "approach_switch": (-0.45, 0.05),
            "bypass": (0.1, -0.65),
            "package": (0.1, 0.65),
            "finish_switch": (0.65, 0.2),
            "dead_end_a": (1.1, -0.55),
            "destination": (1.1, 0.75),
        }
        if rng.bool(0.4):
            positions = {node_id: (x, -y) for node_id, (x, y) in positions.items()}

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        builder.add_edge("start", "approach_switch")
        builder.add_edge("approach_switch", "bypass")
        builder.add_edge("approach_switch", "package")
        builder.add_edge("package", "finish_switch")
        builder.add_edge("finish_switch", "dead_end_a")
        builder.add_edge("finish_switch", "destination")

        route = ["start", "approach_switch", "package", "finish_switch", "destination"]
        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=2,
        )
        solution = self.solution_builder.build_tap_solution(
            level_id,
            ["approach_switch", "finish_switch"],
            preset,
            "Rotate the approach switch to collect the package, then rotate the finish switch to reach destination.",
            times=[0.4, 0.8],
        )
        return self.generated(level, solution, preset, rng.seed)
