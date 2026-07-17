from __future__ import annotations

from dataclasses import dataclass, field

from .recipe_topology_rules import RecipeTopologyRules


@dataclass(frozen=True)
class RecipeVariantSpec:
    name: str
    family_name: str
    difficulty_names: tuple[str, ...]
    topology_rules: RecipeTopologyRules
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
    primary_mechanic_tag: str = ""
    topology_class: str = ""
    unlock_requirement: str | None = None
    prior_mechanic_dependency: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Recipe variant name is required")
        if not self.family_name.strip():
            raise ValueError("Recipe family name is required")
        if not self.difficulty_names:
            raise ValueError("At least one difficulty is required")
        if self.topology_rules is None:
            raise ValueError("Recipe topology rules are required")
        object.__setattr__(self, "name", self.name.strip().lower())
        object.__setattr__(self, "family_name", self.family_name.strip().lower())
        object.__setattr__(
            self,
            "difficulty_names",
            tuple(name.strip().lower() for name in self.difficulty_names),
        )
        object.__setattr__(
            self,
            "mechanic_tags",
            tuple(tag.strip().lower() for tag in self.mechanic_tags if tag.strip()),
        )
        primary_mechanic_tag = self.primary_mechanic_tag.strip().lower()
        if not primary_mechanic_tag and self.mechanic_tags:
            primary_mechanic_tag = self.mechanic_tags[0]
        object.__setattr__(self, "primary_mechanic_tag", primary_mechanic_tag)
        object.__setattr__(self, "topology_class", self.topology_class.strip().lower())
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
            "primaryMechanicTag": self.primary_mechanic_tag,
            "topologyClass": self.topology_class,
            "topologyRules": self.topology_rules.to_metadata(),
            "unlockRequirement": self.unlock_requirement,
            "priorMechanicDependency": self.prior_mechanic_dependency,
        }
