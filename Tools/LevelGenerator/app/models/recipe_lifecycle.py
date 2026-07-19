from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecipeLifecycleStatus(str, Enum):
    """Eligibility of a fixed recipe family or variant in the V3 architecture."""

    PRODUCTION_V3 = "production_v3"
    FIXTURE_ONLY = "fixture_only"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class RecipeLifecycleRecord:
    family_name: str
    variant_name: str | None
    status: RecipeLifecycleStatus
    reason: str

    def __post_init__(self) -> None:
        family_name = self.family_name.strip().lower()
        variant_name = self.variant_name.strip().lower() if self.variant_name else None
        reason = self.reason.strip()
        if not family_name:
            raise ValueError("Recipe lifecycle family name is required")
        if not reason:
            raise ValueError("Recipe lifecycle reason is required")
        object.__setattr__(self, "family_name", family_name)
        object.__setattr__(self, "variant_name", variant_name)
        object.__setattr__(self, "reason", reason)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "family": self.family_name,
            "variant": self.variant_name,
            "status": self.status.value,
            "reason": self.reason,
        }
