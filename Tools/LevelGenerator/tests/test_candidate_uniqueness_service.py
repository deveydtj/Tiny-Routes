from __future__ import annotations

from dataclasses import replace

from app.models.candidate_signature import CandidateSignature
from app.services.candidate_uniqueness_service import CandidateUniquenessService


def _signature(**overrides) -> CandidateSignature:
    values = {
        "level_id": "level_001",
        "template_name": "package_gate",
        "difficulty": "easy",
        "node_count": 7,
        "edge_count": 6,
        "switch_count": 2,
        "required_tap_count": 2,
        "dead_end_count": 2,
        "topology_hash": "topology-a",
        "layout_hash": "layout-a",
        "solution_hash": "solution-a",
        "normalized_positions": (
            ("start", 0.0, 0.5),
            ("approach_switch", 0.3, 0.5),
            ("package", 0.5, 1.0),
            ("finish_switch", 0.7, 0.5),
            ("destination", 1.0, 1.0),
        ),
    }
    values.update(overrides)
    return CandidateSignature(**values)


def test_exact_duplicate_rejection() -> None:
    signature = _signature()
    result = CandidateUniquenessService().check_duplicate(signature, [signature])

    assert result.is_duplicate is True
    assert result.reason_code == "same_topology_and_solution"


def test_near_duplicate_rejection() -> None:
    existing = _signature(level_id="level_001", solution_hash="solution-a")
    candidate = replace(
        existing,
        level_id="level_002",
        solution_hash="solution-b",
        normalized_positions=(
            ("start", 0.0, 0.5),
            ("approach_switch", 0.31, 0.5),
            ("package", 0.5, 0.99),
            ("finish_switch", 0.69, 0.5),
            ("destination", 1.0, 1.0),
        ),
    )

    result = CandidateUniquenessService().check_duplicate(candidate, [existing])

    assert result.is_duplicate is True
    assert result.reason_code == "same_topology_and_layout"


def test_different_topology_is_allowed() -> None:
    existing = _signature(level_id="level_001")
    candidate = replace(existing, level_id="level_002", topology_hash="topology-b", solution_hash="solution-b")

    result = CandidateUniquenessService().check_duplicate(candidate, [existing])

    assert result.is_duplicate is False


def test_different_solution_order_lowers_similarity() -> None:
    existing = _signature(level_id="level_001")
    exact_score = CandidateUniquenessService().similarity_score(existing, existing)
    changed_solution = replace(existing, level_id="level_002", solution_hash="solution-b")

    changed_score = CandidateUniquenessService().similarity_score(changed_solution, existing)

    assert changed_score < exact_score
