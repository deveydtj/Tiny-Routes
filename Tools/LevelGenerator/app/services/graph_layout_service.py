from __future__ import annotations

import math
import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe
from ..random_source import RandomSource


@dataclass(frozen=True)
class BoundingBox:
    min_x: float = -1.2
    max_x: float = 1.2
    min_y: float = -1.3
    max_y: float = 1.0


@dataclass(frozen=True)
class LayoutValidationIssue:
    code: str
    message: str
    node_id: str | None = None


@dataclass(frozen=True)
class LayoutPlanResult:
    strategy: str
    variant: str
    positions: dict[str, tuple[float, float]]
    validation_issues: tuple[LayoutValidationIssue, ...]
    metadata: dict[str, object]

    @property
    def is_valid(self) -> bool:
        return not self.validation_issues


class GraphLayoutService:
    def __init__(
        self,
        bounds: BoundingBox | None = None,
        minimum_node_distance: float = 0.2,
        grid_size: float = 0.05,
    ) -> None:
        self.bounds = bounds or BoundingBox()
        self.minimum_node_distance = minimum_node_distance
        self.grid_size = grid_size

    def snap(self, value: float) -> float:
        return round(round(value / self.grid_size) * self.grid_size, 4)

    def snap_point(self, x: float, y: float) -> tuple[float, float]:
        return self.snap(x), self.snap(y)

    def is_inside_bounds(self, x: float, y: float) -> bool:
        return self.bounds.min_x <= x <= self.bounds.max_x and self.bounds.min_y <= y <= self.bounds.max_y

    def point_distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def scale_positions(
        self,
        positions: dict[str, tuple[float, float]],
        scale_x: float,
        scale_y: float | None = None,
        center: tuple[float, float] = (0.0, 0.0),
    ) -> dict[str, tuple[float, float]]:
        resolved_scale_y = scale_x if scale_y is None else scale_y
        center_x, center_y = center
        return {
            node_id: self.snap_point(
                center_x + ((x - center_x) * scale_x),
                center_y + ((y - center_y) * resolved_scale_y),
            )
            for node_id, (x, y) in positions.items()
        }

    def translate_positions(
        self,
        positions: dict[str, tuple[float, float]],
        dx: float,
        dy: float,
    ) -> dict[str, tuple[float, float]]:
        return {
            node_id: self.snap_point(x + dx, y + dy)
            for node_id, (x, y) in positions.items()
        }

    def rotate_positions(
        self,
        positions: dict[str, tuple[float, float]],
        degrees: float,
        center: tuple[float, float] = (0.0, 0.0),
    ) -> dict[str, tuple[float, float]]:
        radians = math.radians(degrees)
        cos_value = math.cos(radians)
        sin_value = math.sin(radians)
        center_x, center_y = center
        rotated: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            offset_x = x - center_x
            offset_y = y - center_y
            rotated[node_id] = self.snap_point(
                center_x + (offset_x * cos_value) - (offset_y * sin_value),
                center_y + (offset_x * sin_value) + (offset_y * cos_value),
            )
        return rotated

    def normalize_positions(
        self,
        positions: dict[str, tuple[float, float]],
        padding: float = 0.05,
    ) -> dict[str, tuple[float, float]]:
        if not positions:
            return {}

        min_x = min(x for x, _ in positions.values())
        max_x = max(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        max_y = max(y for _, y in positions.values())
        source_width = max(max_x - min_x, 1e-9)
        source_height = max(max_y - min_y, 1e-9)
        target_min_x = self.bounds.min_x + padding
        target_max_x = self.bounds.max_x - padding
        target_min_y = self.bounds.min_y + padding
        target_max_y = self.bounds.max_y - padding
        target_width = max(target_max_x - target_min_x, 1e-9)
        target_height = max(target_max_y - target_min_y, 1e-9)

        normalized: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            normalized[node_id] = self.snap_point(
                target_min_x + (((x - min_x) / source_width) * target_width),
                target_min_y + (((y - min_y) / source_height) * target_height),
            )
        return normalized

    def has_overlaps(self, positions: dict[str, tuple[float, float]]) -> bool:
        return bool(self.overlapping_pairs(positions))

    def overlapping_pairs(self, positions: dict[str, tuple[float, float]]) -> list[tuple[str, str]]:
        node_ids = list(positions)
        pairs: list[tuple[str, str]] = []
        for index, first_id in enumerate(node_ids):
            for second_id in node_ids[index + 1:]:
                if self.point_distance(positions[first_id], positions[second_id]) < self.minimum_node_distance:
                    pairs.append((first_id, second_id))
        return pairs

    def zero_length_edges(self, level_document) -> list[str]:
        positions = {node.id: (node.x, node.y) for node in level_document.graph.nodes}
        edge_ids: list[str] = []
        for edge in level_document.graph.edges:
            if edge.fromNodeID in positions and edge.toNodeID in positions:
                if self.point_distance(positions[edge.fromNodeID], positions[edge.toNodeID]) == 0:
                    edge_ids.append(edge.id)
        return edge_ids

    def mirror_horizontally(self, positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        return {node_id: self.snap_point(-x, y) for node_id, (x, y) in positions.items()}

    def mirror_vertically(self, positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        return {node_id: self.snap_point(x, -y) for node_id, (x, y) in positions.items()}

    def apply_safe_jitter(
        self,
        positions: dict[str, tuple[float, float]],
        rng: RandomSource,
        amount: float = 0.03,
    ) -> dict[str, tuple[float, float]]:
        jittered: dict[str, tuple[float, float]] = {}
        for node_id, (x, y) in positions.items():
            candidate = self.snap_point(x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount))
            if self.is_inside_bounds(*candidate):
                jittered[node_id] = candidate
            else:
                jittered[node_id] = (x, y)
        return jittered if not self.has_overlaps(jittered) else positions

    def edge_crossings(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
    ) -> list[tuple[str | None, str | None]]:
        edge_list = list(edges)
        crossings: list[tuple[str | None, str | None]] = []
        for index, (from_a, to_a, edge_a_id) in enumerate(edge_list):
            if from_a not in positions or to_a not in positions:
                continue
            for from_b, to_b, edge_b_id in edge_list[index + 1:]:
                if from_b not in positions or to_b not in positions:
                    continue
                if len({from_a, to_a, from_b, to_b}) < 4:
                    continue
                if self.segments_intersect(positions[from_a], positions[to_a], positions[from_b], positions[to_b]):
                    crossings.append((edge_a_id, edge_b_id))
        return crossings

    def edge_crossings_for_level(self, level_document) -> list[tuple[str | None, str | None]]:
        positions = {node.id: (node.x, node.y) for node in level_document.graph.nodes}
        edges = [(edge.fromNodeID, edge.toNodeID, edge.id) for edge in level_document.graph.edges]
        return self.edge_crossings(positions, edges)

    def segments_intersect(
        self,
        a1: tuple[float, float],
        a2: tuple[float, float],
        b1: tuple[float, float],
        b2: tuple[float, float],
    ) -> bool:
        def orientation(p, q, r) -> float:
            return ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))

        def on_segment(p, q, r) -> bool:
            return (
                min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
                and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
            )

        o1 = orientation(a1, a2, b1)
        o2 = orientation(a1, a2, b2)
        o3 = orientation(b1, b2, a1)
        o4 = orientation(b1, b2, a2)
        tolerance = 1e-9

        if o1 * o2 < -tolerance and o3 * o4 < -tolerance:
            return True
        if abs(o1) <= tolerance and on_segment(a1, b1, a2):
            return True
        if abs(o2) <= tolerance and on_segment(a1, b2, a2):
            return True
        if abs(o3) <= tolerance and on_segment(b1, a1, b2):
            return True
        if abs(o4) <= tolerance and on_segment(b1, a2, b2):
            return True
        return False

    def edge_spacing_issues(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
        minimum_spacing: float,
    ) -> list[tuple[str, str | None, float]]:
        issues: list[tuple[str, str | None, float]] = []
        for from_node_id, to_node_id, edge_id in edges:
            if from_node_id not in positions or to_node_id not in positions:
                continue
            start = positions[from_node_id]
            end = positions[to_node_id]
            for node_id, point in positions.items():
                if node_id in {from_node_id, to_node_id}:
                    continue
                distance = self._point_to_segment_distance(point, start, end)
                if distance < minimum_spacing:
                    issues.append((node_id, edge_id, round(distance, 4)))
        return issues

    def readability_summary(
        self,
        positions: dict[str, tuple[float, float]],
        edges: Iterable[tuple[str, str, str | None]],
        minimum_edge_spacing: float = 0.12,
    ) -> dict[str, int]:
        return {
            "overlaps": len(self.overlapping_pairs(positions)),
            "crossings": len(self.edge_crossings(positions, edges)),
            "edgeSpacingIssues": len(self.edge_spacing_issues(positions, edges, minimum_edge_spacing)),
        }

    def validate_positions(self, positions: dict[str, tuple[float, float]]) -> list[str]:
        messages: list[str] = []
        for node_id, (x, y) in positions.items():
            if not self.is_inside_bounds(x, y):
                messages.append(f"node_out_of_bounds:{node_id}")
        for first_id, second_id in self.overlapping_pairs(positions):
            messages.append(f"overlapping_nodes:{first_id}:{second_id}")
        return messages

    def _point_to_segment_distance(
        self,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        segment_x = end[0] - start[0]
        segment_y = end[1] - start[1]
        length_squared = (segment_x * segment_x) + (segment_y * segment_y)
        if length_squared == 0:
            return self.point_distance(point, start)
        projection = (
            ((point[0] - start[0]) * segment_x) + ((point[1] - start[1]) * segment_y)
        ) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest = (start[0] + (projection * segment_x), start[1] + (projection * segment_y))
        return self.point_distance(point, closest)


class GraphLayoutPlannerService:
    """Plans readable recipe-first node coordinates before road-shape selection."""

    strategy_names = (
        "horizontal_route_progression",
        "vertical_route_progression",
        "snake_layout",
        "s_curve_layout",
        "vertical_split_lane",
        "vertical_loop",
        "hub_and_spoke",
        "ring_loop",
        "package_inside_loop",
        "split_lane",
        "four_way_intersection",
    )

    def plan_layout(
        self,
        recipe: GraphRecipe,
        preset: DifficultyPreset,
        rng: RandomSource,
        layout_variant_name: str = "normal",
        layout_orientation_preference: str = "horizontal",
        orientation_selection_reason: str = "default_horizontal",
        strategy_override: str | None = None,
    ) -> LayoutPlanResult:
        layout = GraphLayoutService(
            bounds=BoundingBox(*preset.coordinate_bounds),
            minimum_node_distance=preset.minimum_node_distance,
        )
        requested_orientation = layout_orientation_preference.strip().lower()
        strategy = strategy_override or self._strategy_for_recipe(recipe, requested_orientation)
        base_positions = self._base_positions_for_strategy(recipe, strategy, layout)
        positions, variant = self._apply_variation(base_positions, layout, rng, layout_variant_name)
        issues = self.validate_layout(recipe, preset, positions)
        if issues:
            normalized = layout.normalize_positions(positions, padding=0.12)
            normalized_issues = self.validate_layout(recipe, preset, normalized)
            if len(normalized_issues) < len(issues):
                positions = normalized
                issues = normalized_issues
        vertical_rejection_reason = None
        if requested_orientation == "vertical" and issues and strategy_override is None:
            fallback_strategy = self._strategy_for_recipe(recipe, "horizontal")
            if fallback_strategy != strategy:
                fallback_positions, fallback_variant = self._apply_variation(
                    self._base_positions_for_strategy(recipe, fallback_strategy, layout),
                    layout,
                    rng,
                    layout_variant_name,
                )
                fallback_issues = self.validate_layout(recipe, preset, fallback_positions)
                if len(fallback_issues) < len(issues):
                    vertical_rejection_reason = ",".join(sorted({issue.code for issue in issues})) or "layout_invalid"
                    strategy = fallback_strategy
                    positions = fallback_positions
                    variant = fallback_variant
                    issues = fallback_issues
        orientation = self._orientation_for_strategy(strategy)
        metadata = self._metadata(
            recipe,
            strategy,
            variant,
            positions,
            issues,
            orientation=orientation,
            orientation_preference=requested_orientation,
            orientation_selection_reason=orientation_selection_reason,
            vertical_candidate_rejected_reason=vertical_rejection_reason,
        )
        return LayoutPlanResult(
            strategy=strategy,
            variant=variant,
            positions=positions,
            validation_issues=tuple(issues),
            metadata=metadata,
        )

    def validate_layout(
        self,
        recipe: GraphRecipe,
        preset: DifficultyPreset,
        positions: dict[str, tuple[float, float]],
    ) -> list[LayoutValidationIssue]:
        layout = GraphLayoutService(
            bounds=BoundingBox(*preset.coordinate_bounds),
            minimum_node_distance=preset.minimum_node_distance,
        )
        issues: list[LayoutValidationIssue] = []
        margin = max(0.12, preset.minimum_node_distance * 0.55)
        switch_margin = max(0.2, preset.minimum_node_distance * 0.9)
        important_minimum = preset.minimum_node_distance * 1.6
        package_destination_minimum = preset.minimum_node_distance * 2.0

        for node_id, (x, y) in positions.items():
            if not layout.is_inside_bounds(x, y):
                issues.append(LayoutValidationIssue("layout_node_out_of_bounds", f"Node '{node_id}' is outside coordinate bounds.", node_id))
                continue
            if (
                x < layout.bounds.min_x + margin
                or x > layout.bounds.max_x - margin
                or y < layout.bounds.min_y + margin
                or y > layout.bounds.max_y - margin
            ):
                code = "layout_switch_too_close_to_edge" if self._node_role(recipe, node_id) == "switch" else "layout_node_too_close_to_edge"
                issues.append(LayoutValidationIssue(code, f"Node '{node_id}' is too close to the board edge.", node_id))

        for first_id, second_id in layout.overlapping_pairs(positions):
            issues.append(
                LayoutValidationIssue(
                    "layout_node_cluster",
                    f"Nodes '{first_id}' and '{second_id}' are too close together.",
                    first_id,
                )
            )

        important_node_ids = ["start", recipe.package_node_id, recipe.destination_node_id]
        for index, first_id in enumerate(important_node_ids):
            for second_id in important_node_ids[index + 1:]:
                if first_id not in positions or second_id not in positions:
                    continue
                distance = layout.point_distance(positions[first_id], positions[second_id])
                if distance < important_minimum:
                    issues.append(
                        LayoutValidationIssue(
                            "layout_important_nodes_too_close",
                            f"Important nodes '{first_id}' and '{second_id}' are too close.",
                            first_id,
                        )
                    )

        if recipe.package_node_id in positions and recipe.destination_node_id in positions:
            distance = layout.point_distance(positions[recipe.package_node_id], positions[recipe.destination_node_id])
            if distance < package_destination_minimum:
                issues.append(
                    LayoutValidationIssue(
                        "layout_package_destination_confusing",
                        "Package and destination are too close to read as separate goals.",
                        recipe.package_node_id,
                    )
                )

        switch_ids = [node.id for node in recipe.nodes if node.role == "switch"]
        for index, first_id in enumerate(switch_ids):
            if first_id in positions and self._distance_to_bounds(layout, positions[first_id]) < switch_margin:
                issues.append(
                    LayoutValidationIssue(
                        "layout_switch_too_close_to_edge",
                        f"Switch '{first_id}' is too close to the board edge.",
                        first_id,
                    )
                )
            for second_id in switch_ids[index + 1:]:
                if first_id not in positions or second_id not in positions:
                    continue
                if layout.point_distance(positions[first_id], positions[second_id]) < preset.minimum_node_distance * 1.5:
                    issues.append(
                        LayoutValidationIssue(
                            "layout_node_cluster",
                            f"Switches '{first_id}' and '{second_id}' do not have enough separation.",
                            first_id,
                        )
                    )

        parents_by_node_id: dict[str, list[str]] = {}
        for edge in recipe.edges:
            parents_by_node_id.setdefault(edge.to_node_id, []).append(edge.from_node_id)
        for node in recipe.nodes:
            if node.role != "dead_end" or node.id not in positions:
                continue
            parent_id = parents_by_node_id.get(node.id, [None])[0]
            if parent_id is None or parent_id not in positions:
                issues.append(LayoutValidationIssue("layout_dead_end_not_readable", f"Dead end '{node.id}' has no readable parent.", node.id))
                continue
            if layout.point_distance(positions[node.id], positions[parent_id]) < preset.minimum_node_distance * 1.35:
                issues.append(LayoutValidationIssue("layout_dead_end_not_readable", f"Dead end '{node.id}' is too close to its branch.", node.id))

        return issues

    def _strategy_for_recipe(self, recipe: GraphRecipe, orientation_preference: str = "horizontal") -> str:
        if orientation_preference == "vertical":
            return self._vertical_strategy_for_recipe(recipe)
        return self._horizontal_strategy_for_recipe(recipe)

    def _horizontal_strategy_for_recipe(self, recipe: GraphRecipe) -> str:
        family_name = recipe.family_name
        tags = set(recipe.mechanic_tags)
        if family_name == "controlled_repeated_taps":
            return "package_inside_loop"
        if family_name == "four_way_intersection" or "four_way" in tags:
            return "four_way_intersection"
        if family_name == "ring_route" or "ring_route" in tags or "ring" in family_name:
            return "ring_loop"
        if family_name == "return_loop" or "return_loop" in tags:
            return "package_inside_loop"
        if family_name == "package_gate" or "package_gate" in tags:
            return "split_lane"
        if "split_path" in tags or "branch" in tags:
            return "split_lane"
        if any(self._outgoing_count(recipe, node.id) >= 3 for node in recipe.nodes if node.role == "switch"):
            return "hub_and_spoke"
        return "horizontal_route_progression"

    def _vertical_strategy_for_recipe(self, recipe: GraphRecipe) -> str:
        family_name = recipe.family_name
        tags = set(recipe.mechanic_tags)
        if family_name == "controlled_repeated_taps":
            return "vertical_loop"
        if family_name == "four_way_intersection" or "four_way" in tags:
            return "four_way_intersection"
        if family_name == "ring_route" or "ring_route" in tags or "ring" in family_name:
            return "vertical_loop"
        if family_name == "return_loop" or "return_loop" in tags or "loop" in tags:
            return "vertical_loop"
        if family_name == "package_gate" or "package_gate" in tags:
            return "vertical_split_lane"
        if "split_path" in tags or "branch" in tags or "rejoin" in tags:
            return "vertical_split_lane"
        path_length = max(len(recipe.required_path) - 1, 0)
        if path_length >= 9:
            return "s_curve_layout"
        if path_length >= 7:
            return "snake_layout"
        return "vertical_route_progression"

    def _base_positions_for_strategy(
        self,
        recipe: GraphRecipe,
        strategy: str,
        layout: GraphLayoutService,
    ) -> dict[str, tuple[float, float]]:
        if strategy == "vertical_route_progression":
            return self._route_progression_positions(recipe, layout, vertical=True)
        if strategy == "snake_layout":
            return self._snake_positions(recipe, layout)
        if strategy == "s_curve_layout":
            return self._s_curve_positions(recipe, layout)
        if strategy == "vertical_split_lane":
            return self._vertical_split_lane_positions(recipe, layout)
        if strategy == "vertical_loop":
            return self._vertical_loop_positions(recipe, layout)
        if strategy == "hub_and_spoke":
            return self._hub_positions(recipe, layout)
        if strategy == "ring_loop":
            return self._ring_positions(recipe, layout)
        if strategy == "package_inside_loop":
            return self._loop_positions(recipe, layout)
        if strategy == "split_lane":
            return self._split_lane_positions(recipe, layout)
        if strategy == "four_way_intersection":
            return self._four_way_positions(recipe, layout)
        return self._route_progression_positions(recipe, layout, vertical=False)

    def _route_progression_positions(
        self,
        recipe: GraphRecipe,
        layout: GraphLayoutService,
        *,
        vertical: bool,
    ) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        span = 2.0
        step = span / max(len(route) - 1, 1)
        for index, node_id in enumerate(route):
            primary = -1.0 + (index * step)
            offset = 0.0
            role = self._node_role(recipe, node_id)
            if role == "package":
                offset = 0.42
            elif role == "destination":
                offset = -0.32
            elif role == "switch":
                offset = 0.2 if index % 2 else -0.2
            if vertical:
                positions[node_id] = layout.snap_point(offset, 0.85 - (index * (1.85 / max(len(route) - 1, 1))))
            else:
                positions[node_id] = layout.snap_point(primary, offset)
        self._place_off_route_nodes(recipe, layout, positions, vertical=vertical)
        return positions

    def _snake_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        step_y = 1.9 / max(len(route) - 1, 1)
        lanes = (-0.62, 0.62)
        for index, node_id in enumerate(route):
            lane_index = (index // 2) % 2
            x = lanes[lane_index]
            if index % 2 == 1:
                x = lanes[1 - lane_index]
            y = 0.85 - (index * step_y)
            role = self._node_role(recipe, node_id)
            if role == "package":
                x *= 0.55
            elif role == "destination":
                x *= 0.75
            positions[node_id] = layout.snap_point(x, y)
        self._place_off_route_nodes(recipe, layout, positions, vertical=True)
        return positions

    def _s_curve_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        denominator = max(len(route) - 1, 1)
        for index, node_id in enumerate(route):
            progress = index / denominator
            x = math.sin((progress * math.pi * 2.0) - (math.pi / 4.0)) * 0.58
            y = 0.85 - (progress * 1.9)
            role = self._node_role(recipe, node_id)
            if role == "package":
                x += 0.16
            elif role == "destination":
                x -= 0.16
            positions[node_id] = layout.snap_point(x, y)
        self._place_off_route_nodes(recipe, layout, positions, vertical=True)
        return positions

    def _hub_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        if recipe.family_name == "hub_choice":
            return self._hub_choice_positions(recipe, layout)
        positions = self._route_progression_positions(recipe, layout, vertical=False)
        hub_id = next((node.id for node in recipe.nodes if node.role == "switch" and self._outgoing_count(recipe, node.id) >= 3), None)
        if hub_id is None:
            return positions
        positions[hub_id] = layout.snap_point(0.0, 0.0)
        outgoing = [edge.to_node_id for edge in recipe.edges if edge.from_node_id == hub_id]
        spokes = [(-0.75, 0.25), (0.75, 0.25), (0.0, -0.72), (0.0, 0.72)]
        for node_id, point in zip(outgoing, spokes):
            if node_id in positions and node_id not in {"start", recipe.destination_node_id}:
                positions[node_id] = layout.snap_point(*point)
        return positions

    def _hub_choice_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, 0.0),
            "hub": layout.snap_point(-0.55, 0.0),
            "dead_end_a": layout.snap_point(-0.55, 0.65),
            "package_branch": layout.snap_point(0.05, 0.0),
            "package": layout.snap_point(0.82, 0.65),
            "rejoin": layout.snap_point(-0.55, -0.75),
            "switch_b": layout.snap_point(0.2, -1.05),
            "destination": layout.snap_point(1.05, -0.55),
            "dead_end_b": layout.snap_point(0.85, -1.15),
        }
        if any(node.id == "switch_c" for node in recipe.nodes):
            positions.update(
                {
                    "switch_b": layout.snap_point(0.0, -1.05),
                    "route_mid": layout.snap_point(0.45, -0.9),
                    "switch_c": layout.snap_point(0.85, -0.65),
                    "destination": layout.snap_point(1.05, -0.05),
                    "dead_end_b": layout.snap_point(0.75, -1.15),
                    "dead_end_c": layout.snap_point(1.05, -1.15),
                }
            )
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _ring_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        radius_x = 0.82
        radius_y = 0.54
        for index, node_id in enumerate(route):
            angle = math.radians(210 - (300 * index / max(len(route) - 1, 1)))
            positions[node_id] = layout.snap_point(math.cos(angle) * radius_x, math.sin(angle) * radius_y)
        positions["start"] = layout.snap_point(-1.0, -0.55)
        positions[recipe.destination_node_id] = layout.snap_point(1.0, -0.5)
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        if "ring_a" in positions:
            positions["ring_a"] = layout.snap_point(-0.35, -0.05)
        if "dead_end_a" in positions:
            positions["dead_end_a"] = layout.snap_point(0.35, 0.85)
        return positions

    def _loop_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        if recipe.family_name == "controlled_repeated_taps":
            return self._controlled_repeated_taps_positions(recipe, layout)
        positions = self._ring_positions(recipe, layout)
        if recipe.package_node_id in positions:
            positions[recipe.package_node_id] = layout.snap_point(-0.05, 0.42)
        return positions

    def _split_lane_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        if recipe.family_name == "split_path_rejoin":
            return self._split_path_rejoin_positions(recipe, layout)
        if recipe.family_name == "fake_shortcut" and recipe.difficulty == "hard":
            return self._fake_shortcut_hard_positions(recipe, layout)
        if recipe.family_name == "long_detour_gate" and recipe.difficulty == "hard":
            return self._long_detour_gate_hard_positions(recipe, layout)
        positions = self._route_progression_positions(recipe, layout, vertical=False)
        for node_id in recipe.required_path:
            if node_id in positions:
                x, _ = positions[node_id]
                positions[node_id] = layout.snap_point(x, 0.28 if node_id == recipe.package_node_id else -0.08)
        self._place_off_route_nodes(recipe, layout, positions, vertical=False, dead_end_y=0.72)
        return positions

    def _split_path_rejoin_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, 0.0),
            "switch_a": layout.snap_point(-0.55, 0.0),
            "upper_branch": layout.snap_point(-0.05, 0.28),
            "package": layout.snap_point(0.75, 0.55),
            "rejoin": layout.snap_point(-0.05, -0.7),
            "switch_b": layout.snap_point(0.55, -0.95),
            "destination": layout.snap_point(1.05, -0.55),
            "lower_shortcut": layout.snap_point(-0.55, -0.7),
            "dead_end_b": layout.snap_point(0.25, -1.15),
        }
        if any(node.id == "switch_c" for node in recipe.nodes):
            positions.update(
                {
                    "switch_b": layout.snap_point(0.35, 0.28),
                    "package": layout.snap_point(0.78, 0.58),
                    "rejoin": layout.snap_point(-0.05, -0.72),
                    "switch_c": layout.snap_point(0.62, -0.95),
                    "destination": layout.snap_point(1.05, -0.55),
                    "dead_end_b": layout.snap_point(0.35, 0.85),
                    "dead_end_c": layout.snap_point(0.92, -1.15),
                }
            )
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _fake_shortcut_hard_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, -0.15),
            "choice": layout.snap_point(-0.55, -0.15),
            "detour_a": layout.snap_point(-0.1, -0.15),
            "switch_b": layout.snap_point(0.3, -0.15),
            "package": layout.snap_point(0.68, 0.35),
            "detour_b": layout.snap_point(0.2, -0.68),
            "rejoin": layout.snap_point(0.55, -1.0),
            "switch_c": layout.snap_point(0.85, -1.0),
            "destination": layout.snap_point(1.05, -0.28),
            "shortcut_dead_end": layout.snap_point(-0.55, 0.72),
            "dead_end_b": layout.snap_point(0.3, 0.72),
            "dead_end_c": layout.snap_point(1.05, -1.15),
        }
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _long_detour_gate_hard_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, 0.0),
            "switch_gate": layout.snap_point(-0.55, 0.0),
            "detour_a": layout.snap_point(-0.1, 0.28),
            "switch_package": layout.snap_point(0.32, 0.28),
            "package": layout.snap_point(0.72, 0.58),
            "rejoin": layout.snap_point(-0.05, -0.72),
            "switch_exit": layout.snap_point(0.55, -0.95),
            "exit_gate_lane": layout.snap_point(0.85, -0.95),
            "destination": layout.snap_point(1.05, -0.55),
            "direct_bypass": layout.snap_point(-0.55, -0.72),
            "dead_end_b": layout.snap_point(0.32, 0.85),
            "dead_end_c": layout.snap_point(0.25, -1.15),
        }
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _vertical_split_lane_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        step_y = 1.85 / max(len(route) - 1, 1)
        for index, node_id in enumerate(route):
            role = self._node_role(recipe, node_id)
            x = 0.0
            if role == "package":
                x = -0.34
            elif role == "destination":
                x = 0.34
            elif role == "switch":
                x = 0.18 if index % 2 else -0.18
            positions[node_id] = layout.snap_point(x, 0.85 - (index * step_y))

        route_ids = set(route)
        parent_counts: dict[str, int] = {}
        for edge in recipe.edges:
            if edge.to_node_id in positions:
                continue
            parent_position = positions.get(edge.from_node_id, (0.0, 0.0))
            count = parent_counts.get(edge.from_node_id, 0)
            parent_counts[edge.from_node_id] = count + 1
            direction = 1 if count % 2 == 0 else -1
            side_offset = 0.72 * direction
            if edge.to_node_id not in route_ids:
                side_offset = 0.72 if parent_position[0] <= 0 else -0.72
            candidates = [
                layout.snap_point(parent_position[0] + side_offset, parent_position[1] - 0.04),
                layout.snap_point(parent_position[0] - side_offset, parent_position[1] + 0.04),
                layout.snap_point(parent_position[0] + side_offset, parent_position[1] - 0.34),
                layout.snap_point(parent_position[0] - side_offset, parent_position[1] + 0.34),
            ]
            positions[edge.to_node_id] = self._first_readable_candidate(layout, candidates, positions)
        return positions

    def _vertical_loop_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        route = list(recipe.required_path)
        positions: dict[str, tuple[float, float]] = {}
        radius_x = 0.54
        radius_y = 0.82
        for index, node_id in enumerate(route):
            angle = math.radians(140 + (280 * index / max(len(route) - 1, 1)))
            positions[node_id] = layout.snap_point(math.cos(angle) * radius_x, math.sin(angle) * radius_y - 0.08)
        positions["start"] = layout.snap_point(-0.62, 0.82)
        positions[recipe.destination_node_id] = layout.snap_point(0.62, -0.98)
        if recipe.package_node_id in positions:
            positions[recipe.package_node_id] = layout.snap_point(-0.42, -0.02)
        self._place_off_route_nodes(recipe, layout, positions, vertical=True)
        return positions

    def _four_way_positions(self, recipe: GraphRecipe, layout: GraphLayoutService) -> dict[str, tuple[float, float]]:
        if recipe.family_name == "four_way_package_gate":
            return self._four_way_package_gate_positions(recipe, layout)
        if recipe.family_name == "four_way_ring":
            return self._four_way_ring_positions(recipe, layout)
        positions = self._route_progression_positions(recipe, layout, vertical=False)
        switch_id = next((node.id for node in recipe.nodes if node.role == "switch"), None)
        if switch_id is None:
            return positions
        positions[switch_id] = layout.snap_point(0.0, 0.0)
        directions = [(-0.85, 0.28), (0.0, 0.68), (0.85, 0.0), (0.0, -0.68)]
        for node_id, point in zip([edge.to_node_id for edge in recipe.edges if edge.from_node_id == switch_id], directions):
            if node_id in positions and node_id != recipe.destination_node_id:
                positions[node_id] = layout.snap_point(*point)
        positions["start"] = layout.snap_point(-1.05, -0.48)
        if len(recipe.required_path) > 1 and recipe.required_path[1] != switch_id:
            positions[recipe.required_path[1]] = layout.snap_point(-0.78, -0.42)
        positions[recipe.destination_node_id] = layout.snap_point(1.05, -0.48)
        if "return_node" in positions:
            positions["return_node"] = layout.snap_point(0.45, 0.32)
        return positions

    def _controlled_repeated_taps_positions(
        self,
        recipe: GraphRecipe,
        layout: GraphLayoutService,
    ) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, -0.72),
            "repeat_switch": layout.snap_point(-0.55, -0.35),
            "dead_end_a": layout.snap_point(-1.05, -0.12),
            "package_lane": layout.snap_point(-0.55, 0.45),
            "package": layout.snap_point(0.08, 0.68),
            "loop_switch": layout.snap_point(0.72, 0.45),
            "dead_end_b": layout.snap_point(0.72, 0.82),
            "return_lane": layout.snap_point(0.0, -0.95),
            "exit_lane": layout.snap_point(-0.55, -1.05),
            "switch_exit": layout.snap_point(0.75, -1.0),
            "dead_end_c": layout.snap_point(0.75, -0.5),
            "destination": layout.snap_point(1.05, -1.15),
        }
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _four_way_package_gate_positions(
        self,
        recipe: GraphRecipe,
        layout: GraphLayoutService,
    ) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, -0.52),
            "entry_lane": layout.snap_point(-0.72, -0.52),
            "four_way_switch": layout.snap_point(-0.32, -0.2),
            "wrong_dead_end": layout.snap_point(-1.02, -0.2),
            "package_lane": layout.snap_point(-0.32, 0.55),
            "side_loop": layout.snap_point(-0.32, -0.95),
            "package": layout.snap_point(0.28, 0.7),
            "gate_approach": layout.snap_point(0.42, -0.2),
            "switch_exit": layout.snap_point(0.82, -0.2),
            "gate_dead_end": layout.snap_point(0.82, 0.42),
            "exit_lane": layout.snap_point(0.82, -0.85),
            "destination": layout.snap_point(1.05, -1.05),
        }
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _four_way_ring_positions(
        self,
        recipe: GraphRecipe,
        layout: GraphLayoutService,
    ) -> dict[str, tuple[float, float]]:
        positions = {
            "start": layout.snap_point(-1.05, -0.75),
            "ring_entry": layout.snap_point(-0.62, -0.75),
            "four_way_switch": layout.snap_point(-0.2, -0.25),
            "wrong_dead_end": layout.snap_point(-1.0, -0.25),
            "ring_a": layout.snap_point(-0.2, 0.58),
            "ring_inner": layout.snap_point(-0.2, -1.0),
            "package": layout.snap_point(0.42, 0.62),
            "ring_b": layout.snap_point(0.5, 0.25),
            "ring_c": layout.snap_point(0.0, 0.0),
            "switch_exit": layout.snap_point(0.95, 0.25),
            "exit_dead_end": layout.snap_point(0.95, 0.75),
            "destination": layout.snap_point(0.95, -0.75),
        }
        self._place_off_route_nodes(recipe, layout, positions, vertical=False)
        return positions

    def _place_off_route_nodes(
        self,
        recipe: GraphRecipe,
        layout: GraphLayoutService,
        positions: dict[str, tuple[float, float]],
        *,
        vertical: bool,
        dead_end_y: float | None = None,
    ) -> None:
        route_ids = set(recipe.required_path)
        parent_counts: dict[str, int] = {}
        for edge in recipe.edges:
            if edge.to_node_id in positions:
                continue
            parent_position = positions.get(edge.from_node_id, (0.0, 0.0))
            count = parent_counts.get(edge.from_node_id, 0)
            parent_counts[edge.from_node_id] = count + 1
            direction = 1 if count % 2 == 0 else -1
            if vertical:
                candidates = [
                    layout.snap_point(parent_position[0] + (0.62 * direction), parent_position[1]),
                    layout.snap_point(parent_position[0] - (0.62 * direction), parent_position[1]),
                    layout.snap_point(parent_position[0], parent_position[1] + 0.62),
                    layout.snap_point(parent_position[0], parent_position[1] - 0.62),
                ]
            else:
                y = dead_end_y if dead_end_y is not None and edge.to_node_id not in route_ids else parent_position[1] + (0.62 * direction)
                candidates = [
                    layout.snap_point(parent_position[0], y),
                    layout.snap_point(parent_position[0], parent_position[1] - (0.62 * direction)),
                    layout.snap_point(parent_position[0] + 0.62, parent_position[1]),
                    layout.snap_point(parent_position[0] - 0.62, parent_position[1]),
                ]
            positions[edge.to_node_id] = self._first_readable_candidate(layout, candidates, positions)

    def _first_readable_candidate(
        self,
        layout: GraphLayoutService,
        candidates: list[tuple[float, float]],
        positions: dict[str, tuple[float, float]],
    ) -> tuple[float, float]:
        margin = max(0.12, layout.minimum_node_distance * 0.55)
        for candidate in candidates:
            x, y = candidate
            if not (
                layout.bounds.min_x + margin <= x <= layout.bounds.max_x - margin
                and layout.bounds.min_y + margin <= y <= layout.bounds.max_y - margin
            ):
                continue
            if all(layout.point_distance(candidate, existing) >= layout.minimum_node_distance * 1.35 for existing in positions.values()):
                return candidate
        for candidate in candidates:
            if layout.is_inside_bounds(*candidate):
                return candidate
        x, y = candidates[0]
        return layout.snap_point(
            min(max(x, layout.bounds.min_x + margin), layout.bounds.max_x - margin),
            min(max(y, layout.bounds.min_y + margin), layout.bounds.max_y - margin),
        )

    def _apply_variation(
        self,
        positions: dict[str, tuple[float, float]],
        layout: GraphLayoutService,
        rng: RandomSource,
        variant_name: str,
    ) -> tuple[dict[str, tuple[float, float]], str]:
        variant = variant_name if variant_name in {"normal", "mirrored", "wide", "tall", "offset", "jittered", "rotated"} else "normal"
        if variant == "mirrored":
            return (layout.mirror_horizontally(positions) if rng.bool(0.5) else layout.mirror_vertically(positions)), variant
        if variant == "wide":
            return layout.scale_positions(positions, scale_x=1.08, scale_y=0.94), variant
        if variant == "tall":
            return layout.scale_positions(positions, scale_x=0.94, scale_y=1.08), variant
        if variant == "offset":
            return layout.translate_positions(positions, rng.choice([-0.08, -0.04, 0.04, 0.08]), rng.choice([-0.08, -0.04, 0.04, 0.08])), variant
        if variant == "jittered":
            return layout.apply_safe_jitter(positions, rng, amount=0.04), variant
        if variant == "rotated":
            return layout.rotate_positions(positions, 180), variant
        return dict(positions), "normal"

    def _metadata(
        self,
        recipe: GraphRecipe,
        strategy: str,
        variant: str,
        positions: dict[str, tuple[float, float]],
        issues: list[LayoutValidationIssue],
        *,
        orientation: str,
        orientation_preference: str,
        orientation_selection_reason: str,
        vertical_candidate_rejected_reason: str | None,
    ) -> dict[str, object]:
        payload = {
            "strategy": strategy,
            "variant": variant,
            "orientation": orientation,
            "positions": {node_id: [x, y] for node_id, (x, y) in sorted(positions.items())},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {
            "strategy": strategy,
            "variant": variant,
            "orientation": orientation,
            "orientationPreference": orientation_preference,
            "orientationSelectionReason": orientation_selection_reason,
            "verticalCandidateRejectedReason": vertical_candidate_rejected_reason,
            "layoutHash": hashlib.sha256(encoded).hexdigest(),
            "rejectionCodes": [issue.code for issue in issues],
            "nodeCount": len(recipe.nodes),
        }

    def _orientation_for_strategy(self, strategy: str) -> str:
        if strategy in {
            "vertical_route_progression",
            "snake_layout",
            "s_curve_layout",
            "vertical_split_lane",
            "vertical_loop",
        }:
            return "vertical"
        if strategy in {"horizontal_route_progression", "split_lane"}:
            return "horizontal"
        return "horizontal"

    def _node_role(self, recipe: GraphRecipe, node_id: str) -> str:
        return next((node.role for node in recipe.nodes if node.id == node_id), "route")

    def _outgoing_count(self, recipe: GraphRecipe, node_id: str) -> int:
        return sum(1 for edge in recipe.edges if edge.from_node_id == node_id)

    def _distance_to_bounds(self, layout: GraphLayoutService, point: tuple[float, float]) -> float:
        x, y = point
        return min(x - layout.bounds.min_x, layout.bounds.max_x - x, y - layout.bounds.min_y, layout.bounds.max_y - y)
