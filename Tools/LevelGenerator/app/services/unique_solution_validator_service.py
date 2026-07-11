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
    rejoin_detected: bool = False
    rejoin_count: int = 0
    declared_rejoin_count: int = 0
    unsafe_rejoin_detected: bool = False
    unsafe_rejoin_reason: str | None = None
    revisit_detected: bool = False
    revisit_count: int = 0
    declared_revisit_count: int = 0
    unsafe_revisit_detected: bool = False
    unsafe_revisit_reason: str | None = None
    repeated_node_ids: tuple[str, ...] = field(default_factory=tuple)
    repeated_switch_ids: tuple[str, ...] = field(default_factory=tuple)
    max_visit_count_by_node: tuple[tuple[str, int], ...] = field(default_factory=tuple)


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
        rejoin_detection = self._detect_rejoins(generated_level, intended_route)
        revisit_detection = self._detect_revisits(generated_level, intended_route)
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
                rejoin_detected=bool(rejoin_detection.node_ids),
                rejoin_count=len(rejoin_detection.node_ids),
                declared_rejoin_count=rejoin_detection.declared_count,
                revisit_detected=bool(revisit_detection.repeated_node_ids),
                revisit_count=revisit_detection.revisit_count,
                declared_revisit_count=revisit_detection.declared_count,
                repeated_node_ids=revisit_detection.repeated_node_ids,
                repeated_switch_ids=revisit_detection.repeated_switch_ids,
                max_visit_count_by_node=revisit_detection.max_visit_count_by_node,
            )

        enumeration = self._enumerate_solutions(generated_level, initial_state, config)
        max_visit_count_by_node = self._max_visit_count_by_node(
            revisit_detection.max_visit_count_by_node,
            enumeration,
        )
        package_issues = self.validate_package_before_goal(generated_level, enumeration)
        shortcut_issues = self.validate_no_shortcut_path(generated_level, enumeration)
        wrong_branch_issues = self.validate_wrong_branches_fail_correctly(generated_level, enumeration)
        rejoin_issues = self.validate_declared_rejoins(generated_level, enumeration, rejoin_detection)
        revisit_issues = self.validate_declared_revisits(generated_level, enumeration, revisit_detection)
        unique_issues = self._issues_for_result(enumeration) if requires_unique_solution else ()
        issues = (
            *unique_issues,
            *package_issues,
            *shortcut_issues,
            *wrong_branch_issues,
            *rejoin_issues,
            *revisit_issues,
        )
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
            rejoin_detected=bool(rejoin_detection.node_ids),
            rejoin_count=len(rejoin_detection.node_ids),
            declared_rejoin_count=rejoin_detection.declared_count,
            unsafe_rejoin_detected=bool(rejoin_issues),
            unsafe_rejoin_reason=self._first_issue_code(rejoin_issues),
            revisit_detected=bool(revisit_detection.repeated_node_ids),
            revisit_count=revisit_detection.revisit_count,
            declared_revisit_count=revisit_detection.declared_count,
            unsafe_revisit_detected=bool(revisit_issues),
            unsafe_revisit_reason=self._first_issue_code(revisit_issues),
            repeated_node_ids=revisit_detection.repeated_node_ids,
            repeated_switch_ids=revisit_detection.repeated_switch_ids,
            max_visit_count_by_node=max_visit_count_by_node,
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

    def validate_declared_rejoins(
        self,
        generated_level,
        enumeration: "_EnumerationResult | None" = None,
        detection: "_RejoinDetection | None" = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        if detection is None:
            detection = self._detect_rejoins(generated_level)
        if not detection.node_ids:
            return ()
        if enumeration is None:
            enumeration = self._enumerate_solutions(
                generated_level,
                self._initial_state(generated_level),
                self._config(generated_level, self._topology_rules(generated_level)),
            )

        topology_rules = self._topology_rules(generated_level)
        topology_rules_metadata = self._topology_rules_metadata(generated_level)
        if topology_rules_metadata is None:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="topology_rules_missing_for_declared_rejoin_validation",
                    message=(
                        "Rejoin validation found converging route segments, but topologyRules metadata is missing "
                        f"(rejoinCount={len(detection.node_ids)}, nodes={', '.join(detection.node_ids)})."
                    ),
                    related_node_id=detection.node_ids[0],
                ),
            )
        if not bool(topology_rules.get("allowsRejoin", False)):
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="undeclared_rejoin",
                    message=(
                        "Rejoin validation found converging route segments, but the recipe does not allow rejoins "
                        f"(nodes={', '.join(detection.node_ids)})."
                    ),
                    related_node_id=detection.node_ids[0],
                ),
            )

        issues: list[UniqueSolutionValidationIssue] = []
        if detection.declared_count_is_explicit and len(detection.node_ids) > detection.declared_count:
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_rejoin_count_exceeds_metadata",
                    message=(
                        "Rejoin validation found more converging nodes than declared "
                        f"(actual={len(detection.node_ids)}, declared={detection.declared_count})."
                    ),
                    related_node_id=detection.node_ids[0],
                )
            )

        if detection.declared_node_ids is not None and set(detection.declared_node_ids) != set(detection.node_ids):
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_rejoin_metadata_node_mismatch",
                    message=(
                        "Declared rejoin node metadata does not match the graph "
                        f"(actual={', '.join(detection.node_ids)}, "
                        f"declared={', '.join(detection.declared_node_ids) or 'none'})."
                    ),
                    related_node_id=detection.node_ids[0],
                )
            )

        issues.extend(self._rejoin_safety_issues(generated_level, enumeration, detection))
        return tuple(issues)

    def validateDeclaredRejoins(
        self,
        generated_level,
        enumeration: "_EnumerationResult | None" = None,
        detection: "_RejoinDetection | None" = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        return self.validate_declared_rejoins(generated_level, enumeration, detection)

    def validate_declared_revisits(
        self,
        generated_level,
        enumeration: "_EnumerationResult | None" = None,
        detection: "_RevisitDetection | None" = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        if detection is None:
            detection = self._detect_revisits(generated_level)
        if not detection.repeated_node_ids:
            return ()
        if enumeration is None:
            enumeration = self._enumerate_solutions(
                generated_level,
                self._initial_state(generated_level),
                self._config(generated_level, self._topology_rules(generated_level)),
            )

        topology_rules = self._topology_rules(generated_level)
        topology_rules_metadata = self._topology_rules_metadata(generated_level)
        if topology_rules_metadata is None:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="topology_rules_missing_for_declared_revisit_validation",
                    message=(
                        "Revisit validation found repeated intended-route nodes, but topologyRules metadata is missing "
                        f"(revisitCount={detection.revisit_count}, nodes={', '.join(detection.repeated_node_ids)})."
                    ),
                    related_node_id=detection.repeated_node_ids[0],
                ),
            )
        if not bool(topology_rules.get("allowsRevisit", False)):
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="undeclared_revisit",
                    message=(
                        "Revisit validation found repeated intended-route nodes, but the recipe does not allow revisits "
                        f"(nodes={', '.join(detection.repeated_node_ids)})."
                    ),
                    related_node_id=detection.repeated_node_ids[0],
                ),
            )

        issues: list[UniqueSolutionValidationIssue] = []
        if detection.declared_count_is_explicit and detection.revisit_count > detection.declared_count:
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_revisit_count_exceeds_metadata",
                    message=(
                        "Revisit validation found more repeated route visits than declared "
                        f"(actual={detection.revisit_count}, declared={detection.declared_count})."
                    ),
                    related_node_id=detection.repeated_node_ids[0],
                )
            )

        if (
            detection.declared_node_ids is not None
            and set(detection.declared_node_ids) != set(detection.repeated_node_ids)
        ):
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_revisit_metadata_node_mismatch",
                    message=(
                        "Declared revisit node metadata does not match the intended route "
                        f"(actual={', '.join(detection.repeated_node_ids)}, "
                        f"declared={', '.join(detection.declared_node_ids) or 'none'})."
                    ),
                    related_node_id=detection.repeated_node_ids[0],
                )
            )

        if detection.repeated_tap_node_ids and not self._allows_repeated_taps(generated_level):
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_revisit_repeated_taps_not_allowed",
                    message=(
                        "Revisit validation found repeated switch taps, but recipe metadata does not allow them "
                        f"(nodes={', '.join(detection.repeated_tap_node_ids)})."
                    ),
                    related_node_id=detection.repeated_tap_node_ids[0],
                )
            )

        issues.extend(self._revisit_safety_issues(generated_level, enumeration, detection))
        return tuple(issues)

    def validateDeclaredRevisits(
        self,
        generated_level,
        enumeration: "_EnumerationResult | None" = None,
        detection: "_RevisitDetection | None" = None,
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        return self.validate_declared_revisits(generated_level, enumeration, detection)

    def _detect_rejoins(
        self,
        generated_level,
        intended_route: tuple[str, ...] | None = None,
    ) -> "_RejoinDetection":
        level = generated_level.level_document
        route = intended_route if intended_route is not None else self._intended_route(generated_level)
        route_counts = Counter(route)
        incoming: dict[str, list[Any]] = {}
        outgoing: dict[str, list[str]] = {}
        for edge in level.graph.edges:
            incoming.setdefault(edge.toNodeID, []).append(edge)
            outgoing.setdefault(edge.fromNodeID, []).append(edge.toNodeID)

        rejoin_node_ids: list[str] = []
        for node_id, incoming_edges in incoming.items():
            if node_id == level.startNodeID or route_counts.get(node_id, 0) > 1:
                continue
            non_cycle_sources = {
                edge.fromNodeID
                for edge in incoming_edges
                if not self._can_reach(node_id, edge.fromNodeID, outgoing)
            }
            if len(non_cycle_sources) >= 2:
                rejoin_node_ids.append(node_id)

        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        declared_node_ids = self._declared_node_ids(
            metadata,
            ("declaredRejoinNodeIDs", "rejoinNodeIDs"),
        )
        declared_count, count_is_explicit = self._declared_count(
            metadata,
            ("declaredRejoinCount", "allowedRejoinCount", "rejoinCount"),
            declared_node_ids,
            fallback_count=len(rejoin_node_ids) if self._topology_rules(generated_level).get("allowsRejoin") else 0,
        )
        return _RejoinDetection(
            node_ids=tuple(sorted(rejoin_node_ids)),
            declared_count=declared_count,
            declared_count_is_explicit=count_is_explicit,
            declared_node_ids=declared_node_ids,
        )

    def _detect_revisits(
        self,
        generated_level,
        intended_route: tuple[str, ...] | None = None,
    ) -> "_RevisitDetection":
        route = intended_route if intended_route is not None else self._intended_route(generated_level)
        visit_counts = Counter(route)
        repeated_node_ids = tuple(sorted(node_id for node_id, count in visit_counts.items() if count > 1))
        revisit_count = sum(count - 1 for count in visit_counts.values() if count > 1)
        switch_node_ids = self._switch_node_ids(generated_level)
        tap_counts = Counter(self._intended_tap_order(generated_level))
        repeated_tap_node_ids = tuple(sorted(node_id for node_id, count in tap_counts.items() if count > 1))
        repeated_switch_ids = tuple(
            sorted(
                {
                    node_id
                    for node_id in repeated_node_ids
                    if node_id in switch_node_ids
                }
                | set(repeated_tap_node_ids)
            )
        )
        max_visit_count_by_node = tuple(sorted((node_id, count) for node_id, count in visit_counts.items()))

        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        declared_node_ids = self._declared_node_ids(
            metadata,
            ("declaredRevisitNodeIDs", "revisitNodeIDs", "repeatedNodeIDs"),
        )
        declared_count, count_is_explicit = self._declared_count(
            metadata,
            ("declaredRevisitCount", "allowedRevisitCount", "revisitCount"),
            declared_node_ids,
            fallback_count=revisit_count if self._topology_rules(generated_level).get("allowsRevisit") else 0,
        )
        return _RevisitDetection(
            repeated_node_ids=repeated_node_ids,
            repeated_switch_ids=repeated_switch_ids,
            repeated_tap_node_ids=repeated_tap_node_ids,
            max_visit_count_by_node=max_visit_count_by_node,
            revisit_count=revisit_count,
            declared_count=declared_count,
            declared_count_is_explicit=count_is_explicit,
            declared_node_ids=declared_node_ids,
        )

    def _rejoin_safety_issues(
        self,
        generated_level,
        enumeration: "_EnumerationResult",
        detection: "_RejoinDetection",
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        issues: list[UniqueSolutionValidationIssue] = []
        rejoin_nodes = set(detection.node_ids)
        bypass_summary = self._first_summary_through_nodes(
            enumeration.destination_before_package_summaries,
            rejoin_nodes,
        )
        if bypass_summary is not None:
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_rejoin_package_bypass_detected",
                    message=(
                        "Declared rejoin allows the destination to be reached before package collection; "
                        f"sample={self._summary_text(bypass_summary)}."
                    ),
                    related_node_id=self._first_matching_node(bypass_summary, rejoin_nodes),
                    related_edge_id=bypass_summary.edge_ids[-1] if bypass_summary.edge_ids else None,
                )
            )

        intended_route = self._intended_route(generated_level)
        intended_taps = self._intended_tap_order(generated_level)
        non_intended_summary = self._first_non_intended_success(enumeration, intended_route, intended_taps)
        if enumeration.solution_count > 1 and self._summary_visits_any(non_intended_summary, rejoin_nodes):
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_rejoin_multiple_solutions",
                    message=(
                        "Declared rejoin participates in more than one valid package-before-destination route "
                        f"(solutions={enumeration.solution_count}); sample={self._summary_text(non_intended_summary)}."
                    ),
                    related_node_id=self._first_matching_node(non_intended_summary, rejoin_nodes),
                    related_edge_id=(
                        non_intended_summary.edge_ids[-1]
                        if non_intended_summary and non_intended_summary.edge_ids
                        else None
                    ),
                )
            )
        elif enumeration.solution_count <= 1:
            shortcut_summary = self._first_shortcut_success(enumeration, intended_route, intended_taps)
            if self._summary_visits_any(shortcut_summary, rejoin_nodes):
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="declared_rejoin_shortcut_detected",
                        message=(
                            "Declared rejoin participates in a valid route that differs from the intended route; "
                            f"sample={self._summary_text(shortcut_summary)}."
                        ),
                        related_node_id=self._first_matching_node(shortcut_summary, rejoin_nodes),
                        related_edge_id=(
                            shortcut_summary.edge_ids[-1]
                            if shortcut_summary and shortcut_summary.edge_ids
                            else None
                        ),
                    )
                )

        if not enumeration.is_exhaustive:
            limited_summary = self._first_summary_through_nodes(
                enumeration.failure_path_summaries,
                rejoin_nodes,
                terminal_reasons={"max_traversal_depth_reached", "max_taps_reached"},
            )
            if limited_summary is not None:
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="declared_rejoin_search_limit_reached",
                        message=(
                            "Declared rejoin participates in a path that hit traversal limits before validation "
                            f"could prove safety; sample={self._summary_text(limited_summary)}."
                        ),
                        related_node_id=self._first_matching_node(limited_summary, rejoin_nodes),
                        related_edge_id=limited_summary.edge_ids[-1] if limited_summary.edge_ids else None,
                    )
                )

        return tuple(issues)

    def _revisit_safety_issues(
        self,
        generated_level,
        enumeration: "_EnumerationResult",
        detection: "_RevisitDetection",
    ) -> tuple[UniqueSolutionValidationIssue, ...]:
        issues: list[UniqueSolutionValidationIssue] = []
        repeated_nodes = set(detection.repeated_node_ids)
        bypass_summary = self._first_summary_through_nodes(
            enumeration.destination_before_package_summaries,
            repeated_nodes,
        )
        if bypass_summary is not None:
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_revisit_package_bypass_detected",
                    message=(
                        "Declared revisit allows the destination to be reached before package collection; "
                        f"sample={self._summary_text(bypass_summary)}."
                    ),
                    related_node_id=self._first_matching_node(bypass_summary, repeated_nodes),
                    related_edge_id=bypass_summary.edge_ids[-1] if bypass_summary.edge_ids else None,
                )
            )

        intended_route = self._intended_route(generated_level)
        intended_taps = self._intended_tap_order(generated_level)
        non_intended_summary = self._first_non_intended_success(enumeration, intended_route, intended_taps)
        if enumeration.solution_count > 1 and self._summary_visits_any(non_intended_summary, repeated_nodes):
            issues.append(
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="declared_revisit_multiple_solutions",
                    message=(
                        "Declared revisit participates in more than one valid package-before-destination route "
                        f"(solutions={enumeration.solution_count}); sample={self._summary_text(non_intended_summary)}."
                    ),
                    related_node_id=self._first_matching_node(non_intended_summary, repeated_nodes),
                    related_edge_id=(
                        non_intended_summary.edge_ids[-1]
                        if non_intended_summary and non_intended_summary.edge_ids
                        else None
                    ),
                )
            )
        elif enumeration.solution_count <= 1:
            shortcut_summary = self._first_shortcut_success(enumeration, intended_route, intended_taps)
            if self._summary_visits_any(shortcut_summary, repeated_nodes):
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="declared_revisit_shortcut_detected",
                        message=(
                            "Declared revisit participates in a valid route that differs from the intended route; "
                            f"sample={self._summary_text(shortcut_summary)}."
                        ),
                        related_node_id=self._first_matching_node(shortcut_summary, repeated_nodes),
                        related_edge_id=(
                            shortcut_summary.edge_ids[-1]
                            if shortcut_summary and shortcut_summary.edge_ids
                            else None
                        ),
                    )
                )

        if not enumeration.is_exhaustive:
            limited_summary = self._first_summary_through_nodes(
                enumeration.failure_path_summaries,
                repeated_nodes,
                terminal_reasons={"max_traversal_depth_reached", "max_taps_reached"},
            )
            if limited_summary is not None:
                issues.append(
                    UniqueSolutionValidationIssue(
                        severity="error",
                        code="declared_revisit_infinite_traversal_risk",
                        message=(
                            "Declared revisit reaches a traversal limit before validation can prove bounded behavior; "
                            f"sample={self._summary_text(limited_summary)}."
                        ),
                        related_node_id=self._first_matching_node(limited_summary, repeated_nodes),
                        related_edge_id=limited_summary.edge_ids[-1] if limited_summary.edge_ids else None,
                    )
                )

        return tuple(issues)

    def _first_shortcut_success(
        self,
        result: "_EnumerationResult",
        intended_route: tuple[str, ...],
        intended_taps: tuple[str, ...],
    ) -> UniqueSolutionPathSummary | None:
        if not intended_route:
            return None
        intended_route_length = max(0, len(intended_route) - 1) if intended_route else None
        for summary in result.successful_path_summaries:
            path_differs = summary.node_ids != intended_route
            tap_order_differs = summary.tap_history != intended_taps
            shorter_than_intended = (
                intended_route_length is not None
                and summary.route_length < intended_route_length
            )
            fewer_taps_than_intended = len(summary.tap_history) < len(intended_taps)
            if path_differs or tap_order_differs or shorter_than_intended or fewer_taps_than_intended:
                return summary
        return None

    def _first_summary_through_nodes(
        self,
        summaries: tuple[UniqueSolutionPathSummary, ...],
        node_ids: set[str],
        terminal_reasons: set[str] | None = None,
    ) -> UniqueSolutionPathSummary | None:
        for summary in summaries:
            if terminal_reasons is not None and summary.terminal_reason not in terminal_reasons:
                continue
            if self._summary_visits_any(summary, node_ids):
                return summary
        return None

    def _summary_visits_any(
        self,
        summary: UniqueSolutionPathSummary | None,
        node_ids: set[str],
    ) -> bool:
        if summary is None:
            return False
        return any(node_id in node_ids for node_id in summary.node_ids)

    def _first_matching_node(
        self,
        summary: UniqueSolutionPathSummary | None,
        node_ids: set[str],
    ) -> str | None:
        if summary is None:
            return next(iter(sorted(node_ids)), None)
        return next((node_id for node_id in summary.node_ids if node_id in node_ids), None)

    def _can_reach(self, start_id: str, target_id: str, outgoing: dict[str, list[str]]) -> bool:
        if start_id == target_id:
            return True
        stack = [start_id]
        visited: set[str] = set()
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            visited.add(current_id)
            for next_id in outgoing.get(current_id, ()):
                if next_id == target_id:
                    return True
                if next_id not in visited:
                    stack.append(next_id)
        return False

    def _switch_node_ids(self, generated_level) -> set[str]:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        return {
            node.id
            for node in level.graph.nodes
            if len(self._valid_outgoing_edge_ids(node, edge_by_id)) > 1
        }

    def _declared_count(
        self,
        metadata: dict[str, Any],
        count_keys: tuple[str, ...],
        declared_node_ids: tuple[str, ...] | None,
        fallback_count: int,
    ) -> tuple[int, bool]:
        for key in count_keys:
            value = metadata.get(key)
            if isinstance(value, int) and value >= 0:
                return value, True
        if declared_node_ids is not None:
            return len(declared_node_ids), True
        return fallback_count, False

    def _declared_node_ids(
        self,
        metadata: dict[str, Any],
        keys: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, (list, tuple)):
                return tuple(sorted(str(node_id) for node_id in value))
        return None

    def _topology_rules_metadata(self, generated_level) -> dict[str, Any] | None:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        topology_rules = metadata.get("topologyRules")
        return dict(topology_rules) if isinstance(topology_rules, dict) else None

    def _allows_repeated_taps(self, generated_level) -> bool:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        return metadata.get("allowsRepeatedTaps") is True

    def _first_issue_code(self, issues: tuple[UniqueSolutionValidationIssue, ...]) -> str | None:
        return issues[0].code if issues else None

    def _max_visit_count_by_node(
        self,
        base_counts: tuple[tuple[str, int], ...],
        result: "_EnumerationResult",
    ) -> tuple[tuple[str, int], ...]:
        counts = dict(base_counts)
        for summary in (
            *result.successful_path_summaries,
            *result.destination_before_package_summaries,
            *result.failure_path_summaries,
        ):
            for node_id, count in Counter(summary.node_ids).items():
                counts[node_id] = max(counts.get(node_id, 0), count)
        return tuple(sorted(counts.items()))

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
        abstract_decisions = getattr(abstract, "decision_node_ids", ()) if abstract is not None else ()
        if abstract_decisions:
            return tuple(str(node_id) for node_id in abstract_decisions)
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


@dataclass(frozen=True)
class _RejoinDetection:
    node_ids: tuple[str, ...]
    declared_count: int
    declared_count_is_explicit: bool
    declared_node_ids: tuple[str, ...] | None


@dataclass(frozen=True)
class _RevisitDetection:
    repeated_node_ids: tuple[str, ...]
    repeated_switch_ids: tuple[str, ...]
    repeated_tap_node_ids: tuple[str, ...]
    max_visit_count_by_node: tuple[tuple[str, int], ...]
    revisit_count: int
    declared_count: int
    declared_count_is_explicit: bool
    declared_node_ids: tuple[str, ...] | None
