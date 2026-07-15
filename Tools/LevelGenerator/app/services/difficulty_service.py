from __future__ import annotations

from collections import Counter
import math

from ..models.difficulty_preset import DifficultyPreset
from ..models.generation_quality import DifficultyMetrics
from .graph_layout_service import GraphLayoutService
from .switch_classification_service import SwitchClassificationService


class DifficultyService:
    band_order = ("tutorial", "easy", "medium", "hard", "expert")

    def __init__(self) -> None:
        self._presets = {
            "tutorial": DifficultyPreset(
                name="tutorial",
                node_count_range=(3, 8),
                switch_count_range=(0, 2),
                required_tap_range=(0, 2),
                route_length_range=(2, 5),
                dead_end_count_range=(0, 2),
                max_outgoing_edges_per_switch=2,
                allow_return_loops=False,
                allow_repeated_switch_taps=False,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=10,
                map_size_profile_weights=(("standard_portrait", 1),),
                allowed_topology_classes=("straight_line", "single_branch"),
                optional_route_interest_tags=("meaningful_turns",),
                minimum_route_interest_score=0.0,
                max_visual_complexity=0.34,
                max_repeated_mechanics=0,
                required_decision_count_range=(0, 2),
                minimum_decision_window_seconds=2.0,
            ),
            "easy": DifficultyPreset(
                name="easy",
                node_count_range=(5, 7),
                switch_count_range=(1, 2),
                required_tap_range=(1, 2),
                route_length_range=(3, 5),
                dead_end_count_range=(1, 2),
                max_outgoing_edges_per_switch=2,
                allow_return_loops=False,
                allow_repeated_switch_taps=False,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=12,
                map_size_profile_weights=(("standard_portrait", 1),),
                allowed_topology_classes=("single_branch", "two_switch_order", "detour_gate", "package_gate"),
                optional_route_interest_tags=("correct_detour", "package_gate_tension", "meaningful_turns"),
                minimum_route_interest_score=0.20,
                max_visual_complexity=0.44,
                max_repeated_mechanics=1,
                required_decision_count_range=(1, 3),
                minimum_decision_window_seconds=1.6,
                maximum_multiple_taps_in_window=1,
            ),
            "medium": DifficultyPreset(
                name="medium",
                node_count_range=(7, 9),
                switch_count_range=(2, 3),
                required_tap_range=(2, 3),
                route_length_range=(5, 7),
                dead_end_count_range=(1, 3),
                max_outgoing_edges_per_switch=3,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=15,
                map_size_profile_weights=(("standard_portrait", 5), ("large_portrait", 1)),
                allowed_topology_classes=(
                    "two_switch_order",
                    "package_gate",
                    "detour_gate",
                    "split_rejoin",
                    "hub_spoke",
                    "return_loop",
                ),
                optional_route_interest_tags=(
                    "correct_detour",
                    "package_gate_tension",
                    "split_rejoin",
                    "fake_shortcut",
                    "meaningful_turns",
                ),
                minimum_route_interest_score=0.42,
                max_visual_complexity=0.62,
                max_repeated_mechanics=2,
                required_decision_count_range=(2, 4),
                minimum_decision_window_seconds=1.25,
                minimum_strategic_property_count=1,
                maximum_independent_decision_ratio=0.75,
            ),
            "hard": DifficultyPreset(
                name="hard",
                node_count_range=(9, 12),
                switch_count_range=(3, 5),
                required_tap_range=(3, 5),
                route_length_range=(7, 10),
                dead_end_count_range=(2, 4),
                max_outgoing_edges_per_switch=3,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=18,
                map_size_profile_weights=(("standard_portrait", 2), ("large_portrait", 3)),
                allowed_topology_classes=(
                    "two_switch_order",
                    "detour_gate",
                    "split_rejoin",
                    "hub_spoke",
                    "return_loop",
                    "ring",
                    "two_phase",
                    "revisit",
                ),
                optional_route_interest_tags=(
                    "correct_detour",
                    "package_gate_tension",
                    "split_rejoin",
                    "fake_shortcut",
                    "loop_or_revisit",
                    "multi_exit_hub",
                    "two_phase",
                    "meaningful_turns",
                ),
                minimum_route_interest_score=0.54,
                max_visual_complexity=0.76,
                max_repeated_mechanics=2,
                allow_ring_routes=True,
                required_decision_count_range=(3, 6),
                minimum_decision_window_seconds=1.0,
                minimum_strategic_property_count=2,
                maximum_independent_decision_ratio=0.67,
            ),
            "expert": DifficultyPreset(
                name="expert",
                node_count_range=(8, 13),
                switch_count_range=(1, 5),
                required_tap_range=(2, 6),
                route_length_range=(6, 11),
                dead_end_count_range=(1, 4),
                max_outgoing_edges_per_switch=4,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.45,
                time_limit_padding_seconds=20,
                map_size_profile_weights=(("standard_portrait", 2), ("large_portrait", 3)),
                allowed_topology_classes=(
                    "detour_gate",
                    "four_way_gate",
                    "four_way_ring",
                    "hub_spoke",
                    "split_rejoin",
                    "two_switch_order",
                    "return_loop",
                    "ring",
                    "revisit",
                    "two_phase",
                ),
                optional_route_interest_tags=(
                    "package_gate_tension",
                    "split_rejoin",
                    "fake_shortcut",
                    "loop_or_revisit",
                    "multi_exit_hub",
                    "two_phase",
                    "meaningful_turns",
                ),
                minimum_route_interest_score=0.58,
                max_visual_complexity=0.86,
                max_repeated_mechanics=3,
                allow_ring_routes=True,
                required_decision_count_range=(4, 8),
                minimum_decision_window_seconds=0.85,
                minimum_strategic_property_count=2,
                maximum_independent_decision_ratio=0.60,
            ),
        }

    @property
    def valid_names(self) -> list[str]:
        return sorted(self._presets)

    def get_preset(self, name: str) -> DifficultyPreset:
        key = name.strip().lower()
        try:
            return self._presets[key]
        except KeyError as exc:
            raise ValueError(f"Unknown difficulty preset: {name}") from exc

    def check_candidate_matches_difficulty(
        self,
        level_document,
        solution,
        preset: DifficultyPreset,
        allow_range_exceptions: bool = False,
        decision_profile=None,
        configured_lookahead_seconds: float | None = None,
    ) -> list[str]:
        messages: list[str] = []
        node_count = len(level_document.graph.nodes)
        edge_by_id = {edge.id: edge for edge in level_document.graph.edges}
        switch_classification_service = SwitchClassificationService()
        classifications_by_node_id = {
            node.id: switch_classification_service.classify_node(node, edge_by_id)
            for node in level_document.graph.nodes
        }
        switch_nodes = [
            node
            for node in level_document.graph.nodes
            if classifications_by_node_id[node.id].is_switchable
        ]
        tap_count = len(solution.actions)
        dead_end_count = sum(
            1
            for node in level_document.graph.nodes
            if not node.outgoingEdgeIDs and node.id != level_document.destinationNodeID
        )
        repeated_taps = [
            node_id
            for node_id, count in Counter(action.tapNodeID for action in solution.actions).items()
            if count > 1
        ]

        if not allow_range_exceptions:
            self._check_range("node_count", node_count, preset.node_count_range, messages)
            self._check_range("switch_count", len(switch_nodes), preset.switch_count_range, messages)
            self._check_range("required_tap_count", tap_count, preset.required_tap_range, messages)
            self._check_range("dead_end_count", dead_end_count, preset.dead_end_count_range, messages)

        for node in level_document.graph.nodes:
            valid_outgoing_count = classifications_by_node_id[node.id].valid_outgoing_edge_count
            if valid_outgoing_count > preset.max_outgoing_edges_per_switch:
                messages.append(f"switch_too_many_outgoing_edges:{node.id}")
        if repeated_taps and not preset.allow_repeated_switch_taps:
            messages.append(f"repeated_switch_taps_not_allowed:{','.join(sorted(repeated_taps))}")
        if decision_profile is not None:
            messages.extend(
                self.check_decision_profile_matches_difficulty(
                    decision_profile,
                    preset,
                    configured_lookahead_seconds=configured_lookahead_seconds,
                )
            )
        return messages

    def check_decision_profile_matches_difficulty(
        self,
        profile,
        preset: DifficultyPreset,
        *,
        configured_lookahead_seconds: float | None = None,
    ) -> list[str]:
        """Return only measured decision-quality issues for a difficulty preset.

        Corpus migration needs to distinguish a topology/decision problem from
        unrelated node-count and layout-range mismatches. Keeping this as a
        public boundary also prevents reporting tools from duplicating the
        preset threshold logic.
        """

        messages: list[str] = []
        self._check_decision_profile(
            profile,
            preset,
            messages,
            configured_lookahead_seconds=configured_lookahead_seconds,
        )
        return messages

    def _check_decision_profile(
        self,
        profile,
        preset: DifficultyPreset,
        messages: list[str],
        *,
        configured_lookahead_seconds: float | None,
    ) -> None:
        self._check_range(
            "decision_count",
            profile.required_decision_count,
            preset.required_decision_count_range,
            messages,
        )
        if (
            profile.minimum_window_seconds is not None
            and profile.minimum_window_seconds < preset.minimum_decision_window_seconds
            and (
                configured_lookahead_seconds is None
                or configured_lookahead_seconds < preset.minimum_decision_window_seconds
            )
        ):
            messages.append("decision_window_below_preset_minimum")
        if (
            preset.maximum_multiple_taps_in_window is not None
            and profile.multiple_taps_in_window_count > preset.maximum_multiple_taps_in_window
        ):
            messages.append("too_many_multiple_tap_windows")

        phase_change = int(
            profile.package_phase_decisions_before > 0
            and profile.package_phase_decisions_after > 0
        )
        strategic_property_count = (
            profile.ordered_dependency_count
            + profile.switch_state_change_on_revisit_count
            + profile.recoverable_mistake_count
            + profile.route_revisit_count
            + phase_change
        )
        if strategic_property_count < preset.minimum_strategic_property_count:
            messages.append("insufficient_strategic_decision_evidence")
        if (
            profile.required_decision_count > 1
            and profile.independent_decision_ratio > preset.maximum_independent_decision_ratio
        ):
            messages.append("independent_decision_ratio_above_preset_maximum")

    def metrics_for_generated_level(self, generated_level) -> DifficultyMetrics:
        return self.metrics_for_level(
            generated_level.level_document,
            generated_level.solution,
            abstract_solution_metadata=getattr(generated_level, "abstract_solution_metadata", None),
            simulation_result=getattr(generated_level, "simulation_result", None),
            road_shape_metadata=getattr(generated_level, "road_shape_metadata", None) or {},
        )

    def metrics_for_level(
        self,
        level_document,
        solution,
        *,
        abstract_solution_metadata=None,
        simulation_result=None,
        road_shape_metadata: dict | None = None,
    ) -> DifficultyMetrics:
        edge_by_id = {edge.id: edge for edge in level_document.graph.edges}
        switch_classifier = SwitchClassificationService()
        switch_classifications = [
            switch_classifier.classify_node(node, edge_by_id)
            for node in level_document.graph.nodes
        ]
        switch_count = sum(1 for classification in switch_classifications if classification.is_switchable)
        four_way_switch_count = sum(
            1
            for classification in switch_classifications
            if classification.valid_outgoing_edge_count == 4
        )
        tap_counts = Counter(action.tapNodeID for action in solution.actions)
        repeated_tap_count = sum(count - 1 for count in tap_counts.values() if count > 1)
        sorted_actions = sorted(solution.actions, key=lambda action: float(action.timeSeconds))
        tap_times = [float(action.timeSeconds) for action in sorted_actions]
        average_tap_spacing = None
        minimum_tap_spacing = None
        if len(tap_times) >= 2:
            spacings = [current - previous for previous, current in zip(tap_times, tap_times[1:])]
            average_tap_spacing = round(sum(spacings) / len(spacings), 4)
            minimum_tap_spacing = round(min(spacings), 4)

        solution_path_length = 0
        false_branch_count = 0
        loop_count = 0
        if abstract_solution_metadata is not None:
            solution_path_length = max(0, len(abstract_solution_metadata.required_path) - 1)
            false_branch_count = abstract_solution_metadata.false_route_count
            loop_count = abstract_solution_metadata.loop_count
        elif simulation_result is not None:
            traversed_edges = [
                step.edge_id
                for step in simulation_result.steps
                if step.event in {"enter_edge", "begin_transition"} and step.edge_id
            ]
            solution_path_length = len(traversed_edges)
        if solution_path_length == 0:
            solution_path_length = self._shortest_package_route_length(level_document)

        layout_summary = GraphLayoutService().readability_summary(
            {node.id: (node.x, node.y) for node in level_document.graph.nodes},
            [(edge.fromNodeID, edge.toNodeID, edge.id) for edge in level_document.graph.edges],
        )
        crossing_count = int((road_shape_metadata or {}).get("crossingCount", layout_summary["crossings"]))
        route_crossing_score = self._clamp(crossing_count / 4)
        visual_complexity_score = self._clamp(
            (len(level_document.graph.nodes) * 0.045)
            + (len(level_document.graph.edges) * 0.035)
            + (switch_count * 0.08)
            + (four_way_switch_count * 0.18)
            + (layout_summary["edgeSpacingIssues"] * 0.06)
            + (route_crossing_score * 0.18)
        )
        package_detour_complexity = self._package_detour_complexity(level_document)
        mechanical_score = self._clamp(
            (len(solution.actions) * 0.11)
            + (switch_count * 0.10)
            + (four_way_switch_count * 0.18)
            + (repeated_tap_count * 0.12)
            + (solution_path_length * 0.045)
            + (false_branch_count * 0.05)
            + (loop_count * 0.12)
            + (package_detour_complexity * 0.14)
        )
        estimated_band = self.band_for_scores(mechanical_score, visual_complexity_score)
        explanations = self.explain_metrics(
            mechanical_score=mechanical_score,
            visual_score=visual_complexity_score,
            tap_count=len(solution.actions),
            switch_count=switch_count,
            four_way_switch_count=four_way_switch_count,
            repeated_tap_count=repeated_tap_count,
            loop_count=loop_count,
            false_branch_count=false_branch_count,
        )
        return DifficultyMetrics(
            required_tap_count=len(solution.actions),
            switch_count=switch_count,
            four_way_switch_count=four_way_switch_count,
            repeated_tap_count=repeated_tap_count,
            solution_path_length=solution_path_length,
            false_branch_count=false_branch_count,
            loop_count=loop_count,
            average_time_between_required_taps=average_tap_spacing,
            minimum_reaction_window_before_required_switch=minimum_tap_spacing,
            visual_complexity_score=round(visual_complexity_score, 4),
            route_crossing_score=round(route_crossing_score, 4),
            package_detour_complexity=round(package_detour_complexity, 4),
            mechanical_score=round(mechanical_score, 4),
            visual_score=round(visual_complexity_score, 4),
            estimated_band=estimated_band,
            explanations=explanations,
        )

    def band_for_scores(self, mechanical_score: float, visual_score: float) -> str:
        combined = (mechanical_score * 0.7) + (visual_score * 0.3)
        if combined < 0.18:
            return "tutorial"
        if combined < 0.34:
            return "easy"
        if combined < 0.54:
            return "medium"
        if combined < 0.74:
            return "hard"
        return "expert"

    def band_index(self, band: str) -> int:
        return self.band_order.index(band) if band in self.band_order else -1

    def explain_metrics(
        self,
        *,
        mechanical_score: float,
        visual_score: float,
        tap_count: int,
        switch_count: int,
        four_way_switch_count: int,
        repeated_tap_count: int,
        loop_count: int,
        false_branch_count: int,
    ) -> tuple[str, ...]:
        explanations: list[str] = [
            f"mechanical_score={mechanical_score:.2f}",
            f"visual_score={visual_score:.2f}",
        ]
        if tap_count == 0:
            explanations.append("no_required_taps")
        elif tap_count >= 4:
            explanations.append("high_required_tap_count")
        if switch_count >= 3:
            explanations.append("multiple_switches")
        if four_way_switch_count:
            explanations.append("four_way_switch_present")
        if repeated_tap_count:
            explanations.append("repeated_switch_taps")
        if loop_count:
            explanations.append("loop_route")
        if false_branch_count >= 2:
            explanations.append("multiple_false_branches")
        return tuple(explanations)

    def _check_range(self, name: str, value: int, value_range: tuple[int, int], messages: list[str]) -> None:
        minimum, maximum = value_range
        if value < minimum or value > maximum:
            messages.append(f"{name}_outside_difficulty_range:{value}:{minimum}-{maximum}")

    def _shortest_package_route_length(self, level_document) -> int:
        start_to_package = self._shortest_edge_count(
            level_document,
            level_document.startNodeID,
            level_document.packageNodeID,
        )
        package_to_destination = self._shortest_edge_count(
            level_document,
            level_document.packageNodeID,
            level_document.destinationNodeID,
        )
        if start_to_package is None or package_to_destination is None:
            return 0
        return start_to_package + package_to_destination

    def _shortest_edge_count(self, level_document, start_id: str, destination_id: str) -> int | None:
        adjacency: dict[str, list[str]] = {}
        for edge in level_document.graph.edges:
            adjacency.setdefault(edge.fromNodeID, []).append(edge.toNodeID)
        frontier = [(start_id, 0)]
        visited = {start_id}
        for node_id, distance in frontier:
            if node_id == destination_id:
                return distance
            for next_id in adjacency.get(node_id, []):
                if next_id not in visited:
                    visited.add(next_id)
                    frontier.append((next_id, distance + 1))
        return None

    def _package_detour_complexity(self, level_document) -> float:
        node_by_id = {node.id: node for node in level_document.graph.nodes}
        try:
            start = node_by_id[level_document.startNodeID]
            package = node_by_id[level_document.packageNodeID]
            destination = node_by_id[level_document.destinationNodeID]
        except KeyError:
            return 0.0
        direct = max(math.hypot(destination.x - start.x, destination.y - start.y), 1e-9)
        via_package = (
            math.hypot(package.x - start.x, package.y - start.y)
            + math.hypot(destination.x - package.x, destination.y - package.y)
        )
        return self._clamp((via_package / direct - 1.0) / 1.5)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
