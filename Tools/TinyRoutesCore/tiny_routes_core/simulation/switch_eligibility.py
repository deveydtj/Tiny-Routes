"""Read-only live-lookahead switch eligibility, matching the Swift runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .runtime_state import RuntimeState


NUMERIC_TOLERANCE = 1e-9


class SwitchEligibilityReason(str, Enum):
    ELIGIBLE = "eligible"
    OUTSIDE_LOOKAHEAD_WINDOW = "outsideLookaheadWindow"
    NO_UPCOMING_SWITCH = "noUpcomingSwitch"
    INVALID_SPEED = "invalidSpeed"
    CYCLE_DETECTED = "cycleDetected"
    STEP_LIMIT_REACHED = "stepLimitReached"


@dataclass(frozen=True)
class SwitchEligibilitySnapshot:
    eligible_node_id: str | None
    upcoming_node_id: str | None
    travel_time_seconds: float | None
    reason: SwitchEligibilityReason
    steps_examined: int = 0


def edge_length(state: RuntimeState, edge_id: str) -> float:
    edge = state.runtime_graph.index.edges_by_id[edge_id]
    start = state.runtime_graph.index.nodes_by_id[edge.fromNodeID]
    end = state.runtime_graph.index.nodes_by_id[edge.toNodeID]
    dx, dy = abs(end.x - start.x), abs(end.y - start.y)
    if edge.roadShape in {"horizontalFirst", "verticalFirst"}:
        return dx + dy
    return math.hypot(dx, dy)


def switch_eligibility(
    state: RuntimeState,
    *,
    speed: float = 1.0,
    maximum_step_count: int | None = None,
) -> SwitchEligibilitySnapshot:
    """Return the first switch on the selected route and whether it is in range."""
    if not math.isfinite(speed) or speed <= 0:
        return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.INVALID_SPEED)

    index = state.runtime_graph.index
    distance = 0.0
    if state.current_edge_id is not None:
        edge = index.edges_by_id.get(state.current_edge_id)
        if edge is None:
            return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.NO_UPCOMING_SWITCH)
        distance = max(0.0, 1.0 - min(max(state.edge_progress, 0.0), 1.0)) * edge_length(state, edge.id)
        next_node_id = edge.toNodeID
    else:
        next_node_id = state.current_node_id

    limit = maximum_step_count if maximum_step_count is not None else max(
        len(index.nodes_by_id) + len(index.edges_by_id), 1
    )
    visited: set[str] = set()
    steps = 0
    while steps < max(limit, 0):
        steps += 1
        if next_node_id in visited:
            return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.CYCLE_DETECTED, steps)
        visited.add(next_node_id)
        node = index.nodes_by_id.get(next_node_id)
        if node is None:
            return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.NO_UPCOMING_SWITCH, steps)
        outgoing = state.runtime_graph.usable_outgoing(
            node.id,
            state.package_collected,
        )
        if len(outgoing) >= 2:
            travel_time = distance / speed
            window = max(float(state.rules.switch_lookahead_seconds), 0.0)
            eligible = travel_time <= window + NUMERIC_TOLERANCE
            return SwitchEligibilitySnapshot(
                node.id if eligible else None,
                node.id,
                travel_time,
                SwitchEligibilityReason.ELIGIBLE if eligible else SwitchEligibilityReason.OUTSIDE_LOOKAHEAD_WINDOW,
                steps,
            )
        edge_id = state.runtime_graph.active_edge_ids.get(node.id)
        edge = index.edges_by_id.get(edge_id) if edge_id is not None else None
        if edge is None or edge.fromNodeID != node.id:
            return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.NO_UPCOMING_SWITCH, steps)
        distance += edge_length(state, edge.id)
        next_node_id = edge.toNodeID

    return SwitchEligibilitySnapshot(None, None, None, SwitchEligibilityReason.STEP_LIMIT_REACHED, steps)
