"""Classify every gameplay-distinct success beyond the canonical optimum."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models.strategy_search import (
    AlternateSuccessClassification,
    AlternateSuccessKind,
    AlternateSuccessReport,
    StrategyCost,
    StrategyEquivalenceClass,
    StrategySearchResult,
)
from .strategy_equivalence_service import StrategyEquivalenceService


class AlternateSuccessClassificationService:
    """Turn exact successful traces into deterministic cost-based classes."""

    def __init__(
        self,
        equivalence_service: StrategyEquivalenceService | None = None,
    ) -> None:
        self.equivalence_service = equivalence_service or StrategyEquivalenceService()

    def classify(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult,
    ) -> AlternateSuccessReport:
        classes = self.equivalence_service.classify(
            search_result.all_successful_strategies,
            level=level,
        )
        canonical = self._canonical_class(level, search_result, classes)
        if canonical is None or search_result.optimal_cost is None:
            return AlternateSuccessReport(
                optimal_strategy_class=None,
                classifications=(),
                exhaustive=search_result.exhaustive,
                limit_reasons=search_result.limit_reasons,
            )

        optimal = search_result.optimal_cost
        classifications = tuple(
            self._classification(strategy_class, optimal)
            for strategy_class in classes
            if strategy_class.key != canonical.key
        )
        return AlternateSuccessReport(
            optimal_strategy_class=canonical,
            classifications=classifications,
            exhaustive=search_result.exhaustive,
            limit_reasons=search_result.limit_reasons,
        )

    def _canonical_class(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult,
        classes: tuple[StrategyEquivalenceClass, ...],
    ) -> StrategyEquivalenceClass | None:
        trace = search_result.canonical_optimal_strategy
        if trace is None:
            return None
        key = self.equivalence_service.key_for(trace, level=level)
        return next((item for item in classes if item.key == key), None)

    @staticmethod
    def _classification(
        strategy_class: StrategyEquivalenceClass,
        optimal: StrategyCost,
    ) -> AlternateSuccessClassification:
        cost = strategy_class.canonical_trace.cost
        if cost == optimal:
            kind = AlternateSuccessKind.EQUAL_COST_ROUTE
        elif cost.accepted_taps > optimal.accepted_taps:
            kind = AlternateSuccessKind.SUCCESSFUL_HIGHER_TAP_ROUTE
        else:
            kind = AlternateSuccessKind.SUCCESSFUL_SLOWER_ROUTE
        return AlternateSuccessClassification(
            kind=kind,
            strategy_class=strategy_class,
            accepted_tap_delta=cost.accepted_taps - optimal.accepted_taps,
            travel_time_delta_seconds=(
                cost.travel_time_seconds - optimal.travel_time_seconds
            ),
            route_distance_delta=cost.route_distance - optimal.route_distance,
        )
