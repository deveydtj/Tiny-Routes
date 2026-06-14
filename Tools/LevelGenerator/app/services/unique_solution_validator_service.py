from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UniqueSolutionValidationIssue:
    severity: str
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None


@dataclass(frozen=True)
class UniqueSolutionPathSummary:
    terminal_reason: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    tap_history: tuple[str, ...]
    has_collected_package: bool
    traversal_depth: int
    package_index: int | None = None
    destination_index: int | None = None

    @property
    def route_length(self) -> int:
        return max(0, len(self.node_ids) - 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminalReason": self.terminal_reason,
            "nodeIDs": list(self.node_ids),
            "edgeIDs": list(self.edge_ids),
            "tapHistory": list(self.tap_history),
            "hasCollectedPackage": self.has_collected_package,
            "traversalDepth": self.traversal_depth,
            "routeLength": self.route_length,
            "packageIndex": self.package_index,
            "destinationIndex": self.destination_index,
        }


@dataclass(frozen=True)
class UniqueSolutionSearchState:
    """State required for future exhaustive unique-solution traversal."""

    current_node_id: str
    active_edge_by_node_id: tuple[tuple[str, str | None], ...]
    has_collected_package: bool
    visited_node_ids: tuple[str, ...]
    traversed_edge_ids: tuple[str, ...]
    tap_history: tuple[str, ...]
    revisit_counts: tuple[tuple[str, int], ...]
    traversal_depth: int
    current_edge_id: str | None = None
    elapsed_time_seconds: float = 0.0


@dataclass(frozen=True)
class UniqueSolutionValidationConfig:
    max_taps: int
    max_traversal_depth: int
    allow_loops: bool
    allow_rejoins: bool
    allow_revisits: bool
    require_package_gate: bool
    max_explored_states: int = 50000


@dataclass(frozen=True)
class UniqueSolutionValidationResult:
    requires_unique_solution: bool
    is_exhaustive: bool
    solution_count: int | None = None
    issues: tuple[UniqueSolutionValidationIssue, ...] = field(default_factory=tuple)
    initial_state: UniqueSolutionSearchState | None = None
    config: UniqueSolutionValidationConfig | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    explored_states: int = 0
    max_depth_reached: int = 0
    termination_reason: str = "not_started"
    terminal_reason_counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    successful_path_summaries: tuple[UniqueSolutionPathSummary, ...] = field(default_factory=tuple)
    destination_before_package_summaries: tuple[UniqueSolutionPathSummary, ...] = field(default_factory=tuple)
    failure_path_summaries: tuple[UniqueSolutionPathSummary, ...] = field(default_factory=tuple)
    shortcut_detected: bool = False
    package_bypass_detected: bool = False
    wrong_branch_reached_goal: bool = False
    bypass_path_summary: UniqueSolutionPathSummary | None = None
    intended_route_length: int | None = None
    shortest_valid_route_length: int | None = None
    package_reachability_status: str = "not_evaluated"


class UniqueSolutionValidatorService:
    """Counts bounded structural solutions for generated levels."""

    path_summary_limit = 24

    def validate_unique_solution(self, generated_level) -> UniqueSolutionValidationResult:
        topology_rules = self._topology_rules(generated_level)
        requires_unique_solution = bool(topology_rules.get("requiresUniqueSolution", False))
        config = self._config(generated_level, topology_rules)
        initial_state = self._initial_state(generated_level)
        intended_route = self._intended_route(generated_level)
        intended_route_length = max(0, len(intended_route) - 1) if intended_route else None
        should_validate_route_safety = (
            requires_unique_solution
            or self._package_required(generated_level)
            or bool(intended_route)
        )

        if not should_validate_route_safety:
            package_status = self._package_reachability_status(generated_level, intended_route)
            return UniqueSolutionValidationResult(
                requires_unique_solution=False,
                is_exhaustive=False,
                initial_state=initial_state,
                config=config,
                notes=("unique_solution_not_required_by_topology_rules",),
                intended_route_length=intended_route_length,
                package_reachability_status=package_status,
            )

        enumeration = self._enumerate_solutions(generated_level, initial_state, config)
        package_issues = self.validate_package_before_goal(generated_level, enumeration)
        shortcut_issues = self.validate_no_shortcut_path(generated_level, enumeration)
        wrong_branch_issues = self.validate_wrong_branches_fail_correctly(generated_level, enumeration)
        unique_issues = self._issues_for_result(enumeration) if requires_unique_solution else ()
        issues = (*unique_issues, *package_issues, *shortcut_issues, *wrong_branch_issues)
        destination_before_package_summary = (
            enumeration.destination_before_package_summaries[0]
            if enumeration.destination_before_package_summaries
            else None
        )
        return UniqueSolutionValidationResult(
            requires_unique_solution=requires_unique_solution,
            is_exhaustive=enumeration.is_exhaustive,
            solution_count=enumeration.solution_count,
            issues=issues,
            initial_state=initial_state,
            config=config,
            notes=(
                enumeration.notes
                if requires_unique_solution
                else (*enumeration.notes, "unique_solution_not_required_by_topology_rules")
            ),
            explored_states=enumeration.explored_states,
            max_depth_reached=enumeration.max_depth_reached,
            termination_reason=enumeration.termination_reason,
            terminal_reason_counts=enumeration.terminal_reason_counts,
            successful_path_summaries=enumeration.successful_path_summaries,
            destination_before_package_summaries=enumeration.destination_before_package_summaries,
            failure_path_summaries=enumeration.failure_path_summaries,
            shortcut_detected=(
                bool(shortcut_issues)
                or bool(package_issues and destination_before_package_summary is not None)
            ),
            package_bypass_detected=bool(package_issues and destination_before_package_summary is not None),
            wrong_branch_reached_goal=self._wrong_branch_reached_goal(generated_level, enumeration),
            bypass_path_summary=destination_before_package_summary,
            intended_route_length=intended_route_length,
            shortest_valid_route_length=enumeration.shortest_valid_route_length,
            package_reachability_status=self._package_reachability_status(generated_level, intended_route),
        )

    def validateUniqueSolution(self, generated_level) -> UniqueSolutionValidationResult:
        return self.validate_unique_solution(generated_level)

    def _topology_rules(self, generated_level) -> dict[str, Any]:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        topology_rules = metadata.get("topologyRules")
        return dict(topology_rules) if isinstance(topology_rules, dict) else {}

    def _config(
        self,
        generated_level,
        topology_rules: dict[str, Any],
    ) -> UniqueSolutionValidationConfig:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        valid_outgoing_counts = [
            len(self._valid_outgoing_edge_ids(node, edge_by_id))
            for node in level.graph.nodes
        ]
        max_switch_rotation_taps = max((count - 1 for count in valid_outgoing_counts), default=0)
        max_taps = max(
            int(getattr(level, "parTaps", 0) or 0),
            len(getattr(generated_level.solution, "actions", ()) or ()),
            int(getattr(generated_level.solution, "maxTaps", 0) or 0),
        )
        max_depth = max(8, len(level.graph.nodes) * 4)
        if topology_rules.get("allowsCycles") or topology_rules.get("allowsRevisit"):
            max_depth = max(max_depth, len(level.graph.nodes) * 8)
        max_taps = max(max_taps, max_depth * max_switch_rotation_taps)
        max_explored_states = max(
            50000,
            len(level.graph.nodes) * max(1, len(level.graph.edges)) * 512,
        )

        return UniqueSolutionValidationConfig(
            max_taps=max_taps,
            max_traversal_depth=max_depth,
            allow_loops=bool(topology_rules.get("allowsCycles", False)),
            allow_rejoins=bool(topology_rules.get("allowsRejoin", False)),
            allow_revisits=bool(topology_rules.get("allowsRevisit", False)),
            require_package_gate=bool(topology_rules.get("requiresPackageGate", False)),
            max_explored_states=max_explored_states,
        )

    def _initial_state(self, generated_level) -> UniqueSolutionSearchState:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        active_edges: list[tuple[str, str | None]] = []
        for node in level.graph.nodes:
            valid_edges = self._valid_outgoing_edge_ids(node, edge_by_id)
            active_edges.append((node.id, valid_edges[0] if valid_edges else None))

        visited = (level.startNodeID,)
        revisit_counts = tuple(sorted(Counter(visited).items()))
        return UniqueSolutionSearchState(
            current_node_id=level.startNodeID,
            active_edge_by_node_id=tuple(sorted(active_edges)),
            has_collected_package=level.startNodeID == level.packageNodeID,
            visited_node_ids=visited,
            traversed_edge_ids=(),
            tap_history=(),
            revisit_counts=revisit_counts,
            traversal_depth=0,
        )

    def _enumerate_solutions(
        self,
        generated_level,
        initial_state: UniqueSolutionSearchState,
        config: UniqueSolutionValidationConfig,
    ) -> "_EnumerationResult":
        level = generated_level.level_document
        node_by_id = {node.id: node for node in level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        queue: deque[UniqueSolutionSearchState] = deque([initial_state])
        solution_count = 0
        explored_states = 0
        max_depth_reached = initial_state.traversal_depth
        terminal_reasons: Counter[str] = Counter()
        depth_limited = False
        state_limited = False
        successful_path_summaries: list[UniqueSolutionPathSummary] = []
        destination_before_package_summaries: list[UniqueSolutionPathSummary] = []
        failure_path_summaries: list[UniqueSolutionPathSummary] = []

        while queue:
            if explored_states >= config.max_explored_states:
                state_limited = True
                break

            state = queue.popleft()
            explored_states += 1
            max_depth_reached = max(max_depth_reached, state.traversal_depth)

            if state.current_node_id == level.destinationNodeID:
                if state.has_collected_package:
                    solution_count += 1
                    terminal_reasons["success"] += 1
                    self._append_path_summary(
                        successful_path_summaries,
                        self._path_summary(state, "success", level),
                    )
                else:
                    terminal_reasons["destination_before_package"] += 1
                    self._append_path_summary(
                        destination_before_package_summaries,
                        self._path_summary(state, "destination_before_package", level),
                    )
                continue

            if state.traversal_depth >= config.max_traversal_depth:
                depth_limited = True
                terminal_reasons["max_traversal_depth_reached"] += 1
                self._append_path_summary(
                    failure_path_summaries,
                    self._path_summary(state, "max_traversal_depth_reached", level),
                )
                continue

            node = node_by_id.get(state.current_node_id)
            if node is None:
                terminal_reasons["missing_current_node"] += 1
                self._append_path_summary(
                    failure_path_summaries,
                    self._path_summary(state, "missing_current_node", level),
                )
                continue

            valid_edges = self._valid_outgoing_edge_ids(node, edge_by_id)
            if not valid_edges:
                terminal_reasons["dead_end"] += 1
                self._append_path_summary(
                    failure_path_summaries,
                    self._path_summary(state, "dead_end", level),
                )
                continue

            for tap_count in self._tap_options(valid_edges):
                if len(state.tap_history) + tap_count > config.max_taps:
                    terminal_reasons["max_taps_reached"] += 1
                    self._append_path_summary(
                        failure_path_summaries,
                        self._path_summary(state, "max_taps_reached", level),
                    )
                    continue

                active_edges = dict(state.active_edge_by_node_id)
                next_edge_id = self._rotated_edge_id(active_edges.get(node.id), valid_edges, tap_count)
                if next_edge_id is None:
                    terminal_reasons["active_edge_missing"] += 1
                    self._append_path_summary(
                        failure_path_summaries,
                        self._path_summary(state, "active_edge_missing", level),
                    )
                    continue

                edge = edge_by_id.get(next_edge_id)
                if edge is None or edge.fromNodeID != node.id:
                    terminal_reasons["active_edge_invalid"] += 1
                    self._append_path_summary(
                        failure_path_summaries,
                        self._path_summary(state, "active_edge_invalid", level),
                    )
                    continue

                active_edges[node.id] = next_edge_id
                next_node_id = edge.toNodeID
                visited_node_ids = (*state.visited_node_ids, next_node_id)
                tap_history = state.tap_history + ((node.id,) * tap_count)
                queue.append(
                    UniqueSolutionSearchState(
                        current_node_id=next_node_id,
                        active_edge_by_node_id=tuple(sorted(active_edges.items())),
                        has_collected_package=(
                            state.has_collected_package or next_node_id == level.packageNodeID
                        ),
                        visited_node_ids=visited_node_ids,
                        traversed_edge_ids=(*state.traversed_edge_ids, edge.id),
                        tap_history=tap_history,
                        revisit_counts=tuple(sorted(Counter(visited_node_ids).items())),
                        traversal_depth=state.traversal_depth + 1,
                        current_edge_id=edge.id,
                        elapsed_time_seconds=state.elapsed_time_seconds,
                    )
                )

        if state_limited:
            termination_reason = "max_explored_states_reached"
        elif depth_limited:
            termination_reason = "max_traversal_depth_reached"
        else:
            termination_reason = "exhausted"

        is_exhaustive = not state_limited and not depth_limited
        notes: tuple[str, ...] = ("bounded_structural_enumeration",)
        if config.allow_loops:
            notes = (*notes, "declared_loops_traversed_with_depth_limit")
        if config.allow_revisits:
            notes = (*notes, "revisits_traversed_with_depth_limit")
        if config.allow_rejoins:
            notes = (*notes, "rejoin_paths_counted_separately")

        return _EnumerationResult(
            solution_count=solution_count,
            explored_states=explored_states,
            max_depth_reached=max_depth_reached,
            termination_reason=termination_reason,
            terminal_reason_counts=tuple(sorted(terminal_reasons.items())),
            is_exhaustive=is_exhaustive,
            notes=notes,
            successful_path_summaries=tuple(successful_path_summaries),
            destination_before_package_summaries=tuple(destination_before_package_summaries),
            failure_path_summaries=tuple(failure_path_summaries),
            shortest_valid_route_length=min(
                (summary.route_length for summary in successful_path_summaries),
                default=None,
            ),
        )

    def validate_package_before_goal(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        if enumeration is None:
            enumeration = self._enumerate_solutions(
                generated_level,
                self._initial_state(generated_level),
                self._config(generated_level, self._topology_rules(generated_level)),
            )

        issues: list[UniqueSolutionValidationIssue] = []
        if not self._package_required(generated_level):
            if self._metadata_requires_package_gate(generated_level):
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="package_gate_metadata_not_enforceable",
                        message="Package-gate metadata exists, but the level does not define a distinct package before destination.",
                        related_node_id=generated_level.level_document.packageNodeID,
                    )
                )
            return tuple(issues)

        intended_route = self._intended_route(generated_level)
        package_status = self._package_reachability_status(generated_level, intended_route)
        if package_status != "package_before_destination_on_intended_route":
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code=(
                        "package_state_ambiguous"
                        if package_status in {
                            "intended_route_missing",
                            "package_and_destination_not_distinct",
                            "package_repeated_on_intended_route",
                            "destination_repeated_on_intended_route",
                        }
                        else "package_order_intended_route_invalid"
                    ),
                    message=(
                        "Package-before-goal validation could not prove the intended route "
                        f"collects the package before destination (status={package_status})."
                    ),
                    related_node_id=generated_level.level_document.packageNodeID,
                )
            )

        bypass_count = self._terminal_count(enumeration, "destination_before_package")
        if bypass_count:
            summary = (
                enumeration.destination_before_package_summaries[0]
                if enumeration.destination_before_package_summaries
                else None
            )
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="package_bypass_detected",
                    message=(
                        "Destination is structurally reachable before package collection "
                        f"({bypass_count} path(s)); sample={self._summary_text(summary)}."
                    ),
                    related_node_id=generated_level.level_document.destinationNodeID,
                    related_edge_id=summary.edge_ids[-1] if summary and summary.edge_ids else None,
                )
            )

        return tuple(issues)

    def validatePackageBeforeGoal(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        return self.validate_package_before_goal(generated_level, enumeration)

    def validate_no_shortcut_path(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        if enumeration is None:
            enumeration = self._enumerate_solutions(
                generated_level,
                self._initial_state(generated_level),
                self._config(generated_level, self._topology_rules(generated_level)),
            )

        issues: list[UniqueSolutionValidationIssue] = []
        intended_route = self._intended_route(generated_level)
        intended_taps = self._intended_tap_order(generated_level)
        intended_route_length = max(0, len(intended_route) - 1) if intended_route else None

        if not intended_route:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="shortcut_validation_missing_intended_route",
                    message="Shortcut validation requires solutionRoute or abstract required-path metadata.",
                ),
            )

        if self._terminal_count(enumeration, "destination_before_package"):
            summary = (
                enumeration.destination_before_package_summaries[0]
                if enumeration.destination_before_package_summaries
                else None
            )
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="shortcut_path_detected",
                    message=(
                        "Shortcut validation found a route that reaches destination before package collection; "
                        f"sample={self._summary_text(summary)}."
                    ),
                    related_node_id=generated_level.level_document.destinationNodeID,
                    related_edge_id=summary.edge_ids[-1] if summary and summary.edge_ids else None,
                )
            )

        if enumeration.solution_count > 1:
            summary = self._first_non_intended_success(enumeration, intended_route, intended_taps)
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="shortcut_path_detected",
                    message=(
                        "Shortcut validation found multiple valid package-before-destination routes "
                        f"(solutions={enumeration.solution_count}); sample={self._summary_text(summary)}."
                    ),
                    related_edge_id=summary.edge_ids[-1] if summary and summary.edge_ids else None,
                )
            )

        if enumeration.solution_count <= 1:
            for summary in enumeration.successful_path_summaries:
                path_differs = summary.node_ids != intended_route
                tap_order_differs = summary.tap_history != intended_taps
                shorter_than_intended = (
                    intended_route_length is not None
                    and summary.route_length < intended_route_length
                )
                fewer_taps_than_intended = len(summary.tap_history) < len(intended_taps)
                if not (path_differs or tap_order_differs or shorter_than_intended or fewer_taps_than_intended):
                    continue

                reason = "valid route differs from intended route"
                if shorter_than_intended or fewer_taps_than_intended:
                    reason = "valid route uses fewer required route phases or taps than intended"
                elif tap_order_differs:
                    reason = "valid route bypasses required tap order"
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="shortcut_path_detected",
                        message=f"Shortcut validation found {reason}; sample={self._summary_text(summary)}.",
                        related_edge_id=summary.edge_ids[-1] if summary.edge_ids else None,
                    )
                )
                break

        return tuple(issues)

    def validateNoShortcutPath(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        return self.validate_no_shortcut_path(generated_level, enumeration)

    def validate_wrong_branches_fail_correctly(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        if enumeration is None:
            enumeration = self._enumerate_solutions(
                generated_level,
                self._initial_state(generated_level),
                self._config(generated_level, self._topology_rules(generated_level)),
            )

        branch_edge_ids = set(self._off_route_branch_edge_ids(generated_level))
        if not branch_edge_ids:
            return ()

        issues: list[UniqueSolutionValidationIssue] = []
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        node_by_id = {node.id: node for node in level.graph.nodes}
        for edge_id in sorted(branch_edge_ids):
            edge = edge_by_id.get(edge_id)
            if edge is None or not self._looks_like_dead_end(edge.toNodeID):
                continue
            target_node = node_by_id.get(edge.toNodeID)
            if target_node is None:
                continue
            if self._valid_outgoing_edge_ids(target_node, edge_by_id):
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="wrong_branch_dead_end_continues",
                        message=(
                            f"Wrong-branch validation expected '{edge.toNodeID}' to terminate, "
                            "but it has outgoing route edges."
                        ),
                        related_node_id=edge.toNodeID,
                        related_edge_id=edge_id,
                    )
                )
                break

        for summary in enumeration.successful_path_summaries:
            branch_edge_id = self._first_branch_edge_id(summary, branch_edge_ids)
            if branch_edge_id is None:
                continue
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="wrong_branch_reached_goal",
                    message=(
                        "Wrong-branch validation found an off-route branch that reaches destination "
                        f"as a valid solution; sample={self._summary_text(summary)}."
                    ),
                    related_edge_id=branch_edge_id,
                )
            )
            break

        if not any(issue.code == "wrong_branch_reached_goal" for issue in issues):
            for summary in enumeration.destination_before_package_summaries:
                branch_edge_id = self._first_branch_edge_id(summary, branch_edge_ids)
                if branch_edge_id is None:
                    continue
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="wrong_branch_reached_goal",
                        message=(
                            "Wrong-branch validation found an off-route branch that reaches destination "
                            f"before package collection; sample={self._summary_text(summary)}."
                        ),
                        related_edge_id=branch_edge_id,
                    )
                )
                break

        ambiguous_reasons = {"max_traversal_depth_reached", "max_taps_reached"}
        for summary in enumeration.failure_path_summaries:
            if summary.terminal_reason not in ambiguous_reasons:
                continue
            branch_edge_id = self._first_branch_edge_id(summary, branch_edge_ids)
            if branch_edge_id is None:
                continue
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="wrong_branch_ambiguous_termination",
                    message=(
                        "Wrong-branch validation found an off-route branch that does not clearly dead-end "
                        f"or fail before a search limit; sample={self._summary_text(summary)}."
                    ),
                    related_edge_id=branch_edge_id,
                )
            )
            break

        return tuple(issues)

    def validateWrongBranchesFailCorrectly(
        self,
        generated_level,
        enumeration: _EnumerationResult | None = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        return self.validate_wrong_branches_fail_correctly(generated_level, enumeration)

    def _issues_for_result(self, result: "_EnumerationResult") -> tuple[UniqueSolutionValidationIssue, ...]:
        if result.solution_count > 1:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_multiple_solutions",
                    message=(
                        "Unique solution search found more than one valid package-before-destination solution "
                        f"(solutions={result.solution_count}, exploredStates={result.explored_states})."
                    ),
                ),
            )
        if not result.is_exhaustive:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_search_limit_reached",
                    message=(
                        "Unique solution search hit a traversal limit before proving uniqueness "
                        f"(solutions={result.solution_count}, exploredStates={result.explored_states}, "
                        f"maxDepthReached={result.max_depth_reached}, termination={result.termination_reason})."
                    ),
                ),
            )
        if result.solution_count == 0:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_not_found",
                    message=(
                        "Unique solution search found no valid package-before-destination solution "
                        f"(exploredStates={result.explored_states})."
                    ),
                ),
            )
        return ()

    def _path_summary(
        self,
        state: UniqueSolutionSearchState,
        reason: str,
        level,
    ) -> UniqueSolutionPathSummary:
        package_index = self._first_index(state.visited_node_ids, level.packageNodeID)
        destination_index = self._first_index(state.visited_node_ids, level.destinationNodeID)
        return UniqueSolutionPathSummary(
            terminal_reason=reason,
            node_ids=state.visited_node_ids,
            edge_ids=state.traversed_edge_ids,
            tap_history=state.tap_history,
            has_collected_package=state.has_collected_package,
            traversal_depth=state.traversal_depth,
            package_index=package_index,
            destination_index=destination_index,
        )

    def _append_path_summary(
        self,
        summaries: list[UniqueSolutionPathSummary],
        summary: UniqueSolutionPathSummary,
    ) -> None:
        if len(summaries) < self.path_summary_limit:
            summaries.append(summary)

    def _first_index(self, values: tuple[str, ...], needle: str) -> int | None:
        try:
            return values.index(needle)
        except ValueError:
            return None

    def _terminal_count(self, result: "_EnumerationResult", reason: str) -> int:
        return dict(result.terminal_reason_counts).get(reason, 0)

    def _intended_route(self, generated_level) -> tuple[str, ...]:
        solution = getattr(generated_level, "solution", None)
        metadata = dict(getattr(solution, "_extra", {}).get("metadata", {})) if solution is not None else {}
        route = metadata.get("solutionRoute") or []
        if route:
            return tuple(str(node_id) for node_id in route)
        abstract = getattr(generated_level, "abstract_solution_metadata", None)
        abstract_route = getattr(abstract, "required_path", ()) if abstract is not None else ()
        if abstract_route:
            return tuple(str(node_id) for node_id in abstract_route)
        return ()

    def _intended_tap_order(self, generated_level) -> tuple[str, ...]:
        solution = getattr(generated_level, "solution", None)
        metadata = dict(getattr(solution, "_extra", {}).get("metadata", {})) if solution is not None else {}
        tap_order = metadata.get("requiredTapOrder") or []
        if tap_order:
            return tuple(str(node_id) for node_id in tap_order)
        abstract = getattr(generated_level, "abstract_solution_metadata", None)
        abstract_taps = getattr(abstract, "solution_tap_node_ids", ()) if abstract is not None else ()
        if abstract_taps:
            return tuple(str(node_id) for node_id in abstract_taps)
        if solution is None:
            return ()
        return tuple(action.tapNodeID for action in getattr(solution, "actions", ()) or ())

    def _package_required(self, generated_level) -> bool:
        level = generated_level.level_document
        return bool(level.packageNodeID) and level.packageNodeID != level.destinationNodeID

    def _metadata_requires_package_gate(self, generated_level) -> bool:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        topology_rules = metadata.get("topologyRules")
        if isinstance(topology_rules, dict) and topology_rules.get("requiresPackageGate") is True:
            return True
        if metadata.get("requiresPackageGate") is True:
            return True
        tags = set(getattr(generated_level, "mechanic_tags", ()) or ())
        tags.update(str(tag) for tag in metadata.get("mechanicTags", []) if isinstance(tag, str))
        return "package_gate" in tags

    def _package_reachability_status(
        self,
        generated_level,
        intended_route: tuple[str, ...],
    ) -> str:
        level = generated_level.level_document
        node_ids = {node.id for node in level.graph.nodes}
        if not self._package_required(generated_level):
            return "package_not_required"
        if level.packageNodeID == level.destinationNodeID:
            return "package_and_destination_not_distinct"
        if level.packageNodeID not in node_ids:
            return "package_node_missing"
        if level.destinationNodeID not in node_ids:
            return "destination_node_missing"
        if not intended_route:
            return "intended_route_missing"
        if level.packageNodeID not in intended_route:
            return "package_missing_from_intended_route"
        if level.destinationNodeID not in intended_route:
            return "destination_missing_from_intended_route"
        if intended_route.count(level.packageNodeID) > 1:
            return "package_repeated_on_intended_route"
        if intended_route.count(level.destinationNodeID) > 1:
            return "destination_repeated_on_intended_route"

        package_index = intended_route.index(level.packageNodeID)
        destination_index = intended_route.index(level.destinationNodeID)
        if package_index > destination_index:
            return "destination_before_package_on_intended_route"
        missing_edges = self._missing_intended_route_edges(generated_level, intended_route)
        if missing_edges:
            return "intended_route_edges_missing"
        return "package_before_destination_on_intended_route"

    def _missing_intended_route_edges(
        self,
        generated_level,
        intended_route: tuple[str, ...],
    ) -> tuple[tuple[str, str], ...]:
        edge_pairs = {
            (edge.fromNodeID, edge.toNodeID)
            for edge in generated_level.level_document.graph.edges
        }
        return tuple(
            (from_node_id, to_node_id)
            for from_node_id, to_node_id in zip(intended_route, intended_route[1:])
            if (from_node_id, to_node_id) not in edge_pairs
        )

    def _first_non_intended_success(
        self,
        result: "_EnumerationResult",
        intended_route: tuple[str, ...],
        intended_taps: tuple[str, ...],
    ) -> UniqueSolutionPathSummary | None:
        for summary in result.successful_path_summaries:
            if summary.node_ids != intended_route or summary.tap_history != intended_taps:
                return summary
        return result.successful_path_summaries[0] if result.successful_path_summaries else None

    def _off_route_branch_edge_ids(self, generated_level) -> tuple[str, ...]:
        intended_route = self._intended_route(generated_level)
        if not intended_route:
            return ()
        route_nodes = set(intended_route)
        route_edges = set(zip(intended_route, intended_route[1:]))
        branch_edge_ids: list[str] = []
        for edge in generated_level.level_document.graph.edges:
            if edge.fromNodeID not in route_nodes:
                continue
            if (edge.fromNodeID, edge.toNodeID) in route_edges:
                continue
            branch_edge_ids.append(edge.id)
        return tuple(branch_edge_ids)

    def _first_branch_edge_id(
        self,
        summary: UniqueSolutionPathSummary,
        branch_edge_ids: set[str],
    ) -> str | None:
        for edge_id in summary.edge_ids:
            if edge_id in branch_edge_ids:
                return edge_id
        return None

    def _looks_like_dead_end(self, node_id: str) -> bool:
        lowered = node_id.lower()
        return (
            "dead_end" in lowered
            or lowered.startswith("wrong")
            or lowered.endswith("_dead_end")
        )

    def _wrong_branch_reached_goal(
        self,
        generated_level,
        result: "_EnumerationResult",
    ) -> bool:
        branch_edge_ids = set(self._off_route_branch_edge_ids(generated_level))
        if not branch_edge_ids:
            return False
        goal_summaries = (
            *result.successful_path_summaries,
            *result.destination_before_package_summaries,
        )
        return any(self._first_branch_edge_id(summary, branch_edge_ids) is not None for summary in goal_summaries)

    def _summary_text(self, summary: UniqueSolutionPathSummary | None) -> str:
        if summary is None:
            return "unavailable"
        nodes = list(summary.node_ids)
        if len(nodes) > 8:
            nodes = [*nodes[:4], "...", *nodes[-3:]]
        taps = ",".join(summary.tap_history) if summary.tap_history else "none"
        return (
            f"{' -> '.join(nodes)} "
            f"(reason={summary.terminal_reason}, routeLength={summary.route_length}, taps={taps})"
        )

    def _valid_outgoing_edge_ids(self, node, edge_by_id: dict[str, Any]) -> list[str]:
        return [
            edge_id
            for edge_id in node.outgoingEdgeIDs
            if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
        ]

    def _tap_options(self, valid_edge_ids: list[str]) -> range:
        if len(valid_edge_ids) <= 1:
            return range(1)
        return range(len(valid_edge_ids))

    def _rotated_edge_id(
        self,
        current_edge_id: str | None,
        valid_edge_ids: list[str],
        tap_count: int,
    ) -> str | None:
        if not valid_edge_ids:
            return None
        current_index = (
            valid_edge_ids.index(current_edge_id)
            if current_edge_id in valid_edge_ids
            else 0
        )
        return valid_edge_ids[(current_index + tap_count) % len(valid_edge_ids)]


@dataclass(frozen=True)
class _EnumerationResult:
    solution_count: int
    explored_states: int
    max_depth_reached: int
    termination_reason: str
    terminal_reason_counts: tuple[tuple[str, int], ...]
    is_exhaustive: bool
    notes: tuple[str, ...]
    successful_path_summaries: tuple[UniqueSolutionPathSummary, ...]
    destination_before_package_summaries: tuple[UniqueSolutionPathSummary, ...]
    failure_path_summaries: tuple[UniqueSolutionPathSummary, ...]
    shortest_valid_route_length: int | None
