from __future__ import annotations

import json

from app.paths import find_repo_root
from app.services.fixed_seed_regression_service import DEFAULT_SUITES


def test_fixed_seed_release_suite_catalog_and_hashes_are_complete() -> None:
    root = find_repo_root()
    baselines = json.loads(
        (root / "Tools/LevelGenerator/fixtures/fixed_seed_regression_hashes.json").read_text()
    )
    suite_names = {suite.name for suite in DEFAULT_SUITES}

    assert suite_names == {
        "tutorial",
        "easy",
        "medium",
        "hard",
        "expert",
        "mixed_30_level_campaign",
        "revisit_heavy",
        "three_four_way_switches",
        "conditional_roads",
    }
    assert set(baselines) == suite_names
    assert all(len(value) == 64 for value in baselines.values())
    assert next(suite for suite in DEFAULT_SUITES if suite.name == "mixed_30_level_campaign").count == 30
