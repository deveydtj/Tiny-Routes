from __future__ import annotations

import pytest

from app.models import PuzzleExperienceTarget
from app.services import DifficultyTargetResolver, DifficultyTargetResolverService


def test_resolver_matches_locked_v3_difficulty_matrix() -> None:
    resolver = DifficultyTargetResolver()

    expected = {
        "easy": ((2, 3), (2, 3), 1, 1, 1, (1, 2), (0, 1), 1, 2.25),
        "medium": ((3, 4), (3, 5), 2, 1, 2, (1, 2), (1, 2), 2, 1.80),
        "hard": ((3, 5), (5, 7), 3, 2, 3, (2, 3), (1, 3), 2, 1.45),
        "expert": ((4, 6), (6, 10), 4, 3, 4, (3, 5), (2, 4), 3, 1.20),
    }

    assert resolver.valid_names == ["easy", "medium", "hard", "expert"]
    for difficulty, values in expected.items():
        target = resolver.resolve(difficulty)
        assert isinstance(target, PuzzleExperienceTarget)
        assert target.objective_count_range == values[0]
        assert target.meaningful_decision_range == values[1]
        assert target.planning_decision_minimum == values[2]
        assert target.adaptive_decision_minimum == values[3]
        assert target.dependency_depth_range[0] == values[4]
        assert target.state_change_range == values[5]
        assert target.revisit_range == values[6]
        assert target.fatal_mistake_cap == values[7]
        assert target.decision_window_targets[0] == values[8]

    assert [
        resolver.resolve(difficulty).rapid_multi_tap_encounter_cap
        for difficulty in resolver.band_order
    ] == [0, 1, 1, 2]
    assert all(
        resolver.resolve(difficulty).maximum_taps_per_rapid_burst == 2
        for difficulty in resolver.band_order
    )
    assert all(
        resolver.resolve(difficulty).minimum_state_change_visibility_seconds == 1.0
        for difficulty in resolver.band_order
    )


def test_resolver_is_normalized_deterministic_and_has_compatibility_spelling() -> None:
    resolver = DifficultyTargetResolverService()

    assert DifficultyTargetResolverService is DifficultyTargetResolver
    assert resolver.resolve(" Hard ") == resolver.resolve("hard")
    assert resolver.get_target("HARD") == resolver.resolve("hard")


@pytest.mark.parametrize("difficulty", ["tutorial", "auto", "unknown", ""])
def test_resolver_rejects_non_production_or_unresolved_difficulties(
    difficulty: str,
) -> None:
    with pytest.raises(ValueError):
        DifficultyTargetResolver().resolve(difficulty)


def test_targets_never_allow_trivial_production_blueprints() -> None:
    for difficulty in DifficultyTargetResolver.band_order:
        target = DifficultyTargetResolver().resolve(difficulty)
        assert target.objective_count_range[0] >= 2
        assert target.meaningful_decision_range[0] >= 2
        assert target.planning_decision_minimum >= 1
        assert target.adaptive_decision_minimum >= 1
        assert target.state_change_range[0] >= 1
        assert target.recoverable_mistake_range[0] >= 1
