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
    assert evidence.production_unchanged
    assert evidence.staging_artifact_count == 1
    json.dumps(evidence.to_dict(), sort_keys=True)
