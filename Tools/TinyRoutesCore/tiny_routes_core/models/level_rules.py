"""Versioned switch-interaction rules shared by the Python tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Mapping


class SwitchInteractionMode(str, Enum):
    """Serialized values must remain identical to ``SwitchInteractionMode`` in Swift."""

    LEGACY_GLOBAL = "legacyGlobal"
    LIVE_LOOKAHEAD = "liveLookahead"


@dataclass(frozen=True)
class LevelRules:
    """Gameplay rule values with explicit JSON name conversion.

    Numeric validation is intentionally separate from decoding so editors can load
    malformed documents and show all relevant messages. An unknown interaction
    mode cannot be represented and therefore raises ``ValueError`` while decoding.
    """

    switch_interaction_mode: SwitchInteractionMode
    switch_lookahead_seconds: Any
    switch_tap_cooldown_seconds: Any

    DEFAULT_LOOKAHEAD_SECONDS = 1.35
    DEFAULT_TAP_COOLDOWN_SECONDS = 0.12

    @classmethod
    def legacy_defaults(cls) -> "LevelRules":
        return cls(
            switch_interaction_mode=SwitchInteractionMode.LEGACY_GLOBAL,
            switch_lookahead_seconds=cls.DEFAULT_LOOKAHEAD_SECONDS,
            switch_tap_cooldown_seconds=cls.DEFAULT_TAP_COOLDOWN_SECONDS,
        )

    @classmethod
    def from_level_dict(cls, level: Mapping[str, Any]) -> "LevelRules":
        """Decode rules from a complete level document, applying legacy defaults."""

        rules = level.get("rules")
        if rules is None:
            return cls.legacy_defaults()
        if not isinstance(rules, Mapping):
            raise ValueError("rules_must_be_an_object")
        return cls.from_dict(rules)

    @classmethod
    def from_dict(cls, rules: Mapping[str, Any] | None) -> "LevelRules":
        """Decode a serialized ``rules`` object; ``None`` means a legacy level."""

        if rules is None:
            return cls.legacy_defaults()
        if not isinstance(rules, Mapping):
            raise ValueError("rules_must_be_an_object")

        raw_mode = rules.get("switchInteractionMode", SwitchInteractionMode.LEGACY_GLOBAL.value)
        try:
            mode = SwitchInteractionMode(raw_mode)
        except (TypeError, ValueError) as error:
            raise ValueError(f"unknown_switch_interaction_mode:{raw_mode!r}") from error

        return cls(
            switch_interaction_mode=mode,
            switch_lookahead_seconds=rules.get(
                "switchLookaheadSeconds", cls.DEFAULT_LOOKAHEAD_SECONDS
            ),
            switch_tap_cooldown_seconds=rules.get(
                "switchTapCooldownSeconds", cls.DEFAULT_TAP_COOLDOWN_SECONDS
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Encode the version-2 ``rules`` object using the canonical JSON names."""

        return {
            "switchInteractionMode": self.switch_interaction_mode.value,
            "switchLookaheadSeconds": self.switch_lookahead_seconds,
            "switchTapCooldownSeconds": self.switch_tap_cooldown_seconds,
        }

    def validation_messages(self) -> list[str]:
        messages: list[str] = []
        if not self._is_finite_nonnegative(self.switch_lookahead_seconds):
            messages.append("invalid_switch_lookahead_seconds")
        if not self._is_finite_nonnegative(self.switch_tap_cooldown_seconds):
            messages.append("invalid_switch_tap_cooldown_seconds")
        return messages

    @staticmethod
    def _is_finite_nonnegative(value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )
