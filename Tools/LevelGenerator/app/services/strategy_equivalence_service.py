"""Gameplay-equivalence classification for exact structural traces."""

from __future__ import annotations

from collections.abc import Iterable

from tiny_routes_core.graph import GraphIndex
from tiny_routes_core.models import LevelDocument

from ..models.strategy_search import (
    StrategyAction,
    StrategyEquivalenceClass,
    StrategyEquivalenceKey,
    StrategyTrace,
)


class StrategyEquivalenceService:
    """Collapse trace noise without merging distinct gameplay choices."""

    def classify(
        self,
        traces: Iterable[StrategyTrace],
        *,
        level: LevelDocument | None = None,
    ) -> tuple[StrategyEquivalenceClass, ...]:
        grouped: dict[StrategyEquivalenceKey, list[StrategyTrace]] = {}
        for trace in traces:
            key = self.key_for(trace, level=level)
            grouped.setdefault(key, []).append(trace)

        classes: list[StrategyEquivalenceClass] = []
        for key, members in grouped.items():
            ordered = tuple(
                sorted(
                    members,
                    key=lambda trace: (
                        trace.cost,
                        trace.exact_signature,
                        trace.outcome_code,
                    ),
                )
            )
            classes.append(StrategyEquivalenceClass(key, ordered[0], ordered))
        return tuple(
            sorted(
                classes,
                key=lambda item: (
                    item.canonical_trace.cost,
                    item.key,
                    item.canonical_trace.exact_signature,
                ),
            )
        )

    def are_equivalent(
        self,
        first: StrategyTrace,
        second: StrategyTrace,
        *,
        level: LevelDocument | None = None,
    ) -> bool:
        return self.key_for(first, level=level) == self.key_for(second, level=level)

    def key_for(
        self,
        trace: StrategyTrace,
        *,
        level: LevelDocument | None = None,
    ) -> StrategyEquivalenceKey:
        meaningful = tuple(
            (
                self._objective_index_before(action),
                action.node_id,
                action.selected_edge_id,
            )
            for action in trace.actions
            if self._is_meaningful(action, level)
        )
        objectives = tuple(
            objective_id
            for action in trace.actions
            for objective_id in action.completed_objective_ids
        )
        transitions = tuple(
            action.state_transition.signature
            for action in trace.actions
            if action.state_transition is not None and action.state_transition.changes_state
        )
        return StrategyEquivalenceKey(
            outcome=trace.outcome_code,
            meaningful_decisions=meaningful,
            objective_sequence=objectives,
            state_transitions=transitions,
            success_cost=trace.cost if trace.succeeded else None,
        )

    @staticmethod
    def _objective_index_before(action: StrategyAction) -> int:
        transition = action.state_transition
        return transition.objective_index_before if transition is not None else 0

    @staticmethod
    def _is_meaningful(
        action: StrategyAction,
        level: LevelDocument | None,
    ) -> bool:
        if action.meaningful_decision is not None:
            return action.meaningful_decision
        if level is None:
            return True
        index = GraphIndex.build(level.graph)
        return len(index.outgoing_by_node_id.get(action.node_id, ())) >= 2
