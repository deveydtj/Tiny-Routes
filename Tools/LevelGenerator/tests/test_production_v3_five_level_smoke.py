from __future__ import annotations

import json

from test_support.production_v3_smoke import run_five_level_smoke


def test_five_level_fixed_seed_smoke_uses_exact_v3_production_path(tmp_path) -> None:
    evidence = run_five_level_smoke(tmp_path)

    assert evidence.passed
    assert evidence.deterministic
    assert evidence.generator_architecture == "production_v3"
    assert evidence.generator_architecture_version == 3
    assert evidence.requested_count == evidence.selected_count == 5
    assert len(evidence.selected_candidate_ids) == 5
    assert len(set(evidence.behavior_signatures)) == 5
    assert evidence.stage_sequences == (
        (
            "blueprint",
            "composition",
            "strategy",
            "layout",
            "runtime",
            "quality",
        ),
    ) * 5
    assert evidence.parity_statuses == ("smoke_fixture_passed",) * 5
    assert evidence.fallback_count == 0
    assert evidence.stage_path_violation_count == 0
    assert evidence.behavior_duplicate_count == 0
    assert evidence.one_tap_or_less_count == 0
    assert evidence.selected_minimum_accepted_taps >= 2
    assert evidence.static_policy_solvable_count == 0
    assert evidence.unproven_optimal_count == 0
    assert evidence.parity_error_count == 0
    assert evidence.production_unchanged
    assert evidence.staging_artifact_count == 1
    assert evidence.rejected_candidate_count == 5
    assert evidence.automatic_retry_count == 5
    assert evidence.retry_variant_change_count == 5
    assert evidence.automatic_portfolio_selection
    assert evidence.manual_approval_required_count == 0
    assert evidence.manual_repair_required_count == 0
    assert len(evidence.level_logic_fingerprint) == 64
    assert len(evidence.solution_actions_fingerprint) == 64
    assert len(evidence.selection_result_fingerprint) == 64
    assert len(evidence.report_fingerprint) == 64
    json.dumps(evidence.to_dict(), sort_keys=True)
