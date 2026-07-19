from __future__ import annotations

import json

from app.paths import find_repo_root


def test_shared_runtime_parity_fixture_set_is_complete_and_valid_json() -> None:
    root = find_repo_root() / "SharedFixtures" / "RuntimeParity"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected_ids = {
        "straight_no_switch", "two_way_too_early", "two_way_inside_window",
        "noneligible_downstream_switch", "tap_after_commitment", "three_way_two_rotations",
        "four_way_three_rotations", "revisit_different_state", "package_before_destination",
        "destination_before_package", "dead_end_failure", "time_limit_failure", "cycle_safety_limit",
        "package_gate_normalization", "package_gate_revisit_rotation",
        "objective_road_state_progression",
    }
    assert {item["id"] for item in manifest["fixtures"]} == expected_ids
    for item in manifest["fixtures"]:
        payloads = [json.loads((root / item[key]).read_text(encoding="utf-8")) for key in ("level", "events", "expected")]
        assert all(isinstance(payload, dict) for payload in payloads)
        assert payloads[1]["description"]
        assert payloads[2]["description"]
