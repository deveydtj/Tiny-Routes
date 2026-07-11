"""Topology-only puzzle search.

This service chooses switch rotations when a route encounters a decision node. It
does not assign tap timestamps or claim that a decision is a runtime action.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe
from .abstract_puzzle_solver_service import AbstractPuzzleSolverError, AbstractPuzzleSolverService


@dataclass(frozen=True)
class TopologySearchResult:
    solutions: tuple[AbstractPuzzleSolutionMetadata, ...]
    failure_reasons: tuple[str, ...] = ()
    limit_reached: bool = False

    @property
    def succeeded(self) -> bool:
        return bool(self.solutions)


class TopologySolverService(AbstractPuzzleSolverService):
    """Named topology boundary retained independently of runtime timing search."""

    def search(
        self,
        recipe: GraphRecipe,
        preset: DifficultyPreset,
        *,
        solution_cap: int = 8,
    ) -> TopologySearchResult:
        if solution_cap < 1:
            return TopologySearchResult((), ("topology_solution_cap_reached",), True)
        try:
            metadata = self.solve_metadata(recipe, preset)
        except AbstractPuzzleSolverError as error:
            reasons = error.details or (error.code,)
            return TopologySearchResult(
                (),
                tuple(reasons),
                error.code in {"abstract_state_limit", "abstract_path_step_limit"}
                or any("limit" in reason for reason in reasons),
            )
        return TopologySearchResult((metadata,), metadata.failure_reasons, False)


TopologySolverError = AbstractPuzzleSolverError
