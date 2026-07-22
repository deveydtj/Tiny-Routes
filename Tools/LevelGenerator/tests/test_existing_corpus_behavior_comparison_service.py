from __future__ import annotations

from dataclasses import replace

from app.models.candidate_signature import CandidateSignature
from app.services.existing_corpus_behavior_comparison_service import (
    ExistingCorpusBehaviorComparisonService,
)


def _signature(level_id: str, **overrides) -> CandidateSignature:
    signature = CandidateSignature(
        level_id=level_id,
        template_name="ignored-name",
        difficulty="hard",
        node_count=8,
        edge_count=9,
        switch_count=3,
        required_tap_count=4,
        dead_end_count=1,
        topology_hash="topology",
        layout_hash="layout",
        solution_hash="solution",
        normalized_positions=(),
    )
    return replace(signature, **overrides)


def test_exact_structural_behavior_rejects_different_names_and_layouts() -> None:
    service = ExistingCorpusBehaviorComparisonService()
    candidate = _signature(
        "candidate",
        structural_behavior_signature="behavior",
        layout_hash="candidate-layout",
        template_name="candidate-name",
    )
    existing = _signature(
        "existing",
        structural_behavior_signature="behavior",
        layout_hash="existing-layout",
        template_name="existing-name",
    )

    result = service.compare(candidate, existing)

    assert result.too_similar is True
    assert result.reason_code == "same_structural_behavior"
    assert result.matched_level_id == "existing"


def test_sparse_empty_defaults_are_not_behavior_evidence() -> None:
    result = ExistingCorpusBehaviorComparisonService().compare(
        _signature("candidate"),
        _signature("existing", layout_hash="same-layout"),
    )

    assert result.too_similar is False
    assert result.score == 0.0
    assert result.dimensions == ()


def test_rich_matching_proof_dimensions_cross_threshold() -> None:
    evidence = {
        "dependency_dag_signature": "dag",
        "adaptive_decision_pattern": ((1, 1, ("objective",)),),
        "state_transition_pattern": ((0, 1, "objective", 1, 1, 0, 0),),
        "static_policy_proof_signature": "static",
        "agent_performance_profile": (("greedy", 0.0),),
        "revisit_pattern": ((0, 2, 1),),
        "success_failure_distribution": (("successful", 2),),
        "optimal_strategy_signature": "optimal",
        "objective_kinds": ("pickup", "checkpoint", "destination"),
        "switch_degree_sequence": (3, 2),
    }

    result = ExistingCorpusBehaviorComparisonService().compare(
        _signature("candidate", **evidence),
        _signature("existing", **evidence),
    )

    assert result.too_similar is True
    assert result.reason_code == "behavior_similarity_threshold"
    assert result.score == 1.0
