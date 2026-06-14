from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..models.runtime_parity import RuntimeParityValidationResult


@dataclass(frozen=True)
class SwiftValidationGateDecision:
    required: bool
    reason: str
    risky_mechanic_tags: tuple[str, ...] = field(default_factory=tuple)
    requires_swift_runtime_validation: bool = False


class SwiftValidationGate:
    RISKY_TERMS = {
        "four_way",
        "four-way",
        "ring",
        "loop",
        "return_loop",
        "revisit",
        "repeated_tap",
        "rejoin",
        "split_rejoin",
        "split_path_rejoin",
        "package_inside_loop",
        "two_phase",
        "multi_phase",
        "route_reversal",
    }
    RISKY_SOURCE_NAMES = {
        "four_way_intersection",
        "four_way_intro",
        "four_way_package_gate",
        "four_way_ring",
        "multi_four_way_route",
        "ring_route",
        "ring_route_gate",
        "return_loop",
        "return_loop_intro",
        "return_loop_with_gate",
        "multi_switch_revisit",
        "package_inside_loop",
        "controlled_repeated_taps",
        "late_route_reversal",
    }

    def evaluate(self, candidate) -> SwiftValidationGateDecision:
        tags: set[str] = set()
        reasons: list[str] = []
        metadata = dict(getattr(candidate, "mechanic_metadata", {}) or {})
        topology_rules = metadata.get("topologyRules")
        topology_rules = topology_rules if isinstance(topology_rules, dict) else {}

        requires_swift_runtime_validation = bool(topology_rules.get("requiresSwiftRuntimeValidation"))
        if requires_swift_runtime_validation:
            tags.add("requires_swift_runtime_validation")
            reasons.append("RecipeTopologyRules requires Swift runtime validation")
        if getattr(candidate, "requires_swift_validation", False):
            tags.add("candidate_requires_swift_validation")
            reasons.append("Candidate metadata requires Swift validation")

        candidate_terms = self._candidate_terms(candidate, metadata)
        risky_terms = sorted(
            term
            for term in candidate_terms
            if term in self.RISKY_TERMS or any(risky in term for risky in self.RISKY_TERMS)
        )
        for term in risky_terms:
            tags.add(self._canonical_tag(term))
        if risky_terms:
            reasons.append(f"Risky mechanic metadata: {', '.join(risky_terms)}")

        if topology_rules.get("allowsCycles") is True:
            tags.add("declared_loop")
            reasons.append("Topology rules allow declared cycles")
        if topology_rules.get("allowsRing") is True:
            tags.add("ring")
            reasons.append("Topology rules allow declared rings")
        if topology_rules.get("allowsRejoin") is True:
            tags.add("declared_rejoin")
            reasons.append("Topology rules allow declared rejoins")
        if topology_rules.get("allowsRevisit") is True:
            tags.add("declared_revisit")
            reasons.append("Topology rules allow declared revisits")
        if metadata.get("allowsRepeatedTaps") is True:
            tags.add("repeated_tap")
            reasons.append("Recipe metadata allows repeated taps")

        graph_tags = self._graph_risk_tags(candidate)
        for tag in graph_tags:
            tags.add(tag)
        if graph_tags:
            reasons.append(f"Concrete graph risk: {', '.join(graph_tags)}")

        required = bool(requires_swift_runtime_validation or tags)
        if not required:
            return SwiftValidationGateDecision(
                required=False,
                reason="No runtime-risk mechanics detected.",
                risky_mechanic_tags=(),
                requires_swift_runtime_validation=False,
            )

        return SwiftValidationGateDecision(
            required=True,
            reason="; ".join(dict.fromkeys(reasons)),
            risky_mechanic_tags=tuple(sorted(tags)),
            requires_swift_runtime_validation=requires_swift_runtime_validation,
        )

    def source_requires_runtime_validation(self, source_name: str) -> bool:
        normalized = self._normalize(source_name)
        if normalized in self.RISKY_SOURCE_NAMES:
            return True
        return normalized in self.RISKY_TERMS or any(term in normalized for term in self.RISKY_TERMS)

    def _candidate_terms(self, candidate, metadata: dict[str, Any]) -> set[str]:
        terms = {
            getattr(candidate, "template_name", ""),
            getattr(candidate, "recipe_family", ""),
            getattr(candidate, "recipe_variant", ""),
            getattr(candidate, "primary_mechanic_tag", ""),
            getattr(candidate, "topology_class", ""),
        }
        terms.update(getattr(candidate, "mechanic_tags", ()) or ())
        for key in ("mechanicTags", "primaryMechanicTag", "topologyClass", "intendedMechanic"):
            value = metadata.get(key)
            if isinstance(value, str):
                terms.add(value)
            elif isinstance(value, (list, tuple)):
                terms.update(str(item) for item in value)

        normalized: set[str] = set()
        for term in terms:
            normalized_term = self._normalize(str(term))
            if not normalized_term:
                continue
            normalized.add(normalized_term)
            normalized.update(part for part in normalized_term.split("_") if part)
        return normalized

    def _graph_risk_tags(self, candidate) -> tuple[str, ...]:
        level = getattr(candidate, "level_document", None)
        if level is None:
            return ()

        nodes = list(getattr(getattr(level, "graph", None), "nodes", ()) or ())
        edges = list(getattr(getattr(level, "graph", None), "edges", ()) or ())
        edge_by_id = {edge.id: edge for edge in edges}
        outgoing: dict[str, list[str]] = {}
        incoming: dict[str, list[str]] = {}
        for edge in edges:
            outgoing.setdefault(edge.fromNodeID, []).append(edge.toNodeID)
            incoming.setdefault(edge.toNodeID, []).append(edge.fromNodeID)

        tags: set[str] = set()
        for node in nodes:
            valid_outgoing = [
                edge_id
                for edge_id in getattr(node, "outgoingEdgeIDs", ())
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            if len(valid_outgoing) >= 4:
                tags.add("four_way")

        solution_route = self._solution_route(candidate)
        if solution_route:
            repeated_route_nodes = [
                node_id
                for node_id, count in Counter(solution_route).items()
                if count > 1
            ]
            if repeated_route_nodes:
                tags.add("revisit")

        action_node_ids = [
            action.tapNodeID
            for action in getattr(getattr(candidate, "solution", None), "actions", ()) or ()
        ]
        if any(count > 1 for count in Counter(action_node_ids).values()):
            tags.add("repeated_tap")

        rejoin_nodes = [
            node_id
            for node_id, sources in incoming.items()
            if node_id != getattr(level, "startNodeID", "start") and len(set(sources)) >= 2
        ]
        if rejoin_nodes:
            tags.add("rejoin")

        cycles = self._detected_cycles(outgoing)
        if cycles:
            tags.add("loop")
            package_node_id = getattr(level, "packageNodeID", "package")
            if any(package_node_id in cycle for cycle in cycles):
                tags.add("package_inside_loop")
        return tuple(sorted(tags))

    def _solution_route(self, candidate) -> tuple[str, ...]:
        abstract = getattr(candidate, "abstract_solution_metadata", None)
        if abstract is not None and getattr(abstract, "required_path", None):
            return tuple(str(node_id) for node_id in abstract.required_path)
        solution = getattr(candidate, "solution", None)
        metadata = dict(getattr(solution, "_extra", {}).get("metadata", {}) if solution is not None else {})
        route = metadata.get("solutionRoute") or ()
        return tuple(str(node_id) for node_id in route)

    def _detected_cycles(self, outgoing: dict[str, list[str]]) -> tuple[tuple[str, ...], ...]:
        node_ids = sorted(set(outgoing.keys()) | {node_id for targets in outgoing.values() for node_id in targets})
        max_depth = max(1, len(node_ids))
        cycles: set[tuple[str, ...]] = set()

        def visit(start_id: str, current_id: str, path: tuple[str, ...]) -> None:
            if len(path) > max_depth:
                return
            for next_id in outgoing.get(current_id, ()):
                if next_id == start_id:
                    cycles.add(self._canonical_cycle(path))
                    continue
                if next_id in path:
                    continue
                visit(start_id, next_id, (*path, next_id))

        for node_id in node_ids:
            visit(node_id, node_id, (node_id,))
        return tuple(sorted(cycles))

    def _canonical_cycle(self, cycle: tuple[str, ...]) -> tuple[str, ...]:
        if not cycle:
            return cycle
        rotations = [cycle[index:] + cycle[:index] for index in range(len(cycle))]
        return min(rotations)

    def _canonical_tag(self, term: str) -> str:
        normalized = self._normalize(term)
        if "four_way" in normalized or "four-way" in normalized:
            return "four_way"
        if "package_inside_loop" in normalized:
            return "package_inside_loop"
        if "repeated_tap" in normalized:
            return "repeated_tap"
        if "return_loop" in normalized:
            return "loop"
        if "split_rejoin" in normalized or "split_path_rejoin" in normalized:
            return "rejoin"
        if "two_phase" in normalized or "multi_phase" in normalized:
            return "multi_phase"
        if "route_reversal" in normalized:
            return "revisit"
        for term_name in ("ring", "loop", "revisit", "rejoin"):
            if term_name in normalized:
                return term_name
        return normalized

    def _normalize(self, value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")


class RuntimeParityValidator:
    def __init__(self, gate: SwiftValidationGate | None = None) -> None:
        self.gate = gate or SwiftValidationGate()

    def evaluate_candidate(
        self,
        candidate,
        *,
        dry_run: bool,
        run_swift_tests: bool,
        swift_validation_command: list[str] | None = None,
        swift_validation_environment: dict[str, str] | None = None,
        swift_summary=None,
    ) -> RuntimeParityValidationResult:
        decision = self.gate.evaluate(candidate)
        command = list(swift_validation_command or [])
        environment = dict(swift_validation_environment or {})

        if not decision.required:
            return RuntimeParityValidationResult(
                runtime_validation_required=False,
                runtime_validation_status="not_required",
                runtime_validation_reason=decision.reason,
                swift_validation_command=command,
                swift_validation_environment=environment,
                risky_mechanic_tags=decision.risky_mechanic_tags,
                requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
            )

        if swift_summary is not None and swift_summary.passed is True:
            return RuntimeParityValidationResult(
                runtime_validation_required=True,
                runtime_validation_status="passed",
                runtime_validation_reason=decision.reason,
                swift_validation_command=list(getattr(swift_summary, "command", command) or command),
                swift_validation_environment=dict(getattr(swift_summary, "environment", environment) or environment),
                swift_validation_passed=True,
                risky_mechanic_tags=decision.risky_mechanic_tags,
                requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
            )

        if swift_summary is not None and swift_summary.passed is False:
            failure_reasons = list(getattr(swift_summary, "failure_reasons", []) or [])
            failure_reason = failure_reasons[0] if failure_reasons else "swift_runtime_parity_failed"
            return RuntimeParityValidationResult(
                runtime_validation_required=True,
                runtime_validation_status="failed",
                runtime_validation_reason=decision.reason,
                swift_validation_command=list(getattr(swift_summary, "command", command) or command),
                swift_validation_environment=dict(getattr(swift_summary, "environment", environment) or environment),
                swift_validation_passed=False,
                risky_mechanic_tags=decision.risky_mechanic_tags,
                requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
                failure_reason=failure_reason,
                failure_details=tuple(getattr(swift_summary, "failure_details", ()) or ()),
            )

        if dry_run:
            return RuntimeParityValidationResult(
                runtime_validation_required=True,
                runtime_validation_status="skipped_required_for_production",
                runtime_validation_reason=decision.reason,
                swift_validation_command=command,
                swift_validation_environment=environment,
                swift_validation_skipped_reason="dry_run",
                risky_mechanic_tags=decision.risky_mechanic_tags,
                requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
            )

        if run_swift_tests:
            return RuntimeParityValidationResult(
                runtime_validation_required=True,
                runtime_validation_status="pending_required_swift_validation",
                runtime_validation_reason=decision.reason,
                swift_validation_command=command,
                swift_validation_environment=environment,
                risky_mechanic_tags=decision.risky_mechanic_tags,
                requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
            )

        return RuntimeParityValidationResult(
            runtime_validation_required=True,
            runtime_validation_status="missing_required_swift_validation",
            runtime_validation_reason=decision.reason,
            swift_validation_command=command,
            swift_validation_environment=environment,
            swift_validation_skipped_reason="swift_tests_not_requested",
            risky_mechanic_tags=decision.risky_mechanic_tags,
            requires_swift_runtime_validation=decision.requires_swift_runtime_validation,
            failure_reason="missing_required_swift_validation",
        )
