"""Lossless JSON models shared by the generator and level editor."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .edge_availability_rule import EdgeAvailabilityRule
from .level_rules import LevelRules
from .route_objective import (
    LEGACY_PICKUP_OBJECTIVE_ID,
    RouteObjective,
    RouteObjectiveKind,
    legacy_route_objectives,
)


def _extras(data: Mapping[str, Any], known: set[str]) -> dict[str, Any]:
    return deepcopy({key: value for key, value in data.items() if key not in known})


@dataclass
class RouteNode:
    id: str
    x: float
    y: float
    outgoingEdgeIDs: list[str] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RouteNode":
        return cls(str(data["id"]), float(data["x"]), float(data["y"]),
                   list(data["outgoingEdgeIDs"]), _extras(data, {"id", "x", "y", "outgoingEdgeIDs"}))

    def to_dict(self) -> dict[str, Any]:
        return {**deepcopy(self._extra), "id": self.id, "x": self.x, "y": self.y,
                "outgoingEdgeIDs": list(self.outgoingEdgeIDs)}

    def clone(self) -> "RouteNode": return deepcopy(self)


@dataclass
class RouteEdge:
    id: str
    fromNodeID: str
    toNodeID: str
    roadShape: str | None = None
    availability: str = "always"
    availabilityRule: EdgeAvailabilityRule | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    _availability_present: bool = field(default=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RouteEdge":
        return cls(
            id=str(data["id"]),
            fromNodeID=str(data["fromNodeID"]),
            toNodeID=str(data["toNodeID"]),
            roadShape=data.get("roadShape"),
            availability=str(data.get("availability", "always")),
            availabilityRule=(
                EdgeAvailabilityRule.from_dict(data["availabilityRule"])
                if data.get("availabilityRule") is not None
                else None
            ),
            _extra=_extras(
                data,
                {
                    "id",
                    "fromNodeID",
                    "toNodeID",
                    "roadShape",
                    "availability",
                    "availabilityRule",
                },
            ),
            _availability_present="availability" in data,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {**deepcopy(self._extra), "id": self.id, "fromNodeID": self.fromNodeID,
                  "toNodeID": self.toNodeID}
        if self.roadShape is not None: result["roadShape"] = self.roadShape
        if self._availability_present or self.availability != "always":
            result["availability"] = self.availability
        if self.availabilityRule is not None:
            result["availabilityRule"] = self.availabilityRule.to_dict()
        return result

    def effective_availability_rule(
        self,
        package_objective_id: str,
    ) -> EdgeAvailabilityRule:
        """Return the schema-3 rule or adapt the legacy package-state value."""

        if self.availabilityRule is not None:
            return self.availabilityRule.clone()
        return EdgeAvailabilityRule.adapting_legacy_availability(
            self.availability,
            package_objective_id,
        )

    def clone(self) -> "RouteEdge": return deepcopy(self)


@dataclass
class RouteGraph:
    nodes: list[RouteNode] = field(default_factory=list)
    edges: list[RouteEdge] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RouteGraph":
        return cls([RouteNode.from_dict(item) for item in data["nodes"]],
                   [RouteEdge.from_dict(item) for item in data["edges"]],
                   _extras(data, {"nodes", "edges"}))

    def to_dict(self) -> dict[str, Any]:
        return {**deepcopy(self._extra), "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges]}

    def clone(self) -> "RouteGraph": return deepcopy(self)


@dataclass
class EmbeddedSolution:
    tapNodeIDs: list[str] = field(default_factory=list)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EmbeddedSolution":
        return cls(list(data["tapNodeIDs"]), _extras(data, {"tapNodeIDs"}))

    def to_dict(self) -> dict[str, Any]: return {**deepcopy(self._extra), "tapNodeIDs": list(self.tapNodeIDs)}
    def clone(self) -> "EmbeddedSolution": return deepcopy(self)


@dataclass
class LevelDocument:
    id: str
    name: str
    graph: RouteGraph
    startNodeID: str
    packageNodeID: str
    destinationNodeID: str
    timeLimitSeconds: int | float
    parTaps: int
    objectives: list[RouteObjective] | None = None
    solution: EmbeddedSolution | None = None
    rules: LevelRules = field(default_factory=LevelRules.legacy_defaults)
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    _rules_present: bool = field(default=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LevelDocument":
        known = {"id", "name", "graph", "startNodeID", "packageNodeID", "destinationNodeID",
                 "timeLimitSeconds", "parTaps", "objectives", "solution", "rules"}
        solution = data.get("solution")
        objectives = data.get("objectives")
        return cls(str(data["id"]), str(data["name"]), RouteGraph.from_dict(data["graph"]),
                   str(data["startNodeID"]), str(data["packageNodeID"]), str(data["destinationNodeID"]),
                   data["timeLimitSeconds"], data["parTaps"],
                   [RouteObjective.from_dict(item) for item in objectives] if objectives is not None else None,
                   EmbeddedSolution.from_dict(solution) if solution is not None else None,
                   LevelRules.from_level_dict(data), _extras(data, known), "rules" in data)

    def to_dict(self) -> dict[str, Any]:
        result = {**deepcopy(self._extra), "id": self.id, "name": self.name,
                  "graph": self.graph.to_dict(), "startNodeID": self.startNodeID,
                  "packageNodeID": self.packageNodeID, "destinationNodeID": self.destinationNodeID,
                  "timeLimitSeconds": self.timeLimitSeconds, "parTaps": self.parTaps}
        if self.objectives is not None: result["objectives"] = [objective.to_dict() for objective in self.objectives]
        if self.solution is not None: result["solution"] = self.solution.to_dict()
        if self._rules_present or self.rules != LevelRules.legacy_defaults(): result["rules"] = self.rules.to_dict()
        return result

    @property
    def schema_version(self) -> int:
        """Return the effective schema version while retaining the original JSON shape."""

        value = self._extra.get("schemaVersion", 1)
        return value if isinstance(value, int) and not isinstance(value, bool) else 1

    @property
    def effective_objectives(self) -> list[RouteObjective]:
        """Return authored schema-3 objectives or an internal legacy two-stop adapter."""

        if self.schema_version >= 3:
            return [objective.clone() for objective in self.objectives or ()]
        return legacy_route_objectives(self.packageNodeID, self.destinationNodeID)

    def effective_edge_availability_rule(self, edge: RouteEdge) -> EdgeAvailabilityRule:
        """Resolve a road rule against this document's effective pickup objective."""

        pickup = min(
            (
                objective
                for objective in self.effective_objectives
                if objective.kind is RouteObjectiveKind.PICKUP
            ),
            key=lambda objective: objective.sequenceIndex,
            default=None,
        )
        package_objective_id = pickup.id if pickup is not None else LEGACY_PICKUP_OBJECTIVE_ID
        return edge.effective_availability_rule(package_objective_id)

    def clone(self) -> "LevelDocument": return deepcopy(self)


@dataclass
class SolutionAction:
    timeSeconds: int | float
    tapNodeID: str
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SolutionAction":
        return cls(data["timeSeconds"], str(data["tapNodeID"]), _extras(data, {"timeSeconds", "tapNodeID"}))

    def to_dict(self) -> dict[str, Any]:
        return {**deepcopy(self._extra), "timeSeconds": self.timeSeconds, "tapNodeID": self.tapNodeID}
    def clone(self) -> "SolutionAction": return deepcopy(self)


@dataclass
class Solution:
    levelID: str
    description: str | None
    expectedOutcome: str
    maxTaps: int
    requiresWithinTimeLimit: bool
    actions: list[SolutionAction] = field(default_factory=list)
    isPlaceholder: bool | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Solution":
        known = {"levelID", "description", "expectedOutcome", "maxTaps", "requiresWithinTimeLimit",
                 "isPlaceholder", "actions"}
        return cls(str(data["levelID"]), data.get("description"), str(data["expectedOutcome"]),
                   data["maxTaps"], data["requiresWithinTimeLimit"],
                   [SolutionAction.from_dict(item) for item in data["actions"]],
                   data.get("isPlaceholder"), _extras(data, known))

    def to_dict(self) -> dict[str, Any]:
        result = {**deepcopy(self._extra), "levelID": self.levelID, "description": self.description,
                  "expectedOutcome": self.expectedOutcome, "maxTaps": self.maxTaps,
                  "requiresWithinTimeLimit": self.requiresWithinTimeLimit,
                  "actions": [action.to_dict() for action in self.actions]}
        if self.isPlaceholder is not None: result["isPlaceholder"] = self.isPlaceholder
        return result

    def clone(self) -> "Solution": return deepcopy(self)
