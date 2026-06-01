from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RecipeVariantSpec:
    name: str
    family_name: str
    difficulty_names: tuple[str, ...]
    legacy_template_name: str | None = None
    requires_swift_validation: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)
    intended_mechanic: str = ""
    required_player_skill: str = ""
    allowed_switch_counts: tuple[int, int] | None = None
    allowed_tap_counts: tuple[int, int] | None = None
    allows_repeated_taps: bool = False
    visual_layout_requirements: tuple[str, ...] = field(default_factory=tuple)
    design_reason: str = ""
    mechanic_tags: tuple[str, ...] = field(default_factory=tuple)
    unlock_requirement: str | None = None
    prior_mechanic_dependency: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Recipe variant name is required")
        if not self.family_name.strip():
            raise ValueError("Recipe family name is required")
        if not self.difficulty_names:
            raise ValueError("At least one difficulty is required")
        object.__setattr__(self, "name", self.name.strip().lower())
        object.__setattr__(self, "family_name", self.family_name.strip().lower())
        object.__setattr__(
            self,
            "difficulty_names",
            tuple(name.strip().lower() for name in self.difficulty_names),
        )
        if self.legacy_template_name is not None:
            object.__setattr__(self, "legacy_template_name", self.legacy_template_name.strip().lower())
        object.__setattr__(
            self,
            "mechanic_tags",
            tuple(tag.strip().lower() for tag in self.mechanic_tags if tag.strip()),
        )
        object.__setattr__(
            self,
            "visual_layout_requirements",
            tuple(requirement.strip() for requirement in self.visual_layout_requirements if requirement.strip()),
        )
        if self.unlock_requirement is not None:
            object.__setattr__(self, "unlock_requirement", self.unlock_requirement.strip() or None)
        if self.prior_mechanic_dependency is not None:
            object.__setattr__(
                self,
                "prior_mechanic_dependency",
                self.prior_mechanic_dependency.strip() or None,
            )

    def supports_difficulty(self, difficulty_name: str) -> bool:
        return difficulty_name.strip().lower() in self.difficulty_names

    def mechanic_metadata(self) -> dict[str, object]:
        return {
            "intendedMechanic": self.intended_mechanic,
            "supportedDifficulties": list(self.difficulty_names),
            "requiredPlayerSkill": self.required_player_skill,
            "allowedSwitchCounts": list(self.allowed_switch_counts) if self.allowed_switch_counts else None,
            "allowedTapCounts": list(self.allowed_tap_counts) if self.allowed_tap_counts else None,
            "allowsRepeatedTaps": self.allows_repeated_taps,
            "visualLayoutRequirements": list(self.visual_layout_requirements),
            "designReason": self.design_reason,
            "mechanicTags": list(self.mechanic_tags),
            "unlockRequirement": self.unlock_requirement,
            "priorMechanicDependency": self.prior_mechanic_dependency,
        }
