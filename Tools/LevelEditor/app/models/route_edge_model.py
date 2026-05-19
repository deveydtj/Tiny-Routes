from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteEdgeModel:
    """Represents a directed edge in a level's route graph."""

    id: str
    fromNodeID: str
    toNodeID: str
    roadShape: str | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteEdgeModel":
        """Create a RouteEdgeModel from a raw JSON-decoded dictionary."""
        known = {"id", "fromNodeID", "toNodeID", "roadShape"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            id=data["id"],
            fromNodeID=data["fromNodeID"],
            toNodeID=data["toNodeID"],
            roadShape=data.get("roadShape"),
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a JSON-compatible dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "fromNodeID": self.fromNodeID,
            "toNodeID": self.toNodeID,
        }
        if self.roadShape is not None:
            result["roadShape"] = self.roadShape
        result.update(self._extra)
        return result
