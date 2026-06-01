from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..models.template_variant_spec import TemplateVariantSpec
from ..random_source import RandomSource
from ..services.road_shape_service import RoadShapeService
from .base_template import LevelTemplate


class FourWayIntersectionTemplate(LevelTemplate):
    name = "four_way_intersection"
    variant_specs = [
        TemplateVariantSpec("package_down_destination_right", name, ("expert",)),
        TemplateVariantSpec("package_up_destination_right", name, ("expert",)),
        TemplateVariantSpec("package_left_destination_up", name, ("expert",)),
        TemplateVariantSpec("package_right_destination_down", name, ("expert",)),
    ]

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return (
            preset.name == "expert"
            and preset.max_outgoing_edges_per_switch >= 4
            and preset.allow_return_loops
            and preset.allow_repeated_switch_taps
        )

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

        for node_id in positions:
            builder.add_node(node_id, *positions[node_id])
        road_shapes = RoadShapeService().plan_for_graph(
            positions,
            edges,
            required_path=tuple(route),
            strategy="auto",
            important_node_ids=("start", "package", "destination"),
        ).edge_shapes
        for from_node_id, to_node_id in edges:
            builder.add_edge(from_node_id, to_node_id, road_shape=road_shapes[(from_node_id, to_node_id)])

        time_limit = self.calculate_time_limit([positions[node_id] for node_id in route], preset)
        level = builder.build_level_document(
            level_id=level_id,
            name=self.naming.name_for_level_number(level_number),
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=time_limit,
            par_taps=len(tap_node_ids),
        )
        solution = self.solution_builder.build_route_timed_tap_solution(
            level_id,
            tap_node_ids,
            route,
            positions,
            preset,
            "Rotate the central 4-way switch to collect the package, then rotate it again after the return path reaches the intersection.",
            route_edge_shapes=self.route_edge_shapes_for(level, route),
            route_edge_ids_by_pair=self.route_edge_ids_for(level, route),
            outgoing_edge_ids_by_node=self.outgoing_edge_ids_by_node_for(level),
        )
        return self.generated(
            level,
            solution,
            preset,
            rng.seed,
            notes=[f"Template variant: {variant}"],
        )


def _variant_spec(
    variant: str,
) -> tuple[
    dict[str, tuple[float, float]],
    list[tuple[str, str]],
    list[str],
    list[str],
]:
    if variant == "package_up_destination_right":
        positions = {
            "start": (-1.05, 0.0),
            "entry": (-0.5, 0.0),
            "central_switch": (0.0, 0.0),
            "dead_end": (0.0, -0.78),
            "package": (0.0, 0.78),
            "return_node": (-0.45, 0.35),
            "destination": (0.95, 0.0),
            "side_branch": (-0.45, -0.62),
        }
        return positions, _edges(), ["central_switch", "central_switch"], _route()

    if variant == "package_left_destination_up":
        positions = {
            "start": (0.0, -1.05),
            "entry": (0.0, -0.5),
            "central_switch": (0.0, 0.0),
            "dead_end": (0.78, 0.0),
            "package": (-0.78, 0.0),
            "return_node": (-0.35, -0.45),
            "destination": (0.0, 0.95),
            "side_branch": (0.62, -0.45),
        }
        return positions, _edges(), ["central_switch", "central_switch"], _route()

    if variant == "package_right_destination_down":
        positions = {
            "start": (0.0, 0.98),
            "entry": (0.0, 0.48),
            "central_switch": (0.0, 0.0),
            "dead_end": (-0.78, 0.0),
            "package": (0.78, 0.0),
            "return_node": (0.35, 0.35),
            "destination": (0.0, -0.95),
            "side_branch": (-0.62, 0.45),
        }
        return positions, _edges(), ["central_switch", "central_switch"], _route()

    positions = {
        "start": (-1.05, 0.0),
        "entry": (-0.5, 0.0),
        "central_switch": (0.0, 0.0),
        "dead_end": (0.0, 0.78),
        "package": (0.0, -0.78),
        "return_node": (-0.45, -0.35),
        "destination": (0.95, 0.0),
        "side_branch": (-0.45, 0.62),
    }
    return positions, _edges(), ["central_switch", "central_switch"], _route()


def _edges() -> list[tuple[str, str]]:
    return [
        ("start", "entry"),
        ("entry", "central_switch"),
        ("central_switch", "dead_end"),
        ("central_switch", "package"),
        ("central_switch", "destination"),
        ("central_switch", "side_branch"),
        ("package", "return_node"),
        ("return_node", "central_switch"),
    ]


def _route() -> list[str]:
    return [
        "start",
        "entry",
        "central_switch",
        "package",
        "return_node",
        "central_switch",
        "destination",
    ]
