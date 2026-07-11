from __future__ import annotations

import json
from pathlib import Path

import pytest

from tiny_routes_core import LevelRules, SwitchInteractionMode


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_missing_rules_use_swift_compatible_legacy_defaults() -> None:
    rules = LevelRules.from_level_dict({"schemaVersion": 1})

    assert rules == LevelRules.legacy_defaults()
    assert rules.switch_interaction_mode is SwitchInteractionMode.LEGACY_GLOBAL


def test_version_two_rules_round_trip_with_canonical_json_names() -> None:
    payload = {
        "switchInteractionMode": "liveLookahead",
        "switchLookaheadSeconds": 1.5,
        "switchTapCooldownSeconds": 0.15,
    }

    rules = LevelRules.from_dict(payload)

    assert rules.to_dict() == payload
    assert rules.validation_messages() == []


@pytest.mark.parametrize("value", [-0.1, float("inf"), float("nan"), "1.0", True])
def test_invalid_lookahead_values_are_reported(value: object) -> None:
    rules = LevelRules.from_dict({"switchLookaheadSeconds": value})
    assert "invalid_switch_lookahead_seconds" in rules.validation_messages()


@pytest.mark.parametrize("value", [-0.1, float("inf"), float("nan"), "0.1", False])
def test_invalid_cooldown_values_are_reported(value: object) -> None:
    rules = LevelRules.from_dict({"switchTapCooldownSeconds": value})
    assert "invalid_switch_tap_cooldown_seconds" in rules.validation_messages()


def test_unknown_mode_is_rejected_with_a_stable_message() -> None:
    with pytest.raises(ValueError, match="unknown_switch_interaction_mode"):
        LevelRules.from_dict({"switchInteractionMode": "futureMode"})


def test_every_production_level_rules_document_decodes() -> None:
    levels = sorted((REPOSITORY_ROOT / "TinyRoutes/Resources/Levels").glob("*.json"))
    assert levels

    for path in levels:
        level = json.loads(path.read_text(encoding="utf-8"))
        rules = LevelRules.from_level_dict(level)
        assert rules.validation_messages() == [], path
