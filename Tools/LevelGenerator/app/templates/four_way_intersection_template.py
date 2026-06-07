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
        _apply_revisited_route_shape_overrides(road_shapes, route)
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
    package_y = {
        "package_down_destination_right": 0.56,
        "package_up_destination_right": 0.6,
        "package_left_destination_up": 0.64,
        "package_right_destination_down": 0.68,
    }.get(variant, 0.62)
    positions = {
        "start": (-1.15, -0.45),
        "entry": (-0.75, -0.18),
        "central_switch": (-0.35, 0.0),
        "dead_end": (-1.05, 0.0),
        "package": (-0.35, package_y),
        "return_node": (0.95, package_y),
        "destination": (-0.35, -0.95),
        "side_branch": (0.55, -0.35),
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


def _apply_revisited_route_shape_overrides(
    road_shapes: dict[tuple[str, str], str],
    route: list[str],
) -> None:
    seen: dict[str, int] = {}
    for index, node_id in enumerate(route):
        first_index = seen.get(node_id)
        if first_index is None:
            seen[node_id] = index
            continue
        if index <= first_index + 1:
            continue
        for edge in (
            (node_id, route[first_index + 1]) if first_index + 1 < len(route) else None,
            (route[index - 1], node_id) if index > 0 else None,
        ):
            if edge in road_shapes:
                road_shapes[edge] = "verticalFirst"
