from __future__ import annotations

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
            builder.add_edge(from_node_id, to_node_id)

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
        )
        return self.generated(
            level,
            solution,
            preset,
            rng.seed,
            notes=[f"Template variant: {variant}", f"Layout variant: {layout_variant.name}"],
        )


def _variant_spec(
    variant: str,
) -> tuple[
    dict[str, tuple[float, float]],
    list[tuple[str, str]],
    list[str],
    list[str],
]:
    if variant == "return_loop_upper":
        positions = {
            "start": (-1.1, -0.18),
            "upper_alpha_switch": (-0.5, -0.05),
            "package": (0.05, 0.82),
            "upper_beta_switch": (0.68, 0.72),
            "upper_return": (0.82, -0.48),
            "destination": (-0.08, -1.08),
            "upper_dead_end": (1.12, 0.2),
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
        positions = {
            "start": (-1.05, 0.2),
            "lower_alpha_switch": (-0.48, 0.02),
            "package": (0.1, -0.78),
            "lower_beta_switch": (0.72, -0.7),
            "lower_return": (0.78, 0.5),
            "destination": (-0.12, 0.95),
            "lower_dead_end": (1.12, -0.12),
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

    positions = {
        "start": (-1.1, 0.0),
        "alpha_switch": (-0.45, 0.0),
        "package": (0.1, 0.75),
        "beta_switch": (0.75, 0.75),
        "return_a": (0.75, -0.55),
        "destination": (-0.05, -1.05),
        "dead_end_a": (1.15, 0.15),
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
