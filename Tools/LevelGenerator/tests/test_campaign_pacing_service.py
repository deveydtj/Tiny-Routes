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


def test_campaign_pacing_penalizes_repeated_special_mechanics_and_large_profile() -> None:
    previous = _signature(
        level_id="level_031",
        template_name="fake_shortcut",
        difficulty="hard",
        mechanic_tags=("fake_shortcut", "detour"),
        primary_mechanic_tag="fake_shortcut",
        topology_class="detour_gate",
        layout_size_profile="large_portrait",
    )
    candidate = _signature(
        level_id="level_032",
        template_name="long_detour_gate",
        difficulty="hard",
        mechanic_tags=("fake_shortcut", "detour", "package_gate"),
        primary_mechanic_tag="fake_shortcut",
        topology_class="detour_gate",
        layout_size_profile="large_portrait",
    )

    result = CampaignPacingService().score(
        candidate,
        [previous],
        estimated_band="hard",
        target_band="hard",
    )

    assert "campaign_repeated_fake_shortcut_usage" in result.penalties
    assert "campaign_repeated_large_portrait_profile" in result.penalties
    assert "campaign_repeated_switch_count_pattern" in result.penalties
    assert result.details["sameMapSizeProfileInRecentWindow"] == 1


def test_campaign_pacing_introduces_one_early_mechanic_at_a_time() -> None:
    previous = _signature(mechanic_tags=("package",), primary_mechanic_tag="package")
    candidate = _signature(
        level_id="level_002",
        mechanic_tags=("package", "switch", "revisit"),
        primary_mechanic_tag="switch",
    )

    result = CampaignPacingService().score(
        candidate, [previous], estimated_band="tutorial", target_band="tutorial"
    )

    assert "campaign_multiple_mechanics_introduced" in result.penalties
    assert result.details["newMechanics"] == ("revisit", "switch")


def test_campaign_pacing_requires_recovery_after_punitive_level() -> None:
    punitive = _signature(
        failure_outcome_distribution=(("success", 1), ("dead_end", 4)),
    )
    candidate = replace(punitive, level_id="level_032", topology_hash="topology-b")

    result = CampaignPacingService().score(
        candidate, [punitive], estimated_band="hard", target_band="hard"
    )

    assert "campaign_missing_recovery_level" in result.penalties
    assert result.details["previousPunitiveScore"] == 0.8


def test_campaign_pacing_grows_dependency_before_tightening_timing() -> None:
    previous = _signature(
        solution_decision_timing_pattern=(1.0, 4.0),
        decision_dependency_pattern=(2, 2, 0.5),
    )
    candidate = replace(
        previous,
        level_id="level_020",
        solution_decision_timing_pattern=(1.0, 1.2),
    )

    result = CampaignPacingService().score(
        candidate, [previous], estimated_band="medium", target_band="medium"
    )

    assert "campaign_timing_before_dependency_progression" in result.penalties
