from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AbstractPuzzleSwitchState:
    node_id: str
    active_edge_index: int
    active_target_node_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeID": self.node_id,
            "activeEdgeIndex": self.active_edge_index,
            "activeTargetNodeID": self.active_target_node_id,
        }


@dataclass(frozen=True)
class AbstractPuzzleSolutionMetadata:
    solution_tap_node_ids: tuple[str, ...]
    solution_switch_states: tuple[AbstractPuzzleSwitchState, ...]
    required_path: tuple[str, ...]
    alternate_path_count: int
    dead_end_count: int
    failure_path_count: int
    false_route_count: int
    loop_count: int
    minimum_required_taps: int
    optional_tap_count: int
    repeated_switch_usage: bool
    package_before_destination: bool
    failure_reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "solutionTapNodeIDs": list(self.solution_tap_node_ids),
            "solutionSwitchStates": [state.to_dict() for state in self.solution_switch_states],
            "requiredPath": list(self.required_path),
            "alternatePathCount": self.alternate_path_count,
            "deadEndCount": self.dead_end_count,
            "failurePathCount": self.failure_path_count,
            "falseRouteCount": self.false_route_count,
            "loopCount": self.loop_count,
            "minimumRequiredTaps": self.minimum_required_taps,
            "optionalTapCount": self.optional_tap_count,
            "repeatedSwitchUsage": self.repeated_switch_usage,
            "packageBeforeDestination": self.package_before_destination,
            "failureReasons": list(self.failure_reasons),
        }
