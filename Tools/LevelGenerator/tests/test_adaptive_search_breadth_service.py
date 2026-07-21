from __future__ import annotations

import json

from app.models import SearchBreadth
from app.services import AdaptiveSearchBreadthService


def _breadth() -> SearchBreadth:
    return SearchBreadth(
        blueprint_count=2,
        composition_alternatives_per_blueprint=3,
        layout_variants=1,
        road_shape_variants=2,
        candidate_pool_size=4,
        attempt_budget=12,
    )


def test_low_yield_expands_every_search_dimension_without_changing_quality() -> None:
    result = AdaptiveSearchBreadthService().evaluate(
        _breadth(),
        attempted_candidates=8,
        accepted_candidates=1,
        difficulty="hard",
        archetype="return_to_hub",
    )

    assert result.adjusted
    before = result.adjustments[0].before
    after = result.breadth
    assert after.blueprint_count > before.blueprint_count
    assert (
        after.composition_alternatives_per_blueprint
        > before.composition_alternatives_per_blueprint
    )
    assert after.layout_variants > before.layout_variants
    assert after.road_shape_variants > before.road_shape_variants
    assert after.candidate_pool_size > before.candidate_pool_size
    assert after.attempt_budget > before.attempt_budget
    assert result.adjustments[0].hard_quality_gates_unchanged is True
    json.dumps(result.to_report_dict(), sort_keys=True)


def test_sufficient_yield_and_small_samples_do_not_expand_search() -> None:
    service = AdaptiveSearchBreadthService()

    small_sample = service.evaluate(
        _breadth(),
        attempted_candidates=2,
        accepted_candidates=0,
        difficulty="hard",
        archetype="return_to_hub",
    )
    sufficient = service.evaluate(
        _breadth(),
        attempted_candidates=8,
        accepted_candidates=3,
        difficulty="hard",
        archetype="return_to_hub",
    )

    assert not small_sample.adjusted
    assert not sufficient.adjusted
    assert small_sample.breadth == _breadth()
    assert sufficient.breadth == _breadth()


def test_adaptive_breadth_is_deterministic_and_bounded() -> None:
    service = AdaptiveSearchBreadthService()
    first = service.evaluate(
        _breadth(),
        attempted_candidates=12,
        accepted_candidates=0,
        difficulty="expert",
        archetype="closed_return",
    )
    second = service.evaluate(
        _breadth(),
        attempted_candidates=12,
        accepted_candidates=0,
        difficulty="expert",
        archetype="closed_return",
    )

    assert first == second
    maximum = service.config.maximum_breadth
    saturated = service.evaluate(
        maximum,
        attempted_candidates=maximum.attempt_budget,
        accepted_candidates=0,
        difficulty="expert",
        archetype="closed_return",
    )
    assert saturated.breadth == maximum
    assert not saturated.adjusted
