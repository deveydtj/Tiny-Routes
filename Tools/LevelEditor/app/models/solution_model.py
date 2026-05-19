from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SolutionActionModel:
    """Represents a single timed tap action in a solution script."""

    timeSeconds: int | float
    tapNodeID: str
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolutionActionModel":
        known = {"timeSeconds", "tapNodeID"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            timeSeconds=data["timeSeconds"],
            tapNodeID=data["tapNodeID"],
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "timeSeconds": self.timeSeconds,
            "tapNodeID": self.tapNodeID,
        }
        result.update(self._extra)
        return result


@dataclass
class SolutionModel:
    """Represents a level solution sidecar JSON document."""

    levelID: str
    description: str | None
    expectedOutcome: str
    maxTaps: int
    requiresWithinTimeLimit: bool
    actions: list[SolutionActionModel] = field(default_factory=list)
    isPlaceholder: bool | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SolutionModel":
        known = {
            "levelID",
            "description",
            "expectedOutcome",
            "maxTaps",
            "requiresWithinTimeLimit",
            "isPlaceholder",
            "actions",
        }
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            levelID=data["levelID"],
            description=data.get("description"),
            expectedOutcome=data["expectedOutcome"],
            maxTaps=data["maxTaps"],
            requiresWithinTimeLimit=data["requiresWithinTimeLimit"],
            actions=[SolutionActionModel.from_dict(action) for action in data["actions"]],
            isPlaceholder=data.get("isPlaceholder"),
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "levelID": self.levelID,
            "description": self.description,
            "expectedOutcome": self.expectedOutcome,
            "maxTaps": self.maxTaps,
            "requiresWithinTimeLimit": self.requiresWithinTimeLimit,
            "actions": [action.to_dict() for action in self.actions],
        }
        if self.isPlaceholder is not None:
            result["isPlaceholder"] = self.isPlaceholder
        result.update(self._extra)
        return result
