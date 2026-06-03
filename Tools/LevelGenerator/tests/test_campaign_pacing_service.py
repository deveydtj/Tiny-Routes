from __future__ import annotations

from dataclasses import replace

from app.models.candidate_signature import CandidateSignature
from app.services.campaign_pacing_service import CampaignPacingService


def _signature(**overrides) -> CandidateSignature:
    values = {
        "level_id": "level_001",
        "template_name": "single_switch",
        "difficulty": "easy",
        "node_count": 6,
        "edge_count": 6,
        "switch_count": 1,
        "required_tap_count": 1,
        "dead_end_count": 1,
        "topology_hash": "topology-a",
        "layout_hash": "layout-a",
        "solution_hash": "solution-a",
        "normalized_positions": (),
        "mechanic_tags": ("single_switch", "dead_end"),
        "primary_mechanic_tag": "single_switch",
        "topology_class": "single_branch",
        "required_path_length": 4,
        "layout_orientation": "horizontal",
    }
    values.update(overrides)
    return CandidateSignature(**values)


def test_campaign_pacing_penalizes_repeated_topology_and_primary_mechanic() -> None:
    previous = _signature(level_id="level_012")
    candidate = replace(previous, level_id="level_013", template_name="safe_dead_end_choice")

    result = CampaignPacingService().score(
        candidate,
        [previous],
        estimated_band="easy",
        target_band="easy",
    )

    assert result.score < 1
    assert "campaign_repeated_topology_class" in result.penalties
    assert "campaign_repeated_primary_mechanic" in result.penalties
    assert result.details["sameTopologyClassInRecentWindow"] == 1
    assert result.details["nearbyMechanicTagOverlap"] == 1.0


def test_campaign_pacing_allows_distinct_topology_and_mechanic() -> None:
    previous = _signature(level_id="level_012")
    candidate = _signature(
        level_id="level_013",
        template_name="package_gate",
        topology_hash="topology-b",
        topology_class="package_gate",
        mechanic_tags=("package_gate", "multi_switch"),
        primary_mechanic_tag="package_gate",
        required_tap_count=2,
    )

    result = CampaignPacingService().score(
        candidate,
        [previous],
        estimated_band="easy",
        target_band="easy",
    )

    assert "campaign_repeated_topology_class" not in result.penalties
    assert "campaign_repeated_primary_mechanic" not in result.penalties
    assert result.details["sameTopologyClassInRecentWindow"] == 0
    assert result.details["nearbyMechanicTagOverlap"] == 0.0
