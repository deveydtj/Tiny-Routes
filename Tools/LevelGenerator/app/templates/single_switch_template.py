from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from .base_template import LevelTemplate


class SingleSwitchTemplate(LevelTemplate):
    name = "single_switch"

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name in {"tutorial", "easy"}

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        include_approach = preset.name != "tutorial"
        positions = {
            "start": (-1.1, 0.0),
            "approach": (-0.55, 0.0),
            "choice": (0.0, 0.0),
            "dead_end_a": (0.75, -0.65),
            "package": (0.72, 0.55),
            "destination": (1.1, 0.95),
        }
        if rng.bool(0.5):
            positions = {node_id: (x, -y) for node_id, (x, y) in positions.items()}

        node_ids = ["start"]
        if include_approach:
            node_ids.append("approach")
        node_ids.extend(["choice", "dead_end_a", "package", "destination"])
        for node_id in node_ids:
            builder.add_node(node_id, *positions[node_id])

        if include_approach:
            builder.add_edge("start", "approach")
            builder.add_edge("approach", "choice")
        else:
            builder.add_edge("start", "choice")
        builder.add_edge("choice", "dead_end_a")
        builder.add_edge("choice", "package")
        builder.add_edge("package", "destination")

        route = ["start"] + (["approach"] if include_approach else []) + ["choice", "package", "destination"]
        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=1,
        )
        solution = self.solution_builder.build_tap_solution(
            level_id,
            ["choice"],
            preset,
            "Rotate choice once so the route collects the package before heading to destination.",
            times=[0.4],
        )
        return self.generated(level, solution, preset, rng.seed)
