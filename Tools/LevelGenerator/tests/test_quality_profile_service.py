from __future__ import annotations

from dataclasses import replace

import pytest

from app.models.quality_profile import QualityProfileEvidence
from app.services.difficulty_target_resolver import DifficultyTargetResolver
from app.services.quality_profile_service import (
    CURRENT_QUALITY_PROFILE_VERSION,
    QualityProfileService,
)


def test_current_profile_is_versioned_fingerprinted_and_drives_targets() -> None:
    service = QualityProfileService()
    profile = service.load_current()
    resolver = DifficultyTargetResolver(service)

    assert profile.version == CURRENT_QUALITY_PROFILE_VERSION == "1.0.0"
    assert len(profile.fingerprint) == 64
    assert resolver.quality_profile.fingerprint == profile.fingerprint
    assert resolver.resolve("hard") == profile.difficulty_targets["hard"]
    assert profile.protected_invariants["rejectStaticPolicy"] is True
    assert profile.protected_invariants["requireProvenUniqueOptimum"] is True
    assert all(
        target.meaningful_decision_range[0] >= 2
        and target.planning_decision_minimum >= 1
        and target.adaptive_decision_minimum >= 1
        and target.state_change_range[0] >= 1
        for target in profile.difficulty_targets.values()
    )


def test_tuning_requires_new_version_and_updated_evidence() -> None:
    service = QualityProfileService()
    previous = service.load_current()
    weights = dict(previous.ranking_weights)
    weights["planningDepth"] += 0.01
    weights["visualReadability"] -= 0.01
    same_version = replace(previous, ranking_weights=weights)

    with pytest.raises(ValueError, match="explicit version change"):
        service.validate_transition(previous, same_version)

    new_version_old_evidence = replace(same_version, version="1.1.0")
    with pytest.raises(ValueError, match="updated playtest evidence"):
        service.validate_transition(previous, new_version_old_evidence)

    valid = replace(
        new_version_old_evidence,
        evidence=QualityProfileEvidence(
            playtest_evidence="playtests/v3-round-2.json",
            fixed_seed_comparison="fixed-seed/v3-round-2.json",
        ),
    )
    service.validate_transition(previous, valid)


def test_profile_model_refuses_weakened_non_negotiable_invariants() -> None:
    profile = QualityProfileService().load_current()
    weakened = dict(profile.protected_invariants)
    weakened["rejectStaticPolicy"] = False

    with pytest.raises(ValueError, match="cannot be disabled"):
        replace(profile, protected_invariants=weakened, version="2.0.0")
