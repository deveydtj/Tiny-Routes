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

    def supports_difficulty(self, difficulty_name: str) -> bool:
        return difficulty_name.strip().lower() in self.difficulty_names
