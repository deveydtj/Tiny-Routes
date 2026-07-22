from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.models.candidate_signature import CandidateSignature
from app.services.candidate_portfolio_selection_service import (
    CandidatePortfolioSelectionService,
    PortfolioConstraintFailure,
    PortfolioConstraints,
)


def _candidate(
    level_id: str,
    seed: int,
    topology: str,
    layout: str,
    quality: float = 90.0,
    difficulty: str = "easy",
    **signature_overrides,
):
    signature = CandidateSignature(
        level_id=level_id,
        template_name="test",
        difficulty=difficulty,
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
    signature = replace(signature, **signature_overrides)
    return SimpleNamespace(
        level_id=level_id,
        difficulty=difficulty,
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


def test_optimizer_retains_lower_scoring_prefix_when_best_prefix_blocks_later_slot() -> None:
    pools = {
        "level_001": [
            _candidate(
                "level_001", 1, "a", "same", 99.0, blueprint_archetype="hub"
            ),
            _candidate(
                "level_001", 2, "b", "other", 70.0, blueprint_archetype="loop"
            ),
        ],
        "level_002": [
            _candidate(
                "level_002", 3, "c", "different", 90.0, blueprint_archetype="hub"
            )
        ],
    }

    result = CandidatePortfolioSelectionService().select(
        pools,
        [("level_001", "easy"), ("level_002", "easy")],
    )

    assert [candidate.seed for candidate in result.candidates] == [2, 3]
    assert result.explored_states == 4
    assert dict(result.constraint_rejections) == {
        "portfolio_adjacent_blueprint_archetype": 1
    }


def test_identical_v3_behavior_is_a_hard_window_constraint() -> None:
    shared = {
        "dependency_dag_signature": "dependency",
        "adaptive_decision_pattern": ((0, 1, ("objectiveState",)),),
        "state_transition_pattern": ((0, 1, "objective", 0, 1, 0, 0),),
        "static_policy_proof_signature": "static-proof",
        "optimal_strategy_signature": "optimal-proof",
    }
    pools = {
        "level_001": [
            _candidate(
                "level_001",
                1,
                "a",
                "same",
                blueprint_archetype="hub",
                objective_count=3,
                difficulty="medium",
                **shared,
            )
        ],
        "level_002": [
            _candidate(
                "level_002",
                2,
                "b",
                "other",
                blueprint_archetype="loop",
                objective_count=4,
                difficulty="medium",
                **shared,
            )
        ],
    }

    with pytest.raises(PortfolioConstraintFailure) as captured:
        CandidatePortfolioSelectionService().select(
            pools,
            [("level_001", "medium"), ("level_002", "medium")],
        )

    assert captured.value.constrained_level_ids == ("level_002",)
    assert dict(captured.value.reasons)["portfolio_behavior_signature_window"] == 1


def test_medium_window_requires_multiple_adaptive_mechanic_families() -> None:
    pools = {}
    requested = []
    for index, archetype in enumerate(("hub", "loop", "branch"), start=1):
        level_id = f"level_{index:03d}"
        pools[level_id] = [
            _candidate(
                level_id,
                index,
                archetype,
                archetype,
                blueprint_archetype=archetype,
                objective_count=3 + index,
                difficulty="medium",
                dependency_dag_signature=f"dependency-{index}",
                adaptive_decision_pattern=((0, 1, ()),),
                state_transition_pattern=((0, 1, "objective", 0, 1, 0, 0),),
                optimal_strategy_signature=f"optimal-{index}",
            )
        ]
        requested.append((level_id, "medium"))

    service = CandidatePortfolioSelectionService(
        constraints=PortfolioConstraints(
            adaptive_window_size=3,
            minimum_adaptive_families=2,
        )
    )
    with pytest.raises(PortfolioConstraintFailure) as captured:
        service.select(pools, requested)

    assert dict(captured.value.reasons)["portfolio_adaptive_family_window"] == 1
