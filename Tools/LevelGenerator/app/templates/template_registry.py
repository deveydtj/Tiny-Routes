from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..random_source import RandomSource
from .base_template import LevelTemplate
from .multi_switch_chain_template import MultiSwitchChainTemplate
from .package_gate_template import PackageGateTemplate
from .return_loop_template import ReturnLoopTemplate
from .ring_route_template import RingRouteTemplate
from .single_switch_template import SingleSwitchTemplate
from .straight_delivery_template import StraightDeliveryTemplate


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, LevelTemplate] = {
            template.name: template
            for template in [
                StraightDeliveryTemplate(),
                SingleSwitchTemplate(),
                PackageGateTemplate(),
                ReturnLoopTemplate(),
                MultiSwitchChainTemplate(),
                RingRouteTemplate(),
            ]
        }

    @property
    def valid_names(self) -> list[str]:
        return sorted([*self._templates, "mixed"])

    def get(self, name: str) -> LevelTemplate:
        key = name.strip().lower()
        if key == "mixed":
            raise ValueError("Use choose() for mixed template selection")
        try:
            return self._templates[key]
        except KeyError as exc:
            raise ValueError(f"Unknown template: {name}") from exc

    def supported_templates(self, preset: DifficultyPreset, include_swift_required: bool = True) -> list[LevelTemplate]:
        templates = [template for template in self._templates.values() if template.supports_difficulty(preset)]
        if not include_swift_required:
            templates = [template for template in templates if not template.requires_swift_validation]
        return templates

    def choose(
        self,
        name: str,
        preset: DifficultyPreset,
        rng: RandomSource,
        include_swift_required: bool = True,
        weights_override: dict[str, int] | None = None,
    ) -> LevelTemplate:
        key = name.strip().lower()
        if key != "mixed":
            template = self.get(key)
            if not template.supports_difficulty(preset):
                raise ValueError(f"Template '{key}' does not support difficulty '{preset.name}'")
            if template.requires_swift_validation and not include_swift_required:
                raise ValueError(f"Template '{key}' requires Swift validation before production output")
            return template

        weighted = [
            (template, self._weight_for(template.name, preset.name, weights_override))
            for template in self.supported_templates(preset, include_swift_required=include_swift_required)
        ]
        if not weighted:
            raise ValueError(f"No templates support difficulty '{preset.name}'")
        return rng.weighted_choice(weighted)

    def _weight_for(
        self,
        template_name: str,
        difficulty_name: str,
        weights_override: dict[str, int] | None = None,
    ) -> int:
        if weights_override is not None and template_name in weights_override:
            return weights_override[template_name]
        weights = {
            "tutorial": {"straight_delivery": 5, "single_switch": 3},
            "easy": {"single_switch": 5, "package_gate": 3},
            "medium": {"package_gate": 3, "return_loop": 3, "multi_switch_chain": 4},
            "hard": {"multi_switch_chain": 5, "ring_route": 2},
        }
        return weights.get(difficulty_name, {}).get(template_name, 1)
