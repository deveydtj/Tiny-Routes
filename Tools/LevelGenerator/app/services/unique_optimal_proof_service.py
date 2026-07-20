"""Hard proof gate for a unique, target-compliant optimal strategy."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models.strategy_search import (
    OptimalStrategyRequirements,
    StrategyEquivalenceClass,
    StrategySearchResult,
    UniqueOptimalProof,
)
from .strategy_equivalence_service import StrategyEquivalenceService


class UniqueOptimalProofService:
    """Prove uniqueness only from complete exact-search evidence."""

    def __init__(
        self,
        equivalence_service: StrategyEquivalenceService | None = None,
    ) -> None:
        self.equivalence_service = equivalence_service or StrategyEquivalenceService()

    def prove(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult,
        *,
        requirements: OptimalStrategyRequirements | None = None,
        allow_equal_cost_alternatives: bool = False,
    ) -> UniqueOptimalProof:
        requirements = requirements or OptimalStrategyRequirements()
        classes = self.equivalence_service.classify(
            search_result.equal_cost_optimal_strategies,
            level=level,
        )
        canonical = classes[0] if classes else None
        reasons: list[str] = []

        if not search_result.succeeded or not classes:
            reasons.append("unique_optimal_no_successful_strategy")
        if not search_result.exhaustive:
            reasons.append("unique_optimal_search_incomplete")
            reasons.extend(
                f"unique_optimal_limit:{reason}"
                for reason in search_result.limit_reasons
            )
        if len(classes) > 1 and not allow_equal_cost_alternatives:
            reasons.append("unique_optimal_multiple_strategy_classes")
        if canonical is not None:
            reasons.extend(self._target_rejections(canonical, requirements))

        return UniqueOptimalProof(
            accepted=not reasons,
            exhaustive=search_result.exhaustive,
            is_unique=len(classes) == 1,
            optimal_cost=search_result.optimal_cost,
            optimal_strategy_class=canonical,
            equal_cost_strategy_classes=classes,
            rejection_reasons=tuple(reasons),
        )

    @staticmethod
    def _target_rejections(
        strategy_class: StrategyEquivalenceClass,
        requirements: OptimalStrategyRequirements,
    ) -> tuple[str, ...]:
        key = strategy_class.key
        decision_nodes = {node_id for _, node_id, _ in key.meaningful_decisions}
        selected_edges = {edge_id for _, _, edge_id in key.meaningful_decisions}
        objective_ids = set(key.objective_sequence)
        opened: set[str] = set()
        closed: set[str] = set()
        consumed: set[str] = set()
        for transition in strategy_class.canonical_trace.actions:
            state_change = transition.state_transition
            if state_change is None:
                continue
            opened.update(state_change.opened_edge_ids)
            closed.update(state_change.closed_edge_ids)
            consumed.update(state_change.consumed_edge_ids)

        checks = (
            (requirements.required_decision_node_ids, decision_nodes, "decision_node"),
            (requirements.required_selected_edge_ids, selected_edges, "selected_edge"),
            (requirements.required_objective_ids, objective_ids, "objective"),
            (requirements.required_opened_edge_ids, opened, "opened_edge"),
            (requirements.required_closed_edge_ids, closed, "closed_edge"),
            (requirements.required_consumed_edge_ids, consumed, "consumed_edge"),
        )
        return tuple(
            f"unique_optimal_required_{kind}_missing:{identifier}"
            for required, observed, kind in checks
            for identifier in required
            if identifier not in observed
        )
