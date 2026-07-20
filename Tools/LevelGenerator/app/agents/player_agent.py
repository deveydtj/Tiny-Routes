"""Shared player-visible input contract for policy agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models.puzzle_state import PuzzleState
from ..services.puzzle_state_transition_service import StructuralDecision


@dataclass(frozen=True)
class PlayerObservation:
    """The canonical visible state and legal actions presented to every agent."""

    state: PuzzleState
    available_actions: tuple[StructuralDecision, ...]

    def __post_init__(self) -> None:
        actions = tuple(self.available_actions)
        if self.state.is_terminal and actions:
            raise ValueError("a terminal observation cannot contain available actions")
        if self.state.current_node_id is None and actions:
            raise ValueError("actions require a current node")
        if any(action.node_id != self.state.current_node_id for action in actions):
            raise ValueError("all actions must originate at the visible current node")
        edge_ids = tuple(action.selected_edge_id for action in actions)
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("available actions must select unique edges")
        visible_edges = set(self.state.available_edge_ids)
        if any(edge_id not in visible_edges for edge_id in edge_ids):
            raise ValueError("available actions must use visible available edges")
        object.__setattr__(self, "available_actions", actions)


class PlayerAgent(Protocol):
    """Common policy interface used by deterministic evaluation simulations."""

    def choose_action(
        self,
        observation: PlayerObservation,
    ) -> StructuralDecision | None: ...
