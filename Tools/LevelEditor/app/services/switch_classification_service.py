from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SwitchNodeKind(str, Enum):
    TERMINAL = "terminal"
    PASS_THROUGH = "pass_through"
    TWO_WAY_SWITCH = "two_way_switch"
    THREE_WAY_SWITCH = "three_way_switch"
    FOUR_WAY_INTERSECTION_SWITCH = "four_way_intersection_switch"
    INVALID_TOO_MANY_OUTGOING_EDGES = "invalid_too_many_outgoing_edges"


MAX_SUPPORTED_OUTGOING_EDGES = 4


@dataclass(frozen=True)
class SwitchNodeClassification:
    kind: SwitchNodeKind
    valid_outgoing_edge_ids: tuple[str, ...]

    @property
    def valid_outgoing_edge_count(self) -> int:
        return len(self.valid_outgoing_edge_ids)

    @property
    def is_switchable(self) -> bool:
        return self.kind in {
            SwitchNodeKind.TWO_WAY_SWITCH,
            SwitchNodeKind.THREE_WAY_SWITCH,
            SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH,
        }

    @property
    def display_name(self) -> str:
        display_names = {
            SwitchNodeKind.TERMINAL: "Terminal",
            SwitchNodeKind.PASS_THROUGH: "Pass-through",
            SwitchNodeKind.TWO_WAY_SWITCH: "2-way switch",
            SwitchNodeKind.THREE_WAY_SWITCH: "3-way switch",
            SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH: "4-way intersection switch",
            SwitchNodeKind.INVALID_TOO_MANY_OUTGOING_EDGES: "Invalid: too many outgoing edges",
        }
        return display_names[self.kind]


class SwitchClassificationService:
    def classify_node(self, node, edges_by_id: dict[str, object]) -> SwitchNodeClassification:
        valid_outgoing_edge_ids = tuple(
            edge_id
            for edge_id in node.outgoingEdgeIDs
            if (edge := edges_by_id.get(edge_id)) is not None
            and getattr(edge, "fromNodeID", None) == node.id
        )
        return SwitchNodeClassification(
            kind=self.kind_for_count(len(valid_outgoing_edge_ids)),
            valid_outgoing_edge_ids=valid_outgoing_edge_ids,
        )

    def kind_for_count(self, valid_outgoing_edge_count: int) -> SwitchNodeKind:
        if valid_outgoing_edge_count == 0:
            return SwitchNodeKind.TERMINAL
        if valid_outgoing_edge_count == 1:
            return SwitchNodeKind.PASS_THROUGH
        if valid_outgoing_edge_count == 2:
            return SwitchNodeKind.TWO_WAY_SWITCH
        if valid_outgoing_edge_count == 3:
            return SwitchNodeKind.THREE_WAY_SWITCH
        if valid_outgoing_edge_count == 4:
            return SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH
        return SwitchNodeKind.INVALID_TOO_MANY_OUTGOING_EDGES
