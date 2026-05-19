from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteNodeModel:
    """Represents a node in a level's route graph."""

    id: str
    x: float
    y: float
    outgoingEdgeIDs: list[str] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteNodeModel":
        """Create a RouteNodeModel from a raw JSON-decoded dictionary."""
        known = {"id", "x", "y", "outgoingEdgeIDs"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            id=data["id"],
            x=float(data["x"]),
            y=float(data["y"]),
            outgoingEdgeIDs=list(data.get("outgoingEdgeIDs", [])),
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a JSON-compatible dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "outgoingEdgeIDs": list(self.outgoingEdgeIDs),
        }
        result.update(self._extra)
        return result
