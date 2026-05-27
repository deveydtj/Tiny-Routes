from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..models.template_variant_spec import TemplateVariantSpec
from ..random_source import RandomSource
from .base_template import LevelTemplate


class RingRouteTemplate(LevelTemplate):
    name = "ring_route"
    requires_swift_validation = True
    variant_specs = [
        TemplateVariantSpec("ring_route_clockwise", name, ("hard",), requires_swift_validation=True),
        TemplateVariantSpec("ring_route_counterclockwise", name, ("hard",), requires_swift_validation=True),
        TemplateVariantSpec("ring_route_package_inside", name, ("hard",), requires_swift_validation=True),
        TemplateVariantSpec("ring_route_package_outside", name, ("hard",), requires_swift_validation=True),
    ]

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return preset.name == "hard" and preset.allow_ring_routes

    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        builder = self.builder()
        variant = rng.choice([spec.name for spec in self.variant_specs if spec.supports_difficulty(preset.name)])
        positions = _positions_for_variant(variant)
        layout_variant = self.apply_layout_variant(positions, preset, rng)
        positions = layout_variant.positions

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])

        builder.add_edge("start", "hub")
        builder.add_edge("hub", "ring_a")
        builder.add_edge("hub", "package")
        builder.add_edge("ring_a", "ring_b")
        builder.add_edge("ring_b", "ring_a")
        builder.add_edge("ring_b", "gate")
        builder.add_edge("ring_b", "dead_end_a")
        builder.add_edge("package", "ring_b")
        builder.add_edge("gate", "dead_end_b")
        builder.add_edge("gate", "destination")
        builder.add_edge("gate", "ring_a")

        route = ["start", "hub", "package", "ring_b", "gate", "destination"]
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
            ["hub", "ring_b", "gate"],
            route,
            positions,
            preset,
            "Rotate hub to collect the package, rotate the ring exit, then open the destination gate.",
            route_edge_shapes=self.route_edge_shapes_for(level, route),
        )
        return self.generated(
            level,
            solution,
            preset,
            rng.seed,
            notes=[
                f"Template variant: {variant}",
                f"Layout variant: {layout_variant.name}",
                "Ring routes must pass Swift solvability before production output is trusted.",
            ],
        )


def _positions_for_variant(variant: str) -> dict[str, tuple[float, float]]:
    positions = {
        "start": (-1.1, 0.0),
        "hub": (-0.55, 0.0),
        "ring_a": (-0.1, 0.75),
        "ring_b": (0.55, 0.75),
        "package": (-0.1, -0.7),
        "gate": (0.75, -0.25),
        "destination": (1.15, 0.25),
        "dead_end_a": (0.95, 1.0),
        "dead_end_b": (1.15, -0.9),
    }
    if variant == "ring_route_counterclockwise":
        return {node_id: (x, -y) for node_id, (x, y) in positions.items()}
    if variant == "ring_route_package_inside":
        adjusted = dict(positions)
        adjusted["package"] = (0.08, -0.42)
        adjusted["gate"] = (0.78, -0.12)
        adjusted["dead_end_b"] = (1.12, -0.78)
        return adjusted
    if variant == "ring_route_package_outside":
        adjusted = dict(positions)
        adjusted["package"] = (-0.32, -0.92)
        adjusted["ring_a"] = (-0.2, 0.62)
        adjusted["ring_b"] = (0.5, 0.62)
        adjusted["gate"] = (0.78, -0.38)
        return adjusted
    return positions
