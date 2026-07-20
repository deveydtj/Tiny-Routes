"""Typed evidence produced by exact structural strategy search."""

from __future__ import annotations

from dataclasses import dataclass

from .puzzle_state import PuzzleState, PuzzleTerminalOutcome


def _non_negative(value: int | float, field_name: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True, order=True)
class StrategyCost:
    """Lexicographic gameplay cost used by the structural Dijkstra search."""

    accepted_taps: int = 0
    travel_time_seconds: float = 0.0
    route_distance: float = 0.0

    def __post_init__(self) -> None:
        _non_negative(self.accepted_taps, "accepted_taps")
        _non_negative(self.travel_time_seconds, "travel_time_seconds")
        _non_negative(self.route_distance, "route_distance")
        object.__setattr__(self, "travel_time_seconds", round(float(self.travel_time_seconds), 9))
        object.__setattr__(self, "route_distance", round(float(self.route_distance), 9))

    def adding(
        self,
        *,
        accepted_taps: int = 0,
        travel_time_seconds: float = 0.0,
        route_distance: float = 0.0,
    ) -> "StrategyCost":
        return StrategyCost(
            self.accepted_taps + accepted_taps,
            self.travel_time_seconds + travel_time_seconds,
            self.route_distance + route_distance,
        )


@dataclass(frozen=True)
class StrategyAction:
    """One selected road and the structural movement caused by that choice."""

    node_id: str
    selected_edge_id: str
    tap_count: int
    traversed_edge_ids: tuple[str, ...]
    visited_node_ids: tuple[str, ...]
    completed_objective_ids: tuple[str, ...] = ()

    @property
    def signature(self) -> tuple[object, ...]:
        return (
            self.node_id,
            self.selected_edge_id,
            self.tap_count,
            self.traversed_edge_ids,
            self.completed_objective_ids,
        )


@dataclass(frozen=True)
class StrategyTrace:
    """A complete successful or failed structural action trace."""

    actions: tuple[StrategyAction, ...]
    cost: StrategyCost
    final_state: PuzzleState
    outcome_code: str

    @property
    def succeeded(self) -> bool:
        return self.final_state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS

    @property
    def signature(self) -> tuple[tuple[object, ...], ...]:
        # AG-065 will replace this exact action signature with gameplay
        # equivalence classes. Keeping it explicit here prevents accidental
        # route-count inflation from object identity or queue ordering.
        return tuple(action.signature for action in self.actions)


@dataclass(frozen=True)
class StrategySearchResult:
    """Deterministic proof evidence from one complete bounded search."""

    optimal_cost: StrategyCost | None
    canonical_optimal_strategy: StrategyTrace | None
    equal_cost_optimal_strategies: tuple[StrategyTrace, ...]
    near_optimal_strategies: tuple[StrategyTrace, ...]
    longer_successful_strategies: tuple[StrategyTrace, ...]
    failure_outcomes: tuple[StrategyTrace, ...]
    explored_state_count: int
    exhaustive: bool
    limit_reasons: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.canonical_optimal_strategy is not None

    @property
    def all_successful_strategies(self) -> tuple[StrategyTrace, ...]:
        return (
            *self.equal_cost_optimal_strategies,
            *self.near_optimal_strategies,
            *self.longer_successful_strategies,
        )
