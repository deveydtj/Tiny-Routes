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


@dataclass(frozen=True, order=True)
class StrategyStateTransition:
    """One player-observable route-state change caused by an action."""

    objective_index_before: int
    objective_index_after: int
    completed_objective_ids: tuple[str, ...] = ()
    opened_edge_ids: tuple[str, ...] = ()
    closed_edge_ids: tuple[str, ...] = ()
    consumed_edge_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("objective_index_before", "objective_index_after"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.objective_index_after < self.objective_index_before:
            raise ValueError("objective progress cannot move backwards")
        for field_name in (
            "completed_objective_ids",
            "opened_edge_ids",
            "closed_edge_ids",
            "consumed_edge_ids",
        ):
            raw_values = tuple(getattr(self, field_name))
            if any(
                not isinstance(value, str) or not value.strip()
                for value in raw_values
            ):
                raise ValueError(f"{field_name} cannot contain empty identifiers")
            values = tuple(value.strip() for value in raw_values)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain unique identifiers")
            if field_name != "completed_objective_ids":
                values = tuple(sorted(values))
            object.__setattr__(self, field_name, values)

    @property
    def changes_state(self) -> bool:
        return bool(
            self.objective_index_after != self.objective_index_before
            or self.completed_objective_ids
            or self.opened_edge_ids
            or self.closed_edge_ids
            or self.consumed_edge_ids
        )

    @property
    def signature(self) -> tuple[object, ...]:
        return (
            self.objective_index_before,
            self.objective_index_after,
            self.completed_objective_ids,
            self.opened_edge_ids,
            self.closed_edge_ids,
            self.consumed_edge_ids,
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
    meaningful_decision: bool | None = None
    state_transition: StrategyStateTransition | None = None

    @property
    def signature(self) -> tuple[object, ...]:
        """Exact structural signature used internally by bounded search."""

        return (
            self.node_id,
            self.selected_edge_id,
            self.tap_count,
            self.traversed_edge_ids,
            self.visited_node_ids,
            self.completed_objective_ids,
            self.meaningful_decision,
            self.state_transition.signature if self.state_transition is not None else None,
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
        """Exact trace signature; gameplay equivalence is intentionally separate."""

        return tuple(action.signature for action in self.actions)

    @property
    def exact_signature(self) -> tuple[tuple[object, ...], ...]:
        return self.signature


@dataclass(frozen=True, order=True)
class StrategyEquivalenceKey:
    """Canonical gameplay identity for one complete action trace."""

    outcome: str
    meaningful_decisions: tuple[tuple[int, str, str], ...]
    objective_sequence: tuple[str, ...]
    state_transitions: tuple[tuple[object, ...], ...]
    success_cost: StrategyCost | None


@dataclass(frozen=True)
class StrategyEquivalenceClass:
    """A canonical trace plus all exact traces normalized into its class."""

    key: StrategyEquivalenceKey
    canonical_trace: StrategyTrace
    member_traces: tuple[StrategyTrace, ...]

    def __post_init__(self) -> None:
        members = tuple(self.member_traces)
        if not members:
            raise ValueError("a strategy equivalence class requires at least one trace")
        if self.canonical_trace not in members:
            raise ValueError("canonical_trace must be one of member_traces")
        object.__setattr__(self, "member_traces", members)

    @property
    def member_count(self) -> int:
        return len(self.member_traces)


@dataclass(frozen=True)
class OptimalStrategyRequirements:
    """Concrete target evidence that an optimal trace must realize."""

    required_decision_node_ids: tuple[str, ...] = ()
    required_selected_edge_ids: tuple[str, ...] = ()
    required_objective_ids: tuple[str, ...] = ()
    required_opened_edge_ids: tuple[str, ...] = ()
    required_closed_edge_ids: tuple[str, ...] = ()
    required_consumed_edge_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "required_decision_node_ids",
            "required_selected_edge_ids",
            "required_objective_ids",
            "required_opened_edge_ids",
            "required_closed_edge_ids",
            "required_consumed_edge_ids",
        ):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field_name} cannot contain empty identifiers")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain unique identifiers")
            object.__setattr__(self, field_name, values)


@dataclass(frozen=True)
class UniqueOptimalProof:
    """Deterministic acceptance or rejection evidence for optimal uniqueness."""

    accepted: bool
    exhaustive: bool
    is_unique: bool
    optimal_cost: StrategyCost | None
    optimal_strategy_class: StrategyEquivalenceClass | None
    equal_cost_strategy_classes: tuple[StrategyEquivalenceClass, ...]
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        classes = tuple(self.equal_cost_strategy_classes)
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.accepted and reasons:
            raise ValueError("accepted proof cannot contain rejection reasons")
        if not self.accepted and not reasons:
            raise ValueError("rejected proof must contain a rejection reason")
        if self.is_unique != (len(classes) == 1):
            raise ValueError("is_unique must match the equal-cost class count")
        if self.optimal_strategy_class is not None and self.optimal_strategy_class not in classes:
            raise ValueError("optimal_strategy_class must belong to equal-cost classes")
        object.__setattr__(self, "equal_cost_strategy_classes", classes)
        object.__setattr__(self, "rejection_reasons", reasons)


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
