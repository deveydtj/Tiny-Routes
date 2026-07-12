from __future__ import annotations

import inspect
import shutil
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..map_import.map_seed_to_template_adapter import MapSeedToTemplateAdapter
from ..map_import.osm_seed_importer import MapSeedGraph
from ..models.generation_result import GenerationResult
from ..models.stage_result import CandidateStageResult, StageResult
from ..paths import find_repo_root, get_default_reports_directory
from ..random_source import RandomSource
from ..repositories.existing_level_repository import ExistingLevelRepository
from ..repositories.generated_level_repository import GeneratedLevelRepository
from ..repositories.generation_report_repository import GenerationReportRepository
from ..recipes.recipe_family_registry import RecipeFamilyRegistry
from ..templates.template_registry import TemplateRegistry
from .topology_solver_service import TopologySolverService
from .candidate_rejection_service import CandidateRejectionService
from .candidate_signature_service import CandidateSignatureService
from .candidate_portfolio_selection_service import CandidatePortfolioSelectionService
from .candidate_uniqueness_service import CandidateUniquenessService
from .difficulty_curve_service import DifficultyCurveService
from .difficulty_service import DifficultyService
from .decision_profile_service import DecisionProfileService
from .generated_level_validation_service import GeneratedLevelValidationService
from .generation_quality_service import GenerationQualityService
from .level_resource_sync_service import LevelResourceSyncService
from .layout_variant_service import LayoutVariantService
from .recipe_to_level_builder_service import RecipeToLevelBuilderService
from .runtime_parity_validator import RuntimeParityValidator
from .swift_test_service import SwiftTestService


class LevelGenerationService:
    MINIMUM_TOTAL_QUALITY = 0.45
    MINIMUM_TOTAL_SCORE_BY_DIFFICULTY = {
        "tutorial": 65.0,
        "easy": 70.0,
        "medium": 75.0,
        "hard": 80.0,
        "expert": 85.0,
    }
    MINIMUM_SWITCH_CLARITY = 0.40
    MINIMUM_RUNTIME_CONFIDENCE = 0.75
    MAXIMUM_SELECTION_SIMILARITY = 0.87
    MAX_REJECTION_MESSAGES = 50
    MAX_DIVERSITY_DECISIONS = 200
    ROUTE_INTEREST_GATED_DIFFICULTIES = {"medium", "hard", "expert"}
    SIMPLE_CHAIN_TOPOLOGIES = {"two_switch_order"}
    PLAYTEST_BATCH_DUPLICATE_THRESHOLD = 0.98
    PLAYTEST_EXISTING_DUPLICATE_THRESHOLD = 0.98
    PLAYTEST_SELECTION_SIMILARITY_THRESHOLD = 0.98
    PLAYTEST_ROUTE_INTEREST_RELAXATION = {
        "medium": 0.16,
        "hard": 0.18,
        "expert": 0.16,
    }
    PLAYTEST_ROUTE_INTEREST_LATE_RELAXATION = 0.06
    STRONG_ROUTE_INTEREST_TAGS = {
        "fake_shortcut",
        "split_rejoin",
        "correct_detour",
        "loop_or_revisit",
        "two_phase",
        "package_gate_tension",
        "multi_exit_hub",
    }

    def __init__(self) -> None:
        self.difficulty_service = DifficultyService()
        self.difficulty_curve_service = DifficultyCurveService()
        self.template_registry = TemplateRegistry()
        self.recipe_family_registry = RecipeFamilyRegistry()
        self.validation_service = GeneratedLevelValidationService()
        self.generated_level_repository = GeneratedLevelRepository()
        self.report_repository = GenerationReportRepository()
        self.signature_service = CandidateSignatureService()
        self.existing_level_repository = ExistingLevelRepository(self.signature_service)
        self.uniqueness_service = CandidateUniquenessService()
        self.portfolio_selection_service = CandidatePortfolioSelectionService(self.uniqueness_service)
        self.quality_service = GenerationQualityService()
        self.map_seed_adapter = MapSeedToTemplateAdapter()
        self.resource_sync_service = LevelResourceSyncService()
        self.recipe_to_level_builder = RecipeToLevelBuilderService()
        self.layout_variant_service = LayoutVariantService()
        self.abstract_puzzle_solver = TopologySolverService()
        self.runtime_parity_validator = RuntimeParityValidator()
        self.decision_profile_service = DecisionProfileService()

    def generate(self, config: GenerationConfig) -> GenerationResult:
        from .batch_orchestration_service import BatchOrchestrationService

        return BatchOrchestrationService(self).generate(config)

    def _validate_generation_mode(self, config: GenerationConfig) -> None:
        if config.generation_mode == "legacy_template":
            return
        if config.template_name not in self.recipe_family_registry.valid_family_names():
            raise ValueError(f"Unknown recipe family: {config.template_name}")

    def _validate_template(self, template_name: str, config: GenerationConfig) -> None:
        if not config.uses_legacy_templates:
            return
        if template_name not in self.template_registry.valid_names:
            raise ValueError(f"Unknown template: {template_name}")
        if (
            template_name == "mixed"
            and config.difficulty == "hard"
            and not config.dry_run
            and not config.run_swift_tests
        ):
            preset = self.difficulty_service.get_preset("hard")
            eligible_without_swift = self.template_registry.supported_templates(
                preset,
                include_swift_required=False,
            )
            eligible_with_swift = self.template_registry.supported_templates(
                preset,
                include_swift_required=True,
            )
            if len(eligible_without_swift) <= 1 and len(eligible_with_swift) > len(eligible_without_swift):
                without_swift_names = ", ".join(sorted(template.name for template in eligible_without_swift)) or "none"
                swift_only_names = ", ".join(
                    sorted(
                        template.name
                        for template in eligible_with_swift
                        if template.name not in {candidate.name for candidate in eligible_without_swift}
                    )
                )
                raise ValueError(
                    "Hard mixed production generation is too narrow without Swift validation. "
                    f"Eligible without `--swift-tests`: {without_swift_names}. "
                    f"Enable `--swift-tests` to unlock: {swift_only_names}."
                )
        if config.difficulty != "auto":
            preset = self.difficulty_service.get_preset(config.difficulty)
        elif template_name != "mixed":
            return
        else:
            return
        if template_name != "mixed":
            include_swift_required = config.run_swift_tests or config.dry_run
            self.template_registry.choose(template_name, preset, RandomSource(config.base_seed), include_swift_required)

    def _validate_swift_validation_policy(self, config: GenerationConfig, _planned_difficulties: list[str]) -> None:
        if config.dry_run or config.run_swift_tests:
            return
        if config.template_name != "mixed" and self.runtime_parity_validator.gate.source_requires_runtime_validation(
            config.template_name
        ):
            raise ValueError(
                f"Production generation for `{config.template_name}` requires `--swift-tests` "
                "because this mechanic needs Swift runtime validation."
            )

    def _generate_raw_candidates(
        self,
        *,
        config: GenerationConfig,
        level_id: str,
        level_number: int,
        preset,
        rng: RandomSource,
        plan_template_weights: dict[str, int],
        accepted_candidates=(),
        diversity_decisions: list[dict] | None = None,
    ):
        include_swift_required = config.run_swift_tests or config.dry_run
        if diversity_decisions is None:
            diversity_decisions = []
        if config.generation_mode == "legacy_template":
            return [
                self._generate_legacy_candidate(
                    config=config,
                    level_id=level_id,
                    level_number=level_number,
                    preset=preset,
                    rng=rng,
                    include_swift_required=include_swift_required,
                    plan_template_weights=plan_template_weights,
                )
            ]

        candidates = self._generate_recipe_candidates(
            config=config,
            level_id=level_id,
            level_number=level_number,
            preset=preset,
            rng=rng,
            include_swift_required=include_swift_required,
            plan_template_weights=plan_template_weights,
            accepted_candidates=accepted_candidates,
            diversity_decisions=diversity_decisions,
        )
        if config.generation_mode == "hybrid":
            legacy_seed = rng.child_seed("legacy", len(candidates))
            candidates.append(
                self._generate_legacy_candidate(
                    config=config,
                    level_id=level_id,
                    level_number=level_number,
                    preset=preset,
                    rng=RandomSource(legacy_seed),
                    include_swift_required=include_swift_required,
                    plan_template_weights=plan_template_weights,
                )
            )
        return candidates

    def _generate_legacy_candidate(
        self,
        *,
        config: GenerationConfig,
        level_id: str,
        level_number: int,
        preset,
        rng: RandomSource,
        include_swift_required: bool,
        plan_template_weights: dict[str, int],
    ):
        template = self.template_registry.choose(
            config.template_name,
            preset,
            rng,
            include_swift_required=include_swift_required,
            weights_override=plan_template_weights if config.difficulty == "auto" else None,
        )
        return template.generate(level_id, level_number, preset, rng)

    def _generate_recipe_candidates(
        self,
        *,
        config: GenerationConfig,
        level_id: str,
        level_number: int,
        preset,
        rng: RandomSource,
        include_swift_required: bool,
        plan_template_weights: dict[str, int],
        accepted_candidates=(),
        diversity_decisions: list[dict] | None = None,
    ):
        candidates = []
        if diversity_decisions is None:
            diversity_decisions = []
        search_breadth = self._effective_search_breadth(config, preset)
        layout_names = self._layout_variant_names(search_breadth["layouts_per_recipe"])
        road_shape_strategies = self._road_shape_strategies(search_breadth["road_shapes_per_layout"])
        families = self._recipe_family_candidates(
            config=config,
            preset=preset,
            rng=rng,
            include_swift_required=include_swift_required,
            plan_template_weights=plan_template_weights,
            count=search_breadth["recipe_pool_size"],
            accepted_candidates=accepted_candidates,
            level_id=level_id,
            diversity_decisions=diversity_decisions,
        )
        for recipe_index, family in enumerate(families):
            recipe_seed = rng.child_seed("recipe", recipe_index)
            recipe_rng = RandomSource(recipe_seed)
            recipe = family.generate_recipe(level_id, preset, recipe_rng)
            recipe_issues = recipe.validate()
            if recipe_issues:
                raise ValueError(f"Invalid solved recipe candidate: {', '.join(recipe_issues)}")
            recipe = self.abstract_puzzle_solver.solve(recipe, preset)
            self._reject_strategically_weak_recipe(recipe, preset)

            layout_size_profiles = self._layout_size_profiles_for_recipe(config, preset, recipe, recipe_rng)
            for layout_index, layout_name in enumerate(layout_names):
                orientation_requests = self._layout_orientation_requests(
                    config,
                    recipe,
                    preset,
                    rng,
                    layout_index,
                )
                for size_index, layout_size_profile in enumerate(layout_size_profiles):
                    for orientation_index, orientation_request in enumerate(orientation_requests):
                        for road_index, road_shape_strategy in enumerate(road_shape_strategies):
                            candidate_seed = rng.child_seed(
                                "layout",
                                recipe_index,
                                layout_index,
                                size_index,
                                orientation_index,
                                road_index,
                            )
                            candidate = self.recipe_to_level_builder.build_level(
                                recipe,
                                level_number,
                                seed=candidate_seed,
                                layout_variant_name=layout_name,
                                layout_orientation_preference=orientation_request["orientation"],
                                layout_size_profile=layout_size_profile,
                                orientation_selection_reason=orientation_request["reason"],
                                road_shape_strategy=road_shape_strategy,
                            )
                            if candidate.layout_metadata is not None:
                                candidate.layout_metadata["orientationPreference"] = config.layout_orientation_preference
                                candidate.layout_metadata["requestedLayoutSizeProfile"] = config.layout_size_profile
                                candidate.layout_metadata["layoutSizeProfile"] = layout_size_profile
                                candidate.layout_metadata["verticalRouteProbability"] = config.vertical_route_probability
                                candidate.layout_metadata["preferVerticalForLongRoutes"] = config.prefer_vertical_for_long_routes
                                candidate.layout_metadata["orientationRequest"] = orientation_request["orientation"]
                                candidate.layout_metadata["layoutSizeSelectionReason"] = self._layout_size_selection_reason(
                                    config,
                                    preset,
                                    recipe,
                                    layout_size_profile,
                                )
                                candidate.layout_metadata["candidateRecipeIndex"] = recipe_index
                                candidate.layout_metadata["candidateLayoutIndex"] = layout_index
                                candidate.layout_metadata["candidateLayoutSizeIndex"] = size_index
                                candidate.layout_metadata["candidateOrientationIndex"] = orientation_index
                                candidate.layout_metadata["candidateRoadShapeIndex"] = road_index
                            candidate.requires_swift_validation = family.requires_swift_validation
                            candidates.append(candidate)
        return sorted(candidates, key=self._raw_candidate_validation_order)

    def _reject_strategically_weak_recipe(self, recipe, preset) -> None:
        """Gate strategic gameplay before any layout or timing work is attempted."""
        profile = self.decision_profile_service.analyze(
            recipe,
            topology_solutions=(recipe.solved_metadata,) if recipe.solved_metadata else (),
        )
        phase_change = int(
            profile.package_phase_decisions_before > 0
            and profile.package_phase_decisions_after > 0
        )
        strategic_count = (
            profile.ordered_dependency_count
            + profile.switch_state_change_on_revisit_count
            + profile.recoverable_mistake_count
            + profile.route_revisit_count
            + phase_change
        )
        reasons = []
        if strategic_count < preset.minimum_strategic_property_count:
            reasons.append("insufficient_strategic_decision_evidence")
        if (
            profile.required_decision_count > 1
            and profile.independent_decision_ratio > preset.maximum_independent_decision_ratio
        ):
            reasons.append("independent_decision_ratio_above_preset_maximum")
        low, high = preset.required_decision_count_range
        if not low <= profile.required_decision_count <= high:
            reasons.append("decision_count_outside_preset_range")
        if reasons:
            error = ValueError("Strategic quality rejected before layout: " + ", ".join(reasons))
            error.code = "strategic_quality_rejected_before_layout"
            raise error

    def _raw_candidate_validation_order(self, candidate) -> tuple[int, int, int, int, int, int]:
        metadata = getattr(candidate, "layout_metadata", None) or {}
        route_length = self._required_path_length(candidate) or 0
        return (
            int(metadata.get("candidateRoadShapeIndex", 0)),
            int(metadata.get("candidateLayoutIndex", 0)),
            int(metadata.get("candidateLayoutSizeIndex", 0)),
            int(metadata.get("candidateOrientationIndex", 0)),
            int(metadata.get("candidateRecipeIndex", 0)),
            -route_length,
        )

    def _effective_max_attempts(self, config: GenerationConfig, preset) -> int:
        if config.playtest_portfolio:
            if config.candidate_pool_size > 1:
                return config.max_attempts_per_level
            if preset.name == "medium":
                return min(max(config.max_attempts_per_level, 40), 70)
            if preset.name == "hard":
                return min(max(config.max_attempts_per_level, 40), 70)
            if preset.name == "expert":
                return min(max(config.max_attempts_per_level, 25), 45)
            return min(max(config.max_attempts_per_level, 30), 60)
        if preset.name == "medium":
            return min(max(config.max_attempts_per_level, 35), 60)
        if preset.name == "hard":
            return min(max(config.max_attempts_per_level, 40), 70)
        if preset.name == "expert":
            return min(max(config.max_attempts_per_level, 20), 25)
        return config.max_attempts_per_level

    def _effective_search_breadth(self, config: GenerationConfig, preset) -> dict[str, int]:
        recipe_pool_size = config.recipe_pool_size
        layouts_per_recipe = config.layouts_per_recipe
        road_shapes_per_layout = config.road_shapes_per_layout
        if config.playtest_portfolio:
            if config.candidate_pool_size > 1:
                return {
                    "recipe_pool_size": recipe_pool_size,
                    "layouts_per_recipe": layouts_per_recipe,
                    "road_shapes_per_layout": road_shapes_per_layout,
                }
            if preset.name in {"medium", "hard"}:
                recipe_pool_size = min(max(recipe_pool_size, 1), 3)
                layouts_per_recipe = 1
                road_shapes_per_layout = 1
            elif preset.name == "expert":
                recipe_pool_size = min(max(recipe_pool_size, 1), 3)
                layouts_per_recipe = 1
                road_shapes_per_layout = 1
            else:
                recipe_pool_size = min(max(recipe_pool_size, 1), 3)
                layouts_per_recipe = 1
                road_shapes_per_layout = 1
            return {
                "recipe_pool_size": recipe_pool_size,
                "layouts_per_recipe": layouts_per_recipe,
                "road_shapes_per_layout": road_shapes_per_layout,
            }
        if preset.name == "medium":
            recipe_pool_size = max(recipe_pool_size, 4)
            layouts_per_recipe = max(layouts_per_recipe, 2)
            road_shapes_per_layout = max(road_shapes_per_layout, 2)
        elif preset.name == "hard":
            recipe_pool_size = max(recipe_pool_size, 5)
            layouts_per_recipe = max(layouts_per_recipe, 2)
            road_shapes_per_layout = max(road_shapes_per_layout, 2)
        elif preset.name == "expert":
            recipe_pool_size = max(recipe_pool_size, 5)
            layouts_per_recipe = max(layouts_per_recipe, 2)
            road_shapes_per_layout = max(road_shapes_per_layout, 2)
        return {
            "recipe_pool_size": recipe_pool_size,
            "layouts_per_recipe": layouts_per_recipe,
            "road_shapes_per_layout": road_shapes_per_layout,
        }

    def _recipe_family_candidates(
        self,
        *,
        config: GenerationConfig,
        preset,
        rng: RandomSource,
        include_swift_required: bool,
        plan_template_weights: dict[str, int],
        count: int,
        accepted_candidates,
        level_id: str,
        diversity_decisions: list[dict],
    ):
        if config.template_name != "mixed":
            family = self.recipe_family_registry.choose_family(
                config.template_name,
                preset,
                rng,
                include_swift_required=include_swift_required,
                weights_override=plan_template_weights if config.difficulty == "auto" else None,
            )
            return [family] * count

        weights_override = plan_template_weights if config.difficulty == "auto" else None
        supported = self.recipe_family_registry.supported_families(
            preset,
            include_swift_required=include_swift_required,
        )
        weighted, decision = self._diversity_adjusted_family_weights(
            supported=supported,
            preset=preset,
            weights_override=weights_override,
            accepted_candidates=accepted_candidates,
            level_id=level_id,
        )
        self._append_diversity_decision(diversity_decisions, decision)
        weighted = [(family, max(weight, 0)) for family, weight in weighted if weight > 0]
        if not weighted:
            raise ValueError(f"No recipe families support difficulty '{preset.name}'")

        selected = []
        remaining = list(weighted)
        selected_topologies: set[str] = set()
        while len(selected) < count:
            if not remaining:
                remaining = list(weighted)
            topology_spread_remaining = self._without_selected_topologies_when_possible(
                remaining,
                preset,
                selected_topologies,
            )
            if topology_spread_remaining:
                remaining = topology_spread_remaining
            family = rng.weighted_choice(remaining)
            selected.append(family)
            selected_topologies.update(self._family_topology_classes(family, preset))
            remaining = [(candidate, weight) for candidate, weight in remaining if candidate.name != family.name]
        weight_by_family = {family.name: weight for family, weight in weighted}
        decision["selectedFamilies"] = [
            {
                "family": family.name,
                "topologyClasses": list(self._family_topology_classes(family, preset)),
                "adjustedWeight": round(float(weight_by_family.get(family.name, 0.0)), 4),
            }
            for family in selected
        ]
        return selected

    def _diversity_adjusted_family_weights(
        self,
        *,
        supported,
        preset,
        weights_override: dict[str, int] | None,
        accepted_candidates,
        level_id: str,
    ):
        context = self._batch_diversity_context(accepted_candidates)
        accepted = context["accepted"]
        family_counts = context["familyCounts"]
        topology_counts = context["topologyCounts"]
        mechanic_tag_counts = context["mechanicTagCounts"]
        recent_families = context["recentFamilies"]
        recent_topologies = context["recentTopologies"]
        recent_mechanic_tags = context["recentMechanicTags"]
        recent_layout_size_profiles = context["recentLayoutSizeProfiles"]
        max_family_count = max(family_counts.values(), default=0)
        max_topology_count = max(topology_counts.values(), default=0)
        max_mechanic_tag_count = max(mechanic_tag_counts.values(), default=0)

        adjusted = []
        decision_families = []
        for family in supported:
            base_weight = self.recipe_family_registry.weight_for(
                family.name,
                preset.name,
                weights_override=weights_override,
            )
            if base_weight <= 0:
                adjusted.append((family, 0.0))
                continue
            topology_classes = self._family_topology_classes(family, preset)
            family_count = family_counts.get(family.name, 0)
            topology_count = max((topology_counts.get(topology, 0) for topology in topology_classes), default=0)
            family_mechanic_tags = set(getattr(family, "mechanic_tags", ()) or ())
            mechanic_tag_count = max(
                (mechanic_tag_counts.get(tag, 0) for tag in family_mechanic_tags),
                default=0,
            )
            multiplier = 1.0
            reasons: list[str] = []
            penalties: list[dict] = []

            if accepted:
                if family_count == 0:
                    multiplier *= 1.35
                    reasons.append("unused_family_boost")
                elif family_count < max_family_count:
                    multiplier *= 1.15
                    reasons.append("underused_family_boost")
                else:
                    multiplier *= 1.0 / (1.0 + (0.35 * family_count))
                    reasons.append("family_count_penalty")

                if topology_count == 0:
                    multiplier *= 1.25
                    reasons.append("unused_topology_boost")
                elif topology_count < max_topology_count:
                    multiplier *= 1.10
                    reasons.append("underused_topology_boost")
                else:
                    multiplier *= 1.0 / (1.0 + (0.28 * topology_count))
                    reasons.append("topology_count_penalty")

                if family_mechanic_tags:
                    if mechanic_tag_count == 0:
                        multiplier *= 1.08
                        reasons.append("unused_mechanic_tag_boost")
                    elif mechanic_tag_count < max_mechanic_tag_count:
                        multiplier *= 1.04
                        reasons.append("underused_mechanic_tag_boost")

            if recent_families:
                if recent_families[-1] == family.name:
                    factor = 0.25
                    multiplier *= factor
                    reasons.append("last_family_repeat_penalty")
                    penalties.append({"kind": "family", "reason": "last_family_repeat_penalty", "factor": factor})
                elif family.name in recent_families[-2:]:
                    factor = 0.55
                    multiplier *= factor
                    reasons.append("recent_family_repeat_penalty")
                    penalties.append({"kind": "family", "reason": "recent_family_repeat_penalty", "factor": factor})

            if recent_topologies and set(topology_classes):
                if recent_topologies[-1] in topology_classes:
                    factor = 0.40
                    multiplier *= factor
                    reasons.append("last_topology_repeat_penalty")
                    penalties.append({"kind": "topology", "reason": "last_topology_repeat_penalty", "factor": factor})
                elif set(recent_topologies[-2:]) & set(topology_classes):
                    factor = 0.70
                    multiplier *= factor
                    reasons.append("recent_topology_repeat_penalty")
                    penalties.append({"kind": "topology", "reason": "recent_topology_repeat_penalty", "factor": factor})

            if recent_mechanic_tags and family_mechanic_tags:
                if family_mechanic_tags & set(recent_mechanic_tags[-1:]):
                    factor = 0.82
                    multiplier *= factor
                    reasons.append("last_mechanic_tag_repeat_penalty")
                    penalties.append({"kind": "mechanic_tag", "reason": "last_mechanic_tag_repeat_penalty", "factor": factor})
                elif family_mechanic_tags & set(recent_mechanic_tags[-3:]):
                    factor = 0.92
                    multiplier *= factor
                    reasons.append("recent_mechanic_tag_repeat_penalty")
                    penalties.append({"kind": "mechanic_tag", "reason": "recent_mechanic_tag_repeat_penalty", "factor": factor})

            adjusted_weight = max(base_weight * multiplier, 0.01)
            adjusted.append((family, adjusted_weight))
            decision_families.append(
                {
                    "family": family.name,
                    "topologyClasses": list(topology_classes),
                    "mechanicTags": sorted(family_mechanic_tags),
                    "baseWeight": round(float(base_weight), 4),
                    "adjustedWeight": round(float(adjusted_weight), 4),
                    "weightAfterDiversityAdjustment": round(float(adjusted_weight), 4),
                    "familyCount": int(family_count),
                    "topologyCount": int(topology_count),
                    "mechanicTagCount": int(mechanic_tag_count),
                    "reasons": reasons,
                    "penalties": penalties,
                }
            )

        return adjusted, {
            "levelID": level_id,
            "difficulty": preset.name,
            "acceptedCount": len(accepted),
            "recentFamilies": recent_families,
            "recentTopologies": recent_topologies,
            "recentMechanicTags": recent_mechanic_tags,
            "recentLayoutSizeProfiles": recent_layout_size_profiles,
            "familyCounts": dict(sorted(family_counts.items())),
            "topologyCounts": dict(sorted(topology_counts.items())),
            "mechanicTagCounts": dict(sorted(mechanic_tag_counts.items())),
            "recentFamilyPenalties": [
                item
                for item in decision_families
                if any(penalty["kind"] == "family" for penalty in item["penalties"])
            ],
            "recentTopologyPenalties": [
                item
                for item in decision_families
                if any(penalty["kind"] == "topology" for penalty in item["penalties"])
            ],
            "chosenFamilyWeightsAfterDiversityAdjustment": [
                {
                    "family": item["family"],
                    "topologyClasses": item["topologyClasses"],
                    "baseWeight": item["baseWeight"],
                    "adjustedWeight": item["adjustedWeight"],
                    "reasons": item["reasons"],
                }
                for item in sorted(decision_families, key=lambda item: item["adjustedWeight"], reverse=True)
                if item["adjustedWeight"] > 0
            ],
            "families": sorted(decision_families, key=lambda item: item["family"]),
        }

    def _batch_diversity_context(self, accepted_candidates) -> dict:
        accepted = list(accepted_candidates)
        recent = accepted[-3:]
        return {
            "accepted": accepted,
            "familyCounts": Counter(level.recipe_family or level.template_name for level in accepted),
            "topologyCounts": Counter(getattr(level, "topology_class", "") or "unknown" for level in accepted),
            "mechanicTagCounts": Counter(
                tag
                for level in accepted
                for tag in (getattr(level, "mechanic_tags", ()) or ())
            ),
            "recentFamilies": [
                level.recipe_family or level.template_name
                for level in recent
                if level.recipe_family or level.template_name
            ],
            "recentTopologies": [
                getattr(level, "topology_class", "") or "unknown"
                for level in recent
            ],
            "recentMechanicTags": [
                tag
                for level in recent
                for tag in (getattr(level, "mechanic_tags", ()) or ())
            ],
            "recentLayoutSizeProfiles": [
                (getattr(level, "layout_metadata", None) or {}).get("layoutSizeProfile", "unknown")
                for level in recent
            ],
        }

    def _family_topology_classes(self, family, preset) -> tuple[str, ...]:
        topologies = [
            variant.topology_class
            for variant in family.variants_for_difficulty(preset)
            if variant.topology_class
        ]
        if not topologies and getattr(family, "topology_class", ""):
            topologies = [family.topology_class]
        return tuple(dict.fromkeys(topologies))

    def _without_selected_topologies_when_possible(self, weighted, preset, selected_topologies: set[str]):
        if not selected_topologies:
            return weighted
        alternatives = [
            (family, weight)
            for family, weight in weighted
            if not (set(self._family_topology_classes(family, preset)) & selected_topologies)
        ]
        return alternatives or weighted

    def _append_diversity_decision(self, decisions: list[dict], decision: dict) -> None:
        level_id = decision.get("levelID")
        if level_id:
            for index, existing in enumerate(decisions):
                if existing.get("levelID") == level_id:
                    decisions[index] = decision
                    return
        if len(decisions) >= self.MAX_DIVERSITY_DECISIONS:
            return
        decisions.append(decision)

    def _record_candidate_generation(self, result: GenerationResult, difficulty: str, count: int) -> None:
        result.candidate_generation_count += count
        result.candidate_generation_counts_by_difficulty[difficulty] = (
            result.candidate_generation_counts_by_difficulty.get(difficulty, 0) + count
        )

    def _record_candidate_validation(self, result: GenerationResult, difficulty: str) -> None:
        result.candidate_validation_count += 1
        result.candidate_validation_counts_by_difficulty[difficulty] = (
            result.candidate_validation_counts_by_difficulty.get(difficulty, 0) + 1
        )

    def _record_rejection_by_difficulty(self, result: GenerationResult, difficulty: str, reason: str) -> None:
        difficulty_key = difficulty or "unknown"
        reason_key = reason or "unknown"
        by_reason = result.rejection_reason_counts_by_difficulty.setdefault(difficulty_key, {})
        by_reason[reason_key] = by_reason.get(reason_key, 0) + 1
        stage = CandidateRejectionService.validation_stage_for_code(reason_key)
        result.rejection_stage_counts[stage] = result.rejection_stage_counts.get(stage, 0) + 1
        if stage in {"layout_readability_validation", "road_shape_validation"}:
            result.geometry_rejection_counts_by_code[reason_key] = (
                result.geometry_rejection_counts_by_code.get(reason_key, 0) + 1
            )
        if reason_key == "candidate_too_similar_to_batch":
            result.similarity_rejection_counts_by_difficulty[difficulty_key] = (
                result.similarity_rejection_counts_by_difficulty.get(difficulty_key, 0) + 1
            )

    def _record_layout_entry(self, result: GenerationResult, candidate) -> None:
        # Legacy templates predate constructive layout metadata; only count candidates
        # that actually passed through the layout/repair stage.
        if getattr(candidate, "layout_metadata", None) is None:
            return
        result.candidates_entering_layout += 1
        metadata = candidate.layout_metadata or {}
        if int(metadata.get("layoutRepairSuccessCount", 0)) > 0 and not metadata.get("remainingRepairViolations"):
            result.candidates_repaired_successfully += 1

    def _successful_layout_repairs(self, candidate) -> int:
        return int((getattr(candidate, "layout_metadata", None) or {}).get("layoutRepairSuccessCount", 0))

    def _record_filter_rejection(self, result: GenerationResult) -> None:
        result.filter_rejection_count += 1

    def _record_validation_rejection(self, result: GenerationResult) -> None:
        result.validation_rejection_count += 1

    def _record_generation_error(self, result: GenerationResult) -> None:
        result.generation_error_count += 1

    def _batch_similarity_signatures(
        self,
        config: GenerationConfig,
        accepted_signatures,
        candidate_pool_signatures,
    ) -> list:
        accepted = list(accepted_signatures)
        if config.playtest_portfolio:
            accepted = accepted[-config.playtest_uniqueness_window :]
        return [*accepted, *candidate_pool_signatures]

    def _quality_comparison_signatures(self, config: GenerationConfig, accepted_signatures) -> list:
        accepted = list(accepted_signatures)
        if config.playtest_portfolio:
            return accepted[-config.playtest_uniqueness_window :]
        return accepted

    def _batch_duplicate_threshold(
        self,
        config: GenerationConfig,
        *,
        accepted_count: int,
        attempt: int,
        effective_max_attempts: int,
    ) -> float | None:
        if not config.playtest_portfolio:
            return None
        pressure = self._portfolio_pressure(attempt, effective_max_attempts)
        threshold = self.PLAYTEST_BATCH_DUPLICATE_THRESHOLD
        if accepted_count >= config.playtest_uniqueness_window:
            threshold += 0.01
        if pressure >= 0.50:
            threshold += 0.01
        if pressure >= 0.75:
            threshold += 0.01
        return min(threshold, 0.99)

    def _existing_duplicate_threshold(self, config: GenerationConfig) -> float | None:
        if config.playtest_portfolio:
            return self.PLAYTEST_EXISTING_DUPLICATE_THRESHOLD
        return None

    def _maximum_selection_similarity(self, config: GenerationConfig | None) -> float:
        if config is not None and config.playtest_portfolio:
            return self.PLAYTEST_SELECTION_SIMILARITY_THRESHOLD
        return self.MAXIMUM_SELECTION_SIMILARITY

    def _portfolio_pressure(self, attempt: int, effective_max_attempts: int) -> float:
        if effective_max_attempts <= 1:
            return 1.0
        return max(0.0, min(1.0, attempt / float(effective_max_attempts - 1)))

    def _preset_for_candidate_layout(self, candidate, preset):
        metadata = getattr(candidate, "layout_metadata", None) or {}
        return self._preset_for_layout_size_profile(preset, metadata.get("layoutSizeProfile", "standard_portrait"))

    def _preset_for_layout_size_profile(self, preset, layout_size_profile: str):
        if layout_size_profile != "large_portrait":
            return preset
        return replace(
            preset,
            coordinate_bounds=(-1.15, 1.15, -3.4, 1.35),
            minimum_node_distance=max(preset.minimum_node_distance, 0.24),
        )

    def _layout_size_profiles_for_recipe(
        self,
        config: GenerationConfig,
        preset,
        recipe,
        rng: RandomSource,
    ) -> list[str]:
        if config.layout_size_profile != "difficulty_curve":
            return [config.layout_size_profile]

        weights = dict(preset.map_size_profile_weights)
        profiles = ["standard_portrait"]
        large_weight = weights.get("large_portrait", 0)
        if large_weight <= 0:
            return profiles

        total_weight = max(sum(max(weight, 0) for weight in weights.values()), 1)
        large_probability = large_weight / total_weight
        route_length = max(len(getattr(recipe, "required_path", ())) - 1, 0)
        mechanic_tags = set(getattr(recipe, "mechanic_tags", ()) or ())
        topology_class = str(getattr(recipe, "topology_class", "") or "")
        large_friendly_tags = {
            "long_route",
            "detour",
            "split_path",
            "rejoin",
            "loop",
            "revisit",
            "ring",
            "package_inside_loop",
            "two_phase",
            "four_way",
        }
        strong_interest_tags = {
            "fake_shortcut",
            "split_path",
            "rejoin",
            "detour",
            "package_gate",
            "loop",
            "revisit",
            "ring",
            "two_phase",
            "hub",
        }
        route_needs_room = route_length >= preset.route_length_range[0] + 1
        interest_needs_room = bool(mechanic_tags & strong_interest_tags) or topology_class in {
            "split_rejoin",
            "hub_spoke",
            "return_loop",
            "ring",
            "revisit",
            "two_phase",
            "four_way_ring",
        }
        structure_benefits_from_large = (
            route_length >= preset.route_length_range[1]
            or bool(mechanic_tags & large_friendly_tags)
            or any(term in topology_class for term in ("loop", "ring", "rejoin", "phase", "four_way"))
        )

        include_large = False
        if preset.name == "medium":
            include_large = structure_benefits_from_large and rng.bool(min(large_probability, 0.35))
        elif preset.name == "hard":
            include_large = route_needs_room and interest_needs_room and (
                structure_benefits_from_large or rng.bool(min(large_probability, 0.60))
            )
        elif preset.name == "expert":
            include_large = route_needs_room and interest_needs_room and (
                structure_benefits_from_large or rng.bool(min(large_probability, 0.75))
            )

        if include_large:
            profiles.append("large_portrait")
        return profiles

    def _layout_size_selection_reason(self, config: GenerationConfig, preset, recipe, layout_size_profile: str) -> str:
        if config.layout_size_profile != "difficulty_curve":
            return "explicit_profile"
        if layout_size_profile == "standard_portrait":
            return "difficulty_curve_standard_candidate"
        route_length = max(len(getattr(recipe, "required_path", ())) - 1, 0)
        mechanic_tags = set(getattr(recipe, "mechanic_tags", ()) or ())
        if route_length >= preset.route_length_range[1]:
            return "difficulty_curve_long_route_candidate"
        if mechanic_tags:
            return "difficulty_curve_route_interest_candidate"
        return "difficulty_curve_weighted_candidate"

    def _layout_orientation_requests(
        self,
        config: GenerationConfig,
        recipe,
        preset,
        rng: RandomSource,
        layout_index: int,
    ) -> list[dict[str, str]]:
        preference = config.layout_orientation_preference
        if preference == "portrait_vertical":
            return [{"orientation": "portrait_vertical", "reason": "portrait_profile_default"}]
        if preference == "horizontal":
            return [{"orientation": "horizontal", "reason": "explicit_preference"}]
        if preference == "vertical":
            return [{"orientation": "vertical", "reason": "explicit_preference"}]

        if preference == "mixed":
            requests = [{"orientation": "horizontal", "reason": "mixed_horizontal"}]
            if layout_index == 0:
                requests.append({"orientation": "vertical", "reason": "mixed_preference"})
            elif rng.bool(config.vertical_route_probability):
                requests.append({"orientation": "vertical", "reason": "probability"})
            return requests

        if config.prefer_vertical_for_long_routes and self._is_long_route(recipe, preset):
            return [{"orientation": "vertical", "reason": "long_route_preference"}]
        if self._recipe_metadata_prefers_vertical(recipe) and rng.bool(config.vertical_route_probability):
            return [{"orientation": "vertical", "reason": "probability"}]
        if max(len(recipe.required_path) - 1, 0) >= 5 and rng.bool(config.vertical_route_probability):
            return [{"orientation": "vertical", "reason": "probability"}]
        return [{"orientation": "horizontal", "reason": "auto_horizontal"}]

    def _recipe_metadata_prefers_vertical(self, recipe) -> bool:
        tags = set(getattr(recipe, "mechanic_tags", ()) or ())
        topology_class = str(getattr(recipe, "topology_class", "") or "")
        return bool(tags.intersection({"loop", "ring", "rejoin", "package_gate", "long_route"}) or "loop" in topology_class)

    def _is_long_route(self, recipe, preset) -> bool:
        route_length = max(len(recipe.required_path) - 1, 0)
        thresholds = {
            "tutorial": 4,
            "easy": 6,
            "medium": 8,
            "hard": 10,
            "expert": 11,
        }
        return route_length >= thresholds.get(preset.name, 8)

    def _layout_variant_names(self, count: int) -> list[str]:
        names = list(self.layout_variant_service.variant_names)
        return [names[index % len(names)] for index in range(count)]

    def _road_shape_strategies(self, count: int) -> list[str]:
        names = [
            "auto",
            "switch_clarity_optimized",
            "crossing_minimized",
            "main_route_smoothed",
            "horizontal_first",
            "vertical_first",
            "all_straight",
            "alternating",
        ]
        return [names[index % len(names)] for index in range(count)]

    def _append_rejection_message(self, result: GenerationResult, message: str) -> None:
        rejection_message_count = sum(1 for existing in result.messages if existing.startswith("Rejected candidate "))
        if rejection_message_count < self.MAX_REJECTION_MESSAGES:
            result.messages.append(message)
            return
        suppression_message = (
            f"Additional candidate rejection messages suppressed after {self.MAX_REJECTION_MESSAGES}; "
            "see rejectionReasonCounts and candidateSelection in the report."
        )
        if suppression_message not in result.messages:
            result.messages.append(suppression_message)

    def _annotate_runtime_parity(self, candidate, config: GenerationConfig, swift_summary=None):
        swift_service = SwiftTestService(
            find_repo_root(),
            timeout_seconds=config.swift_timeout_seconds,
            level_ids=(candidate.level_id,),
            levels_output_dir=config.levels_output_dir,
            solutions_output_dir=config.solutions_output_dir,
        )
        result = self.runtime_parity_validator.evaluate_candidate(
            candidate,
            dry_run=config.dry_run,
            run_swift_tests=config.run_swift_tests,
            swift_validation_command=swift_service.build_command(),
            swift_validation_environment=swift_service.build_environment(),
            swift_summary=swift_summary,
        )
        candidate.runtime_parity_validation_result = result
        candidate.requires_swift_validation = bool(
            getattr(candidate, "requires_swift_validation", False)
            or result.runtime_validation_required
        )
        return result

    def _runtime_validation_rejection(self, candidate) -> tuple[str, str] | None:
        result = getattr(candidate, "runtime_parity_validation_result", None)
        if result is None or not result.runtime_validation_required:
            return None
        if result.runtime_validation_status == "missing_required_swift_validation":
            return (
                "missing_required_swift_validation",
                (
                    f"{result.runtime_validation_reason}; "
                    "rerun production generation with `--swift-tests` or use `--dry-run` for reporting only"
                ),
            )
        if result.runtime_validation_status == "failed":
            return (
                result.failure_reason or "swift_runtime_parity_failed",
                result.runtime_validation_reason,
            )
        return None

    def _apply_swift_validation_summary(self, config: GenerationConfig, result: GenerationResult, swift_summary) -> None:
        batch_command = list(getattr(swift_summary, "command", []) or [])
        batch_environment = dict(getattr(swift_summary, "environment", {}) or {})
        for candidate in result.accepted:
            existing = getattr(candidate, "runtime_parity_validation_result", None)
            if existing is None:
                self._annotate_runtime_parity(candidate, config, swift_summary=swift_summary)
                continue
            candidate.runtime_parity_validation_result = self.runtime_parity_validator.evaluate_candidate(
                candidate,
                dry_run=config.dry_run,
                run_swift_tests=config.run_swift_tests,
                swift_validation_command=batch_command,
                swift_validation_environment=batch_environment,
                swift_summary=swift_summary if existing.runtime_validation_required else None,
            )

    def _candidate_selection_key(self, candidate) -> tuple[float, float, float, float, float, float, int]:
        quality = candidate.quality_score
        if quality is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -candidate.seed)
        categories = quality.category_scores
        return (
            quality.total_score,
            categories.get("routeInterestScore", 0.0),
            categories.get("layoutScore", 0.0),
            categories.get("difficultyFitScore", 0.0),
            categories.get("diversityScore", 0.0),
            categories.get("logicScore", 0.0),
            -candidate.seed,
        )

    def _candidate_pool_ready(self, candidate_pool: list, config: GenerationConfig, preset) -> bool:
        if len(candidate_pool) >= config.candidate_pool_size:
            return True
        if config.template_name != "mixed" or preset.name not in {"medium", "hard", "expert"}:
            return False
        if config.candidate_pool_size <= 4 or len(candidate_pool) < 4:
            return False

        families = {candidate.recipe_family or candidate.template_name for candidate in candidate_pool}
        topologies = {getattr(candidate, "topology_class", "") or "unknown" for candidate in candidate_pool}
        best_quality = max(
            (candidate.quality_score.total_score for candidate in candidate_pool if candidate.quality_score is not None),
            default=0.0,
        )
        best_diversity = max(
            (candidate.quality_score.diversity_score for candidate in candidate_pool if candidate.quality_score is not None),
            default=0.0,
        )
        return (
            len(families) >= 3
            and len(topologies) >= 3
            and best_quality >= self.MINIMUM_TOTAL_SCORE_BY_DIFFICULTY.get(preset.name, 75.0)
            and best_diversity >= 0.70
        )

    def _score_candidate_quality(self, candidate, preset, comparison_signatures, accepted_signatures):
        parameters = inspect.signature(self.quality_service.score).parameters
        if "accepted_signatures" in parameters:
            return self.quality_service.score(
                candidate,
                preset,
                comparison_signatures,
                accepted_signatures=accepted_signatures,
            )
        return self.quality_service.score(candidate, preset, comparison_signatures)

    def _quality_rejection(
        self,
        candidate,
        *,
        config: GenerationConfig | None = None,
        attempt: int = 0,
        accepted_count: int = 0,
        effective_max_attempts: int = 1,
    ) -> tuple[str, str] | None:
        quality = candidate.quality_score
        if quality is None:
            return None
        gate_rejection = self._quality_gate_rejection(
            candidate,
            quality,
            config=config,
            attempt=attempt,
            accepted_count=accepted_count,
            effective_max_attempts=effective_max_attempts,
        )
        if gate_rejection is not None:
            return gate_rejection
        max_similarity = float(quality.details.get("maxSimilarity", 0.0))
        maximum_selection_similarity = self._maximum_selection_similarity(config)
        if quality.runtime_solvability < self.MINIMUM_RUNTIME_CONFIDENCE:
            return (
                "quality_runtime_confidence_below_threshold",
                (
                    f"runtime confidence {quality.runtime_solvability:.2f} "
                    f"< {self.MINIMUM_RUNTIME_CONFIDENCE:.2f}"
                ),
            )
        if quality.switch_clarity < self.MINIMUM_SWITCH_CLARITY:
            return (
                "quality_switch_clarity_below_threshold",
                f"switch clarity {quality.switch_clarity:.2f} < {self.MINIMUM_SWITCH_CLARITY:.2f}",
            )
        if max_similarity > maximum_selection_similarity:
            return (
                "quality_similarity_above_threshold",
                f"similarity {max_similarity:.2f} > {maximum_selection_similarity:.2f}",
            )
        minimum_total_score = self.MINIMUM_TOTAL_SCORE_BY_DIFFICULTY.get(
            str(getattr(candidate, "difficulty", "") or "").strip().lower(),
            self.MINIMUM_TOTAL_QUALITY * 100.0,
        )
        if quality.total_score < minimum_total_score:
            return (
                "quality_total_below_difficulty_threshold",
                f"quality score {quality.total_score:.2f} < {minimum_total_score:.2f}",
            )
        return None

    def _quality_gate_rejection(
        self,
        candidate,
        quality,
        *,
        config: GenerationConfig | None = None,
        attempt: int = 0,
        accepted_count: int = 0,
        effective_max_attempts: int = 1,
    ) -> tuple[str, str] | None:
        difficulty = str(getattr(candidate, "difficulty", "") or "").strip().lower()
        route_interest = float(getattr(quality, "route_interest", 0.0) or 0.0)
        preset_content_fit = quality.details.get("presetContentFit", {})
        minimum_route_interest = float(preset_content_fit.get("minimumRouteInterestScore", 0.0) or 0.0)
        effective_minimum_route_interest = self._effective_minimum_route_interest(
            difficulty,
            minimum_route_interest,
            config=config,
            attempt=attempt,
            accepted_count=accepted_count,
            effective_max_attempts=effective_max_attempts,
        )
        route_interest_audit = quality.details.get("routeInterest", {})
        route_interest_tags = set(route_interest_audit.get("tags", ()) or ())
        topology_class = str(getattr(candidate, "topology_class", "") or "")
        recipe_family = str(getattr(candidate, "recipe_family", "") or "")

        if self._has_large_portrait_without_puzzle_need(quality) and not self._allow_portfolio_large_portrait(
            config,
            attempt=attempt,
            effective_max_attempts=effective_max_attempts,
        ):
            return (
                "large_portrait_without_puzzle_need",
                "large_portrait layout did not have enough route length, topology, and route-interest justification",
            )

        if difficulty in {"hard", "expert"} and self._is_boring_topology_for_difficulty(
            difficulty=difficulty,
            recipe_family=recipe_family,
            topology_class=topology_class,
            route_interest=route_interest,
            minimum_route_interest=effective_minimum_route_interest,
            route_interest_tags=route_interest_tags,
            config=config,
            attempt=attempt,
            effective_max_attempts=effective_max_attempts,
        ):
            return (
                "boring_topology_for_difficulty",
                (
                    f"{difficulty} candidate recipe={recipe_family or 'unknown'} "
                    f"topology={topology_class or 'unknown'} route_interest={route_interest:.3f} "
                    f"tags={','.join(sorted(route_interest_tags)) or 'none'}"
                ),
            )

        if difficulty in self.ROUTE_INTEREST_GATED_DIFFICULTIES and route_interest < minimum_route_interest:
            if config is not None and config.playtest_portfolio and route_interest >= effective_minimum_route_interest:
                return None
            return (
                f"route_interest_below_{difficulty}_gate",
                f"route interest {route_interest:.3f} < {effective_minimum_route_interest:.3f}",
            )

        return None

    def _effective_minimum_route_interest(
        self,
        difficulty: str,
        minimum_route_interest: float,
        *,
        config: GenerationConfig | None,
        attempt: int,
        accepted_count: int,
        effective_max_attempts: int,
    ) -> float:
        if config is None or not config.playtest_portfolio:
            return minimum_route_interest
        relaxation = self.PLAYTEST_ROUTE_INTEREST_RELAXATION.get(difficulty, 0.0)
        pressure = self._portfolio_pressure(attempt, effective_max_attempts)
        if pressure >= 0.50 or accepted_count >= config.playtest_uniqueness_window:
            relaxation += self.PLAYTEST_ROUTE_INTEREST_LATE_RELAXATION
        if pressure >= 0.75:
            relaxation += 0.03
        floor_by_difficulty = {
            "medium": 0.24,
            "hard": 0.34,
            "expert": 0.38,
        }
        floor = floor_by_difficulty.get(difficulty, 0.0)
        return max(floor, minimum_route_interest - relaxation)

    def _allow_portfolio_large_portrait(
        self,
        config: GenerationConfig | None,
        *,
        attempt: int,
        effective_max_attempts: int,
    ) -> bool:
        if config is None or not config.playtest_portfolio:
            return False
        return self._portfolio_pressure(attempt, effective_max_attempts) >= 0.50

    def _has_large_portrait_without_puzzle_need(self, quality) -> bool:
        preset_content_fit = quality.details.get("presetContentFit", {})
        large_map_fit = preset_content_fit.get("largeMapFit", {})
        return "large_portrait_without_puzzle_need" in set(large_map_fit.get("penalties", ()) or ())

    def _is_boring_topology_for_difficulty(
        self,
        *,
        difficulty: str,
        recipe_family: str,
        topology_class: str,
        route_interest: float,
        minimum_route_interest: float,
        route_interest_tags: set[str],
        config: GenerationConfig | None = None,
        attempt: int = 0,
        effective_max_attempts: int = 1,
    ) -> bool:
        if config is not None and config.playtest_portfolio:
            pressure = self._portfolio_pressure(attempt, effective_max_attempts)
            has_strong_interest = bool(route_interest_tags & self.STRONG_ROUTE_INTEREST_TAGS)
            if has_strong_interest and (route_interest >= minimum_route_interest or pressure >= 0.50):
                return False
            if difficulty == "hard" and pressure >= 0.75 and route_interest >= minimum_route_interest:
                return False
        if topology_class not in self.SIMPLE_CHAIN_TOPOLOGIES:
            return False
        if difficulty == "hard" and recipe_family == "multi_switch_chain":
            return not bool(route_interest_tags & self.STRONG_ROUTE_INTEREST_TAGS)
        if difficulty == "expert":
            has_strong_interest = bool(route_interest_tags & self.STRONG_ROUTE_INTEREST_TAGS)
            return not (has_strong_interest and route_interest >= minimum_route_interest)
        return False

    def _candidate_selection_summary(
        self, level_id: str, accepted_candidate, candidate_pool, near_miss_candidates
    ) -> StageResult:
        scored_candidates = [candidate for candidate in candidate_pool if candidate.quality_score is not None]
        sorted_candidates = sorted(scored_candidates, key=self._candidate_selection_key, reverse=True)
        runner_ups = [
            self._candidate_summary(
                candidate,
                "not_selected",
                "not_selected",
                "Candidate passed validation and quality gates but was not selected.",
            )
            for candidate in sorted_candidates
            if candidate is not accepted_candidate
        ]
        top_rejected = sorted(
            [*runner_ups, *near_miss_candidates],
            key=lambda item: item.get("quality", {}).get("totalScore", item.get("quality", {}).get("total", 0.0)),
            reverse=True,
        )[:5]
        scores = [
            *[candidate.quality_score.total_score for candidate in scored_candidates],
            *[
                near_miss.get("quality", {}).get("totalScore")
                for near_miss in near_miss_candidates
                if near_miss.get("quality", {}).get("totalScore") is not None
            ],
        ]
        accepted_summary = self._candidate_summary(
            accepted_candidate,
            "accepted",
            "accepted",
            "Accepted during candidate selection.",
        )
        accepted_score = accepted_candidate.quality_score.total_score if accepted_candidate.quality_score is not None else 0.0
        next_summary = top_rejected[0] if top_rejected else None
        report_fields = {
            "levelID": level_id,
            "candidateCount": len(scores),
            "acceptedCandidate": accepted_summary,
            "notSelectedCandidates": runner_ups,
            "scoreStats": {
                "minimum": round(min(scores), 4) if scores else None,
                "average": round(sum(scores) / len(scores), 4) if scores else None,
                "maximum": round(max(scores), 4) if scores else None,
            },
            "topRejectedNearMisses": top_rejected,
            "selectionRationale": self._selection_rationale(accepted_summary, accepted_score, next_summary),
        }
        return StageResult(
            passed=True,
            stage="candidate_selection",
            code="candidate_selected",
            details=report_fields["selectionRationale"],
            metrics={"candidateCount": len(scores), **report_fields["scoreStats"]},
            report_fields=report_fields,
        )

    def _selection_rationale(
        self,
        accepted_summary: CandidateStageResult,
        accepted_score: float,
        next_summary: CandidateStageResult | None,
    ) -> str:
        if next_summary is None:
            return "Only one scored candidate passed validation and quality thresholds."
        next_quality = next_summary.get("quality", {})
        next_score = next_quality.get("totalScore")
        accepted_quality = accepted_summary.get("quality", {})
        accepted_base = accepted_quality.get("baseQualityScore")
        next_base = next_quality.get("baseQualityScore")
        accepted_diversity = accepted_quality.get("diversityScore")
        next_diversity = next_quality.get("diversityScore")
        if (
            next_score is not None
            and accepted_base is not None
            and next_base is not None
            and accepted_diversity is not None
            and next_diversity is not None
            and accepted_base < next_base
            and accepted_diversity > next_diversity + 0.10
        ):
            return (
                "Accepted candidate had the highest deterministic quality score after diversity scoring "
                f"({accepted_score:.4f} vs {next_score:.4f}); stronger diversity "
                f"({accepted_diversity:.4f} vs {next_diversity:.4f}) offset close base quality "
                f"({accepted_base:.4f} vs {next_base:.4f})."
            )
        return f"Accepted candidate had the highest deterministic quality score ({accepted_score:.4f} vs {next_score:.4f})."

    def _candidate_summary(
        self,
        candidate,
        status: str,
        reason: str | None = None,
        detail: str | None = None,
    ) -> CandidateStageResult:
        quality = candidate.quality_score
        runtime_parity = self._runtime_parity_summary(candidate)
        status_metadata = self._candidate_status_metadata(candidate, status, reason, detail)
        topology_report = self._topology_report(candidate)
        solver_report = self._solver_report(candidate)
        layout_readability_report = self._layout_readability_summary(candidate)
        road_shape_report = self._road_shape_summary(candidate)
        quality_breakdown = self._quality_breakdown(quality)
        report_fields = {
            **status_metadata,
            "levelID": candidate.level_id,
            "seed": candidate.seed,
            "difficulty": candidate.difficulty,
            "selectedPreset": candidate.difficulty,
            "template": candidate.template_name,
            "recipeFamily": candidate.recipe_family,
            "recipeVariant": candidate.recipe_variant,
            "mechanicTags": list(getattr(candidate, "mechanic_tags", ()) or ()),
            "primaryMechanicTag": getattr(candidate, "primary_mechanic_tag", "") or None,
            "topologyClass": getattr(candidate, "topology_class", "") or None,
            "requiredPathLength": self._required_path_length(candidate),
            "layoutOrientation": self._layout_orientation(candidate),
            "layoutProfile": (candidate.layout_metadata or {}).get("layoutProfile"),
            "layoutSizeProfile": (candidate.layout_metadata or {}).get("layoutSizeProfile"),
            "requestedLayoutSizeProfile": (candidate.layout_metadata or {}).get("requestedLayoutSizeProfile"),
            "layoutSizeSelectionReason": (candidate.layout_metadata or {}).get("layoutSizeSelectionReason"),
            "portraitMetrics": (candidate.layout_metadata or {}).get("portraitMetrics"),
            "portraitChecksPassed": (candidate.layout_metadata or {}).get("portraitChecksPassed"),
            "requiresSwiftValidation": bool(getattr(candidate, "requires_swift_validation", False)),
            "runtimeParity": runtime_parity,
            "runtimeValidationRequired": runtime_parity.get("runtimeValidationRequired", False),
            "runtimeValidationStatus": runtime_parity.get("runtimeValidationStatus"),
            "runtimeValidationReason": runtime_parity.get("runtimeValidationReason"),
            "swiftValidationCommand": runtime_parity.get("swiftValidationCommand", []),
            "swiftValidationPassed": runtime_parity.get("swiftValidationPassed"),
            "swiftValidationSkippedReason": runtime_parity.get("swiftValidationSkippedReason"),
            "riskyMechanicTags": runtime_parity.get("riskyMechanicTags", []),
            "requiresSwiftRuntimeValidation": runtime_parity.get("requiresSwiftRuntimeValidation", False),
            "layoutStrategy": (candidate.layout_metadata or {}).get("strategy"),
            "layoutOrientationSelectionReason": (candidate.layout_metadata or {}).get("orientationSelectionReason"),
            "verticalCandidateRejectedReason": (candidate.layout_metadata or {}).get("verticalCandidateRejectedReason"),
            "diversityAudit": self._diversity_audit(candidate),
            "topologyDiversityScore": self._diversity_audit(candidate)["topologyDiversityScore"],
            "nearbyMechanicTagPenalty": self._diversity_audit(candidate)["nearbyMechanicTagPenalty"],
            "nearbyTopologyClassPenalty": self._diversity_audit(candidate)["nearbyTopologyClassPenalty"],
            "diversityScore": self._diversity_audit(candidate)["diversityScore"],
            "routeInterestAudit": self._route_interest_audit(candidate),
            "layoutVariant": candidate.selected_layout_variant,
            "roadShapeStrategy": candidate.selected_road_shape_strategy,
            "topologyReport": topology_report,
            **topology_report,
            "solverReport": solver_report,
            **solver_report,
            "layoutReadabilityReport": layout_readability_report,
            **layout_readability_report,
            "roadShapeReport": road_shape_report,
            **road_shape_report,
            "runtimeParityReport": runtime_parity,
            "qualityScoreBreakdown": quality_breakdown,
            "totalQualityScore": quality_breakdown.get("totalQualityScore"),
            "logicScore": quality_breakdown.get("logicScore"),
            "routeInterestScore": quality_breakdown.get("routeInterestScore"),
            "layoutScore": quality_breakdown.get("layoutScore"),
            "difficultyFitScore": quality_breakdown.get("difficultyFitScore"),
            "topPositiveFactors": quality_breakdown.get("topPositiveFactors", []),
            "topNegativeFactors": quality_breakdown.get("topNegativeFactors", []),
            "difficultyFit": self._difficulty_fit_summary(quality),
            "routeInterestFit": self._route_interest_audit(candidate),
            "pacingPenalties": self._pacing_penalties(candidate),
            "validationResult": "passed" if status in {"accepted", "not_selected"} else "failed",
            "quality": self._quality_summary(quality),
            "signature": (
                {
                    "topologyHashShort": candidate.candidate_signature.topology_hash[:8],
                    "layoutHashShort": candidate.candidate_signature.layout_hash[:8],
                    "solutionHashShort": candidate.candidate_signature.solution_hash[:8],
                }
                if candidate.candidate_signature is not None
                else None
            ),
        }
        return CandidateStageResult(
            passed=status in {"accepted", "not_selected"},
            stage=status_metadata["validationStage"],
            code=status_metadata["rejectionCode"] or "accepted",
            details=detail,
            metrics={
                "totalQualityScore": quality_breakdown.get("totalQualityScore"),
                "requiredPathLength": self._required_path_length(candidate),
            },
            report_fields=report_fields,
            candidate_id=status_metadata["candidateID"],
            level_id=candidate.level_id,
            seed=candidate.seed,
            difficulty=candidate.difficulty,
            status=status,
        )

    def _candidate_status_metadata(
        self,
        candidate,
        status: str,
        reason: str | None,
        detail: str | None,
    ) -> dict:
        rejection_code = None if status == "accepted" else (reason or status)
        stage = (
            "candidate_selection"
            if status in {"accepted", "not_selected"}
            else CandidateRejectionService.validation_stage_for_code(rejection_code)
        )
        accepted_or_rejected_reason = reason or ("accepted" if status == "accepted" else status)
        return {
            "candidateID": self._candidate_id(candidate),
            "status": status,
            "acceptedOrRejectedReason": accepted_or_rejected_reason,
            "validationStage": stage,
            "rejectionCode": rejection_code,
            "rejectionDetails": detail,
        }

    def _candidate_id(self, candidate) -> str:
        return f"{candidate.level_id}:{candidate.seed}"

    def _record_rejected_candidate_summary(
        self,
        result: GenerationResult,
        candidate,
        reason: str,
        detail: str,
    ) -> None:
        result.rejected_candidate_summaries.append(
            self._candidate_summary(candidate, "rejected", reason, detail)
        )

    def _record_generation_error_summary(
        self,
        result: GenerationResult,
        *,
        level_id: str,
        seed: int,
        difficulty: str,
        reason: str,
        detail: str,
    ) -> None:
        stage = CandidateRejectionService.validation_stage_for_code(reason)
        report_fields = {
                "candidateID": f"{level_id}:{seed}",
                "levelID": level_id,
                "seed": seed,
                "difficulty": difficulty,
                "recipeFamily": None,
                "recipeVariant": None,
                "topologyClass": None,
                "mechanicTags": [],
                "status": "rejected",
                "acceptedOrRejectedReason": reason,
                "validationStage": stage,
                "rejectionCode": reason,
                "rejectionDetails": detail,
            }
        result.rejected_candidate_summaries.append(
            CandidateStageResult(
                passed=False,
                stage=stage,
                code=reason,
                details=detail,
                report_fields=report_fields,
                candidate_id=f"{level_id}:{seed}",
                level_id=level_id,
                seed=seed,
                difficulty=difficulty,
                status="rejected",
            )
        )

    def _topology_report(self, candidate) -> dict:
        metadata = getattr(candidate, "mechanic_metadata", {}) or {}
        rules = metadata.get("topologyRules") if isinstance(metadata, dict) else None
        topology_rules = dict(rules) if isinstance(rules, dict) else {}
        abstract = getattr(candidate, "abstract_solution_metadata", None)
        unique = getattr(candidate, "unique_solution_validation_result", None)
        actual_cycle_count = self._actual_cycle_count(candidate)
        declared_loop_count = self._declared_int(metadata, ("declaredLoopCount", "declaredCycleCount", "loopCount"))
        if declared_loop_count is None:
            declared_loop_count = getattr(abstract, "loop_count", None)
        declared_rejoin_count = getattr(unique, "declared_rejoin_count", None)
        if declared_rejoin_count is None:
            declared_rejoin_count = self._declared_count(metadata, ("declaredRejoinCount", "allowedRejoinCount", "rejoinCount"), ("declaredRejoinNodeIDs", "rejoinNodeIDs"))
        declared_revisit_count = getattr(unique, "declared_revisit_count", None)
        if declared_revisit_count is None:
            declared_revisit_count = self._declared_count(metadata, ("declaredRevisitCount", "allowedRevisitCount", "revisitCount"), ("declaredRevisitNodeIDs", "revisitNodeIDs", "repeatedNodeIDs"))
        return {
            "topologyRules": topology_rules,
            "allowsCycles": bool(topology_rules.get("allowsCycles", False)),
            "allowsRejoin": bool(topology_rules.get("allowsRejoin", False)),
            "allowsRevisit": bool(topology_rules.get("allowsRevisit", False)),
            "allowsReturnPath": bool(topology_rules.get("allowsReturnPath", False)),
            "allowsRing": bool(topology_rules.get("allowsRing", False)),
            "allowedCycleCount": int(topology_rules.get("allowedCycleCount", 0) or 0),
            "actualCycleCount": actual_cycle_count,
            "declaredLoopCount": int(declared_loop_count or 0),
            "declaredRejoinCount": int(declared_rejoin_count or 0),
            "declaredRevisitCount": int(declared_revisit_count or 0),
        }

    def _solver_report(self, candidate) -> dict:
        result = getattr(candidate, "unique_solution_validation_result", None)
        if result is None:
            return {
                "solutionCount": None,
                "exploredStates": 0,
                "maxDepthReached": 0,
                "traversalLimitHit": False,
                "packageReachabilityStatus": "not_evaluated",
                "shortestValidRouteLength": None,
                "intendedRouteLength": self._required_path_length(candidate),
                "shortcutDetected": False,
                "packageBypassDetected": False,
                "wrongBranchReachedGoal": False,
            }
        terminal_reason_counts = dict(result.terminal_reason_counts)
        traversal_limit_hit = (
            result.termination_reason in {"max_explored_states_reached", "max_traversal_depth_reached"}
            or terminal_reason_counts.get("max_traversal_depth_reached", 0) > 0
            or terminal_reason_counts.get("max_taps_reached", 0) > 0
        )
        return {
            "solutionCount": result.solution_count,
            "exploredStates": result.explored_states,
            "maxDepthReached": result.max_depth_reached,
            "traversalLimitHit": traversal_limit_hit,
            "packageReachabilityStatus": result.package_reachability_status,
            "shortestValidRouteLength": result.shortest_valid_route_length,
            "intendedRouteLength": result.intended_route_length,
            "shortcutDetected": result.shortcut_detected,
            "packageBypassDetected": result.package_bypass_detected,
            "wrongBranchReachedGoal": result.wrong_branch_reached_goal,
        }

    def _layout_readability_summary(self, candidate) -> dict:
        report = getattr(candidate, "layout_readability_validation_result", None)
        metadata = dict(getattr(report, "metadata", {}) or {})
        return {
            "layoutReadabilityPassed": bool(metadata.get("passed", report is not None and not report.has_errors)),
            "nodeOverlapDetected": bool(metadata.get("nodeOverlapDetected", False)),
            "implicitIntersectionDetected": bool(metadata.get("implicitIntersectionDetected", False)),
            "roadsTooCloseDetected": bool(metadata.get("roadsTooCloseDetected", False)),
            "switchExitOverlapDetected": bool(metadata.get("switchExitOverlapDetected", False)),
            "importantNodeBlocked": bool(metadata.get("importantNodeBlocked", False)),
            "startGoalTooClose": bool(metadata.get("startGoalTooClose", False)),
            "portraitSafetyFailure": bool(metadata.get("portraitSafetyFailure", False)),
            "offendingNodes": list(metadata.get("offendingNodes", [])),
            "offendingRoads": list(metadata.get("offendingRoads", [])),
            "measuredDistances": list(metadata.get("measuredDistances", [])),
            "measuredAngles": list(metadata.get("measuredAngles", [])),
        }

    def _road_shape_summary(self, candidate) -> dict:
        metadata = getattr(candidate, "road_shape_metadata", None) or {}
        return {
            "switchDirectionQuality": metadata.get("switchClarityScore"),
            "ambiguousSwitchDetected": bool(metadata.get("ambiguousSwitchDetected", False)),
            "directionBucketAssignments": metadata.get("directionBucketAssignments", {}),
            "switchExitAngleSeparation": metadata.get("switchExitAngleSeparation", {}),
            "roadShapeWarnings": list(metadata.get("warnings", [])),
            "roadShapeIssues": list(metadata.get("issues", [])),
            "readabilityAdjustments": list(metadata.get("readabilityAdjustments", [])),
        }

    def _quality_breakdown(self, quality) -> dict:
        if quality is None:
            return {
                "totalQualityScore": None,
                "logicScore": None,
                "routeInterestScore": None,
                "layoutScore": None,
                "difficultyFitScore": None,
                "diversityScore": None,
                "topPositiveFactors": [],
                "topNegativeFactors": [],
                "pacingPenalties": [],
            }
        categories = quality.category_scores or {}
        return {
            "totalQualityScore": quality.total_score,
            "logicScore": categories.get("logicScore"),
            "routeInterestScore": categories.get("routeInterestScore"),
            "layoutScore": categories.get("layoutScore"),
            "difficultyFitScore": categories.get("difficultyFitScore"),
            "diversityScore": categories.get("diversityScore"),
            "topPositiveFactors": list(quality.top_positive_factors),
            "topNegativeFactors": list(quality.top_negative_factors),
            "pacingPenalties": [penalty for penalty in quality.penalties if penalty.startswith("campaign_")],
        }

    def _difficulty_fit_summary(self, quality) -> dict:
        if quality is None:
            return {}
        return {
            "difficultyFitScore": quality.difficulty_fit,
            "estimatedDifficultyBand": quality.estimated_difficulty_band,
            "mechanicalDifficulty": quality.mechanical_difficulty,
            "visualDifficulty": quality.visual_difficulty,
            "presetContentFit": quality.details.get("presetContentFit", {}),
        }

    def _pacing_penalties(self, candidate) -> list[str]:
        quality = getattr(candidate, "quality_score", None)
        if quality is None:
            return []
        return [penalty for penalty in quality.penalties if penalty.startswith("campaign_")]

    def _actual_cycle_count(self, candidate) -> int:
        level = candidate.level_document
        adjacency: dict[str, list[str]] = {}
        for edge in level.graph.edges:
            adjacency.setdefault(edge.fromNodeID, []).append(edge.toNodeID)
        cycles: set[tuple[str, ...]] = set()
        for start in sorted(adjacency):
            stack = [(start, [start])]
            while stack:
                node_id, path = stack.pop()
                for next_id in adjacency.get(node_id, []):
                    if next_id == start and len(path) > 1:
                        cycles.add(self._canonical_cycle(tuple(path)))
                        continue
                    if next_id in path or len(path) > len(adjacency):
                        continue
                    stack.append((next_id, [*path, next_id]))
        return len(cycles)

    def _canonical_cycle(self, cycle: tuple[str, ...]) -> tuple[str, ...]:
        rotations = [cycle[index:] + cycle[:index] for index in range(len(cycle))]
        return min(rotations)

    def _declared_count(self, metadata: dict, count_keys: tuple[str, ...], node_keys: tuple[str, ...]) -> int | None:
        explicit = self._declared_int(metadata, count_keys)
        if explicit is not None:
            return explicit
        for key in node_keys:
            value = metadata.get(key)
            if isinstance(value, (list, tuple)):
                return len(value)
        return None

    def _declared_int(self, metadata: dict, keys: tuple[str, ...]) -> int | None:
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, int) and value >= 0:
                return value
        return None

    def _runtime_parity_summary(self, candidate) -> dict:
        result = getattr(candidate, "runtime_parity_validation_result", None)
        if result is not None:
            return result.to_metadata()
        return {
            "runtimeValidationRequired": bool(getattr(candidate, "requires_swift_validation", False)),
            "runtimeValidationStatus": "unknown",
            "runtimeValidationReason": "Runtime parity gate has not evaluated this candidate.",
            "swiftValidationCommand": [],
            "swiftValidationEnvironment": {},
            "swiftValidationPassed": None,
            "swiftValidationSkippedReason": None,
            "riskyMechanicTags": [],
            "requiresSwiftRuntimeValidation": bool(getattr(candidate, "requires_swift_validation", False)),
            "failureReason": None,
            "failureDetails": [],
        }

    def _quality_summary(self, quality) -> dict:
        if quality is None:
            return {}
        return {
            "totalScore": quality.total_score,
            "categoryScores": quality.category_scores,
            "total": quality.total,
            "abstractMechanicQuality": quality.abstract_mechanic_quality,
            "runtimeSolvability": quality.runtime_solvability,
            "readability": quality.readability,
            "switchClarity": quality.switch_clarity,
            "difficultyFit": quality.difficulty_fit,
            "uniqueness": quality.uniqueness,
            "campaignPacing": quality.campaign_pacing,
            "topologyDiversityScore": quality.topology_diversity_score,
            "nearbyMechanicTagPenalty": quality.nearby_mechanic_tag_penalty,
            "nearbyTopologyClassPenalty": quality.nearby_topology_class_penalty,
            "diversityScore": quality.diversity_score,
            "routeInterest": quality.route_interest,
            "routeInterestAudit": quality.details.get("routeInterest", {}),
            "baseQualityScore": quality.details.get("baseQualityScore", quality.total),
            "mobileTapComfort": quality.mobile_tap_comfort,
            "visualAppeal": quality.visual_appeal,
            "topPositiveFactors": list(quality.top_positive_factors),
            "topNegativeFactors": list(quality.top_negative_factors),
            "penalties": list(quality.penalties),
            "maxSimilarity": quality.details.get("maxSimilarity", 0.0),
            "presetContentFit": quality.details.get("presetContentFit", {}),
            "campaignPacingDetails": quality.details.get("campaignPacing", {}),
        }

    def _route_interest_audit(self, candidate) -> dict:
        quality = getattr(candidate, "quality_score", None)
        if quality is None:
            return {}
        audit = quality.details.get("routeInterest", {})
        return {
            "score": audit.get("score"),
            "tags": audit.get("tags", []),
            "fakeShortcutPresent": audit.get("fakeShortcutPresent", False),
            "branchRejoinPresent": audit.get("branchRejoinPresent", False),
            "packageGateTensionPresent": audit.get("packageGateTensionPresent", False),
            "loopRevisitPresent": audit.get("loopRevisitPresent", False),
            "meaningfulTurnCount": audit.get("meaningfulTurnCount", 0),
            "repeatedTopologyPenalty": audit.get("repeatedTopologyPenalty", 0.0),
            "bonuses": audit.get("bonuses", {}),
            "penaltyValues": audit.get("penaltyValues", {}),
            "penalties": list(audit.get("penalties", [])),
        }

    def _required_path_length(self, candidate) -> int | None:
        signature = getattr(candidate, "candidate_signature", None)
        if signature is not None and signature.required_path_length is not None:
            return signature.required_path_length
        metadata = getattr(candidate, "abstract_solution_metadata", None)
        if metadata is not None and getattr(metadata, "required_path", None):
            return max(len(metadata.required_path) - 1, 0)
        solution_metadata = dict(getattr(candidate.solution, "_extra", {}).get("metadata", {}))
        route = solution_metadata.get("solutionRoute") or []
        if route:
            return max(len(route) - 1, 0)
        return None

    def _layout_orientation(self, candidate) -> str:
        signature = getattr(candidate, "candidate_signature", None)
        if signature is not None:
            return signature.layout_orientation
        metadata = getattr(candidate, "layout_metadata", None) or {}
        explicit = metadata.get("orientation")
        if explicit:
            return str(explicit).strip().lower() or "unknown"
        strategy = str(metadata.get("strategy", "")).lower()
        if "vertical" in strategy:
            return "vertical"
        if "horizontal" in strategy:
            return "horizontal"
        variant = str(getattr(candidate, "selected_layout_variant", "") or metadata.get("variant", "")).lower()
        if variant == "tall":
            return "vertical"
        if variant == "wide":
            return "horizontal"
        return "unknown"

    def _diversity_audit(self, candidate) -> dict[str, float | None]:
        signature = getattr(candidate, "candidate_signature", None)
        return {
            "topologyDiversityScore": getattr(signature, "topology_diversity_score", None),
            "nearbyMechanicTagPenalty": getattr(signature, "nearby_mechanic_tag_penalty", None),
            "nearbyTopologyClassPenalty": getattr(signature, "nearby_topology_class_penalty", None),
            "diversityScore": getattr(signature, "diversity_score", None),
        }

    def _preflight_output_collisions(self, config: GenerationConfig) -> None:
        if config.overwrite or config.dry_run:
            return
        collisions: list[Path] = []
        for offset in range(config.count):
            level_id = format_level_id(config.start_level_number + offset)
            for path in [
                self.generated_level_repository.level_path(level_id, config.levels_output_dir),
                self.generated_level_repository.solution_path(level_id, config.solutions_output_dir),
            ]:
                if path.exists():
                    collisions.append(path)
        if collisions:
            formatted = "\n".join(str(path) for path in collisions)
            raise FileExistsError(f"Refusing to overwrite existing output files:\n{formatted}")

    def _load_existing_signatures(
        self,
        config: GenerationConfig,
        result: GenerationResult,
        target_level_ids: set[str],
    ):
        if not config.compare_against_existing:
            return []

        existing_result = self.existing_level_repository.load_existing_levels(
            config.levels_output_dir,
            config.solutions_output_dir,
            get_default_reports_directory() / "production_manifest.json",
        )
        result.messages.extend(existing_result.warnings)
        signatures = [
            signature
            for signature in existing_result.signatures
            if signature.level_id not in target_level_ids
        ]
        if signatures:
            result.messages.append(f"Loaded {len(signatures)} existing level signatures for similarity checks.")
        return signatures

    def _load_map_seed_graph(self, config: GenerationConfig, result: GenerationResult) -> MapSeedGraph | None:
        if config.map_seed_path is None:
            return None
        import json

        try:
            payload = json.loads(config.map_seed_path.read_text(encoding="utf-8"))
            graph_payload = payload.get("simplifiedGraph", payload)
            graph = MapSeedGraph.from_dict(graph_payload)
        except Exception as exc:
            result.messages.append(f"Could not load map seed {config.map_seed_path}: {exc}")
            return None
        result.messages.append(f"Loaded map seed from {config.map_seed_path}.")
        return graph

    def _write_generated_files(self, config: GenerationConfig, result: GenerationResult) -> None:
        for generated_level in result.accepted:
            level_path = self.generated_level_repository.level_path(generated_level.level_id, config.levels_output_dir)
            solution_path = self.generated_level_repository.solution_path(generated_level.level_id, config.solutions_output_dir)
            result.written_level_paths.append(
                self.generated_level_repository.write_level(
                    generated_level.level_document,
                    level_path,
                    overwrite=config.overwrite,
                )
            )
            result.written_solution_paths.append(
                self.generated_level_repository.write_solution(
                    generated_level.solution,
                    solution_path,
                    overwrite=config.overwrite,
                )
            )

    def _sync_xcode_project(self, config: GenerationConfig) -> list[str]:
        if not config.sync_xcode_project:
            return []
        if not self._uses_default_output_dirs(config):
            return []

        repo_root = find_repo_root()
        project_yml = repo_root / "project.yml"
        if not project_yml.exists():
            return ["Skipped xcodegen because project.yml was not found."]
        if shutil.which("xcodegen") is None:
            return ["Skipped xcodegen because the xcodegen command was not found."]

        completed = subprocess.run(
            ["xcodegen", "generate"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return ["Regenerated TinyRoutes.xcodeproj with xcodegen."]

        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit code {completed.returncode}"
        return [f"xcodegen generate failed: {detail}"]

    def _uses_default_output_dirs(self, config: GenerationConfig) -> bool:
        repo_root = find_repo_root()
        try:
            return (
                config.levels_output_dir.resolve() == (repo_root / "TinyRoutes" / "Resources" / "Levels").resolve()
                and config.solutions_output_dir.resolve()
                == (repo_root / "TinyRoutesTests" / "Resources" / "LevelSolutions").resolve()
            )
        except FileNotFoundError:
            return False

    def _write_reports(self, config: GenerationConfig, result: GenerationResult) -> None:
        if config.report_path is not None:
            result.report_path = self.report_repository.write_markdown(config.report_path, config, result)
        if config.json_report_path is not None:
            result.json_report_path = self.report_repository.write_json(config.json_report_path, config, result)

    def _resource_reference_warnings(self, config: GenerationConfig, result: GenerationResult) -> list[str]:
        if not self._uses_default_output_dirs(config):
            return []

        sync_result = self.resource_sync_service.check_project_references(
            config.levels_output_dir,
            config.solutions_output_dir,
        )
        return [*sync_result.errors, *sync_result.warnings]
