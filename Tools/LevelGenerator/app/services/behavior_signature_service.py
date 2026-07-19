"""ID-independent strategic behavior signatures for recipe graphs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge
from .graph_isomorphism_service import GraphIsomorphismService


@dataclass(frozen=True, order=True)
class StrategyBehaviorClass:
    """One equivalent decision strategy and its observable outcome."""

    outcome: str
    decisions: tuple[tuple[Any, ...], ...]
    cost_vector: tuple[int, int, int]
    recovered: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "decisions": [list(decision) for decision in self.decisions],
            "costVector": list(self.cost_vector),
            "recovered": self.recovered,
        }


@dataclass(frozen=True)
class BehaviorSignature:
    """Canonical strategy, outcome, recovery, and optimum evidence."""

    strategy_classes: tuple[StrategyBehaviorClass, ...]
    failure_outcomes: tuple[tuple[str, int], ...]
    recovery_outcomes: tuple[tuple[str, int], ...]
    optimal_cost_vector: tuple[int, int, int] | None
    optimal_strategy_classes: tuple[tuple[tuple[Any, ...], ...], ...]
    digest: str

    @property
    def has_unique_optimal_strategy(self) -> bool:
        return len(self.optimal_strategy_classes) == 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategyClasses": [strategy.to_dict() for strategy in self.strategy_classes],
            "failureOutcomes": [list(item) for item in self.failure_outcomes],
            "recoveryOutcomes": [list(item) for item in self.recovery_outcomes],
            "optimalCostVector": (
                list(self.optimal_cost_vector)
                if self.optimal_cost_vector is not None
                else None
            ),
            "optimalStrategyClasses": [
                [list(decision) for decision in strategy]
                for strategy in self.optimal_strategy_classes
            ],
            "digest": self.digest,
        }


@dataclass(frozen=True)
class _ExplorationState:
    node_id: str
    collected_objective: bool
    switch_indices: tuple[int, ...]
    usage_counts: tuple[int, ...]
    path: tuple[str, ...]
    decisions: tuple[tuple[str, int, int, int, int], ...]
    tap_count: int
    repeated_node: bool
    seen_states: frozenset[tuple[Any, ...]]


class BehaviorSignatureService:
    """Compare actual route behavior, independently of IDs and labels."""

    def __init__(self, graph_service: GraphIsomorphismService | None = None) -> None:
        self.graph_service = graph_service or GraphIsomorphismService()

    def signature_for(self, recipe: GraphRecipe) -> BehaviorSignature:
        classes = self._strategy_classes(recipe)
        successes = tuple(item for item in classes if item.outcome == "success")
        optimal_cost = min((item.cost_vector for item in successes), default=None)

        if optimal_cost is not None:
            classes = tuple(
                replace(
                    item,
                    recovered=(
                        item.recovered
                        or (item.outcome == "success" and item.cost_vector != optimal_cost)
                    ),
                )
                for item in classes
            )
            successes = tuple(item for item in classes if item.outcome == "success")

        failures = Counter(item.outcome for item in classes if item.outcome != "success")
        recoveries = Counter(item.outcome for item in classes if item.recovered)
        optimal_strategies = tuple(
            sorted(
                {
                    item.decisions
                    for item in successes
                    if item.cost_vector == optimal_cost
                }
            )
        )
        payload = {
            "strategies": [item.to_dict() for item in classes],
            "failures": sorted(failures.items()),
            "recoveries": sorted(recoveries.items()),
            "optimalCost": optimal_cost,
            "optimalStrategies": optimal_strategies,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return BehaviorSignature(
            strategy_classes=classes,
            failure_outcomes=tuple(sorted(failures.items())),
            recovery_outcomes=tuple(sorted(recoveries.items())),
            optimal_cost_vector=optimal_cost,
            optimal_strategy_classes=optimal_strategies,
            digest=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        )

    def are_isomorphic(self, first: GraphRecipe, second: GraphRecipe) -> bool:
        return self.signature_for(first).digest == self.signature_for(second).digest

    def is_isomorphic(self, first: GraphRecipe, second: GraphRecipe) -> bool:
        """Singular-name compatibility alias."""

        return self.are_isomorphic(first, second)

    def _strategy_classes(self, recipe: GraphRecipe) -> tuple[StrategyBehaviorClass, ...]:
        node_by_id = {node.id: node for node in recipe.nodes}
        outgoing = self._outgoing(recipe)
        switch_ids = tuple(
            node.id
            for node in recipe.nodes
            if len(outgoing.get(node.id, ())) > 1
        )
        switch_position = {node_id: index for index, node_id in enumerate(switch_ids)}
        limited_edges = tuple(
            edge_index
            for edge_index, edge in enumerate(recipe.edges)
            if edge.usage_limit is not None
        )
        limited_position = {edge_index: index for index, edge_index in enumerate(limited_edges)}
        edge_index_by_identity = {id(edge): index for index, edge in enumerate(recipe.edges)}
        start = recipe.required_path[0] if recipe.required_path else "start"
        collected = start == recipe.package_node_id
        initial_indices = self._normalize_switch_indices(
            tuple(0 for _ in switch_ids),
            switch_ids,
            outgoing,
            collected,
        )
        initial_key = (start, collected, initial_indices, tuple(0 for _ in limited_edges))
        stack = [
            _ExplorationState(
                node_id=start,
                collected_objective=collected,
                switch_indices=initial_indices,
                usage_counts=tuple(0 for _ in limited_edges),
                path=(start,),
                decisions=(),
                tap_count=0,
                repeated_node=False,
                seen_states=frozenset({initial_key}),
            )
        ]
        maximum_steps = max(len(recipe.required_path), len(recipe.nodes) + 2)
        completed: set[StrategyBehaviorClass] = set()

        while stack:
            state = stack.pop()
            if state.node_id == recipe.destination_node_id:
                outcome = (
                    "success"
                    if state.collected_objective
                    else "destination_before_objective"
                )
                completed.add(self._class_for(recipe, state, outcome))
                continue
            if len(state.path) - 1 >= maximum_steps:
                completed.add(self._class_for(recipe, state, "step_limit"))
                continue

            usable = self._usable_outgoing(
                outgoing.get(state.node_id, ()),
                state.collected_objective,
                state.usage_counts,
                limited_position,
                edge_index_by_identity,
            )
            if not usable:
                role = node_by_id.get(state.node_id)
                role_name = role.role.strip().lower() if role is not None else "unknown"
                completed.add(self._class_for(recipe, state, f"dead_end:{role_name}"))
                continue

            switch_tuple_index = switch_position.get(state.node_id)
            authored = outgoing.get(state.node_id, ())
            active_usable_index = 0
            if switch_tuple_index is not None:
                active_authored_index = state.switch_indices[switch_tuple_index]
                active_edge = authored[active_authored_index][1]
                active_usable_index = next(
                    (
                        index
                        for index, (_, candidate) in enumerate(usable)
                        if candidate is active_edge
                    ),
                    0,
                )

            for chosen_usable_index, (authored_index, edge) in enumerate(usable):
                taps = (
                    (chosen_usable_index - active_usable_index) % len(usable)
                    if len(usable) > 1
                    else 0
                )
                switch_indices = state.switch_indices
                decisions = state.decisions
                if switch_tuple_index is not None:
                    switch_indices = (
                        switch_indices[:switch_tuple_index]
                        + (authored_index,)
                        + switch_indices[switch_tuple_index + 1 :]
                    )
                    decisions = (
                        *decisions,
                        (
                            state.node_id,
                            int(state.collected_objective),
                            len(usable),
                            chosen_usable_index,
                            taps,
                        ),
                    )

                usage_counts = state.usage_counts
                edge_index = edge_index_by_identity[id(edge)]
                if edge_index in limited_position:
                    usage_index = limited_position[edge_index]
                    usage_counts = (
                        usage_counts[:usage_index]
                        + (usage_counts[usage_index] + 1,)
                        + usage_counts[usage_index + 1 :]
                    )

                next_collected = (
                    state.collected_objective
                    or edge.to_node_id == recipe.package_node_id
                )
                if next_collected != state.collected_objective:
                    switch_indices = self._normalize_switch_indices(
                        switch_indices,
                        switch_ids,
                        outgoing,
                        next_collected,
                    )
                next_key = (
                    edge.to_node_id,
                    next_collected,
                    switch_indices,
                    usage_counts,
                )
                next_state = _ExplorationState(
                    node_id=edge.to_node_id,
                    collected_objective=next_collected,
                    switch_indices=switch_indices,
                    usage_counts=usage_counts,
                    path=(*state.path, edge.to_node_id),
                    decisions=decisions,
                    tap_count=state.tap_count + taps,
                    repeated_node=(
                        state.repeated_node or edge.to_node_id in state.path
                    ),
                    seen_states=state.seen_states | {next_key},
                )
                if next_key in state.seen_states:
                    completed.add(self._class_for(recipe, next_state, "loop"))
                else:
                    stack.append(next_state)

        return tuple(sorted(completed))

    def _class_for(
        self,
        recipe: GraphRecipe,
        state: _ExplorationState,
        outcome: str,
    ) -> StrategyBehaviorClass:
        node_by_id = {node.id: node for node in recipe.nodes}
        token_by_node_id: dict[str, int] = {}
        normalized: list[tuple[Any, ...]] = []
        for node_id, phase, degree, choice, taps in state.decisions:
            if node_id not in token_by_node_id:
                token_by_node_id[node_id] = len(token_by_node_id)
            node = node_by_id[node_id]
            descriptor = self.graph_service.node_descriptor(recipe, node)
            normalized.append(
                (
                    token_by_node_id[node_id],
                    descriptor,
                    phase,
                    degree,
                    choice,
                    taps,
                )
            )
        return StrategyBehaviorClass(
            outcome=outcome,
            decisions=tuple(normalized),
            cost_vector=(state.tap_count, len(state.path) - 1, int(state.repeated_node)),
            recovered=state.repeated_node,
        )

    @staticmethod
    def _outgoing(
        recipe: GraphRecipe,
    ) -> dict[str, tuple[tuple[int, GraphRecipeEdge], ...]]:
        grouped: dict[str, list[tuple[int, GraphRecipeEdge]]] = {}
        for edge_index, edge in enumerate(recipe.edges):
            grouped.setdefault(edge.from_node_id, []).append((edge_index, edge))
        return {node_id: tuple(edges) for node_id, edges in grouped.items()}

    @staticmethod
    def _available(edge: GraphRecipeEdge, collected: bool) -> bool:
        phase = "afterPackage" if collected else "beforePackage"
        return edge.availability in {"always", phase}

    def _usable_outgoing(
        self,
        outgoing: tuple[tuple[int, GraphRecipeEdge], ...],
        collected: bool,
        usage_counts: tuple[int, ...],
        limited_position: dict[int, int],
        edge_index_by_identity: dict[int, int],
    ) -> tuple[tuple[int, GraphRecipeEdge], ...]:
        usable: list[tuple[int, GraphRecipeEdge]] = []
        for authored_index, (_, edge) in enumerate(outgoing):
            if not self._available(edge, collected):
                continue
            edge_index = edge_index_by_identity[id(edge)]
            if edge.usage_limit is not None:
                usage_index = limited_position[edge_index]
                if usage_counts[usage_index] >= edge.usage_limit:
                    continue
            usable.append((authored_index, edge))
        return tuple(usable)

    def _normalize_switch_indices(
        self,
        indices: tuple[int, ...],
        switch_ids: tuple[str, ...],
        outgoing: dict[str, tuple[tuple[int, GraphRecipeEdge], ...]],
        collected: bool,
    ) -> tuple[int, ...]:
        normalized: list[int] = []
        for node_id, requested_index in zip(switch_ids, indices):
            authored = outgoing[node_id]
            available_indices = tuple(
                index
                for index, (_, edge) in enumerate(authored)
                if self._available(edge, collected)
            )
            if not available_indices or requested_index in available_indices:
                normalized.append(requested_index)
            else:
                normalized.append(available_indices[0])
        return tuple(normalized)
