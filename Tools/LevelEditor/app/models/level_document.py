from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .route_node_model import RouteNodeModel
from .route_edge_model import RouteEdgeModel


@dataclass
class EmbeddedSolution:
    """Optional solution hint embedded directly in some level JSON files."""

    tapNodeIDs: list[str] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmbeddedSolution":
        known = {"tapNodeIDs"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            tapNodeIDs=list(data["tapNodeIDs"]),
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"tapNodeIDs": list(self.tapNodeIDs)}
        result.update(self._extra)
        return result


@dataclass
class RouteGraphModel:
    """Represents the graph object inside a level document."""

    nodes: list[RouteNodeModel] = field(default_factory=list)
    edges: list[RouteEdgeModel] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteGraphModel":
        known = {"nodes", "edges"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            nodes=[RouteNodeModel.from_dict(n) for n in data["nodes"]],
            edges=[RouteEdgeModel.from_dict(e) for e in data["edges"]],
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
        result.update(self._extra)
        return result


@dataclass
class LevelDocument:
    """Represents a complete level JSON document."""

    id: str
    name: str
    graph: RouteGraphModel
    startNodeID: str
    packageNodeID: str
    destinationNodeID: str
    timeLimitSeconds: int | float
    parTaps: int
    solution: EmbeddedSolution | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LevelDocument":
        """Create a LevelDocument from a raw JSON-decoded dictionary."""
        known = {
            "id", "name", "graph", "startNodeID", "packageNodeID",
            "destinationNodeID", "timeLimitSeconds", "parTaps", "solution",
        }
        extra = {k: v for k, v in data.items() if k not in known}
        solution_data = data.get("solution")
        return cls(
            id=data["id"],
            name=data["name"],
            graph=RouteGraphModel.from_dict(data["graph"]),
            startNodeID=data["startNodeID"],
            packageNodeID=data["packageNodeID"],
            destinationNodeID=data["destinationNodeID"],
            timeLimitSeconds=data["timeLimitSeconds"],
            parTaps=data["parTaps"],
            solution=EmbeddedSolution.from_dict(solution_data) if solution_data is not None else None,
            _extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a JSON-compatible dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "graph": self.graph.to_dict(),
            "startNodeID": self.startNodeID,
            "packageNodeID": self.packageNodeID,
            "destinationNodeID": self.destinationNodeID,
            "timeLimitSeconds": self.timeLimitSeconds,
            "parTaps": self.parTaps,
        }
        if self.solution is not None:
            result["solution"] = self.solution.to_dict()
        result.update(self._extra)
        return result
