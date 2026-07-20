"""Immediate duplicate and repetition-cap gates for V3 composition pools."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

from ..models.composition_diversity import (
    CompositionDiversityConstraints,
    CompositionDuplicateAssessment,
    CompositionPoolEntry,
    CompositionPoolResult,
)
from ..models.composition_state import CompositionState
from ..models.puzzle_blueprint import PuzzleBlueprint


class CompositionDuplicateRejectionService:
    """Reject equivalent completed graphs before layout or runtime work.

    The default signature is an ID-independent canonicalization of topology,
    ordered objective placement, authored edge order/state, and route effects.
    The exact strategy solver can be injected as ``behavior_signature_for`` as
    it comes online, without changing the pool contract.
    """

    def __init__(
        self,
        constraints: CompositionDiversityConstraints | None = None,
        *,
        behavior_signature_for: Callable[[CompositionState], str] | None = None,
    ) -> None:
        self.constraints = constraints or CompositionDiversityConstraints()
        if behavior_signature_for is not None and not callable(behavior_signature_for):
            raise TypeError("behavior_signature_for must be callable")
        self._behavior_signature_for = behavior_signature_for or self.behavior_signature_for

    def assess(
        self,
        candidate_id: str,
        blueprint: PuzzleBlueprint,
        state: CompositionState,
        accepted_entries: Iterable[CompositionPoolEntry] = (),
    ) -> CompositionDuplicateAssessment:
        if not isinstance(blueprint, PuzzleBlueprint):
            raise TypeError("blueprint must be a PuzzleBlueprint")
        blueprint_issues = blueprint.validate()
        if blueprint_issues:
            raise ValueError(f"blueprint is invalid: {blueprint_issues[0]}")
        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        state_issues = state.validate()
        if state_issues:
            raise ValueError(f"composition state is invalid: {state_issues[0]}")
        if state.blueprint_id != blueprint.id:
            raise ValueError("composition state blueprint does not match blueprint")
        if not state.is_complete:
            raise ValueError("composition state must be complete")

        accepted = tuple(accepted_entries)
        if any(not isinstance(item, CompositionPoolEntry) for item in accepted):
            raise TypeError("accepted_entries must contain CompositionPoolEntry values")
        if len({item.candidate_id for item in accepted}) != len(accepted):
            raise ValueError("accepted_entries candidate IDs must be unique")

        behavior_signature = self._behavior_signature_for(state)
        if not isinstance(behavior_signature, str) or not behavior_signature.strip():
            raise ValueError("behavior signature must not be empty")
        entry = CompositionPoolEntry(
            candidate_id=candidate_id,
            blueprint_archetype=blueprint.archetype,
            motif_multiset=tuple(sorted(Counter(state.placed_motif_ids).items())),
            dependency_dag_signature=self.dependency_dag_signature_for(blueprint),
            behavior_signature=behavior_signature,
            state_signature=state.signature,
        )

        # Behavior equivalence is the strongest gate and is intentionally
        # checked first so duplicates never consume pool-cap capacity.
        duplicate = next(
            (
                item
                for item in accepted
                if item.behavior_signature == entry.behavior_signature
            ),
            None,
        )
        if duplicate is not None:
            return CompositionDuplicateAssessment(
                entry,
                (f"composition_duplicate_behavior_isomorphic:{duplicate.candidate_id}",),
            )

        reasons: list[str] = []
        if (
            self._count(
                accepted,
                "blueprint_archetype",
                entry.blueprint_archetype,
            )
            >= self.constraints.blueprint_archetype_cap
        ):
            reasons.append(
                f"composition_diversity_blueprint_archetype_cap:{entry.blueprint_archetype}"
            )
        if (
            self._count(accepted, "motif_multiset", entry.motif_multiset)
            >= self.constraints.motif_multiset_cap
        ):
            reasons.append("composition_diversity_motif_multiset_cap")
        if (
            self._count(
                accepted,
                "dependency_dag_signature",
                entry.dependency_dag_signature,
            )
            >= self.constraints.dependency_dag_cap
        ):
            reasons.append("composition_diversity_dependency_dag_cap")
        return CompositionDuplicateAssessment(entry, tuple(reasons))

    def filter_pool(
        self,
        candidates: Iterable[tuple[str, PuzzleBlueprint, CompositionState]],
    ) -> CompositionPoolResult:
        accepted: list[CompositionPoolEntry] = []
        assessments: list[CompositionDuplicateAssessment] = []
        seen_ids: set[str] = set()
        for candidate_id, blueprint, state in candidates:
            if candidate_id in seen_ids:
                raise ValueError(f"candidate ID is duplicated: {candidate_id}")
            seen_ids.add(candidate_id)
            assessment = self.assess(candidate_id, blueprint, state, accepted)
            assessments.append(assessment)
            if assessment.is_accepted:
                accepted.append(assessment.entry)
        return CompositionPoolResult(tuple(accepted), tuple(assessments))

    def behavior_signature_for(self, state: CompositionState) -> str:
        """Return an ID- and presentation-independent composed-graph signature."""

        graph = state.current_graph
        node_by_id = {node.id: node for node in graph.nodes}
        outgoing: dict[str, list[tuple[int, Any]]] = {}
        authored_counts: dict[str, int] = {}
        for edge in graph.edges:
            authored_index = authored_counts.get(edge.from_node_id, 0)
            authored_counts[edge.from_node_id] = authored_index + 1
            outgoing.setdefault(edge.from_node_id, []).append((authored_index, edge))

        start_ids = tuple(
            node.id for node in graph.nodes if node.role.strip().lower() == "start"
        )
        seeds = start_ids or tuple(node_by_id)
        candidates: list[str] = []
        for seed in seeds:
            prefix = self._traverse(seed, outgoing, frozenset())
            for order in self._disconnected_orders(tuple(node_by_id), outgoing, prefix):
                candidates.append(self._serialize_state(state, order, outgoing))
        canonical = min(candidates, default=self._serialize_state(state, (), outgoing))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def dependency_dag_signature_for(blueprint: PuzzleBlueprint) -> str:
        graph = blueprint.decision_graph
        ordered_decisions = tuple(
            sorted(graph.decisions, key=lambda item: item.sequence_index)
        )
        decision_index = {
            decision.id: index
            for index, decision in enumerate(ordered_decisions)
        }
        objective_phase = dict(graph.objective_phase_indices)
        switch_role_tokens: dict[str, int] = {}
        for decision in ordered_decisions:
            switch_role_tokens.setdefault(
                decision.switch_role, len(switch_role_tokens)
            )
        outgoing_role_index = {
            decision.id: {
                role: index for index, role in enumerate(decision.outgoing_edge_roles)
            }
            for decision in ordered_decisions
        }
        payload = {
            "decisions": [
                (
                    decision.sequence_index,
                    decision.phase_index,
                    switch_role_tokens[decision.switch_role],
                    len(decision.outgoing_edge_roles),
                    outgoing_role_index[decision.id].get(
                        decision.required_outgoing_edge_role, -1
                    ),
                )
                for decision in ordered_decisions
            ],
            "dependencies": sorted(
                (
                    (
                        ("objective", objective_phase.get(dependency.source_id, -1))
                        if dependency.source_id not in decision_index
                        else ("decision", decision_index[dependency.source_id])
                    ),
                    decision_index.get(dependency.target_id, -1),
                    dependency.kind.value,
                    outgoing_role_index.get(dependency.source_id, {}).get(
                        dependency.required_source_outgoing_edge_role, -1
                    ),
                )
                for dependency in graph.dependencies
            ),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _count(
        entries: tuple[CompositionPoolEntry, ...],
        field_name: str,
        value: object,
    ) -> int:
        return sum(getattr(entry, field_name) == value for entry in entries)

    @staticmethod
    def _traverse(
        seed: str,
        outgoing: dict[str, list[tuple[int, Any]]],
        visited_prefix: frozenset[str],
    ) -> tuple[str, ...]:
        visited = set(visited_prefix)
        order: list[str] = []
        pending = [seed]
        while pending:
            node_id = pending.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            order.append(node_id)
            pending.extend(edge.to_node_id for _, edge in outgoing.get(node_id, ()))
        return tuple(order)

    def _disconnected_orders(
        self,
        node_ids: tuple[str, ...],
        outgoing: dict[str, list[tuple[int, Any]]],
        prefix: tuple[str, ...],
    ) -> tuple[tuple[str, ...], ...]:
        remaining = set(node_ids).difference(prefix)
        if not remaining:
            return (prefix,)
        results: list[tuple[str, ...]] = []
        for seed in remaining:
            block = self._traverse(seed, outgoing, frozenset(prefix))
            results.extend(
                self._disconnected_orders(node_ids, outgoing, (*prefix, *block))
            )
        return tuple(results)

    @staticmethod
    def _serialize_state(
        state: CompositionState,
        order: tuple[str, ...],
        outgoing: dict[str, list[tuple[int, Any]]],
    ) -> str:
        index = {node_id: position for position, node_id in enumerate(order)}
        node_by_id = {node.id: node for node in state.current_graph.nodes}
        phase_roles: dict[str, list[tuple[int, str]]] = {}
        for boundary in state.objective_phase_boundaries:
            if boundary.entry_node_id is not None:
                phase_roles.setdefault(boundary.entry_node_id, []).append(
                    (boundary.phase_index, "entry")
                )
            if boundary.exit_node_id is not None:
                phase_roles.setdefault(boundary.exit_node_id, []).append(
                    (boundary.phase_index, "exit")
                )
        effects_by_pair: dict[tuple[str, str], list[Any]] = {}
        for effect in state.assigned_state_effects:
            effects_by_pair.setdefault(
                (effect.from_node_id, effect.to_node_id), []
            ).append(effect)
        transition_tokens: dict[str, int] = {}
        edges: list[tuple[Any, ...]] = []
        for from_node_id in order:
            for authored_index, edge in outgoing.get(from_node_id, ()):
                effects: list[tuple[int, str]] = []
                for effect in sorted(
                    effects_by_pair.get((edge.from_node_id, edge.to_node_id), ()),
                    key=lambda item: (item.kind.value, item.transition_id),
                ):
                    token = transition_tokens.setdefault(
                        effect.transition_id, len(transition_tokens)
                    )
                    effects.append((token, effect.kind.value))
                edges.append(
                    (
                        index[edge.from_node_id],
                        index[edge.to_node_id],
                        authored_index,
                        edge.availability,
                        edge.usage_limit,
                        effects,
                    )
                )
        payload = {
            "nodes": [
                (
                    node_by_id[node_id].role.strip().lower(),
                    sorted(phase_roles.get(node_id, ())),
                )
                for node_id in order
            ],
            "edges": edges,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
