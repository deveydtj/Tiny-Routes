from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    weight: int = 1
    requires_swift_validation: bool = False
