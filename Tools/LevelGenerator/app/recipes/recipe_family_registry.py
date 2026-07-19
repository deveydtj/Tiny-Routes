from __future__ import annotations

from ..models.difficulty_preset import DifficultyPreset
from ..random_source import RandomSource
from .base_recipe import MechanicRecipeGenerator, RecipeFamily
from .expanded_recipe_family import ExpandedRecipeFamily, expanded_recipe_family_definitions
from .template_recipe_family import TemplateRecipeFamily, template_recipe_family_definitions


class RecipeFamilyRegistry(MechanicRecipeGenerator):
    QUARANTINED_FAMILY_REASONS: dict[str, str] = {
        "branch_then_rejoin_with_wrong_order": "claimed_rejoin_not_detected",
        "late_route_reversal": "behavior_isomorphic_alias:controlled_repeated_taps",
        "multi_four_way_route": "behavior_isomorphic_alias:four_way_package_gate",
        "return_loop_intro": "claimed_cycle_not_detected",
        "return_loop_with_gate": "behavior_isomorphic_alias:controlled_repeated_taps",
        "ring_route_gate": "claimed_ring_not_detected",
        "multi_switch_revisit": "behavior_isomorphic_alias:controlled_repeated_taps",
    }

    def __init__(self) -> None:
        self._families: dict[str, RecipeFamily] = {
            family.name: family
            for family in [
                *[TemplateRecipeFamily(definition) for definition in template_recipe_family_definitions()],
                *[ExpandedRecipeFamily(definition) for definition in expanded_recipe_family_definitions()],
            ]
        }
        self._validate_topology_rules()

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
        families = [
            family
            for family in self._families.values()
            if family.supports_difficulty(preset) and not self.is_quarantined(family.name)
        ]
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
            quarantine_reason = self.quarantine_reason(key)
            if quarantine_reason is not None:
                raise ValueError(
                    f"Recipe family '{key}' is quarantined from production selection: "
                    f"{quarantine_reason}"
                )
            if not family.supports_difficulty(preset):
                raise ValueError(f"Recipe family '{key}' does not support difficulty '{preset.name}'")
            if family.requires_swift_validation and not include_swift_required:
                raise ValueError(f"Recipe family '{key}' requires Swift validation before production output")
            return family

        weighted = [
            (family, self.weight_for(family.name, preset.name, weights_override))
            for family in self.supported_families(preset, include_swift_required=include_swift_required)
        ]
        if not weighted:
            raise ValueError(f"No recipe families support difficulty '{preset.name}'")
        return rng.weighted_choice(weighted)

    def is_quarantined(self, family_name: str) -> bool:
        return family_name.strip().lower() in self.QUARANTINED_FAMILY_REASONS

    def quarantine_reason(self, family_name: str) -> str | None:
        return self.QUARANTINED_FAMILY_REASONS.get(family_name.strip().lower())

    def quarantined_family_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.QUARANTINED_FAMILY_REASONS))

    def weight_for(
        self,
        family_name: str,
        difficulty_name: str,
        weights_override: dict[str, int] | None = None,
    ) -> int:
        if weights_override is not None and family_name in weights_override:
            return weights_override[family_name]
        weights = {
            "tutorial": {
                "straight_delivery_intro": 6,
                "single_switch_intro": 4,
                "single_switch_wrong_dead_end": 3,
                "package_before_destination_intro": 4,
                "straight_delivery": 3,
                "single_switch": 2,
            },
            "easy": {
                "single_switch_package_choice": 4,
                "two_switch_order_intro": 3,
                "short_detour_gate": 3,
                "safe_dead_end_choice": 3,
                "package_gate_simple": 4,
                "single_switch": 2,
                "package_gate": 2,
            },
            "medium": {
                "multi_switch_order": 4,
                "package_gate_double_choice": 4,
                "return_loop_intro": 3,
                "split_path_rejoin": 3,
                "fake_shortcut": 3,
                "hub_choice": 2,
                "package_gate": 1,
                "return_loop": 1,
                "multi_switch_chain": 2,
            },
            "hard": {
                "return_loop_with_gate": 4,
                "ring_route_gate": 4,
                "multi_switch_revisit": 3,
                "package_inside_loop": 3,
                "two_phase_route": 4,
                "branch_then_rejoin_with_wrong_order": 3,
                "multi_switch_chain": 1,
                "ring_route": 1,
            },
            "expert": {
                "four_way_intro": 2,
                "four_way_package_gate": 4,
                "four_way_ring": 4,
                "multi_four_way_route": 4,
                "controlled_repeated_taps": 3,
                "late_route_reversal": 3,
                "fake_shortcut": 3,
                "split_path_rejoin": 3,
                "hub_choice": 3,
                "long_detour_gate": 3,
                "four_way_intersection": 2,
                "multi_switch_chain": 1,
                "ring_route": 1,
            },
        }
        return weights.get(difficulty_name, {}).get(family_name, 1)

    def _validate_topology_rules(self) -> None:
        for family in self._families.values():
            if not family.variants:
                raise ValueError(f"Recipe family '{family.name}' must define at least one variant")
            for variant in family.variants:
                rules = variant.topology_rules
                if rules is None:
                    raise ValueError(
                        f"Recipe family '{family.name}' variant '{variant.name}' is missing topology rules"
                    )
                if variant.requires_swift_validation != rules.requires_swift_runtime_validation:
                    raise ValueError(
                        f"Recipe family '{family.name}' variant '{variant.name}' has mismatched Swift validation rules"
                    )
