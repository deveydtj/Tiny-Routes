"""Deterministic challenge-archetype blueprints for production V3 generation."""

from __future__ import annotations

from random import Random
from typing import Callable

from ..models.decision_dependency_graph import (
    DecisionDependency,
    DecisionDependencyGraph,
    DecisionDependencyKind,
    DecisionNode,
)
from ..models.puzzle_blueprint import (
    ObjectiveSpec,
    PuzzleBlueprint,
    StateTransitionSpec,
)
from ..models.puzzle_experience_target import PuzzleExperienceTarget
from .difficulty_target_resolver import DifficultyTargetResolver


class PuzzleBlueprintService:
    """Build validated graph-independent blueprints from difficulty and seed.

    Only archetypes with completed production contracts are exposed here. New
    archetypes can be appended without weakening callers into a legacy or
    partially specified fallback.
    """

    supported_archetypes = ("return_to_hub", "unlock_shortcut")

    def __init__(
        self,
        difficulty_resolver: DifficultyTargetResolver | None = None,
    ) -> None:
        self._difficulty_resolver = difficulty_resolver or DifficultyTargetResolver()

    def generate(
        self,
        difficulty: str,
        seed: int,
        archetype: str | None = None,
    ) -> PuzzleBlueprint:
        """Return one deterministic, validated blueprint.

        Omitting ``archetype`` performs deterministic selection among only the
        archetypes that have completed contracts. Explicit selection is useful
        for campaign planning and fixed-seed regression coverage.
        """

        seed = self._validated_seed(seed)
        if archetype is None:
            archetype = self.supported_archetypes[seed % len(self.supported_archetypes)]
        if not isinstance(archetype, str):
            raise ValueError("archetype must be a supported blueprint name")
        archetype = archetype.strip().lower()

        builders = {
            "return_to_hub": self.build_return_to_hub,
            "unlock_shortcut": self.build_unlock_shortcut,
        }
        try:
            builder = builders[archetype]
        except KeyError as exc:
            supported = ", ".join(self.supported_archetypes)
            raise ValueError(
                f"Unknown production V3 blueprint archetype: {archetype}. "
                f"Supported archetypes: {supported}"
            ) from exc
        return builder(difficulty=difficulty, seed=seed)

    def build_return_to_hub(self, difficulty: str, seed: int = 0) -> PuzzleBlueprint:
        """Require the same hub to use different correct exits across phases."""

        seed = self._validated_seed(seed)
        target = self._difficulty_resolver.resolve(difficulty)
        randomizer = Random(f"return_to_hub:{target.difficulty}:{seed}")
        return self._build_blueprint(
            archetype="return_to_hub",
            seed=seed,
            target=target,
            randomizer=randomizer,
            hub_switch_role="central_route_hub",
            hub_outgoing_roles=(
                "hub_exit_primary_objective",
                "hub_exit_next_objective",
                "hub_exit_recovery_loop",
            ),
            objective_prefix="route",
            required_mechanics=("hub_revisit",),
            transition_factory=self._return_to_hub_transition,
        )

    def build_unlock_shortcut(
        self,
        difficulty: str,
        seed: int = 0,
    ) -> PuzzleBlueprint:
        """Require a long outbound route before an objective unlocks a shortcut."""

        seed = self._validated_seed(seed)
        target = self._difficulty_resolver.resolve(difficulty)
        randomizer = Random(f"unlock_shortcut:{target.difficulty}:{seed}")
        return self._build_blueprint(
            archetype="unlock_shortcut",
            seed=seed,
            target=target,
            randomizer=randomizer,
            hub_switch_role="shortcut_junction",
            hub_outgoing_roles=(
                "long_outbound_route",
                "unlocked_shortcut",
                "shortcut_recovery_detour",
            ),
            objective_prefix="shortcut",
            required_mechanics=("unlock_shortcut",),
            transition_factory=self._unlock_shortcut_transition,
        )

    def _build_blueprint(
        self,
        *,
        archetype: str,
        seed: int,
        target: PuzzleExperienceTarget,
        randomizer: Random,
        hub_switch_role: str,
        hub_outgoing_roles: tuple[str, ...],
        objective_prefix: str,
        required_mechanics: tuple[str, ...],
        transition_factory: Callable[
            [int, tuple[ObjectiveSpec, ...]],
            StateTransitionSpec,
        ],
    ) -> PuzzleBlueprint:
        objective_count = randomizer.randint(*target.objective_count_range)
        decision_lower = max(target.meaningful_decision_range[0], objective_count)
        decision_count = randomizer.randint(
            decision_lower,
            target.meaningful_decision_range[1],
        )
        revisit_lower = max(1, target.revisit_range[0])
        revisit_upper = min(
            target.revisit_range[1],
            objective_count - 1,
            decision_count - 1,
        )
        if revisit_upper < revisit_lower:
            raise ValueError(
                f"{archetype} cannot satisfy the {target.difficulty} revisit target"
            )
        revisit_count = randomizer.randint(revisit_lower, revisit_upper)

        state_change_upper = min(target.state_change_range[1], objective_count - 1)
        if state_change_upper < target.state_change_range[0]:
            raise ValueError(
                f"{archetype} cannot satisfy the {target.difficulty} state-change target"
            )
        state_change_count = randomizer.randint(
            target.state_change_range[0],
            state_change_upper,
        )

        objectives = self._build_objectives(
            objective_count,
            objective_prefix=objective_prefix,
            first_objective_id=(
                "shortcut_key" if archetype == "unlock_shortcut" else "primary_pickup"
            ),
        )
        phase_indices = self._decision_phase_indices(decision_count, objective_count)
        hub_indices = self._hub_visit_indices(phase_indices, revisit_count)
        decisions = self._build_decisions(
            phase_indices=phase_indices,
            hub_indices=hub_indices,
            hub_switch_role=hub_switch_role,
            hub_outgoing_roles=hub_outgoing_roles,
            archetype=archetype,
        )
        dependencies = self._build_dependencies(
            decisions=decisions,
            objectives=objectives,
            hub_indices=hub_indices,
            adaptive_count=target.adaptive_decision_minimum,
        )
        adaptive_ids = self._adaptive_decision_ids(
            decisions,
            target.adaptive_decision_minimum,
        )
        transitions = tuple(
            transition_factory(index, objectives)
            for index in range(state_change_count)
        )

        blueprint = PuzzleBlueprint(
            id=f"{target.difficulty}_{archetype}_{seed}",
            archetype=archetype,
            experience_target=target,
            objectives=objectives,
            decision_graph=DecisionDependencyGraph(
                decisions=decisions,
                dependencies=dependencies,
                objective_phase_indices=tuple(
                    (objective.id, objective.sequence_index)
                    for objective in objectives
                ),
            ),
            state_transitions=transitions,
            planning_decision_ids=tuple(
                decision.id
                for decision in decisions[: target.planning_decision_minimum]
            ),
            adaptive_decision_ids=adaptive_ids,
            required_revisit_decision_ids=tuple(
                decisions[index].id for index in hub_indices[1:]
            ),
            successful_strategy_count_range=(
                target.successful_route_class_range[0],
                min(2, target.successful_route_class_range[1]),
            ),
            requires_unique_optimal_strategy=True,
            requires_static_policy_rejection=True,
            recoverable_mistake_target=randomizer.randint(
                *target.recoverable_mistake_range
            ),
            fatal_mistake_cap=target.fatal_mistake_cap,
            required_mechanic_categories=required_mechanics,
        )
        issues = blueprint.validate()
        if issues:
            raise ValueError(
                f"Generated invalid {archetype} blueprint: {', '.join(issues)}"
            )
        return blueprint

    @staticmethod
    def _build_objectives(
        count: int,
        *,
        objective_prefix: str,
        first_objective_id: str,
    ) -> tuple[ObjectiveSpec, ...]:
        objectives: list[ObjectiveSpec] = []
        for index in range(count):
            if index == count - 1:
                objective_id = "destination"
                kind = "destination"
            elif index == 0:
                objective_id = first_objective_id
                kind = "pickup"
            else:
                objective_id = f"checkpoint_{index}"
                kind = "checkpoint"
            objectives.append(
                ObjectiveSpec(
                    id=objective_id,
                    kind=kind,
                    sequence_index=index,
                    phase_entry_role=f"{objective_prefix}_phase_{index}_entry",
                    phase_exit_role=f"{objective_prefix}_phase_{index}_exit",
                    reveal_policy="always" if index == 0 else "afterPrevious",
                )
            )
        return tuple(objectives)

    @staticmethod
    def _decision_phase_indices(
        decision_count: int,
        objective_count: int,
    ) -> tuple[int, ...]:
        return tuple(
            min((index * objective_count) // decision_count, objective_count - 1)
            for index in range(decision_count)
        )

    @staticmethod
    def _hub_visit_indices(
        phase_indices: tuple[int, ...],
        revisit_count: int,
    ) -> tuple[int, ...]:
        first_by_phase: dict[int, int] = {}
        for index, phase_index in enumerate(phase_indices):
            first_by_phase.setdefault(phase_index, index)
        later_visits = tuple(
            first_by_phase[phase_index]
            for phase_index in sorted(first_by_phase)
            if phase_index > 0
        )
        return (0, *later_visits[:revisit_count])

    @staticmethod
    def _build_decisions(
        *,
        phase_indices: tuple[int, ...],
        hub_indices: tuple[int, ...],
        hub_switch_role: str,
        hub_outgoing_roles: tuple[str, ...],
        archetype: str,
    ) -> tuple[DecisionNode, ...]:
        hub_visit_by_index = {
            decision_index: visit_index
            for visit_index, decision_index in enumerate(hub_indices)
        }
        decisions: list[DecisionNode] = []
        for index, phase_index in enumerate(phase_indices):
            if index in hub_visit_by_index:
                visit_index = hub_visit_by_index[index]
                decisions.append(
                    DecisionNode(
                        id=f"{archetype}_hub_visit_{visit_index}",
                        sequence_index=index,
                        phase_index=phase_index,
                        switch_role=hub_switch_role,
                        outgoing_edge_roles=hub_outgoing_roles,
                        required_outgoing_edge_role=hub_outgoing_roles[
                            visit_index % len(hub_outgoing_roles)
                        ],
                    )
                )
                continue

            preferred_role = f"{archetype}_decision_{index}_preferred"
            decisions.append(
                DecisionNode(
                    id=f"{archetype}_decision_{index}",
                    sequence_index=index,
                    phase_index=phase_index,
                    switch_role=f"{archetype}_support_switch_{index}",
                    outgoing_edge_roles=(
                        preferred_role,
                        f"{archetype}_decision_{index}_alternate",
                        f"{archetype}_decision_{index}_recovery",
                    ),
                    required_outgoing_edge_role=preferred_role,
                )
            )
        return tuple(decisions)

    @classmethod
    def _build_dependencies(
        cls,
        *,
        decisions: tuple[DecisionNode, ...],
        objectives: tuple[ObjectiveSpec, ...],
        hub_indices: tuple[int, ...],
        adaptive_count: int,
    ) -> tuple[DecisionDependency, ...]:
        dependencies: list[DecisionDependency] = []
        for source, target in zip(decisions, decisions[1:]):
            dependencies.append(
                DecisionDependency(
                    source_id=source.id,
                    target_id=target.id,
                    kind=DecisionDependencyKind.EARLIER_CHOICE,
                    required_source_outgoing_edge_role=(
                        source.required_outgoing_edge_role
                    ),
                )
            )

        for source_index, target_index in zip(hub_indices, hub_indices[1:]):
            source = decisions[source_index]
            target = decisions[target_index]
            dependencies.append(
                DecisionDependency(
                    source_id=source.id,
                    target_id=target.id,
                    kind=DecisionDependencyKind.REVISIT,
                    required_source_outgoing_edge_role=(
                        source.required_outgoing_edge_role
                    ),
                )
            )

        for target in cls._adaptive_decisions(decisions, adaptive_count):
            prerequisite = objectives[target.phase_index - 1]
            dependencies.append(
                DecisionDependency(
                    source_id=prerequisite.id,
                    target_id=target.id,
                    kind=DecisionDependencyKind.OBJECTIVE_STATE,
                )
            )
        return tuple(dependencies)

    @classmethod
    def _adaptive_decision_ids(
        cls,
        decisions: tuple[DecisionNode, ...],
        count: int,
    ) -> tuple[str, ...]:
        return tuple(decision.id for decision in cls._adaptive_decisions(decisions, count))

    @staticmethod
    def _adaptive_decisions(
        decisions: tuple[DecisionNode, ...],
        count: int,
    ) -> tuple[DecisionNode, ...]:
        candidates = tuple(decision for decision in decisions if decision.phase_index > 0)
        if len(candidates) < count:
            raise ValueError("blueprint does not contain enough post-objective decisions")
        return candidates[:count]

    @staticmethod
    def _return_to_hub_transition(
        phase_index: int,
        objectives: tuple[ObjectiveSpec, ...],
    ) -> StateTransitionSpec:
        trigger = objectives[phase_index]
        following = objectives[phase_index + 1]
        hub_exit_roles = (
            "hub_exit_primary_objective",
            "hub_exit_next_objective",
            "hub_exit_recovery_loop",
        )
        return StateTransitionSpec(
            id=f"return_hub_phase_{phase_index + 1}",
            from_phase_index=phase_index,
            to_phase_index=phase_index + 1,
            trigger_objective_id=trigger.id,
            required_completed_objective_ids=(trigger.id,),
            revealed_objective_ids=(following.id,),
            opened_edge_roles=(
                hub_exit_roles[(phase_index + 1) % len(hub_exit_roles)],
            ),
            closed_edge_roles=(
                hub_exit_roles[phase_index % len(hub_exit_roles)],
            ),
        )

    @staticmethod
    def _unlock_shortcut_transition(
        phase_index: int,
        objectives: tuple[ObjectiveSpec, ...],
    ) -> StateTransitionSpec:
        trigger = objectives[phase_index]
        following = objectives[phase_index + 1]
        if phase_index == 0:
            opened_roles = ("unlocked_shortcut",)
            closed_roles = ("long_outbound_route",)
        else:
            opened_roles = (f"shortcut_phase_{phase_index + 1}_connector",)
            closed_roles = (f"shortcut_phase_{phase_index}_connector",)
        return StateTransitionSpec(
            id=f"unlock_shortcut_phase_{phase_index + 1}",
            from_phase_index=phase_index,
            to_phase_index=phase_index + 1,
            trigger_objective_id=trigger.id,
            required_completed_objective_ids=(trigger.id,),
            revealed_objective_ids=(following.id,),
            opened_edge_roles=opened_roles,
            closed_edge_roles=closed_roles,
        )

    @staticmethod
    def _validated_seed(seed: int) -> int:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")
        return seed


PuzzleBlueprintGeneratorService = PuzzleBlueprintService
