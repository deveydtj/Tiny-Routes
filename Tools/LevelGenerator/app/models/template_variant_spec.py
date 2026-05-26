from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateVariantSpec:
    name: str
    template_name: str
    difficulty_names: tuple[str, ...]
    requires_swift_validation: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Template variant name is required")
        if not self.template_name.strip():
            raise ValueError("Template name is required")
        if not self.difficulty_names:
            raise ValueError("At least one difficulty is required")
        object.__setattr__(self, "name", self.name.strip().lower())
        object.__setattr__(self, "template_name", self.template_name.strip().lower())
        object.__setattr__(self, "difficulty_names", tuple(name.strip().lower() for name in self.difficulty_names))

    def supports_difficulty(self, difficulty_name: str) -> bool:
        return difficulty_name.strip().lower() in self.difficulty_names
