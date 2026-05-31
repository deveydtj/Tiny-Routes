from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..random_source import RandomSource
from .base_recipe import MechanicRecipeGenerator, RecipeFamily
from .template_recipe_family import TemplateRecipeFamily, template_recipe_family_definitions


class RecipeFamilyRegistry(MechanicRecipeGenerator):
    def __init__(self) -> None:
        self._families: dict[str, RecipeFamily] = {
            family.name: family
            for family in [TemplateRecipeFamily(definition) for definition in template_recipe_family_definitions()]
        }

    def valid_family_names(self) -> list[str]:
        return sorted([*self._families, "mixed"])

    def get_family(self, name: str) -> RecipeFamily:
        key = name.strip().lower()
        if key == "mixed":
            raise ValueError("Use choose_family() for mixed recipe family selection")
        try:
            return self._families[key]
        except KeyError as exc:
            raise ValueError(f"Unknown recipe family: {name}") from exc

    def supported_families(self, preset: DifficultyPreset, include_swift_required: bool = True) -> list[RecipeFamily]:
        families = [family for family in self._families.values() if family.supports_difficulty(preset)]
        if not include_swift_required:
            families = [family for family in families if not family.requires_swift_validation]
        return families

    def choose_family(
        self,
        name: str,
        preset: DifficultyPreset,
        rng: RandomSource,
        include_swift_required: bool = True,
        weights_override: dict[str, int] | None = None,
    ) -> RecipeFamily:
        key = name.strip().lower()
        if key != "mixed":
            family = self.get_family(key)
            if not family.supports_difficulty(preset):
                raise ValueError(f"Recipe family '{key}' does not support difficulty '{preset.name}'")
            if family.requires_swift_validation and not include_swift_required:
                raise ValueError(f"Recipe family '{key}' requires Swift validation before production output")
            return family

        weighted = [
            (family, self._weight_for(family.name, preset.name, weights_override))
            for family in self.supported_families(preset, include_swift_required=include_swift_required)
        ]
        if not weighted:
            raise ValueError(f"No recipe families support difficulty '{preset.name}'")
        return rng.weighted_choice(weighted)

    def _weight_for(
        self,
        family_name: str,
        difficulty_name: str,
        weights_override: dict[str, int] | None = None,
    ) -> int:
        if weights_override is not None and family_name in weights_override:
            return weights_override[family_name]
        weights = {
            "tutorial": {"straight_delivery": 5, "single_switch": 3},
            "easy": {"single_switch": 5, "package_gate": 3},
            "medium": {"package_gate": 3, "return_loop": 3, "multi_switch_chain": 4},
            "hard": {"multi_switch_chain": 5, "ring_route": 2},
            "expert": {"four_way_intersection": 5, "multi_switch_chain": 2, "ring_route": 2},
        }
        return weights.get(difficulty_name, {}).get(family_name, 1)
