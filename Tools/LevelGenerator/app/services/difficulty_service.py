from __future__ import annotations

from collections import Counter

from ..models.difficulty_preset import DifficultyPreset
from .switch_classification_service import SwitchClassificationService


class DifficultyService:
    def __init__(self) -> None:
        self._presets = {
            "tutorial": DifficultyPreset(
                name="tutorial",
                node_count_range=(3, 5),
                switch_count_range=(0, 1),
                required_tap_range=(0, 1),
                dead_end_count_range=(0, 1),
                max_outgoing_edges_per_switch=2,
                allow_return_loops=False,
                allow_repeated_switch_taps=False,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=10,
            ),
            "easy": DifficultyPreset(
                name="easy",
                node_count_range=(5, 7),
                switch_count_range=(1, 2),
                required_tap_range=(1, 2),
                dead_end_count_range=(1, 2),
                max_outgoing_edges_per_switch=2,
                allow_return_loops=False,
                allow_repeated_switch_taps=False,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=12,
            ),
            "medium": DifficultyPreset(
                name="medium",
                node_count_range=(7, 9),
                switch_count_range=(2, 3),
                required_tap_range=(2, 3),
                dead_end_count_range=(1, 3),
                max_outgoing_edges_per_switch=3,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=15,
            ),
            "hard": DifficultyPreset(
                name="hard",
                node_count_range=(9, 12),
                switch_count_range=(3, 5),
                required_tap_range=(3, 5),
                dead_end_count_range=(2, 4),
                max_outgoing_edges_per_switch=3,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.40,
                time_limit_padding_seconds=18,
                allow_ring_routes=True,
            ),
            "expert": DifficultyPreset(
                name="expert",
                node_count_range=(7, 12),
                switch_count_range=(1, 5),
                required_tap_range=(2, 6),
                dead_end_count_range=(1, 4),
                max_outgoing_edges_per_switch=4,
                allow_return_loops=True,
                allow_repeated_switch_taps=True,
                min_tap_spacing_seconds=0.45,
                time_limit_padding_seconds=20,
                allow_ring_routes=True,
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
        return messages

    def _check_range(self, name: str, value: int, value_range: tuple[int, int], messages: list[str]) -> None:
        minimum, maximum = value_range
        if value < minimum or value > maximum:
            messages.append(f"{name}_outside_difficulty_range:{value}:{minimum}-{maximum}")
