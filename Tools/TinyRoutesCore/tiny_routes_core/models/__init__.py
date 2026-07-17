"""Versioned Tiny Routes data models."""

from .level_rules import LevelRules, SwitchInteractionMode
from .route_objective import (
    LEGACY_DESTINATION_OBJECTIVE_ID,
    LEGACY_PICKUP_OBJECTIVE_ID,
    RouteObjective,
    RouteObjectiveKind,
    legacy_route_objectives,
)
from .documents import (
    EmbeddedSolution,
    LevelDocument,
    RouteEdge,
    RouteGraph,
    RouteNode,
    Solution,
    SolutionAction,
)

__all__ = [name for name in globals() if not name.startswith("_")]
