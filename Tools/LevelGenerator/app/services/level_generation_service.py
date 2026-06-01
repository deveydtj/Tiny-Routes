from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..map_import.map_seed_to_template_adapter import MapSeedToTemplateAdapter
from ..map_import.osm_seed_importer import MapSeedGraph
from ..models.generation_result import GenerationResult
from ..paths import find_repo_root, get_default_reports_directory
from ..random_source import RandomSource
from ..repositories.existing_level_repository import ExistingLevelRepository
from ..repositories.generated_level_repository import GeneratedLevelRepository
from ..repositories.generation_report_repository import GenerationReportRepository
from ..recipes.recipe_family_registry import RecipeFamilyRegistry
from ..templates.template_registry import TemplateRegistry
from .abstract_puzzle_solver_service import AbstractPuzzleSolverService
from .candidate_rejection_service import CandidateRejectionService
from .candidate_signature_service import CandidateSignatureService
from .candidate_uniqueness_service import CandidateUniquenessService
from .difficulty_curve_service import DifficultyCurveService
from .difficulty_service import DifficultyService
from .generated_level_validation_service import GeneratedLevelValidationService
from .generation_quality_service import GenerationQualityService
from .level_resource_sync_service import LevelResourceSyncService
from .layout_variant_service import LayoutVariantService
from .recipe_to_level_builder_service import RecipeToLevelBuilderService
from .swift_test_service import SwiftTestService


class LevelGenerationService:
    MINIMUM_TOTAL_QUALITY = 0.45
    MINIMUM_SWITCH_CLARITY = 0.40
    MINIMUM_RUNTIME_CONFIDENCE = 0.75
    MAXIMUM_SELECTION_SIMILARITY = 0.87
    MAX_REJECTION_MESSAGES = 50

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
        self.quality_service = GenerationQualityService()
        self.map_seed_adapter = MapSeedToTemplateAdapter()
        self.resource_sync_service = LevelResourceSyncService()
        self.recipe_to_level_builder = RecipeToLevelBuilderService()
        self.layout_variant_service = LayoutVariantService()
        self.abstract_puzzle_solver = AbstractPuzzleSolverService()

    def generate(self, config: GenerationConfig) -> GenerationResult:
        result = GenerationResult()
        try:
            batch_plan = self.difficulty_curve_service.build_plan(
                config.start_level_number,
                config.count,
                config.difficulty,
            )
            self._validate_generation_mode(config)
            self._validate_template(config.template_name, config)
            self._validate_swift_validation_policy(config, [entry.difficulty for entry in batch_plan.entries])
            self._preflight_output_collisions(config)
        except Exception as exc:
            result.passed = False
            result.messages.append(str(exc))
            self._write_reports(config, result)
            return result
        if not config.dry_run and config.candidate_pool_size == 1:
            result.messages.append(
                "Warning: production generation is using `candidate_pool_size=1`; "
                "use a larger pool for quality-based selection."
            )

        rejection_service = CandidateRejectionService()
        base_rng = RandomSource(config.base_seed)
        accepted_signatures = []
        target_level_ids = {
            format_level_id(config.start_level_number + offset)
            for offset in range(config.count)
        }
        existing_signatures = self._load_existing_signatures(config, result, target_level_ids)
        map_seed_graph = self._load_map_seed_graph(config, result)
        if config.map_seed_path is not None and map_seed_graph is None:
            result.passed = False
            self._write_reports(config, result)
            return result

        for offset in range(config.count):
            plan_entry = batch_plan.entries[offset]
            level_number = plan_entry.level_number
            level_id = plan_entry.level_id
            preset = self.difficulty_service.get_preset(plan_entry.difficulty)
            accepted_candidate = None
            candidate_pool = []
            candidate_pool_signatures = []
            near_miss_candidates = []

            for attempt in range(config.max_attempts_per_level):
                candidate_seed = base_rng.child_seed(plan_entry.difficulty, config.template_name, level_id, attempt)
                rng = RandomSource(candidate_seed)
                try:
                    candidates = self._generate_raw_candidates(
                        config=config,
                        level_id=level_id,
                        level_number=level_number,
                        preset=preset,
                        rng=rng,
                        plan_template_weights=plan_entry.template_weights,
                    )
                except Exception as exc:
                    rejection_code = getattr(exc, "code", "candidate_generation_error")
                    rejection_service.reason_counts[rejection_code] += 1
                    result.messages.append(f"Rejected candidate {level_id} attempt={attempt}: {exc}")
                    continue

                for candidate_index, candidate in enumerate(candidates):
                    candidate_rng = RandomSource(base_rng.child_seed(level_id, attempt, candidate_index, "map"))
                    if map_seed_graph is not None:
                        candidate = self.map_seed_adapter.apply_to_generated_level(map_seed_graph, candidate, candidate_rng)

                    level_path = self.generated_level_repository.level_path(level_id, config.levels_output_dir)
                    solution_path = self.generated_level_repository.solution_path(level_id, config.solutions_output_dir)
                    validation_result = self.validation_service.validate(
                        candidate,
                        preset=preset,
                        level_output_path=level_path,
                        solution_output_path=solution_path,
                        overwrite=config.overwrite or config.dry_run,
                    )
                    candidate.warning_messages = [
                        f"{message.code}: {message.message}"
                        for message in validation_result.messages
                        if message.severity != "error"
                    ]
                    if rejection_service.can_save(validation_result):
                        candidate_signature = self.signature_service.signature_for(candidate)
                        duplicate_result = self.uniqueness_service.check_duplicate(
                            candidate_signature,
                            [*accepted_signatures, *candidate_pool_signatures],
                        )
                        if duplicate_result.is_duplicate:
                            message = rejection_service.record_custom_rejection(
                                candidate,
                                "candidate_too_similar_to_batch",
                                duplicate_result.message,
                                config.debug_failures_dir,
                            )
                            self._append_rejection_message(result, message)
                            continue

                        if config.compare_against_existing:
                            existing_duplicate_result = self.uniqueness_service.check_duplicate(
                                candidate_signature,
                                existing_signatures,
                            )
                            if existing_duplicate_result.is_duplicate:
                                message = rejection_service.record_custom_rejection(
                                    candidate,
                                    "candidate_too_similar_to_existing",
                                    existing_duplicate_result.message,
                                    config.debug_failures_dir,
                                )
                                self._append_rejection_message(result, message)
                                continue

                        candidate.candidate_signature = candidate_signature
                        candidate.quality_score = self.quality_service.score(
                            candidate,
                            preset,
                            [
                                *accepted_signatures,
                                *candidate_pool_signatures,
                                *(existing_signatures if config.compare_against_existing else []),
                            ],
                        )
                        quality_rejection = self._quality_rejection(candidate)
                        if quality_rejection is not None:
                            reason, detail = quality_rejection
                            near_miss_candidates.append(self._candidate_summary(candidate, reason))
                            message = rejection_service.record_custom_rejection(
                                candidate,
                                reason,
                                detail,
                                config.debug_failures_dir,
                            )
                            self._append_rejection_message(result, message)
                            continue
                        candidate_pool.append(candidate)
                        candidate_pool_signatures.append(candidate_signature)
                        if len(candidate_pool) >= config.candidate_pool_size:
                            break
                        continue

                    rejection_service.record_rejection(candidate, validation_result, config.debug_failures_dir)

                if len(candidate_pool) >= config.candidate_pool_size:
                    break

            if candidate_pool:
                accepted_candidate = max(candidate_pool, key=self._candidate_selection_key)
                accepted_signatures.append(accepted_candidate.candidate_signature)
                result.candidate_selection_summaries.append(
                    self._candidate_selection_summary(level_id, accepted_candidate, candidate_pool, near_miss_candidates)
                )

            if accepted_candidate is None:
                result.passed = False
                result.messages.append(
                    f"Could not generate valid {level_id} after {config.max_attempts_per_level} attempts."
                )
                break
            result.accepted.append(accepted_candidate)

        result.add_rejections(dict(rejection_service.reason_counts))

        if result.passed and not config.dry_run:
            self._write_generated_files(config, result)
            result.messages.extend(self._sync_xcode_project(config))

        if result.passed and config.run_swift_tests and not config.dry_run:
            result.messages.extend(self._resource_reference_warnings(config, result))
            swift_summary = SwiftTestService(
                find_repo_root(),
                timeout_seconds=config.swift_timeout_seconds,
                level_ids=tuple(level.level_id for level in result.accepted),
                levels_output_dir=config.levels_output_dir,
                solutions_output_dir=config.solutions_output_dir,
            ).run()
            result.swift_test_summary = swift_summary
            if swift_summary.passed is not True:
                result.passed = False
                result.messages.append(swift_summary.summary)

        self._write_reports(config, result)
        return result

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

    def _validate_swift_validation_policy(self, config: GenerationConfig, planned_difficulties: list[str]) -> None:
        if config.dry_run or config.run_swift_tests:
            return
        risky_difficulties = {"hard", "expert"}
        risky_templates = {"ring_route", "four_way_intersection"}
        planned_risky_difficulties = sorted(risky_difficulties.intersection(planned_difficulties))
        if planned_risky_difficulties:
            joined = ", ".join(planned_risky_difficulties)
            raise ValueError(
                f"Production generation for {joined} levels requires `--swift-tests`. "
                "Use `--dry-run` for Python-only iteration."
            )
        if config.template_name in risky_templates:
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
    ):
        include_swift_required = config.run_swift_tests or config.dry_run
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
    ):
        candidates = []
        layout_names = self._layout_variant_names(config.layouts_per_recipe)
        road_shape_strategies = self._road_shape_strategies(config.road_shapes_per_layout)
        for recipe_index in range(config.recipe_pool_size):
            recipe_seed = rng.child_seed("recipe", recipe_index)
            recipe_rng = RandomSource(recipe_seed)
            family = self.recipe_family_registry.choose_family(
                config.template_name,
                preset,
                recipe_rng,
                include_swift_required=include_swift_required,
                weights_override=plan_template_weights if config.difficulty == "auto" else None,
            )
            recipe = family.generate_recipe(level_id, preset, recipe_rng)
            recipe_issues = recipe.validate()
            if recipe_issues:
                raise ValueError(f"Invalid solved recipe candidate: {', '.join(recipe_issues)}")
            recipe = self.abstract_puzzle_solver.solve(recipe, preset)

            for layout_index, layout_name in enumerate(layout_names):
                for road_index, road_shape_strategy in enumerate(road_shape_strategies):
                    candidate_seed = rng.child_seed("layout", recipe_index, layout_index, road_index)
                    candidate = self.recipe_to_level_builder.build_level(
                        recipe,
                        level_number,
                        seed=candidate_seed,
                        layout_variant_name=layout_name,
                        road_shape_strategy=road_shape_strategy,
                    )
                    candidate.requires_swift_validation = family.requires_swift_validation
                    candidates.append(candidate)
        return candidates

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

    def _candidate_selection_key(self, candidate) -> tuple[float, float, float, int]:
        quality = candidate.quality_score
        if quality is None:
            return (0.0, 0.0, 0.0, -candidate.seed)
        return (quality.total, quality.switch_clarity, quality.uniqueness, -candidate.seed)

    def _quality_rejection(self, candidate) -> tuple[str, str] | None:
        quality = candidate.quality_score
        if quality is None:
            return None
        max_similarity = float(quality.details.get("maxSimilarity", 0.0))
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
        if max_similarity > self.MAXIMUM_SELECTION_SIMILARITY:
            return (
                "quality_similarity_above_threshold",
                f"similarity {max_similarity:.2f} > {self.MAXIMUM_SELECTION_SIMILARITY:.2f}",
            )
        if quality.total < self.MINIMUM_TOTAL_QUALITY:
            return (
                "quality_total_below_threshold",
                f"quality total {quality.total:.2f} < {self.MINIMUM_TOTAL_QUALITY:.2f}",
            )
        return None

    def _candidate_selection_summary(self, level_id: str, accepted_candidate, candidate_pool, near_miss_candidates):
        scored_candidates = [candidate for candidate in candidate_pool if candidate.quality_score is not None]
        sorted_candidates = sorted(scored_candidates, key=self._candidate_selection_key, reverse=True)
        runner_ups = [
            self._candidate_summary(candidate, "not_selected")
            for candidate in sorted_candidates
            if candidate is not accepted_candidate
        ]
        top_rejected = sorted(
            [*runner_ups, *near_miss_candidates],
            key=lambda item: item.get("quality", {}).get("total", 0.0),
            reverse=True,
        )[:5]
        scores = [
            *[candidate.quality_score.total for candidate in scored_candidates],
            *[
                near_miss.get("quality", {}).get("total")
                for near_miss in near_miss_candidates
                if near_miss.get("quality", {}).get("total") is not None
            ],
        ]
        accepted_score = accepted_candidate.quality_score.total if accepted_candidate.quality_score is not None else 0.0
        next_score = top_rejected[0]["quality"]["total"] if top_rejected else None
        return {
            "levelID": level_id,
            "candidateCount": len(scores),
            "acceptedCandidate": self._candidate_summary(accepted_candidate, "accepted"),
            "scoreStats": {
                "minimum": round(min(scores), 4) if scores else None,
                "average": round(sum(scores) / len(scores), 4) if scores else None,
                "maximum": round(max(scores), 4) if scores else None,
            },
            "topRejectedNearMisses": top_rejected,
            "selectionRationale": self._selection_rationale(accepted_score, next_score),
        }

    def _selection_rationale(self, accepted_score: float, next_score: float | None) -> str:
        if next_score is None:
            return "Only one scored candidate passed validation and quality thresholds."
        return f"Accepted candidate had the highest deterministic quality score ({accepted_score:.4f} vs {next_score:.4f})."

    def _candidate_summary(self, candidate, status: str) -> dict:
        quality = candidate.quality_score
        return {
            "levelID": candidate.level_id,
            "seed": candidate.seed,
            "template": candidate.template_name,
            "recipeFamily": candidate.recipe_family,
            "recipeVariant": candidate.recipe_variant,
            "mechanicTags": list(getattr(candidate, "mechanic_tags", ()) or ()),
            "primaryMechanicTag": getattr(candidate, "primary_mechanic_tag", "") or None,
            "topologyClass": getattr(candidate, "topology_class", "") or None,
            "requiredPathLength": self._required_path_length(candidate),
            "layoutOrientation": self._layout_orientation(candidate),
            "diversityAudit": self._diversity_audit(candidate),
            "topologyDiversityScore": None,
            "nearbyMechanicTagPenalty": None,
            "nearbyTopologyClassPenalty": None,
            "diversityScore": None,
            "layoutVariant": candidate.selected_layout_variant,
            "roadShapeStrategy": candidate.selected_road_shape_strategy,
            "status": status,
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

    def _quality_summary(self, quality) -> dict:
        if quality is None:
            return {}
        return {
            "total": quality.total,
            "abstractMechanicQuality": quality.abstract_mechanic_quality,
            "runtimeSolvability": quality.runtime_solvability,
            "readability": quality.readability,
            "switchClarity": quality.switch_clarity,
            "difficultyFit": quality.difficulty_fit,
            "uniqueness": quality.uniqueness,
            "campaignPacing": quality.campaign_pacing,
            "mobileTapComfort": quality.mobile_tap_comfort,
            "visualAppeal": quality.visual_appeal,
            "penalties": list(quality.penalties),
            "maxSimilarity": quality.details.get("maxSimilarity", 0.0),
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
