from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.candidate_signature import CandidateSignature
from app.services.candidate_portfolio_selection_service import CandidatePortfolioSelectionService


def _candidate(level_id: str, seed: int, topology: str, layout: str, quality: float = 90.0):
    signature = CandidateSignature(
        level_id=level_id,
        template_name="test",
        difficulty="easy",
        node_count=5,
        edge_count=5,
        switch_count=1,
        required_tap_count=1,
        dead_end_count=1,
        topology_hash=topology,
        layout_hash=layout,
        solution_hash=f"solution-{topology}",
        normalized_positions=(),
        topology_class=topology,
        primary_mechanic_tag=topology,
        mechanic_tags=(topology,),
        layout_silhouette=((0.0, 0.0),) if layout == "same" else ((1.0, 1.0),),
        road_direction_histogram=((layout, 1),),
        decision_dependency_pattern=(seed, 0, 0.0),
    )
    return SimpleNamespace(
        level_id=level_id,
        difficulty="easy",
        seed=seed,
        candidate_signature=signature,
        quality_score=SimpleNamespace(total_score=quality, difficulty_fit=1.0),
    )


def test_portfolio_selection_returns_requested_count_and_is_deterministic() -> None:
    pools = {
        "level_001": [_candidate("level_001", 1, "a", "same"), _candidate("level_001", 2, "b", "other")],
        "level_002": [_candidate("level_002", 3, "a", "same"), _candidate("level_002", 4, "c", "different")],
    }
    requested = [("level_001", "easy"), ("level_002", "easy")]
    service = CandidatePortfolioSelectionService()

    first = service.select(pools, requested)
    second = service.select(pools, requested)

    assert len(first.candidates) == 2
    assert [item.seed for item in first.candidates] == [item.seed for item in second.candidates]
    assert first.candidates[0].candidate_signature.topology_class != first.candidates[1].candidate_signature.topology_class
    assert all(selection.rationale for selection in first.selections)


def test_portfolio_selection_enforces_difficulty_and_level_constraints() -> None:
    candidate = _candidate("level_001", 1, "a", "same")

    with pytest.raises(ValueError, match="no hard candidate"):
        CandidatePortfolioSelectionService().select(
            {"level_001": [candidate]},
            [("level_001", "hard")],
        )
