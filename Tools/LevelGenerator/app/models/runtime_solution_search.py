from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeSolutionAction:
    time_seconds: float
    tap_node_id: str
    expected_edge_after_tap: str | None = None


@dataclass(frozen=True)
class RuntimeDecisionTimingDiagnostic:
    node_id: str
    visit_index: int
    rotation_count: int
    window_open_seconds: float | None
    window_close_seconds: float | None
    chosen_tap_seconds: tuple[float, ...] = ()
    safety_margin_seconds: float = 0.0
    failure_reason: str | None = None
    objective_index: int | None = None
    active_objective_id: str | None = None
    completed_objective_ids: tuple[str, ...] = ()
    available_edge_ids: tuple[str, ...] = ()
    consumed_edge_ids: tuple[str, ...] = ()
    selected_edge_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "nodeID": self.node_id,
            "visitIndex": self.visit_index,
            "rotationCount": self.rotation_count,
            "windowOpenSeconds": self.window_open_seconds,
            "windowCloseSeconds": self.window_close_seconds,
            "chosenTapSeconds": list(self.chosen_tap_seconds),
            "safetyMarginSeconds": self.safety_margin_seconds,
            "failureReason": self.failure_reason,
        }
        if self.objective_index is not None:
            payload["objectiveIndex"] = self.objective_index
        if self.active_objective_id is not None:
            payload["activeObjectiveID"] = self.active_objective_id
        if self.completed_objective_ids:
            payload["completedObjectiveIDs"] = list(self.completed_objective_ids)
        if self.available_edge_ids:
            payload["availableEdgeIDs"] = list(self.available_edge_ids)
        if self.consumed_edge_ids:
            payload["consumedEdgeIDs"] = list(self.consumed_edge_ids)
        if self.selected_edge_id is not None:
            payload["selectedEdgeID"] = self.selected_edge_id
        return payload


@dataclass
class RuntimeSolutionSearchResult:
    passed: bool
    actions: tuple[RuntimeSolutionAction, ...] = ()
    diagnostics: tuple[RuntimeDecisionTimingDiagnostic, ...] = ()
    failure_reason: str | None = None
    replay_result: Any | None = field(default=None, repr=False)
    jitter_report: Any | None = field(default=None, repr=False)
