"""Classify failures and recoveries for non-optimal meaningful choices."""

from __future__ import annotations

from collections import defaultdict

from tiny_routes_core.models import LevelDocument

from ..models.strategy_search import (
    AlternateSuccessKind,
    FailureRecoveryReport,
    MeaningfulChoiceClassification,
    MeaningfulChoiceKey,
    MeaningfulChoiceOutcomeKind,
    StrategyAction,
    StrategySearchResult,
    StrategyTrace,
)
from .alternate_success_classification_service import (
    AlternateSuccessClassificationService,
)
from .strategy_equivalence_service import StrategyEquivalenceService


class FailureRecoveryClassificationService:
    """Prove the best attainable outcome after each observed wrong choice."""

    def __init__(
        self,
        alternate_success_service: AlternateSuccessClassificationService | None = None,
        equivalence_service: StrategyEquivalenceService | None = None,
    ) -> None:
        self.equivalence_service = equivalence_service or StrategyEquivalenceService()
        self.alternate_success_service = alternate_success_service or (
            AlternateSuccessClassificationService(self.equivalence_service)
        )

    def classify(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult,
    ) -> FailureRecoveryReport:
        alternate_report = self.alternate_success_service.classify(level, search_result)
        optimal_class = alternate_report.optimal_strategy_class
        if optimal_class is None:
            return FailureRecoveryReport(
                optimal_strategy_class=None,
                classifications=(),
                exhaustive=search_result.exhaustive,
                limit_reasons=search_result.limit_reasons,
            )

        optimal = optimal_class.canonical_trace
        alternate_kind_by_key = {
            item.strategy_class.key: item.kind
            for item in alternate_report.classifications
        }
        traces = (
            *(item.strategy_class.canonical_trace for item in alternate_report.classifications),
            *(
                item.canonical_trace
                for item in self.equivalence_service.classify(
                    search_result.failure_outcomes,
                    level=level,
                )
            ),
        )
        grouped: dict[
            MeaningfulChoiceKey,
            list[tuple[StrategyTrace, int]],
        ] = defaultdict(list)
        for trace in traces:
            divergence = self._first_divergence(optimal, trace)
            if divergence is None:
                continue
            key, action_index = divergence
            grouped[key].append((trace, action_index))

        classifications = tuple(
            self._classify_choice(
                key,
                grouped[key],
                optimal,
                alternate_kind_by_key,
                level,
            )
            for key in sorted(grouped)
        )
        return FailureRecoveryReport(
            optimal_strategy_class=optimal_class,
            classifications=classifications,
            exhaustive=search_result.exhaustive,
            limit_reasons=search_result.limit_reasons,
        )

    def _classify_choice(
        self,
        key: MeaningfulChoiceKey,
        evidence: list[tuple[StrategyTrace, int]],
        optimal: StrategyTrace,
        alternate_kind_by_key,
        level: LevelDocument,
    ) -> MeaningfulChoiceClassification:
        ordered = sorted(
            evidence,
            key=lambda item: (
                0 if item[0].succeeded else 1,
                item[0].cost,
                item[0].exact_signature,
                item[0].outcome_code,
            ),
        )
        canonical, action_index = ordered[0]
        rejoins = canonical.succeeded and self._rejoins_optimal(
            optimal,
            canonical,
            key.decision_ordinal,
        )
        if canonical.succeeded:
            strategy_key = self.equivalence_service.key_for(canonical, level=level)
            alternate_kind = alternate_kind_by_key[strategy_key]
            if rejoins:
                kind = MeaningfulChoiceOutcomeKind.RECOVERABLE_DETOUR
            elif alternate_kind is AlternateSuccessKind.SUCCESSFUL_HIGHER_TAP_ROUTE:
                kind = MeaningfulChoiceOutcomeKind.SUCCESSFUL_HIGHER_TAP_ROUTE
            elif alternate_kind is AlternateSuccessKind.EQUAL_COST_ROUTE:
                kind = MeaningfulChoiceOutcomeKind.SUCCESSFUL_EQUAL_COST_ROUTE
            else:
                kind = MeaningfulChoiceOutcomeKind.SUCCESSFUL_SLOWER_ROUTE
        else:
            kind = self._failure_kind(level, canonical, action_index)

        supporting = tuple(
            item[0]
            for item in sorted(
                evidence,
                key=lambda item: (
                    item[0].cost,
                    item[0].exact_signature,
                    item[0].outcome_code,
                ),
            )
        )
        return MeaningfulChoiceClassification(
            key=key,
            kind=kind,
            canonical_trace=canonical,
            supporting_traces=supporting,
            rejoins_optimal_route=rejoins,
        )

    @staticmethod
    def _first_divergence(
        optimal: StrategyTrace,
        candidate: StrategyTrace,
    ) -> tuple[MeaningfulChoiceKey, int] | None:
        optimal_actions = tuple(
            action for action in optimal.actions if action.meaningful_decision
        )
        candidate_actions = tuple(
            (index, action)
            for index, action in enumerate(candidate.actions)
            if action.meaningful_decision
        )
        for ordinal, (action_index, action) in enumerate(candidate_actions):
            if ordinal < len(optimal_actions) and (
                action.node_id,
                action.selected_edge_id,
            ) == (
                optimal_actions[ordinal].node_id,
                optimal_actions[ordinal].selected_edge_id,
            ):
                continue
            return (
                MeaningfulChoiceKey(
                    decision_ordinal=ordinal,
                    objective_index=(
                        action.state_transition.objective_index_before
                        if action.state_transition is not None
                        else 0
                    ),
                    node_id=action.node_id,
                    selected_edge_id=action.selected_edge_id,
                ),
                action_index,
            )
        return None

    def _rejoins_optimal(
        self,
        optimal: StrategyTrace,
        candidate: StrategyTrace,
        divergence_ordinal: int,
    ) -> bool:
        optimal_meaningful = tuple(
            action for action in optimal.actions if action.meaningful_decision
        )
        candidate_meaningful = tuple(
            action for action in candidate.actions if action.meaningful_decision
        )
        optimal_suffix = {
            self._action_choice(action)
            for action in optimal_meaningful[divergence_ordinal:]
        }
        candidate_suffix = {
            self._action_choice(action)
            for action in candidate_meaningful[divergence_ordinal + 1 :]
        }
        if optimal_suffix.intersection(candidate_suffix):
            return True

        optimal_edges = self._route_suffix_edges(optimal, divergence_ordinal)
        candidate_edges = self._route_suffix_edges(candidate, divergence_ordinal)
        return bool(optimal_edges.intersection(candidate_edges))

    @staticmethod
    def _route_suffix_edges(
        trace: StrategyTrace,
        meaningful_ordinal: int,
    ) -> set[str]:
        seen_meaningful = 0
        suffix: set[str] = set()
        for action in trace.actions:
            if action.meaningful_decision:
                if seen_meaningful == meaningful_ordinal:
                    suffix.update(action.traversed_edge_ids[1:])
                elif seen_meaningful > meaningful_ordinal:
                    suffix.update(action.traversed_edge_ids)
                seen_meaningful += 1
            elif seen_meaningful > meaningful_ordinal:
                suffix.update(action.traversed_edge_ids)
        return suffix

    @staticmethod
    def _action_choice(action: StrategyAction) -> tuple[int, str, str]:
        transition = action.state_transition
        return (
            transition.objective_index_before if transition is not None else 0,
            action.node_id,
            action.selected_edge_id,
        )

    def _failure_kind(
        self,
        level: LevelDocument,
        trace: StrategyTrace,
        divergent_action_index: int,
    ) -> MeaningfulChoiceOutcomeKind:
        if (
            trace.outcome_code == "structural_destination_before_objective"
            or self._has_objective_order_violation(level, trace)
        ):
            return MeaningfulChoiceOutcomeKind.OBJECTIVE_ORDER_FAILURE
        if trace.outcome_code in {
            "structural_automatic_cycle",
            "strategy_action_limit_reached",
        }:
            return MeaningfulChoiceOutcomeKind.LOOP_UNTIL_TIME_EXPIRES
        if (
            trace.outcome_code in {"structural_dead_end", "structural_initial_dead_end"}
            and len(trace.actions) == divergent_action_index + 1
        ):
            return MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END
        return MeaningfulChoiceOutcomeKind.STATE_TRAP

    @staticmethod
    def _has_objective_order_violation(
        level: LevelDocument,
        trace: StrategyTrace,
    ) -> bool:
        objectives = tuple(
            sorted(level.effective_objectives, key=lambda item: item.sequenceIndex)
        )
        for action in trace.actions:
            transition = action.state_transition
            active_index = transition.objective_index_before if transition is not None else 0
            future_nodes = {
                objective.nodeID
                for objective in objectives[active_index + 1 :]
            }
            if future_nodes.intersection(action.visited_node_ids):
                return True
        return False
