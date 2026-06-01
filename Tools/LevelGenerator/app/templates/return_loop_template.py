from __future__ import annotations

from ..models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..models.template_variant_spec import TemplateVariantSpec
from ..random_source import RandomSource
from .base_template import LevelTemplate


class ReturnLoopTemplate(LevelTemplate):
    name = "return_loop"
    variant_specs = [
        TemplateVariantSpec("return_loop_classic", name, ("medium",)),
        TemplateVariantSpec("return_loop_upper", name, ("medium",)),
        TemplateVariantSpec("return_loop_lower", name, ("medium",)),
    ]

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
        variant = rng.choice([spec.name for spec in self.variant_specs if spec.supports_difficulty(preset.name)])
        positions, edges, tap_node_ids, route = _variant_spec(variant)
        layout_variant = self.apply_layout_variant(positions, preset, rng)
        positions = layout_variant.positions

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        for from_node_id, to_node_id in edges:
            destination_shape = "horizontalFirst" if to_node_id == "destination" else None
            builder.add_edge(from_node_id, to_node_id, road_shape=destination_shape)

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
        solution = self.solution_builder.build_route_timed_tap_solution(
            level_id,
            tap_node_ids,
            route,
            positions,
            preset,
            "Rotate alpha to collect the package, rotate beta onto the return path, then rotate alpha again for destination.",
            lead_time_seconds=0.5,
            route_edge_shapes=self.route_edge_shapes_for(level, route),
        )
        generated = self.generated(
            level,
            solution,
            preset,
            rng.seed,
            notes=[f"Template variant: {variant}", f"Layout variant: {layout_variant.name}"],
        )
        generated.abstract_solution_metadata = AbstractPuzzleSolutionMetadata(
            solution_tap_node_ids=tuple(tap_node_ids),
            solution_switch_states=(),
            required_path=tuple(route),
            alternate_path_count=0,
            dead_end_count=1,
            failure_path_count=0,
            false_route_count=1,
            loop_count=1,
            minimum_required_taps=len(tap_node_ids),
            optional_tap_count=0,
            repeated_switch_usage=True,
            package_before_destination=True,
        )
        return generated


def _variant_spec(
    variant: str,
) -> tuple[
    dict[str, tuple[float, float]],
    list[tuple[str, str]],
    list[str],
    list[str],
]:
    if variant == "return_loop_upper":
        # Keep the return leg on the switch corridor and the destination leg on a
        # separate left corridor so the loop never reads as a shortcut.
        positions = {
            "start": (-1.15, -0.18),
            "upper_alpha_switch": (-0.25, -0.06),
            "package": (0.02, 0.68),
            "upper_beta_switch": (0.58, 0.52),
            "upper_return": (0.9, -0.58),
            "destination": (-0.75, -1.08),
            "upper_dead_end": (1.05, 0.18),
        }
        edges = [
            ("start", "upper_alpha_switch"),
            ("upper_alpha_switch", "destination"),
            ("upper_alpha_switch", "package"),
            ("package", "upper_beta_switch"),
            ("upper_beta_switch", "upper_dead_end"),
            ("upper_beta_switch", "upper_return"),
            ("upper_return", "upper_alpha_switch"),
        ]
        return positions, edges, ["upper_alpha_switch", "upper_beta_switch", "upper_alpha_switch"], [
            "start",
            "upper_alpha_switch",
            "package",
            "upper_beta_switch",
            "upper_return",
            "upper_alpha_switch",
            "destination",
        ]

    if variant == "return_loop_lower":
        # Mirror the upper variant's spacing: destination routes outside the
        # loop while the return path rejoins alpha from the interior corridor.
        positions = {
            "start": (-1.15, 0.22),
            "lower_alpha_switch": (-0.25, 0.02),
            "package": (0.04, -0.68),
            "lower_beta_switch": (0.58, -0.52),
            "lower_return": (0.9, 0.58),
            "destination": (-0.75, 0.94),
            "lower_dead_end": (1.05, -0.14),
        }
        edges = [
            ("start", "lower_alpha_switch"),
            ("lower_alpha_switch", "destination"),
            ("lower_alpha_switch", "package"),
            ("package", "lower_beta_switch"),
            ("lower_beta_switch", "lower_dead_end"),
            ("lower_beta_switch", "lower_return"),
            ("lower_return", "lower_alpha_switch"),
        ]
        return positions, edges, ["lower_alpha_switch", "lower_beta_switch", "lower_alpha_switch"], [
            "start",
            "lower_alpha_switch",
            "package",
            "lower_beta_switch",
            "lower_return",
            "lower_alpha_switch",
            "destination",
        ]

    # Classic uses the same spacing rule as the offset variants: the return
    # path approaches alpha on the inner corridor, away from the destination leg.
    positions = {
        "start": (-1.15, 0.0),
        "alpha_switch": (-0.25, 0.0),
        "package": (0.08, 0.64),
        "beta_switch": (0.62, 0.52),
        "return_a": (0.9, -0.62),
        "destination": (-0.75, -1.05),
        "dead_end_a": (1.08, 0.12),
    }
    edges = [
        ("start", "alpha_switch"),
        ("alpha_switch", "destination"),
        ("alpha_switch", "package"),
        ("package", "beta_switch"),
        ("beta_switch", "dead_end_a"),
        ("beta_switch", "return_a"),
        ("return_a", "alpha_switch"),
    ]
    return positions, edges, ["alpha_switch", "beta_switch", "alpha_switch"], [
        "start",
        "alpha_switch",
        "package",
        "beta_switch",
        "return_a",
        "alpha_switch",
        "destination",
    ]
