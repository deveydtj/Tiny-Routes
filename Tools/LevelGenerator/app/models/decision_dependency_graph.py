"""Decision dependency DAG for graph-independent V3 puzzle blueprints."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DecisionDependencyKind(str, Enum):
    """Supported reasons why a blueprint decision is not independent."""

    OBJECTIVE_STATE = "objectiveState"
    EARLIER_CHOICE = "earlierChoice"
    REVISIT = "revisit"


@dataclass(frozen=True)
class DecisionNode:
    """One decision occurrence; revisits use a new ID in a later phase."""

    id: str
    sequence_index: int
    phase_index: int
    switch_role: str
    outgoing_edge_roles: tuple[str, ...]
    required_outgoing_edge_role: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outgoing_edge_roles", tuple(self.outgoing_edge_roles))


@dataclass(frozen=True)
class DecisionDependency:
    """A typed prerequisite directed from ``source_id`` to ``target_id``.

    For objective-state dependencies, ``source_id`` is an objective ID. For
    earlier-choice and revisit dependencies it is a decision ID.
    """

    source_id: str
    target_id: str
    kind: DecisionDependencyKind
    required_source_outgoing_edge_role: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DecisionDependencyKind):
            object.__setattr__(self, "kind", DecisionDependencyKind(self.kind))


@dataclass(frozen=True)
class DecisionDependencyGraph:
    """A deterministic, validated description of strategic dependencies."""

    decisions: tuple[DecisionNode, ...]
    dependencies: tuple[DecisionDependency, ...] = ()
    objective_phase_indices: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(
            self,
            "objective_phase_indices",
            tuple(tuple(item) for item in self.objective_phase_indices),
        )

    @property
    def independent_decision_ids(self) -> tuple[str, ...]:
        dependent_ids = {dependency.target_id for dependency in self.dependencies}
        return tuple(
            decision.id
            for decision in self.decisions
            if decision.id not in dependent_ids
        )

    @property
    def dependency_depth(self) -> int:
        """Return the longest realizable decision chain, measured in decisions."""

        if not self.decisions:
            return 0

        known = {decision.id for decision in self.decisions}
        predecessors: dict[str, list[str]] = {decision_id: [] for decision_id in known}
        for dependency in self.dependencies:
            if (
                dependency.kind is not DecisionDependencyKind.OBJECTIVE_STATE
                and dependency.source_id in known
                and dependency.target_id in known
            ):
                predecessors[dependency.target_id].append(dependency.source_id)

        cache: dict[str, int] = {}
        visiting: set[str] = set()

        def depth(decision_id: str) -> int:
            if decision_id in cache:
                return cache[decision_id]
            if decision_id in visiting:
                # Invalid cycles are reported by validate(); keep this property
                # total so diagnostics can still inspect malformed blueprints.
                return 0
            visiting.add(decision_id)
            result = 1 + max(
                (depth(source_id) for source_id in predecessors[decision_id]),
                default=0,
            )
            visiting.remove(decision_id)
            cache[decision_id] = result
            return result

        return max(depth(decision.id) for decision in self.decisions)

    @property
    def is_realizable(self) -> bool:
        return not self.validate()

    def validate(self) -> tuple[str, ...]:
        """Return stable issue codes for malformed or unrealizable dependencies."""

        issues: list[str] = []
        decisions_by_id: dict[str, DecisionNode] = {}
        sequence_indices: set[int] = set()

        for decision in self.decisions:
            if not decision.id.strip():
                issues.append("decision_id_empty")
                continue
            if decision.id in decisions_by_id:
                issues.append(f"decision_id_duplicate:{decision.id}")
                continue
            decisions_by_id[decision.id] = decision

            if (
                not isinstance(decision.sequence_index, int)
                or isinstance(decision.sequence_index, bool)
                or decision.sequence_index < 0
            ):
                issues.append(f"decision_sequence_index_invalid:{decision.id}")
            elif decision.sequence_index in sequence_indices:
                issues.append(
                    f"decision_sequence_index_duplicate:{decision.sequence_index}"
                )
            else:
                sequence_indices.add(decision.sequence_index)
            if (
                not isinstance(decision.phase_index, int)
                or isinstance(decision.phase_index, bool)
                or decision.phase_index < 0
            ):
                issues.append(f"decision_phase_index_invalid:{decision.id}")
            if not decision.switch_role.strip():
                issues.append(f"decision_switch_role_empty:{decision.id}")
            if len(decision.outgoing_edge_roles) < 2:
                issues.append(f"decision_outgoing_roles_insufficient:{decision.id}")
            if len(decision.outgoing_edge_roles) != len(set(decision.outgoing_edge_roles)):
                issues.append(f"decision_outgoing_roles_duplicate:{decision.id}")
            if any(not role.strip() for role in decision.outgoing_edge_roles):
                issues.append(f"decision_outgoing_role_empty:{decision.id}")
            if (
                decision.required_outgoing_edge_role is not None
                and decision.required_outgoing_edge_role not in decision.outgoing_edge_roles
            ):
                issues.append(f"decision_required_role_unknown:{decision.id}")

        objective_phases: dict[str, int] = {}
        for objective_id, phase_index in self.objective_phase_indices:
            if not objective_id.strip():
                issues.append("objective_dependency_id_empty")
                continue
            if objective_id in objective_phases:
                issues.append(f"objective_dependency_id_duplicate:{objective_id}")
                continue
            if (
                not isinstance(phase_index, int)
                or isinstance(phase_index, bool)
                or phase_index < 0
            ):
                issues.append(f"objective_dependency_phase_invalid:{objective_id}")
                continue
            objective_phases[objective_id] = phase_index

        dependency_keys: set[tuple[str, str, DecisionDependencyKind]] = set()
        adjacency: dict[str, list[str]] = {
            decision_id: [] for decision_id in decisions_by_id
        }
        for dependency in self.dependencies:
            key = (dependency.source_id, dependency.target_id, dependency.kind)
            if key in dependency_keys:
                issues.append(
                    f"decision_dependency_duplicate:{dependency.source_id}:"
                    f"{dependency.target_id}:{dependency.kind.value}"
                )
                continue
            dependency_keys.add(key)

            target = decisions_by_id.get(dependency.target_id)
            if target is None:
                issues.append(f"decision_dependency_target_unknown:{dependency.target_id}")
                continue

            if dependency.kind is DecisionDependencyKind.OBJECTIVE_STATE:
                objective_phase = objective_phases.get(dependency.source_id)
                if objective_phase is None:
                    issues.append(
                        f"decision_dependency_objective_unknown:{dependency.source_id}"
                    )
                elif objective_phase >= target.phase_index:
                    issues.append(
                        f"decision_dependency_objective_not_completed:{dependency.source_id}:"
                        f"{dependency.target_id}"
                    )
                if dependency.required_source_outgoing_edge_role is not None:
                    issues.append(
                        f"decision_dependency_objective_has_choice:{dependency.source_id}:"
                        f"{dependency.target_id}"
                    )
                continue

            source = decisions_by_id.get(dependency.source_id)
            if source is None:
                issues.append(f"decision_dependency_source_unknown:{dependency.source_id}")
                continue
            adjacency[source.id].append(target.id)
            if source.sequence_index >= target.sequence_index:
                issues.append(
                    f"decision_dependency_not_earlier:{source.id}:{target.id}"
                )
            required_source_role = dependency.required_source_outgoing_edge_role
            if required_source_role is None:
                issues.append(
                    f"decision_dependency_choice_missing:{source.id}:{target.id}"
                )
            elif required_source_role not in source.outgoing_edge_roles:
                issues.append(
                    f"decision_dependency_choice_unknown:{source.id}:"
                    f"{required_source_role}"
                )
            elif (
                source.required_outgoing_edge_role is not None
                and source.required_outgoing_edge_role != required_source_role
            ):
                issues.append(
                    f"decision_dependency_choice_unrealizable:{source.id}:"
                    f"{required_source_role}"
                )

            if dependency.kind is DecisionDependencyKind.REVISIT:
                if source.phase_index >= target.phase_index:
                    issues.append(
                        f"decision_revisit_phase_not_later:{source.id}:{target.id}"
                    )
                if source.switch_role != target.switch_role:
                    issues.append(
                        f"decision_revisit_switch_mismatch:{source.id}:{target.id}"
                    )
                if source.required_outgoing_edge_role is None:
                    issues.append(f"decision_revisit_source_role_missing:{source.id}")
                if target.required_outgoing_edge_role is None:
                    issues.append(f"decision_revisit_target_role_missing:{target.id}")
                if (
                    source.required_outgoing_edge_role is not None
                    and source.required_outgoing_edge_role
                    == target.required_outgoing_edge_role
                ):
                    issues.append(
                        f"decision_revisit_role_unchanged:{source.id}:{target.id}"
                    )

        issues.extend(self._cycle_issues(adjacency))
        return tuple(issues)

    @staticmethod
    def _cycle_issues(adjacency: dict[str, list[str]]) -> tuple[str, ...]:
        visiting: set[str] = set()
        visited: set[str] = set()
        cycle_nodes: set[str] = set()
        path: list[str] = []

        def visit(decision_id: str) -> None:
            if decision_id in visited:
                return
            if decision_id in visiting:
                cycle_start = path.index(decision_id)
                cycle_nodes.update(path[cycle_start:])
                return
            visiting.add(decision_id)
            path.append(decision_id)
            for dependent_id in adjacency[decision_id]:
                visit(dependent_id)
            path.pop()
            visiting.remove(decision_id)
            visited.add(decision_id)

        for decision_id in adjacency:
            visit(decision_id)
        if not cycle_nodes:
            return ()
        return ("decision_dependency_cycle:" + ",".join(sorted(cycle_nodes)),)
