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

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeID": self.node_id,
            "visitIndex": self.visit_index,
            "rotationCount": self.rotation_count,
            "windowOpenSeconds": self.window_open_seconds,
            "windowCloseSeconds": self.window_close_seconds,
            "chosenTapSeconds": list(self.chosen_tap_seconds),
            "safetyMarginSeconds": self.safety_margin_seconds,
            "failureReason": self.failure_reason,
        }


@dataclass
class RuntimeSolutionSearchResult:
    passed: bool
    actions: tuple[RuntimeSolutionAction, ...] = ()
    diagnostics: tuple[RuntimeDecisionTimingDiagnostic, ...] = ()
    failure_reason: str | None = None
    replay_result: Any | None = field(default=None, repr=False)

