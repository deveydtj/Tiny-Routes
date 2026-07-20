"""Controlled, solver-proven transformations for composed V3 graphs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ..models.composition_state import (
    CompositionGraph,
    CompositionState,
)
from ..models.composition_transformation import (
    CompositionTransformation,
    CompositionTransformationKind,
    CompositionTransformationProof,
    CompositionTransformationResult,
)
from ..models.graph_recipe import GraphRecipeEdge, GraphRecipeNode
from ..models.motif_contract import MotifEdgeStateChangeKind
from .puzzle_composer_service import PuzzleCompositionError


class CompositionTransformationService:
    """Create true variants and accept them only after a fresh solver proof."""

    def __init__(
        self,
        solve: Callable[[CompositionState], CompositionTransformationProof],
    ) -> None:
        if not callable(solve):
            raise TypeError("solve must be callable")
        self._solve = solve

    def apply(
        self,
        state: CompositionState,
        transformation: CompositionTransformation,
    ) -> CompositionTransformationResult:
        if not isinstance(state, CompositionState):
            raise TypeError("state must be a CompositionState")
        if not isinstance(transformation, CompositionTransformation):
            raise TypeError("transformation must be a CompositionTransformation")
        issues = state.validate()
        if issues:
            raise PuzzleCompositionError(
                f"composition_transformation_state_invalid:{issues[0]}"
            )
        if not state.is_complete:
            raise PuzzleCompositionError("composition_transformation_state_incomplete")

        dispatch = {
            CompositionTransformationKind.EXCHANGE_PHASE_HUB_EXITS: (
                self._exchange_phase_hub_exits
            ),
            CompositionTransformationKind.MOVE_OBJECTIVE_TO_BRANCH: self._move_objective,
            CompositionTransformationKind.REVERSE_RING_PHASE_ORDER: self._reverse_ring_phase_order,
            CompositionTransformationKind.CONVERT_FATAL_BRANCH_TO_RECOVERY: (
                self._convert_fatal_to_recovery
            ),
            CompositionTransformationKind.CHANGE_SHORTCUT_UNLOCK_OBJECTIVE: (
                self._change_shortcut_objective
            ),
            CompositionTransformationKind.SWAP_BRANCH_COSTS: self._swap_branch_costs,
            CompositionTransformationKind.INSERT_READABILITY_SEGMENT: (
                self._insert_readability_segment
            ),
            CompositionTransformationKind.REMOVE_READABILITY_SEGMENT: (
                self._remove_readability_segment
            ),
        }
        candidate = dispatch[transformation.kind](state, transformation)
        if candidate.signature == state.signature:
            raise PuzzleCompositionError("composition_transformation_no_op")
        candidate_issues = candidate.validate()
        if candidate_issues:
            raise PuzzleCompositionError(
                f"composition_transformation_candidate_invalid:{candidate_issues[0]}"
            )

        proof = self._solve(candidate)
        if not isinstance(proof, CompositionTransformationProof):
            raise TypeError("solve must return CompositionTransformationProof")
        status = "accepted" if proof.accepted else "solver_rejected"
        return CompositionTransformationResult(
            transformation=transformation,
            status=status,
            original_state_signature=state.signature,
            candidate_state_signature=candidate.signature,
            solver_proof=proof,
            transformed_state=candidate if proof.accepted else None,
        )

    def apply_all(
        self,
        state: CompositionState,
        transformations: tuple[CompositionTransformation, ...],
    ) -> tuple[CompositionTransformationResult, ...]:
        """Apply requests independently in stable transformation-ID order."""

        requests = tuple(transformations)
        if any(not isinstance(item, CompositionTransformation) for item in requests):
            raise TypeError(
                "transformations must contain CompositionTransformation values"
            )
        ids = tuple(item.id for item in requests)
        if len(ids) != len(set(ids)):
            raise ValueError("transformations must be unique")
        return tuple(
            self.apply(state, item)
            for item in sorted(requests, key=lambda item: item.id)
        )

    def _exchange_phase_hub_exits(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        first_index, second_index = self._exact_edge_indices(state, request, 2)
        edges = list(state.current_graph.edges)
        first, second = edges[first_index], edges[second_index]
        if first.from_node_id != second.from_node_id:
            raise PuzzleCompositionError(
                "composition_transformation_hub_exits_require_same_source"
            )
        if {first.availability, second.availability} != {
            "beforePackage",
            "afterPackage",
        }:
            raise PuzzleCompositionError(
                "composition_transformation_hub_exits_require_distinct_phases"
            )
        edges[first_index] = replace(first, availability=second.availability)
        edges[second_index] = replace(second, availability=first.availability)
        return self._with_edges(state, tuple(edges))

    def _move_objective(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        if request.objective_id is None or len(request.node_ids) != 2:
            raise PuzzleCompositionError(
                "composition_transformation_objective_requires_id_and_entry_exit"
            )
        entry_id, exit_id = request.node_ids
        node_by_id = {node.id: node for node in state.current_graph.nodes}
        if entry_id not in node_by_id or exit_id not in node_by_id:
            raise PuzzleCompositionError(
                "composition_transformation_objective_branch_node_unknown"
            )
        if any(
            token in node_by_id[node_id].role.strip().lower()
            for node_id in (entry_id, exit_id)
            for token in ("failure", "dead_end")
        ):
            raise PuzzleCompositionError(
                "composition_transformation_objective_branch_incompatible"
            )
        if entry_id != exit_id and not self._is_reachable(
            state.current_graph,
            entry_id,
            exit_id,
        ):
            raise PuzzleCompositionError(
                "composition_transformation_objective_branch_disconnected"
            )
        boundaries = list(state.objective_phase_boundaries)
        matching = [
            index
            for index, boundary in enumerate(boundaries)
            if boundary.objective_id == request.objective_id
        ]
        if not matching:
            raise PuzzleCompositionError(
                f"composition_transformation_objective_unknown:{request.objective_id}"
            )
        target_pair = (entry_id, exit_id)
        if any(
            boundary.objective_id != request.objective_id
            and (boundary.entry_node_id, boundary.exit_node_id) == target_pair
            for boundary in boundaries
        ):
            raise PuzzleCompositionError(
                "composition_transformation_objective_branch_already_occupied"
            )
        index = matching[0]
        boundaries[index] = replace(
            boundaries[index],
            entry_node_id=entry_id,
            exit_node_id=exit_id,
        )
        return state.evolve(objective_phase_boundaries=tuple(boundaries))

    def _reverse_ring_phase_order(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        indices = self._at_least_edge_indices(state, request, 2)
        edges = list(state.current_graph.edges)
        availabilities = {edges[index].availability for index in indices}
        if not {"beforePackage", "afterPackage"}.issubset(availabilities):
            raise PuzzleCompositionError(
                "composition_transformation_ring_requires_both_phases"
            )
        if any(
            not self._is_reachable(
                state.current_graph,
                edges[index].to_node_id,
                edges[index].from_node_id,
            )
            for index in indices
        ):
            raise PuzzleCompositionError(
                "composition_transformation_ring_edge_not_in_cycle"
            )
        selected_pairs: set[tuple[str, str]] = set()
        for index in indices:
            edge = edges[index]
            selected_pairs.add((edge.from_node_id, edge.to_node_id))
            if edge.availability == "beforePackage":
                edges[index] = replace(edge, availability="afterPackage")
            elif edge.availability == "afterPackage":
                edges[index] = replace(edge, availability="beforePackage")
        effects = tuple(
            replace(effect, kind=self._reversed_effect_kind(effect.kind))
            if (effect.from_node_id, effect.to_node_id) in selected_pairs
            else effect
            for effect in state.assigned_state_effects
        )
        return state.evolve(
            current_graph=CompositionGraph(state.current_graph.nodes, tuple(edges)),
            assigned_state_effects=effects,
        )

    def _convert_fatal_to_recovery(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        if len(request.node_ids) != 2:
            raise PuzzleCompositionError(
                "composition_transformation_recovery_requires_source_target"
            )
        source_id, target_id = request.node_ids
        if source_id == target_id:
            raise PuzzleCompositionError(
                "composition_transformation_recovery_requires_distinct_nodes"
            )
        node_by_id = {node.id: node for node in state.current_graph.nodes}
        if source_id not in node_by_id or target_id not in node_by_id:
            raise PuzzleCompositionError(
                "composition_transformation_recovery_node_unknown"
            )
        source_role = node_by_id[source_id].role.strip().lower()
        if "failure" not in source_role and "dead_end" not in source_role:
            raise PuzzleCompositionError(
                "composition_transformation_recovery_source_not_fatal"
            )
        if any(
            edge.from_node_id == source_id and edge.to_node_id == target_id
            for edge in state.current_graph.edges
        ):
            raise PuzzleCompositionError(
                "composition_transformation_recovery_edge_exists"
            )
        graph = CompositionGraph(
            state.current_graph.nodes,
            (*state.current_graph.edges, GraphRecipeEdge(source_id, target_id)),
        )
        metrics = replace(
            state.partial_strategic_metrics,
            recovery_count=state.partial_strategic_metrics.recovery_count + 1,
        )
        return state.evolve(current_graph=graph, partial_strategic_metrics=metrics)

    def _change_shortcut_objective(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        if request.transition_id is None or request.replacement_id is None:
            raise PuzzleCompositionError(
                "composition_transformation_shortcut_requires_transition_ids"
            )
        matching = tuple(
            effect
            for effect in state.assigned_state_effects
            if effect.transition_id == request.transition_id
            and "shortcut" in effect.edge_role.lower()
        )
        if not matching:
            raise PuzzleCompositionError(
                f"composition_transformation_shortcut_transition_unknown:{request.transition_id}"
            )
        existing_keys = {
            (effect.transition_id, effect.edge_role)
            for effect in state.assigned_state_effects
            if effect not in matching
        }
        if any(
            (request.replacement_id, effect.edge_role) in existing_keys
            for effect in matching
        ):
            raise PuzzleCompositionError(
                "composition_transformation_shortcut_transition_duplicate"
            )
        effects = tuple(
            replace(effect, transition_id=request.replacement_id)
            if effect in matching
            else effect
            for effect in state.assigned_state_effects
        )
        return state.evolve(assigned_state_effects=effects)

    def _swap_branch_costs(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        first_index, second_index = self._exact_edge_indices(state, request, 2)
        edges = list(state.current_graph.edges)
        first, second = edges[first_index], edges[second_index]
        if first.from_node_id != second.from_node_id:
            raise PuzzleCompositionError(
                "composition_transformation_branch_costs_require_same_source"
            )
        edges[first_index] = replace(
            first,
            to_node_id=second.to_node_id,
            availability=second.availability,
            usage_limit=second.usage_limit,
        )
        edges[second_index] = replace(
            second,
            to_node_id=first.to_node_id,
            availability=first.availability,
            usage_limit=first.usage_limit,
        )
        return self._with_edges(state, tuple(edges))

    def _insert_readability_segment(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        (edge_index,) = self._exact_edge_indices(state, request, 1)
        if request.replacement_id is None:
            raise PuzzleCompositionError(
                "composition_transformation_readability_insert_requires_node_id"
            )
        if request.replacement_id in state.current_graph.node_ids:
            raise PuzzleCompositionError(
                "composition_transformation_readability_node_exists"
            )
        edges = list(state.current_graph.edges)
        original = edges[edge_index]
        edges[edge_index : edge_index + 1] = [
            GraphRecipeEdge(
                original.from_node_id,
                request.replacement_id,
                original.availability,
                original.usage_limit,
            ),
            GraphRecipeEdge(request.replacement_id, original.to_node_id),
        ]
        effects = tuple(
            replace(effect, to_node_id=request.replacement_id)
            if (effect.from_node_id, effect.to_node_id)
            == (original.from_node_id, original.to_node_id)
            else effect
            for effect in state.assigned_state_effects
        )
        footprint = replace(
            state.estimated_layout_footprint,
            width=state.estimated_layout_footprint.width + 1,
            height=max(1, state.estimated_layout_footprint.height),
        )
        return state.evolve(
            current_graph=CompositionGraph(
                (
                    *state.current_graph.nodes,
                    GraphRecipeNode(request.replacement_id, "readability"),
                ),
                tuple(edges),
            ),
            assigned_state_effects=effects,
            estimated_layout_footprint=footprint,
        )

    def _remove_readability_segment(
        self,
        state: CompositionState,
        request: CompositionTransformation,
    ) -> CompositionState:
        if len(request.node_ids) != 1:
            raise PuzzleCompositionError(
                "composition_transformation_readability_remove_requires_node"
            )
        node_id = request.node_ids[0]
        node_by_id = {node.id: node for node in state.current_graph.nodes}
        node = node_by_id.get(node_id)
        if node is None:
            raise PuzzleCompositionError(
                "composition_transformation_readability_node_unknown"
            )
        if node.role.strip().lower() not in {"readability", "spacer"}:
            raise PuzzleCompositionError(
                "composition_transformation_readability_role_invalid"
            )
        if any(
            node_id in (boundary.entry_node_id, boundary.exit_node_id)
            for boundary in state.objective_phase_boundaries
        ) or any(port.node_id == node_id for port in state.open_ports):
            raise PuzzleCompositionError(
                "composition_transformation_readability_node_in_use"
            )
        incoming = [
            edge for edge in state.current_graph.edges if edge.to_node_id == node_id
        ]
        outgoing = [
            edge for edge in state.current_graph.edges if edge.from_node_id == node_id
        ]
        if len(incoming) != 1 or len(outgoing) != 1:
            raise PuzzleCompositionError(
                "composition_transformation_readability_not_linear"
            )
        entering, leaving = incoming[0], outgoing[0]
        if leaving.availability != "always" or leaving.usage_limit is not None:
            raise PuzzleCompositionError(
                "composition_transformation_readability_remove_changes_semantics"
            )
        replacement_edge = GraphRecipeEdge(
            entering.from_node_id,
            leaving.to_node_id,
            entering.availability,
            entering.usage_limit,
        )
        rebuilt_edges: list[GraphRecipeEdge] = []
        for edge in state.current_graph.edges:
            if edge is entering:
                rebuilt_edges.append(replacement_edge)
            elif edge is not leaving:
                rebuilt_edges.append(edge)
        edges = tuple(rebuilt_edges)
        effects = tuple(
            replace(effect, to_node_id=leaving.to_node_id)
            if (effect.from_node_id, effect.to_node_id)
            == (entering.from_node_id, entering.to_node_id)
            else effect
            for effect in state.assigned_state_effects
        )
        footprint = replace(
            state.estimated_layout_footprint,
            width=max(0, state.estimated_layout_footprint.width - 1),
        )
        return state.evolve(
            current_graph=CompositionGraph(
                tuple(node for node in state.current_graph.nodes if node.id != node_id),
                edges,
            ),
            assigned_state_effects=effects,
            estimated_layout_footprint=footprint,
        )

    @staticmethod
    def _exact_edge_indices(
        state: CompositionState,
        request: CompositionTransformation,
        count: int,
    ) -> tuple[int, ...]:
        if len(request.edge_indices) != count:
            raise PuzzleCompositionError(
                f"composition_transformation_requires_{count}_edge_indices"
            )
        return CompositionTransformationService._checked_edge_indices(
            state, request.edge_indices
        )

    @staticmethod
    def _at_least_edge_indices(
        state: CompositionState,
        request: CompositionTransformation,
        count: int,
    ) -> tuple[int, ...]:
        if len(request.edge_indices) < count:
            raise PuzzleCompositionError(
                f"composition_transformation_requires_at_least_{count}_edge_indices"
            )
        return CompositionTransformationService._checked_edge_indices(
            state, request.edge_indices
        )

    @staticmethod
    def _checked_edge_indices(
        state: CompositionState,
        indices: tuple[int, ...],
    ) -> tuple[int, ...]:
        if any(index >= len(state.current_graph.edges) for index in indices):
            raise PuzzleCompositionError(
                "composition_transformation_edge_index_out_of_range"
            )
        return indices

    @staticmethod
    def _with_edges(
        state: CompositionState,
        edges: tuple[GraphRecipeEdge, ...],
    ) -> CompositionState:
        graph = CompositionGraph(state.current_graph.nodes, edges)
        edge_pairs = {(edge.from_node_id, edge.to_node_id) for edge in edges}
        if any(
            (effect.from_node_id, effect.to_node_id) not in edge_pairs
            for effect in state.assigned_state_effects
        ):
            raise PuzzleCompositionError(
                "composition_transformation_would_detach_state_effect"
            )
        return state.evolve(current_graph=graph)

    @staticmethod
    def _reversed_effect_kind(
        kind: MotifEdgeStateChangeKind,
    ) -> MotifEdgeStateChangeKind:
        if kind is MotifEdgeStateChangeKind.OPEN:
            return MotifEdgeStateChangeKind.CLOSE
        if kind is MotifEdgeStateChangeKind.CLOSE:
            return MotifEdgeStateChangeKind.OPEN
        return kind

    @staticmethod
    def _is_reachable(
        graph: CompositionGraph,
        start_node_id: str,
        target_node_id: str,
    ) -> bool:
        outgoing: dict[str, list[str]] = {}
        for edge in graph.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        pending = [start_node_id]
        visited: set[str] = set()
        while pending:
            node_id = pending.pop()
            if node_id == target_node_id:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            pending.extend(reversed(outgoing.get(node_id, ())))
        return False
