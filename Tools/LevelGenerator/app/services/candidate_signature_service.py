from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from ..models.candidate_signature import CandidateSignature
from ..models.decision_dependency_graph import DecisionDependencyKind


class CandidateSignatureService:
    def signature_for(
        self,
        generated_level,
        *,
        blueprint=None,
        strategy_result=None,
        static_policy_result=None,
        policy_evaluation=None,
        puzzle_analysis=None,
    ) -> CandidateSignature:
        level = generated_level.level_document
        solution = generated_level.solution
        blueprint = blueprint or getattr(generated_level, "puzzle_blueprint", None)
        strategy_result = strategy_result or getattr(
            generated_level, "strategy_search_result", None
        )
        static_policy_result = static_policy_result or getattr(
            generated_level, "static_policy_search_result", None
        )
        policy_evaluation = policy_evaluation or getattr(
            generated_level, "policy_evaluation_report", None
        )
        puzzle_analysis = puzzle_analysis or getattr(
            generated_level, "puzzle_analysis", None
        )
        normalized_edges = self._normalized_edges(level)
        normalized_positions = self._normalized_positions(level)
        tap_node_ids = [action.tapNodeID for action in sorted(solution.actions, key=lambda action: action.timeSeconds)]
        edges_by_id = {edge.id: edge for edge in level.graph.edges}
        outgoing_edge_counts = [
            sum(
                1
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edges_by_id and edges_by_id[edge_id].fromNodeID == node.id
            )
            for node in level.graph.nodes
        ]
        max_outgoing_edge_count = max(outgoing_edge_counts, default=0)
        central_switch_revisit_count = max(
            (tap_node_ids.count(node.id) for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1),
            default=0,
        )
        dead_end_count = sum(
            1
            for node in level.graph.nodes
            if not node.outgoingEdgeIDs and node.id != level.destinationNodeID
        )
        topology_payload = {
            "start": level.startNodeID,
            "package": level.packageNodeID,
            "destination": level.destinationNodeID,
            "edges": normalized_edges,
            "maxOutgoingEdgeCount": max_outgoing_edge_count,
            "hasFourWaySwitch": max_outgoing_edge_count == 4,
        }
        layout_payload = {
            "positions": normalized_positions,
        }
        solution_payload = {
            "tapNodeIDs": tap_node_ids,
            "centralSwitchRevisitCount": central_switch_revisit_count,
        }
        profile = getattr(generated_level, "decision_profile", None)
        switch_degree_sequence = tuple(sorted((count for count in outgoing_edge_counts if count > 1), reverse=True))
        failure_distribution = self._failure_distribution(profile)
        silhouette, mirrored_silhouette = self._layout_silhouettes(normalized_positions)
        action_times = tuple(float(action.timeSeconds) for action in sorted(solution.actions, key=lambda action: action.timeSeconds))
        objectives = tuple(
            sorted(level.effective_objectives, key=lambda item: item.sequenceIndex)
        )
        optimal_trace = (
            getattr(strategy_result, "canonical_optimal_strategy", None)
            if strategy_result is not None
            else None
        )
        return CandidateSignature(
            level_id=generated_level.level_id,
            template_name=generated_level.template_name,
            difficulty=generated_level.difficulty,
            node_count=len(level.graph.nodes),
            edge_count=len(level.graph.edges),
            switch_count=sum(1 for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1),
            required_tap_count=len(solution.actions),
            dead_end_count=dead_end_count,
            topology_hash=self._hash_payload(topology_payload),
            layout_hash=self._hash_payload(layout_payload),
            solution_hash=self._hash_payload(solution_payload),
            normalized_positions=normalized_positions,
            max_outgoing_edge_count=max_outgoing_edge_count,
            has_four_way_switch=max_outgoing_edge_count == 4,
            central_switch_revisit_count=central_switch_revisit_count,
            mechanic_tags=tuple(getattr(generated_level, "mechanic_tags", ()) or ()),
            primary_mechanic_tag=getattr(generated_level, "primary_mechanic_tag", "") or "",
            topology_class=getattr(generated_level, "topology_class", "") or "",
            required_path_length=self._required_path_length(generated_level),
            layout_orientation=self._layout_orientation(generated_level),
            layout_size_profile=self._layout_size_profile(generated_level),
            decision_dependency_pattern=(
                int(getattr(profile, "required_decision_count", len(solution.actions))),
                int(getattr(profile, "ordered_dependency_count", 0)),
                float(getattr(profile, "independent_decision_ratio", 0.0)),
            ),
            switch_degree_sequence=switch_degree_sequence,
            revisit_state_reversal_pattern=(
                int(getattr(profile, "route_revisit_count", 0)),
                int(getattr(profile, "repeated_switch_decision_count", central_switch_revisit_count)),
                int(getattr(profile, "switch_state_change_on_revisit_count", 0)),
            ),
            failure_outcome_distribution=failure_distribution,
            package_phase_pattern=(
                int(getattr(profile, "package_phase_decisions_before", 0)),
                int(getattr(profile, "package_phase_decisions_after", 0)),
            ),
            layout_silhouette=silhouette,
            mirrored_layout_silhouette=mirrored_silhouette,
            road_direction_histogram=self._road_direction_histogram(level),
            solution_decision_timing_pattern=self._timing_pattern(action_times),
            blueprint_archetype=(
                str(getattr(blueprint, "archetype", "") or "").strip().lower()
            ),
            objective_count=len(objectives),
            objective_kinds=tuple(
                getattr(objective.kind, "value", str(objective.kind))
                for objective in objectives
            ),
            dependency_dag_signature=self._dependency_dag_signature(blueprint),
            adaptive_decision_pattern=self._adaptive_decision_pattern(blueprint),
            state_transition_pattern=self._state_transition_pattern(blueprint),
            static_policy_proof_signature=self._static_policy_proof_signature(
                static_policy_result
            ),
            agent_performance_profile=self._agent_performance_profile(
                policy_evaluation, puzzle_analysis
            ),
            revisit_pattern=self._revisit_pattern(optimal_trace),
            success_failure_distribution=self._success_failure_distribution(
                strategy_result, puzzle_analysis
            ),
            optimal_strategy_signature=self._optimal_strategy_signature(optimal_trace),
            road_state_visual_signature=self._road_state_visual_signature(level),
        )

    def signature_for_pipeline_result(self, pipeline_result) -> CandidateSignature:
        """Build the complete V3 signature from one accepted pipeline result."""

        if not getattr(pipeline_result, "passed", False):
            raise ValueError("candidate signatures require an accepted pipeline result")
        candidate = getattr(pipeline_result, "candidate", None)
        if candidate is None:
            raise ValueError("accepted pipeline result is missing its generated candidate")

        stages = {
            getattr(stage, "stage", ""): stage
            for stage in getattr(pipeline_result, "stage_results", ())
        }
        blueprint_stage = stages.get("blueprint")
        strategy_stage = stages.get("strategy")
        quality_stage = stages.get("quality")
        if blueprint_stage is None or strategy_stage is None or quality_stage is None:
            raise ValueError("accepted pipeline result is missing signature evidence")

        blueprint = getattr(blueprint_stage, "blueprint", None)
        strategy_result = getattr(strategy_stage, "strategy_search", None)
        static_policy_result = getattr(strategy_stage, "static_policy_search", None)
        policy_evaluation = getattr(strategy_stage, "policy_evaluation", None)
        puzzle_analysis = getattr(quality_stage, "puzzle_analysis", None)
        if any(
            item is None
            for item in (
                blueprint,
                strategy_result,
                static_policy_result,
                policy_evaluation,
                puzzle_analysis,
            )
        ):
            raise ValueError("accepted pipeline result has incomplete signature evidence")

        signature = self.signature_for(
            candidate,
            blueprint=blueprint,
            strategy_result=strategy_result,
            static_policy_result=static_policy_result,
            policy_evaluation=policy_evaluation,
            puzzle_analysis=puzzle_analysis,
        )
        candidate.candidate_signature = signature
        return signature

    def _failure_distribution(self, profile) -> tuple[tuple[str, int], ...]:
        if profile is None:
            return ()
        counts = Counter(getattr(profile, "failure_outcome_types", ()) or ())
        dead_ends = int(getattr(profile, "dead_end_choice_count", 0))
        early_destination = int(getattr(profile, "destination_before_package_choice_count", 0))
        if dead_ends:
            counts["dead_end"] = dead_ends
        if early_destination:
            counts["destination_before_package"] = early_destination
        known = sum(counts.values())
        remainder = max(0, int(getattr(profile, "failure_route_count", known)) - known)
        if remainder:
            counts["other"] += remainder
        return tuple(sorted(counts.items()))

    def _layout_silhouettes(self, positions):
        visual = tuple(sorted((x, y) for _, x, y in positions))
        mirrored = tuple(sorted((round(1.0 - x, 4), y) for x, y in visual))
        return visual, min(visual, mirrored)

    def _road_direction_histogram(self, level_document) -> tuple[tuple[str, int], ...]:
        positions = {node.id: (float(node.x), float(node.y)) for node in level_document.graph.nodes}
        counts: Counter[str] = Counter()
        for edge in level_document.graph.edges:
            if edge.fromNodeID not in positions or edge.toNodeID not in positions:
                continue
            x1, y1 = positions[edge.fromNodeID]
            x2, y2 = positions[edge.toNodeID]
            dx, dy = x2 - x1, y2 - y1
            if abs(dx) >= abs(dy):
                counts["right" if dx >= 0 else "left"] += 1
            else:
                counts["down" if dy >= 0 else "up"] += 1
        return tuple(sorted(counts.items()))

    def _timing_pattern(self, times: tuple[float, ...]) -> tuple[float, ...]:
        if not times:
            return ()
        origin = times[0]
        relative = tuple(time - origin for time in times)
        scale = relative[-1]
        if scale <= 0:
            return tuple(0.0 for _ in relative)
        return tuple(round(value / scale, 4) for value in relative)

    def _dependency_dag_signature(self, blueprint) -> str:
        if blueprint is None:
            return ""
        graph = blueprint.decision_graph
        decisions = sorted(
            graph.decisions,
            key=lambda item: (item.sequence_index, item.phase_index, item.id),
        )
        indices = {decision.id: index for index, decision in enumerate(decisions)}
        objective_phases = dict(graph.objective_phase_indices)
        payload = {
            "decisions": [
                (
                    decision.phase_index,
                    len(decision.outgoing_edge_roles),
                    decision.required_outgoing_edge_role is not None,
                )
                for decision in decisions
            ],
            "dependencies": sorted(
                (
                    (
                        ("objective", objective_phases.get(dependency.source_id, -1))
                        if dependency.kind is DecisionDependencyKind.OBJECTIVE_STATE
                        else ("decision", indices.get(dependency.source_id, -1))
                    ),
                    indices.get(dependency.target_id, -1),
                    dependency.kind.value,
                    dependency.required_source_outgoing_edge_role is not None,
                )
                for dependency in graph.dependencies
            ),
        }
        return self._hash_payload(payload)

    def _adaptive_decision_pattern(self, blueprint) -> tuple[tuple[object, ...], ...]:
        if blueprint is None:
            return ()
        graph = blueprint.decision_graph
        adaptive = set(blueprint.adaptive_decision_ids)
        dependencies_by_target: dict[str, list[str]] = {}
        for dependency in graph.dependencies:
            dependencies_by_target.setdefault(dependency.target_id, []).append(
                dependency.kind.value
            )
        return tuple(
            (
                decision.sequence_index,
                decision.phase_index,
                tuple(sorted(dependencies_by_target.get(decision.id, ()))),
            )
            for decision in sorted(
                graph.decisions,
                key=lambda item: (item.sequence_index, item.phase_index, item.id),
            )
            if decision.id in adaptive
        )

    def _state_transition_pattern(self, blueprint) -> tuple[tuple[object, ...], ...]:
        if blueprint is None:
            return ()
        return tuple(
            (
                transition.from_phase_index,
                transition.to_phase_index,
                "objective" if transition.trigger_objective_id is not None else "decision",
                len(transition.revealed_objective_ids),
                len(transition.opened_edge_roles),
                len(transition.closed_edge_roles),
                len(transition.consumed_edge_roles),
            )
            for transition in sorted(
                blueprint.state_transitions,
                key=lambda item: (item.from_phase_index, item.to_phase_index, item.id),
            )
        )

    def _static_policy_proof_signature(self, proof) -> str:
        if proof is None:
            return ""
        payload = {
            "exhaustive": bool(proof.exhaustive),
            "tested": int(proof.tested_policy_count),
            "total": int(proof.total_policy_count),
            "successfulPolicyCount": len(proof.successful_policies),
            "limits": tuple(proof.limit_reasons),
        }
        return self._hash_payload(payload)

    def _agent_performance_profile(
        self, policy_evaluation, puzzle_analysis
    ) -> tuple[tuple[object, ...], ...]:
        evaluations = ()
        if policy_evaluation is not None:
            evaluations = getattr(policy_evaluation, "evaluations", ())
        elif puzzle_analysis is not None:
            evaluations = getattr(puzzle_analysis, "agent_results", ())
        return tuple(
            (
                evaluation.policy_name,
                round(float(evaluation.success_rate), 6),
                self._rounded_optional(evaluation.average_taps),
                self._rounded_optional(evaluation.average_completion_time_seconds),
                self._rounded_optional(evaluation.average_route_distance),
                tuple(
                    (failure.code, failure.count)
                    for failure in evaluation.failure_types
                ),
            )
            for evaluation in sorted(
                evaluations, key=lambda item: item.policy_name
            )
        )

    @staticmethod
    def _rounded_optional(value) -> float | None:
        return None if value is None else round(float(value), 6)

    def _revisit_pattern(self, trace) -> tuple[tuple[int, int, int], ...]:
        if trace is None:
            return ()
        first_occurrence: dict[str, int] = {}
        repeats: list[tuple[int, int, int]] = []
        for ordinal, action in enumerate(trace.actions):
            first = first_occurrence.setdefault(action.node_id, ordinal)
            if first == ordinal:
                continue
            phase = (
                action.state_transition.objective_index_before
                if action.state_transition is not None
                else 0
            )
            repeats.append((first, ordinal, phase))
        return tuple(repeats)

    def _success_failure_distribution(
        self, strategy_result, puzzle_analysis
    ) -> tuple[tuple[str, int], ...]:
        counts: Counter[str] = Counter()
        if strategy_result is not None:
            counts["successful"] = len(strategy_result.all_successful_strategies)
            counts.update(
                trace.outcome_code for trace in strategy_result.failure_outcomes
            )
        elif puzzle_analysis is not None:
            counts["successful"] = int(
                getattr(puzzle_analysis, "successful_strategy_classes", 0)
            )
            for outcome in getattr(
                puzzle_analysis, "recovery_failure_distribution", ()
            ):
                counts[outcome.outcome_code] += outcome.count
        return tuple(sorted((code, count) for code, count in counts.items() if count))

    def _optimal_strategy_signature(self, trace) -> str:
        if trace is None:
            return ""
        node_indices: dict[str, int] = {}
        edge_indices: dict[str, int] = {}

        def node_index(node_id: str) -> int:
            return node_indices.setdefault(node_id, len(node_indices))

        def edge_index(edge_id: str) -> int:
            return edge_indices.setdefault(edge_id, len(edge_indices))

        actions = []
        for action in trace.actions:
            transition = action.state_transition
            actions.append(
                (
                    node_index(action.node_id),
                    edge_index(action.selected_edge_id),
                    action.tap_count,
                    tuple(edge_index(edge_id) for edge_id in action.traversed_edge_ids),
                    tuple(node_index(node_id) for node_id in action.visited_node_ids),
                    len(action.completed_objective_ids),
                    action.meaningful_decision,
                    None
                    if transition is None
                    else (
                        transition.objective_index_before,
                        transition.objective_index_after,
                        len(transition.completed_objective_ids),
                        len(transition.opened_edge_ids),
                        len(transition.closed_edge_ids),
                        len(transition.consumed_edge_ids),
                    ),
                )
            )
        return self._hash_payload(
            {
                "actions": actions,
                "outcome": trace.outcome_code,
                "cost": (
                    trace.cost.accepted_taps,
                    trace.cost.travel_time_seconds,
                    trace.cost.route_distance,
                ),
            }
        )

    def _road_state_visual_signature(self, level_document) -> str:
        objectives = tuple(
            sorted(level_document.effective_objectives, key=lambda item: item.sequenceIndex)
        )
        positions = {
            node.id: (float(node.x), float(node.y))
            for node in level_document.graph.nodes
        }
        snapshots = []
        for objective_index in range(len(objectives) + 1):
            completed = {
                objective.id for objective in objectives[:objective_index]
            }
            active_index = objective_index if objective_index < len(objectives) else None
            state_counts: Counter[tuple[str, str]] = Counter()
            for edge in level_document.graph.edges:
                rule = level_document.effective_edge_availability_rule(edge)
                state = "open" if rule.allows(completed, active_index) else "locked"
                state_counts[(state, self._edge_direction(edge, positions))] += 1
            snapshots.append(tuple(sorted((state, direction, count) for (state, direction), count in state_counts.items())))
        return self._hash_payload(snapshots)

    @staticmethod
    def _edge_direction(edge, positions: dict[str, tuple[float, float]]) -> str:
        if edge.fromNodeID not in positions or edge.toNodeID not in positions:
            return "unknown"
        x1, y1 = positions[edge.fromNodeID]
        x2, y2 = positions[edge.toNodeID]
        dx, dy = x2 - x1, y2 - y1
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        return "down" if dy >= 0 else "up"

    def _normalized_edges(self, level_document) -> tuple[tuple[str, ...], ...]:
        return tuple(
            sorted(
                (edge.fromNodeID, edge.toNodeID)
                if edge.availability == "always"
                else (edge.fromNodeID, edge.toNodeID, edge.availability)
                for edge in level_document.graph.edges
            )
        )

    def _normalized_positions(self, level_document) -> tuple[tuple[str, float, float], ...]:
        raw_positions = {node.id: (float(node.x), float(node.y)) for node in level_document.graph.nodes}
        if not raw_positions:
            return ()

        xs = [position[0] for position in raw_positions.values()]
        ys = [position[1] for position in raw_positions.values()]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        width = max_x - min_x
        height = max_y - min_y

        normalized: list[tuple[str, float, float]] = []
        for node_id, (x, y) in raw_positions.items():
            normalized_x = 0.5 if width == 0 else (x - min_x) / width
            normalized_y = 0.5 if height == 0 else (y - min_y) / height
            normalized.append((node_id, round(normalized_x, 4), round(normalized_y, 4)))
        return tuple(sorted(normalized))

    def _hash_payload(self, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _required_path_length(self, generated_level) -> int | None:
        metadata = getattr(generated_level, "abstract_solution_metadata", None)
        if metadata is not None and getattr(metadata, "required_path", None):
            return max(len(metadata.required_path) - 1, 0)

        solution_metadata = dict(getattr(generated_level.solution, "_extra", {}).get("metadata", {}))
        route = solution_metadata.get("solutionRoute") or []
        if route:
            return max(len(route) - 1, 0)
        return None

    def _layout_orientation(self, generated_level) -> str:
        metadata = getattr(generated_level, "layout_metadata", None) or {}
        explicit = metadata.get("orientation")
        if explicit:
            return str(explicit).strip().lower() or "unknown"

        strategy = str(metadata.get("strategy", "")).lower()
        if "vertical" in strategy:
            return "vertical"
        if "horizontal" in strategy:
            return "horizontal"

        variant = str(getattr(generated_level, "selected_layout_variant", "") or metadata.get("variant", "")).lower()
        if variant == "tall":
            return "vertical"
        if variant == "wide":
            return "horizontal"
        return "unknown"

    def _layout_size_profile(self, generated_level) -> str:
        metadata = getattr(generated_level, "layout_metadata", None) or {}
        profile = str(metadata.get("layoutSizeProfile", "")).strip().lower()
        return profile or "standard_portrait"
