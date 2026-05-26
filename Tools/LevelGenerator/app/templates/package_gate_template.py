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
        variant = rng.choice(_variants_for(preset.name))
        positions, edges, tap_node_ids, route = _variant_spec(variant)
        if rng.bool(0.4):
            positions = {node_id: (x, -y) for node_id, (x, y) in positions.items()}

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        for from_node_id, to_node_id in edges:
            builder.add_edge(from_node_id, to_node_id)

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
            tap_node_ids,
            preset,
            "Rotate the approach switch to collect the package, then rotate the finish switch to reach destination.",
            times=[0.4, 0.8],
        )
        return self.generated(level, solution, preset, rng.seed, notes=[f"Template variant: {variant}"])


def _variants_for(difficulty_name: str) -> list[str]:
    variants = ["classic", "upper_package", "lower_package", "left_entry", "right_entry", "short_gate"]
    if difficulty_name == "medium":
        variants.append("long_gate")
    return variants


def _variant_spec(
    variant: str,
) -> tuple[
    dict[str, tuple[float, float]],
    list[tuple[str, str]],
    list[str],
    list[str],
]:
    if variant == "upper_package":
        positions = {
            "start": (-1.1, -0.2),
            "upper_entry_switch": (-0.5, -0.05),
            "upper_bypass": (0.1, -0.75),
            "package": (0.05, 0.7),
            "upper_finish_switch": (0.62, 0.18),
            "upper_dead_end": (1.1, -0.45),
            "destination": (1.05, 0.8),
        }
        edges = [
            ("start", "upper_entry_switch"),
            ("upper_entry_switch", "upper_bypass"),
            ("upper_entry_switch", "package"),
            ("package", "upper_finish_switch"),
            ("upper_finish_switch", "upper_dead_end"),
            ("upper_finish_switch", "destination"),
        ]
        return positions, edges, ["upper_entry_switch", "upper_finish_switch"], [
            "start",
            "upper_entry_switch",
            "package",
            "upper_finish_switch",
            "destination",
        ]

    if variant == "lower_package":
        positions = {
            "start": (-1.05, 0.38),
            "lower_entry_switch": (-0.5, 0.18),
            "lower_bypass": (0.12, 0.78),
            "package": (0.0, -0.72),
            "lower_finish_switch": (0.62, -0.15),
            "lower_dead_end": (1.05, 0.48),
            "destination": (1.1, -0.85),
        }
        edges = [
            ("start", "lower_entry_switch"),
            ("lower_entry_switch", "lower_bypass"),
            ("lower_entry_switch", "package"),
            ("package", "lower_finish_switch"),
            ("lower_finish_switch", "lower_dead_end"),
            ("lower_finish_switch", "destination"),
        ]
        return positions, edges, ["lower_entry_switch", "lower_finish_switch"], [
            "start",
            "lower_entry_switch",
            "package",
            "lower_finish_switch",
            "destination",
        ]

    if variant == "long_gate":
        positions = {
            "start": (-1.1, 0.25),
            "long_entry_switch": (-0.62, 0.05),
            "long_bypass": (-0.15, -0.78),
            "package": (-0.05, 0.72),
            "mid_path": (0.36, 0.44),
            "long_finish_switch": (0.72, 0.1),
            "long_dead_end": (1.12, -0.58),
            "destination": (1.08, 0.76),
        }
        edges = [
            ("start", "long_entry_switch"),
            ("long_entry_switch", "long_bypass"),
            ("long_entry_switch", "package"),
            ("package", "mid_path"),
            ("mid_path", "long_finish_switch"),
            ("long_finish_switch", "long_dead_end"),
            ("long_finish_switch", "destination"),
        ]
        return positions, edges, ["long_entry_switch", "long_finish_switch"], [
            "start",
            "long_entry_switch",
            "package",
            "mid_path",
            "long_finish_switch",
            "destination",
        ]

    if variant == "left_entry":
        positions = {
            "start": (-1.1, -0.35),
            "left_entry_switch": (-0.6, -0.18),
            "left_bypass": (-0.1, -0.82),
            "package": (0.05, 0.58),
            "left_finish_switch": (0.55, 0.08),
            "left_dead_end": (1.08, -0.52),
            "destination": (1.08, 0.72),
        }
        edges = [
            ("start", "left_entry_switch"),
            ("left_entry_switch", "left_bypass"),
            ("left_entry_switch", "package"),
            ("package", "left_finish_switch"),
            ("left_finish_switch", "left_dead_end"),
            ("left_finish_switch", "destination"),
        ]
        return positions, edges, ["left_entry_switch", "left_finish_switch"], [
            "start",
            "left_entry_switch",
            "package",
            "left_finish_switch",
            "destination",
        ]

    if variant == "right_entry":
        positions = {
            "start": (-1.1, 0.45),
            "right_entry_switch": (-0.58, 0.18),
            "right_bypass": (0.02, 0.82),
            "package": (0.0, -0.58),
            "right_finish_switch": (0.58, -0.08),
            "right_dead_end": (1.08, 0.52),
            "destination": (1.08, -0.72),
        }
        edges = [
            ("start", "right_entry_switch"),
            ("right_entry_switch", "right_bypass"),
            ("right_entry_switch", "package"),
            ("package", "right_finish_switch"),
            ("right_finish_switch", "right_dead_end"),
            ("right_finish_switch", "destination"),
        ]
        return positions, edges, ["right_entry_switch", "right_finish_switch"], [
            "start",
            "right_entry_switch",
            "package",
            "right_finish_switch",
            "destination",
        ]

    if variant == "short_gate":
        positions = {
            "start": (-1.1, 0.12),
            "short_entry_switch": (-0.52, 0.02),
            "short_bypass": (-0.02, -0.48),
            "package": (0.08, 0.52),
            "short_finish_switch": (0.58, 0.18),
            "short_dead_end": (0.98, -0.32),
            "destination": (1.08, 0.62),
        }
        edges = [
            ("start", "short_entry_switch"),
            ("short_entry_switch", "short_bypass"),
            ("short_entry_switch", "package"),
            ("package", "short_finish_switch"),
            ("short_finish_switch", "short_dead_end"),
            ("short_finish_switch", "destination"),
        ]
        return positions, edges, ["short_entry_switch", "short_finish_switch"], [
            "start",
            "short_entry_switch",
            "package",
            "short_finish_switch",
            "destination",
        ]

    positions = {
        "start": (-1.1, 0.25),
        "approach_switch": (-0.45, 0.05),
        "bypass": (0.1, -0.65),
        "package": (0.1, 0.65),
        "finish_switch": (0.65, 0.2),
        "dead_end_a": (1.1, -0.55),
        "destination": (1.1, 0.75),
    }
    edges = [
        ("start", "approach_switch"),
        ("approach_switch", "bypass"),
        ("approach_switch", "package"),
        ("package", "finish_switch"),
        ("finish_switch", "dead_end_a"),
        ("finish_switch", "destination"),
    ]
    return positions, edges, ["approach_switch", "finish_switch"], [
        "start",
        "approach_switch",
        "package",
        "finish_switch",
        "destination",
    ]
