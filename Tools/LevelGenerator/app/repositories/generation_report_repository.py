from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import find_repo_root
from ..services.preview_image_service import PreviewImageService
from ..services.route_timing_service import RouteTimingService
from ..services.switch_visual_clarity_service import SwitchVisualClarityService
from ..services.layout_readability_validator import LayoutReadabilityValidator
from ..services.visual_clarity_validation_service import VisualClarityValidationService
from ..services.candidate_rejection_service import CandidateRejectionService


class GenerationReportRepository:
    def __init__(self) -> None:
        self.preview_image_service = PreviewImageService()
        self.route_timing = RouteTimingService()
        self.switch_visual_clarity = SwitchVisualClarityService()
        self.layout_readability_validator = LayoutReadabilityValidator()
        self.visual_clarity_validation = VisualClarityValidationService()

    def write_markdown(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_previews(path.parent, result)
        path.write_text(self._markdown(config, result), encoding="utf-8")
        return path

    def write_json(self, path: Path, config, result) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_previews(path.parent, result)
        path.write_text(json.dumps(self._payload(config, result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def _payload(self, config, result) -> dict[str, Any]:
        repo_root = find_repo_root()
        return {
            "generationTimestamp": datetime.now(timezone.utc).isoformat(),
            "commandArguments": config.command_arguments or [],
            "repoRoot": str(repo_root),
            "levelsOutputDir": str(config.levels_output_dir),
            "solutionsOutputDir": str(config.solutions_output_dir),
            "difficulty": config.difficulty,
            "template": config.template_name,
            "generationProfile": "playtest_portfolio" if getattr(config, "playtest_portfolio", False) else "production",
            "playtestPortfolio": bool(getattr(config, "playtest_portfolio", False)),
            "generationMode": config.generation_mode,
            "recipePoolSize": config.recipe_pool_size,
            "layoutsPerRecipe": config.layouts_per_recipe,
            "roadShapesPerLayout": config.road_shapes_per_layout,
            "playtestUniquenessWindow": getattr(config, "playtest_uniqueness_window", None),
            "layoutOrientationPreference": getattr(config, "layout_orientation_preference", "auto"),
            "layoutProfile": getattr(config, "layout_orientation_preference", "auto"),
            "layoutSizeProfile": getattr(config, "layout_size_profile", "standard_portrait"),
            "verticalRouteProbability": getattr(config, "vertical_route_probability", 0.0),
            "preferVerticalForLongRoutes": getattr(config, "prefer_vertical_for_long_routes", True),
            "baseSeed": config.seed,
            "dryRun": config.dry_run,
            "dryRunSummary": self._dry_run_summary(config, result),
            "overwrite": config.overwrite,
            "syncXcodeProject": config.sync_xcode_project,
            "compareAgainstExisting": config.compare_against_existing,
            "candidatePoolSize": config.candidate_pool_size,
            "candidateGenerationCount": int(getattr(result, "candidate_generation_count", 0)),
            "candidateValidationCount": int(getattr(result, "candidate_validation_count", 0)),
            "rejectionPhaseCounts": {
                "generationErrors": int(getattr(result, "generation_error_count", 0)),
                "validationFailures": int(getattr(result, "validation_rejection_count", 0)),
                "selectionFilters": int(getattr(result, "filter_rejection_count", 0)),
            },
            "candidateGenerationCountsByDifficulty": dict(
                sorted(getattr(result, "candidate_generation_counts_by_difficulty", {}).items())
            ),
            "candidateValidationCountsByDifficulty": dict(
                sorted(getattr(result, "candidate_validation_counts_by_difficulty", {}).items())
            ),
            "passed": getattr(result, "passed", True),
            "acceptedLevels": [
                {
                    **self._candidate_status_payload(
                        level,
                        status="accepted",
                        reason="accepted",
                        detail="Accepted during candidate selection.",
                    ),
                    "levelID": level.level_id,
                    "selectedPreset": level.difficulty,
                    "template": level.template_name,
                    "recipeFamily": level.recipe_family,
                    "recipeVariant": level.recipe_variant,
                    "mechanicTags": list(getattr(level, "mechanic_tags", ()) or ()),
                    "primaryMechanicTag": getattr(level, "primary_mechanic_tag", "") or None,
                    "topologyClass": getattr(level, "topology_class", "") or None,
                    **self._topology_reporting_payload(level),
                    "requiredPathLength": self._required_path_length(level),
                    "layoutOrientation": self._layout_orientation(level),
                    "layoutProfile": (level.layout_metadata or {}).get("layoutProfile"),
                    "layoutSizeProfile": (level.layout_metadata or {}).get("layoutSizeProfile"),
                    "requestedLayoutSizeProfile": (level.layout_metadata or {}).get("requestedLayoutSizeProfile"),
                    "layoutSizeSelectionReason": (level.layout_metadata or {}).get("layoutSizeSelectionReason"),
                    "portraitMetrics": (level.layout_metadata or {}).get("portraitMetrics"),
                    "portraitChecksPassed": (level.layout_metadata or {}).get("portraitChecksPassed"),
                    "portraitCheckIssues": (level.layout_metadata or {}).get("portraitCheckIssues", []),
                    "requiresSwiftValidation": bool(getattr(level, "requires_swift_validation", False)),
                    "runtimeParity": (runtime_parity := self._runtime_parity_payload(level)),
                    "runtimeParityReport": runtime_parity,
                    "runtimeValidationRequired": runtime_parity["runtimeValidationRequired"],
                    "runtimeValidationStatus": runtime_parity["runtimeValidationStatus"],
                    "runtimeValidationReason": runtime_parity["runtimeValidationReason"],
                    "swiftValidationCommand": runtime_parity["swiftValidationCommand"],
                    "swiftValidationPassed": runtime_parity["swiftValidationPassed"],
                    "swiftValidationSkippedReason": runtime_parity["swiftValidationSkippedReason"],
                    "riskyMechanicTags": runtime_parity["riskyMechanicTags"],
                    "requiresSwiftRuntimeValidation": runtime_parity["requiresSwiftRuntimeValidation"],
                    "layoutStrategy": (level.layout_metadata or {}).get("strategy"),
                    "layoutVariant": level.selected_layout_variant,
                    "layoutOrientationSelectionReason": (level.layout_metadata or {}).get("orientationSelectionReason"),
                    "verticalCandidateRejectedReason": (level.layout_metadata or {}).get("verticalCandidateRejectedReason"),
                    "diversityAudit": self._diversity_audit(level),
                    "topologyDiversityScore": self._diversity_audit(level)["topologyDiversityScore"],
                    "nearbyMechanicTagPenalty": self._diversity_audit(level)["nearbyMechanicTagPenalty"],
                    "nearbyTopologyClassPenalty": self._diversity_audit(level)["nearbyTopologyClassPenalty"],
                    "diversityScore": self._diversity_audit(level)["diversityScore"],
                    "routeInterestAudit": self._route_interest_audit(level),
                    "unlockRequirement": getattr(level, "unlock_requirement", None),
                    "priorMechanicDependency": getattr(level, "prior_mechanic_dependency", None),
                    "mechanicMetadata": getattr(level, "mechanic_metadata", {}) or {},
                    "abstractGraphSignature": level.abstract_graph_signature,
                    "abstractGraphSignatureShort": (
                        level.abstract_graph_signature[:12] if level.abstract_graph_signature else None
                    ),
                    "selectedLayoutVariant": level.selected_layout_variant,
                    "layoutMetadata": level.layout_metadata,
                    "selectedRoadShapeStrategy": level.selected_road_shape_strategy,
                    "roadShapeMetadata": level.road_shape_metadata,
                    "abstractSolution": self._abstract_solution_payload(level),
                    "seed": level.seed,
                    "difficulty": level.difficulty,
                    "nodes": level.node_count,
                    "edges": level.edge_count,
                    "switches": level.switch_count,
                    "parTaps": level.level_document.parTaps,
                    "timeLimit": level.level_document.timeLimitSeconds,
                    "requiredTaps": level.required_tap_count,
                    "signature": self._signature_payload(level),
                    "quality": self._quality_payload(level),
                    "qualityScoreBreakdown": self._quality_breakdown_payload(level),
                    "totalQualityScore": (
                        self._quality_breakdown_payload(level).get("totalQualityScore")
                        if self._quality_breakdown_payload(level)
                        else None
                    ),
                    "logicScore": (
                        self._quality_breakdown_payload(level).get("logicScore")
                        if self._quality_breakdown_payload(level)
                        else None
                    ),
                    "layoutScore": (
                        self._quality_breakdown_payload(level).get("layoutScore")
                        if self._quality_breakdown_payload(level)
                        else None
                    ),
                    "difficultyFitScore": (
                        self._quality_breakdown_payload(level).get("difficultyFitScore")
                        if self._quality_breakdown_payload(level)
                        else None
                    ),
                    "routeInterestScore": (
                        self._route_interest_audit(level).get("score")
                        if self._route_interest_audit(level)
                        else None
                    ),
                    "routeInterestFit": self._route_interest_audit(level),
                    "difficultyFit": self._difficulty_fit_payload(level),
                    "difficultyScore": (
                        self._quality_payload(level).get("difficultyFit")
                        if self._quality_payload(level)
                        else None
                    ),
                    "pacingPenalties": self._pacing_penalties(level),
                    "validationResult": "passed",
                    "acceptedOrRejectedReason": "accepted",
                    "validationStage": "candidate_selection",
                    "rejectionCode": None,
                    "rejectionDetails": None,
                    "simulation": self._simulation_payload(level),
                    "uniqueSolutionValidation": self._unique_solution_payload(level),
                    "solverReport": (solver_report := self._solver_reporting_payload(level)),
                    **solver_report,
                    "solution": self._solution_payload(level),
                    "switchPreview": self._switch_preview_payload(level),
                    "visualClarity": self._visual_clarity_payload(level),
                    "layoutReadability": (layout_readability := self._layout_readability_payload(level)),
                    "layoutReadabilityReport": (
                        layout_readability_report := self._layout_readability_report_payload(layout_readability)
                    ),
                    **layout_readability_report,
                    "roadShapeReport": (road_shape_report := self._road_shape_report_payload(level)),
                    **road_shape_report,
                    "previewPath": str(level.preview_path) if level.preview_path else None,
                    "status": "accepted",
                    "notes": level.generation_notes,
                    "warnings": list(getattr(level, "warning_messages", [])),
                }
                for level in result.accepted
            ],
            "candidateSelection": list(getattr(result, "candidate_selection_summaries", [])),
            "rejectedCandidateSummaries": list(getattr(result, "rejected_candidate_summaries", [])),
            "topRejectedNearMisses": self._top_rejected_near_misses(result),
            "acceptedDifficultyDistribution": self._distribution(
                (level.difficulty for level in result.accepted)
            ),
            "acceptedRecipeDistribution": self._distribution(
                (level.recipe_family or level.template_name for level in result.accepted)
            ),
            "acceptedTopologyDistribution": self._distribution(
                (getattr(level, "topology_class", "") or "unknown" for level in result.accepted)
            ),
            "acceptedMechanicDistribution": self._distribution(
                tag
                for level in result.accepted
                for tag in (getattr(level, "mechanic_tags", ()) or ("unknown",))
            ),
            "acceptedFamilyStreaks": self._accepted_streaks(
                level.recipe_family or level.template_name for level in result.accepted
            ),
            "acceptedTopologyStreaks": self._accepted_streaks(
                getattr(level, "topology_class", "") or "unknown" for level in result.accepted
            ),
            "acceptedMapSizeDistribution": self._distribution(
                ((level.layout_metadata or {}).get("layoutSizeProfile", "unknown") for level in result.accepted)
            ),
            "routeInterestScoreDistribution": self._score_distribution(
                self._route_interest_audit(level).get("score")
                for level in result.accepted
                if self._route_interest_audit(level)
            ),
            "routeInterestScoreByDifficulty": self._route_interest_by_difficulty(result),
            "acceptedRejectedCountsByDifficulty": self._accepted_rejected_counts_by_difficulty(result),
            "starvationCauseSummary": self._starvation_cause_summary(result),
            "rejectedCandidateCount": result.rejected_candidate_count,
            "rejectionReasonCounts": result.rejection_reason_counts,
            "rejectionStageCounts": dict(
                sorted(getattr(result, "rejection_stage_counts", {}).items())
            ),
            "rejectionReasonCountsByDifficulty": dict(
                sorted(getattr(result, "rejection_reason_counts_by_difficulty", {}).items())
            ),
            "similarityRejectionCountsByDifficulty": dict(
                sorted(getattr(result, "similarity_rejection_counts_by_difficulty", {}).items())
            ),
            "diversityAdjustmentDecisions": list(getattr(result, "diversity_adjustment_decisions", [])),
            "writtenLevelPaths": [str(path) for path in result.written_level_paths],
            "writtenSolutionPaths": [str(path) for path in result.written_solution_paths],
            "swiftTests": {
                "run": result.swift_test_summary.passed is not None,
                "command": result.swift_test_summary.command,
                "environment": getattr(result.swift_test_summary, "environment", {}),
                "exitCode": result.swift_test_summary.exit_code,
                "passed": result.swift_test_summary.passed,
                "summary": result.swift_test_summary.summary,
                "failureDetails": getattr(result.swift_test_summary, "failure_details", []),
                "failureReasons": getattr(result.swift_test_summary, "failure_reasons", []),
            },
            "messages": list(result.messages),
            "recommendations": self._recommendations(config, result),
            "xcodegenNote": (
                "project.yml includes resource directories. Production generation syncs TinyRoutes.xcodeproj "
                "with `xcodegen generate` before Swift tests unless `--no-xcodegen` is used."
            ),
        }

    def _markdown(self, config, result) -> str:
        payload = self._payload(config, result)
        lines = [
            "# Tiny Routes Generation Report",
            "",
            f"- Generated: `{payload['generationTimestamp']}`",
            f"- Repo root: `{payload['repoRoot']}`",
            f"- Difficulty: `{payload['difficulty']}`",
            f"- Template mode: `{payload['template']}`",
            f"- Generation profile: `{payload['generationProfile']}`",
            f"- Generation mode: `{payload['generationMode']}`",
            f"- Base seed: `{payload['baseSeed']}`",
            f"- Dry run: `{payload['dryRun']}`",
            f"- Dry-run pass rate: `{payload['dryRunSummary']['passRate']}`",
            f"- Compare existing levels: `{payload['compareAgainstExisting']}`",
            f"- Candidate pool size: `{payload['candidatePoolSize']}`",
            f"- Candidate generation count: `{payload['candidateGenerationCount']}`",
            f"- Candidate validation count: `{payload['candidateValidationCount']}`",
            f"- Rejection phases: `{payload['rejectionPhaseCounts']}`",
            f"- Recipe pool size: `{payload['recipePoolSize']}`",
            f"- Layouts per recipe: `{payload['layoutsPerRecipe']}`",
            f"- Road shapes per layout: `{payload['roadShapesPerLayout']}`",
            f"- Playtest uniqueness window: `{payload['playtestUniquenessWindow']}`",
            f"- Layout orientation preference: `{payload['layoutOrientationPreference']}`",
            f"- Layout profile: `{payload['layoutProfile']}`",
            f"- Layout size profile: `{payload['layoutSizeProfile']}`",
            f"- Vertical route probability: `{payload['verticalRouteProbability']}`",
            f"- Prefer vertical for long routes: `{payload['preferVerticalForLongRoutes']}`",
            f"- Xcode project sync: `{payload['syncXcodeProject']}`",
            f"- Swift tests: `{payload['swiftTests']['summary']}`",
            "",
            "## Distributions",
            "",
            f"- Difficulty: `{payload['acceptedDifficultyDistribution']}`",
            f"- Recipe: `{payload['acceptedRecipeDistribution']}`",
            f"- Topology: `{payload['acceptedTopologyDistribution']}`",
            f"- Mechanics: `{payload['acceptedMechanicDistribution']}`",
            f"- Family streaks: `{payload['acceptedFamilyStreaks']}`",
            f"- Topology streaks: `{payload['acceptedTopologyStreaks']}`",
            f"- Map size: `{payload['acceptedMapSizeDistribution']}`",
            f"- Route interest score: `{payload['routeInterestScoreDistribution']}`",
            f"- Route interest by difficulty: `{payload['routeInterestScoreByDifficulty']}`",
            f"- Candidate generation by difficulty: `{payload['candidateGenerationCountsByDifficulty']}`",
            f"- Candidate validation by difficulty: `{payload['candidateValidationCountsByDifficulty']}`",
            f"- Accepted vs rejected by difficulty: `{payload['acceptedRejectedCountsByDifficulty']}`",
            f"- Similarity rejections by difficulty: `{payload['similarityRejectionCountsByDifficulty']}`",
            f"- Starvation causes: `{payload['starvationCauseSummary']}`",
            f"- Rejection stages: `{payload['rejectionStageCounts']}`",
            "",
            "## Accepted Levels",
            "",
            "| Level | Source | Mechanics | Topology | Path | Orientation | Diversity | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |",
            "|---|---|---|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for level in payload["acceptedLevels"]:
            signature = level["signature"]
            signature_summary = ""
            if signature:
                signature_summary = (
                    f"T:{signature['topologyHashShort']} "
                    f"L:{signature['layoutHashShort']} "
                    f"S:{signature['solutionHashShort']}"
                )
            quality_summary = level["quality"]["total"] if level["quality"] else ""
            preview = f"[SVG]({level['previewPath']})" if level["previewPath"] else ""
            source = level["template"]
            if level["recipeFamily"]:
                source = f"{level['recipeFamily']} / {level['recipeVariant']}"
            mechanic_summary = ", ".join(level["mechanicTags"]) or ""
            if level["primaryMechanicTag"]:
                mechanic_summary = f"{level['primaryMechanicTag']}: {mechanic_summary}"
            topology_summary = level["topologyClass"] or ""
            diversity_summary = self._diversity_summary(level["diversityAudit"])
            lines.append(
                "| `{levelID}` | `{source}` | `{mechanic_summary}` | `{topology_summary}` | {requiredPathLength} | "
                "`{layoutOrientation}` | `{diversity_summary}` | {seed} | {difficulty} | "
                "{nodes} | {edges} | {switches} | {parTaps} | {timeLimit} | {quality_summary} | {preview} | "
                "`{signature_summary}` | {status} |".format(
                    source=source,
                    mechanic_summary=mechanic_summary,
                    topology_summary=topology_summary,
                    diversity_summary=diversity_summary,
                    quality_summary=quality_summary,
                    preview=preview,
                    signature_summary=signature_summary,
                    **level,
                )
            )
        if not payload["acceptedLevels"]:
            lines.append("| _None_ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | failed |")

        if payload["acceptedLevels"]:
            lines.extend(["", "## Level Details", ""])
            for level in payload["acceptedLevels"]:
                lines.append(f"### `{level['levelID']}`")
                if level["recipeFamily"]:
                    lines.append(
                        f"- Recipe: `{level['recipeFamily']}` variant `{level['recipeVariant']}`; "
                        f"abstract signature `{level['abstractGraphSignatureShort']}`."
                    )
                    if level["mechanicTags"] or level["unlockRequirement"] or level["priorMechanicDependency"]:
                        lines.append(
                            f"- Mechanics: tags `{', '.join(level['mechanicTags']) or 'none'}`; "
                            f"primary `{level['primaryMechanicTag'] or 'none'}`; "
                            f"topology `{level['topologyClass'] or 'none'}`; "
                            f"required path length `{level['requiredPathLength']}`; "
                            f"layout orientation `{level['layoutOrientation']}` "
                            f"via `{level['layoutOrientationSelectionReason'] or 'unknown'}`; "
                            f"Swift-required `{level['requiresSwiftValidation']}`; "
                            f"runtime validation `{level['runtimeValidationStatus']}`; "
                            f"unlock `{level['unlockRequirement'] or 'none'}`; "
                            f"depends on `{level['priorMechanicDependency'] or 'none'}`."
                        )
                    lines.append(f"- Diversity audit: {self._diversity_summary(level['diversityAudit'])}.")
                    lines.append(
                        f"- Layout: `{level['selectedLayoutVariant']}`; "
                        f"strategy: `{level['layoutStrategy'] or 'unknown'}`; "
                        f"profile: `{level['layoutProfile'] or 'unknown'}`; "
                        f"map size: `{level['layoutSizeProfile'] or 'unknown'}` "
                        f"from `{level['requestedLayoutSizeProfile'] or 'unknown'}` "
                        f"via `{level['layoutSizeSelectionReason'] or 'unknown'}`; "
                        f"orientation: `{level['layoutOrientation']}`; "
                        f"road shapes: `{level['selectedRoadShapeStrategy']}` "
                        f"(score `{(level['roadShapeMetadata'] or {}).get('score', 'unknown')}`)."
                    )
                    if level["portraitMetrics"]:
                        metrics = level["portraitMetrics"]
                        lines.append(
                            f"- Portrait checks: passed `{level['portraitChecksPassed']}`; "
                            f"width `{metrics['width']}`, height `{metrics['height']}`, "
                            f"aspect `{metrics['aspectRatio']}`, "
                            f"start-destination vertical separation `{metrics['verticalSeparation']}`."
                        )
                    if level["verticalCandidateRejectedReason"]:
                        lines.append(
                            f"- Vertical candidate rejected: `{level['verticalCandidateRejectedReason']}`."
                        )
                    if level["roadShapeMetadata"]:
                        road_shape = level["roadShapeMetadata"]
                        lines.append(
                            f"- Road-shape checks: {road_shape.get('crossingCount', 0)} crossings, "
                            f"{road_shape.get('requiredPathCrossingCount', 0)} required-path crossings, "
                            f"{road_shape.get('longParallelSegmentCount', 0)} long parallel segments."
                        )
                    visual_clarity = level["visualClarity"]
                    lines.append(
                        f"- Visual clarity: score `{visual_clarity['score']}`, "
                        f"{len(visual_clarity['issues'])} issue(s)."
                    )
                    layout_readability = level["layoutReadability"]
                    lines.append(
                        f"- Layout readability: passed `{layout_readability['passed']}`, "
                        f"{len(layout_readability['issues'])} issue(s); "
                        f"flags `{layout_readability['metadata']['issueCounts']}`."
                    )
                    if level["abstractSolution"]:
                        abstract = level["abstractSolution"]
                        lines.append(
                            f"- Topology solution: {abstract['minimumRequiredDecisions']} required decisions, "
                            f"{abstract['alternatePathCount']} alternate paths, "
                            f"{abstract['deadEndCount']} dead ends, {abstract['loopCount']} loops."
                        )
                    topology = level["topologyReport"]
                    lines.append(
                        f"- Topology rules: cycles `{topology['allowsCycles']}` "
                        f"allowed `{topology['allowedCycleCount']}` actual `{topology['actualCycleCount']}`; "
                        f"rejoin `{topology['allowsRejoin']}` declared `{topology['declaredRejoinCount']}`; "
                        f"revisit `{topology['allowsRevisit']}` declared `{topology['declaredRevisitCount']}`; "
                        f"return path `{topology['allowsReturnPath']}`; ring `{topology['allowsRing']}`."
                    )
                    if level["uniqueSolutionValidation"]:
                        unique = level["uniqueSolutionValidation"]
                        lines.append(
                            f"- Unique solution validation: solutions `{unique['solutionCount']}`, "
                            f"exhaustive `{unique['isExhaustive']}`, "
                            f"explored states `{unique['exploredStates']}`, "
                            f"max depth `{unique['maxDepthReached']}`, "
                            f"traversal limit `{unique['traversalLimitHit']}`, "
                            f"shortcut `{unique['shortcutDetected']}`, "
                            f"package bypass `{unique['packageBypassDetected']}`, "
                            f"wrong branch reached goal `{unique['wrongBranchReachedGoal']}`, "
                            f"package status `{unique['packageReachabilityStatus']}`, "
                            f"shortest route `{unique['shortestValidRouteLength']}`."
                        )
                        lines.append(
                            f"- Rejoin/revisit validation: rejoin detected `{unique['rejoinDetected']}` "
                            f"count `{unique['rejoinCount']}` declared `{unique['declaredRejoinCount']}` "
                            f"unsafe `{unique['unsafeRejoinDetected']}` reason `{unique['unsafeRejoinReason']}`; "
                            f"revisit detected `{unique['revisitDetected']}` count `{unique['revisitCount']}` "
                            f"declared `{unique['declaredRevisitCount']}` unsafe `{unique['unsafeRevisitDetected']}` "
                            f"reason `{unique['unsafeRevisitReason']}`."
                        )
                runtime = level["runtimeParity"]
                lines.append(
                    f"- Runtime parity: required `{runtime['runtimeValidationRequired']}`; "
                    f"status `{runtime['runtimeValidationStatus']}`; "
                    f"requiresSwiftRuntimeValidation `{runtime['requiresSwiftRuntimeValidation']}`; "
                    f"risky tags `{', '.join(runtime['riskyMechanicTags']) or 'none'}`; "
                    f"reason `{runtime['runtimeValidationReason']}`."
                )
                if runtime["swiftValidationSkippedReason"]:
                    lines.append(
                        f"- Runtime parity skipped reason: `{runtime['swiftValidationSkippedReason']}`."
                    )
                if runtime["failureReason"]:
                    lines.append(f"- Runtime parity failure reason: `{runtime['failureReason']}`.")
                if level["quality"]:
                    quality = level["quality"]
                    categories = quality.get("categoryScores") or {}
                    lines.append(
                        f"- Quality score: `{quality.get('totalScore')}`/100; "
                        f"logic `{categories.get('logicScore')}`, "
                        f"route interest `{categories.get('routeInterestScore')}`, "
                        f"layout `{categories.get('layoutScore')}`, "
                        f"difficulty fit `{categories.get('difficultyFitScore')}`, "
                        f"diversity `{categories.get('diversityScore')}`."
                    )
                    lines.append(
                        f"- Quality factors: positives `{', '.join(quality.get('topPositiveFactors') or []) or 'none'}`; "
                        f"negatives `{', '.join(quality.get('topNegativeFactors') or []) or 'none'}`."
                    )
                    if level["pacingPenalties"]:
                        lines.append(f"- Pacing penalties: `{', '.join(level['pacingPenalties'])}`.")
                    lines.append(
                        f"- Difficulty model: estimated `{quality['estimatedDifficultyBand']}`, "
                        f"mechanical `{quality['mechanicalDifficulty']}`, "
                        f"visual `{quality['visualDifficulty']}`, campaign pacing `{quality['campaignPacing']}`, "
                        f"preset fit `{(quality.get('presetContentFit') or {}).get('score')}`."
                    )
                    lines.append(
                        f"- Score breakdown: mechanic `{quality['abstractMechanicQuality']}`, "
                        f"runtime `{quality['runtimeSolvability']}`, readability `{quality['readability']}`, "
                        f"route interest `{quality['routeInterest']}`, "
                        f"switch clarity `{quality['switchClarity']}`, mobile comfort `{quality['mobileTapComfort']}`, "
                        f"visual appeal `{quality['visualAppeal']}`, diversity `{quality['diversityScore']}` "
                        f"(topology `{quality['topologyDiversityScore']}`, "
                        f"mechanic penalty `{quality['nearbyMechanicTagPenalty']}`, "
                        f"topology penalty `{quality['nearbyTopologyClassPenalty']}`)."
                    )
                    route_interest = level["routeInterestAudit"]
                    lines.append(
                        f"- Route interest: score `{route_interest.get('score')}`; "
                        f"tags `{', '.join(route_interest.get('tags') or []) or 'none'}`; "
                        f"fake shortcut `{route_interest.get('fakeShortcutPresent')}`; "
                        f"branch/rejoin `{route_interest.get('branchRejoinPresent')}`; "
                        f"package tension `{route_interest.get('packageGateTensionPresent')}`; "
                        f"loop/revisit `{route_interest.get('loopRevisitPresent')}`; "
                        f"turns `{route_interest.get('meaningfulTurnCount')}`; "
                        f"repeated topology penalty `{route_interest.get('repeatedTopologyPenalty')}`."
                    )
                solution = level["solution"]
                route_summary = " -> ".join(f"`{node_id}`" for node_id in solution["route"])
                if route_summary:
                    lines.append(f"- Solution route: {route_summary}.")
                if solution["actions"]:
                    tap_summary = ", ".join(
                        (
                            f"tap `{action['tapNodeID']}` at `{action['timeSeconds']:.2f}s`"
                            f" -> `{action.get('expectedEdgeAfterTap') or 'unknown'}`"
                            f" ({action.get('reactionWindowSeconds', 'unknown')}s window)"
                        )
                        for action in solution["actions"]
                    )
                    lines.append(f"- Required taps: {tap_summary}.")
                else:
                    lines.append("- Required taps: none.")
                selection = self._selection_for_level(payload["candidateSelection"], level["levelID"])
                if selection:
                    stats = selection["scoreStats"]
                    lines.append(
                        f"- Candidate selection: {selection['selectionRationale']} "
                        f"Scores min/avg/max `{stats['minimum']}`/`{stats['average']}`/`{stats['maximum']}`."
                    )
                    accepted_summary = selection["acceptedCandidate"]
                    lines.append(
                        f"- Accepted candidate audit: family `{accepted_summary.get('recipeFamily') or 'none'}`; "
                        f"variant `{accepted_summary.get('recipeVariant') or 'none'}`; "
                        f"tags `{', '.join(accepted_summary.get('mechanicTags') or []) or 'none'}`; "
                        f"primary `{accepted_summary.get('primaryMechanicTag') or 'none'}`; "
                        f"topology `{accepted_summary.get('topologyClass') or 'none'}`; "
                        f"path `{accepted_summary.get('requiredPathLength')}`; "
                        f"orientation `{accepted_summary.get('layoutOrientation', 'unknown')}`; "
                        f"Swift-required `{accepted_summary.get('requiresSwiftValidation', False)}`; "
                        f"runtime validation `{accepted_summary.get('runtimeValidationStatus', 'unknown')}`; "
                        f"strategy `{accepted_summary.get('layoutStrategy', 'unknown')}`; "
                        f"variant `{accepted_summary.get('layoutVariant', 'unknown')}`; "
                        f"orientation reason `{accepted_summary.get('layoutOrientationSelectionReason', 'unknown')}`; "
                        f"route interest `{(accepted_summary.get('routeInterestAudit') or {}).get('score')}`; "
                        f"diversity `{self._diversity_summary(accepted_summary.get('diversityAudit') or {})}`."
                    )
                    for near_miss in selection["topRejectedNearMisses"][:3]:
                        near_quality = near_miss.get("quality", {})
                        lines.append(
                            f"- Near miss `{near_miss.get('status')}` seed `{near_miss.get('seed')}` "
                            f"score `{near_quality.get('totalScore', near_quality.get('total'))}` "
                            f"family `{near_miss.get('recipeFamily') or 'none'}` "
                            f"variant `{near_miss.get('recipeVariant') or 'none'}` "
                            f"tags `{', '.join(near_miss.get('mechanicTags') or []) or 'none'}` "
                            f"primary `{near_miss.get('primaryMechanicTag') or 'none'}` "
                            f"topology `{near_miss.get('topologyClass') or 'none'}` "
                            f"path `{near_miss.get('requiredPathLength')}` "
                            f"orientation `{near_miss.get('layoutOrientation', 'unknown')}` "
                            f"Swift-required `{near_miss.get('requiresSwiftValidation', False)}` "
                            f"runtime validation `{near_miss.get('runtimeValidationStatus', 'unknown')}` "
                            f"strategy `{near_miss.get('layoutStrategy', 'unknown')}` "
                            f"variant `{near_miss.get('layoutVariant', 'unknown')}` "
                            f"orientation reason `{near_miss.get('layoutOrientationSelectionReason', 'unknown')}` "
                            f"route interest `{(near_miss.get('routeInterestAudit') or {}).get('score')}` "
                            f"diversity `{self._diversity_summary(near_miss.get('diversityAudit') or {})}`."
                        )
                    not_selected = selection.get("notSelectedCandidates") or []
                    if not_selected:
                        lines.append(
                            f"- Not selected after quality scoring: `{len(not_selected)}` candidate(s); "
                            f"top status `{not_selected[0].get('acceptedOrRejectedReason')}` "
                            f"seed `{not_selected[0].get('seed')}`."
                        )
                for switch in level["switchPreview"]:
                    transition_summary = ", ".join(
                        (
                            f"tap {transition['tapSequence']} @ {transition['timeSeconds']:.2f}s"
                            f" -> `{transition['targetEdgeID']}` ({transition['postTapArrowDirection']})"
                        )
                        for transition in switch["tapTransitions"]
                    ) or "no scripted taps"
                    lines.append(
                        f"- Switch `{switch['switchID']}` starts on `{switch['initialActiveEdgeID']}` "
                        f"({switch['initialArrowDirection']}); {transition_summary}."
                    )
                for warning in level["warnings"]:
                    lines.append(f"- Warning: {warning}")
                for issue in level["visualClarity"]["issues"]:
                    lines.append(
                        f"- Visual clarity {issue['severity']}: `{issue['code']}` "
                        f"node `{issue['relatedNodeID']}` edge `{issue['relatedEdgeID']}`."
                    )
                for issue in level["layoutReadability"]["issues"]:
                    lines.append(
                        f"- Layout readability {issue['severity']}: `{issue['code']}` "
                        f"nodes `{issue['relatedNodeIDs']}` roads `{issue['relatedEdgeIDs']}`."
                    )
                if not level["switchPreview"] and not level["warnings"]:
                    lines.append("- No switch-specific review notes.")

        lines.extend(["", "## Rejections", ""])
        lines.append(f"- Rejected candidates: `{payload['rejectedCandidateCount']}`")
        lines.append(f"- Rejection stages: `{payload['rejectionStageCounts']}`")
        for reason, count in sorted(payload["rejectionReasonCounts"].items()):
            lines.append(f"- `{reason}`: {count}")
        if payload["topRejectedNearMisses"]:
            lines.extend(["", "### Top Rejected Near Misses", ""])
            for near_miss in payload["topRejectedNearMisses"][:10]:
                quality = near_miss.get("quality") or near_miss.get("qualityScoreBreakdown") or {}
                score = quality.get("totalScore", quality.get("totalQualityScore"))
                lines.append(
                    f"- `{near_miss.get('candidateID')}` stage `{near_miss.get('validationStage')}` "
                    f"code `{near_miss.get('rejectionCode')}` score `{score}` "
                    f"difficulty `{near_miss.get('difficulty')}` family `{near_miss.get('recipeFamily') or 'none'}` "
                    f"topology `{near_miss.get('topologyClass') or 'none'}` seed `{near_miss.get('seed')}`."
                )

        if payload["messages"]:
            lines.extend(["", "## Messages", ""])
            for message in payload["messages"]:
                lines.append(f"- {message}")

        if payload["recommendations"]:
            lines.extend(["", "## Recommendations", ""])
            for recommendation in payload["recommendations"]:
                lines.append(f"- {recommendation}")

        lines.extend(
            [
                "",
                "## Swift Test Summary",
                "",
                f"- Command: `{ ' '.join(payload['swiftTests']['command']) if payload['swiftTests']['command'] else 'not run' }`",
                f"- Result: `{payload['swiftTests']['summary']}`",
            ]
        )
        if payload["swiftTests"].get("environment"):
            lines.append(f"- Environment: `{payload['swiftTests']['environment']}`")
        if payload["swiftTests"].get("failureDetails"):
            lines.append("- Failure details:")
            for detail in payload["swiftTests"]["failureDetails"]:
                lines.append(f"  - `{detail}`")
        if payload["swiftTests"].get("failureReasons"):
            lines.append(f"- Failure reasons: `{payload['swiftTests']['failureReasons']}`")
        lines.extend(
            [
                "",
                "## Next Steps",
                "",
                "- Open generated levels in the Level Editor.",
                "- Run Python validation and Swift solvability before committing production levels.",
                "- `xcodegen generate` runs automatically for default production output; rerun it manually if resources were deleted outside the generator.",
                "",
            ]
        )
        return "\n".join(lines)

    def _write_previews(self, report_dir: Path, result) -> None:
        if not result.accepted:
            return
        preview_dir = report_dir / "previews"
        for level in result.accepted:
            if level.preview_path is None:
                self.preview_image_service.write_preview(level, preview_dir)

    def _signature_payload(self, level) -> dict[str, Any] | None:
        signature = getattr(level, "candidate_signature", None)
        if signature is None:
            return None
        return {
            "levelID": signature.level_id,
            "template": signature.template_name,
            "difficulty": signature.difficulty,
            "nodeCount": signature.node_count,
            "edgeCount": signature.edge_count,
            "switchCount": signature.switch_count,
            "requiredTapCount": signature.required_tap_count,
            "deadEndCount": signature.dead_end_count,
            "maxOutgoingEdgeCount": signature.max_outgoing_edge_count,
            "hasFourWaySwitch": signature.has_four_way_switch,
            "centralSwitchRevisitCount": signature.central_switch_revisit_count,
            "mechanicTags": list(signature.mechanic_tags),
            "primaryMechanicTag": signature.primary_mechanic_tag or None,
            "topologyClass": signature.topology_class or None,
            "requiredPathLength": signature.required_path_length,
            "layoutOrientation": signature.layout_orientation,
            "layoutSizeProfile": signature.layout_size_profile,
            "diversityAudit": {
                "topologyDiversityScore": signature.topology_diversity_score,
                "nearbyMechanicTagPenalty": signature.nearby_mechanic_tag_penalty,
                "nearbyTopologyClassPenalty": signature.nearby_topology_class_penalty,
                "diversityScore": signature.diversity_score,
            },
            "topologyHash": signature.topology_hash,
            "topologyHashShort": signature.topology_hash[:8],
            "layoutHash": signature.layout_hash,
            "layoutHashShort": signature.layout_hash[:8],
            "solutionHash": signature.solution_hash,
            "solutionHashShort": signature.solution_hash[:8],
            "normalizedPositions": list(signature.normalized_positions),
        }

    def _candidate_status_payload(
        self,
        level,
        *,
        status: str,
        reason: str,
        detail: str | None,
    ) -> dict[str, Any]:
        rejection_code = None if status == "accepted" else reason
        return {
            "candidateID": f"{level.level_id}:{level.seed}",
            "status": status,
            "acceptedOrRejectedReason": reason,
            "validationStage": (
                "candidate_selection"
                if status == "accepted"
                else CandidateRejectionService.validation_stage_for_code(rejection_code)
            ),
            "rejectionCode": rejection_code,
            "rejectionDetails": detail,
        }

    def _topology_reporting_payload(self, level) -> dict[str, Any]:
        metadata = getattr(level, "mechanic_metadata", {}) or {}
        raw_rules = metadata.get("topologyRules") if isinstance(metadata, dict) else None
        topology_rules = dict(raw_rules) if isinstance(raw_rules, dict) else {}
        unique = getattr(level, "unique_solution_validation_result", None)
        abstract = getattr(level, "abstract_solution_metadata", None)
        declared_loop_count = self._declared_int(metadata, ("declaredLoopCount", "declaredCycleCount", "loopCount"))
        if declared_loop_count is None:
            declared_loop_count = getattr(abstract, "loop_count", None)
        declared_rejoin_count = getattr(unique, "declared_rejoin_count", None)
        if declared_rejoin_count is None:
            declared_rejoin_count = self._declared_count(
                metadata,
                ("declaredRejoinCount", "allowedRejoinCount", "rejoinCount"),
                ("declaredRejoinNodeIDs", "rejoinNodeIDs"),
            )
        declared_revisit_count = getattr(unique, "declared_revisit_count", None)
        if declared_revisit_count is None:
            declared_revisit_count = self._declared_count(
                metadata,
                ("declaredRevisitCount", "allowedRevisitCount", "revisitCount"),
                ("declaredRevisitNodeIDs", "revisitNodeIDs", "repeatedNodeIDs"),
            )
        report = {
            "topologyRules": topology_rules,
            "allowsCycles": bool(topology_rules.get("allowsCycles", False)),
            "allowsRejoin": bool(topology_rules.get("allowsRejoin", False)),
            "allowsRevisit": bool(topology_rules.get("allowsRevisit", False)),
            "allowsReturnPath": bool(topology_rules.get("allowsReturnPath", False)),
            "allowsRing": bool(topology_rules.get("allowsRing", False)),
            "allowedCycleCount": int(topology_rules.get("allowedCycleCount", 0) or 0),
            "actualCycleCount": self._actual_cycle_count(level),
            "declaredLoopCount": int(declared_loop_count or 0),
            "declaredRejoinCount": int(declared_rejoin_count or 0),
            "declaredRevisitCount": int(declared_revisit_count or 0),
        }
        return {
            "topologyReport": report,
            **report,
        }

    def _solver_reporting_payload(self, level) -> dict[str, Any]:
        result = getattr(level, "unique_solution_validation_result", None)
        if result is None:
            return {
                "solutionCount": None,
                "exploredStates": 0,
                "maxDepthReached": 0,
                "traversalLimitHit": False,
                "packageReachabilityStatus": "not_evaluated",
                "shortestValidRouteLength": None,
                "intendedRouteLength": self._required_path_length(level),
                "shortcutDetected": False,
                "packageBypassDetected": False,
                "wrongBranchReachedGoal": False,
            }
        terminal_reason_counts = dict(result.terminal_reason_counts)
        return {
            "solutionCount": result.solution_count,
            "exploredStates": result.explored_states,
            "maxDepthReached": result.max_depth_reached,
            "traversalLimitHit": (
                result.termination_reason in {"max_explored_states_reached", "max_traversal_depth_reached"}
                or terminal_reason_counts.get("max_traversal_depth_reached", 0) > 0
                or terminal_reason_counts.get("max_taps_reached", 0) > 0
            ),
            "packageReachabilityStatus": result.package_reachability_status,
            "shortestValidRouteLength": result.shortest_valid_route_length,
            "intendedRouteLength": result.intended_route_length,
            "shortcutDetected": result.shortcut_detected,
            "packageBypassDetected": result.package_bypass_detected,
            "wrongBranchReachedGoal": result.wrong_branch_reached_goal,
        }

    def _layout_readability_report_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(payload.get("metadata") or {})
        return {
            "layoutReadabilityPassed": bool(metadata.get("passed", payload.get("passed", False))),
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

    def _road_shape_report_payload(self, level) -> dict[str, Any]:
        metadata = getattr(level, "road_shape_metadata", None) or {}
        return {
            "switchDirectionQuality": metadata.get("switchClarityScore"),
            "ambiguousSwitchDetected": bool(metadata.get("ambiguousSwitchDetected", False)),
            "directionBucketAssignments": metadata.get("directionBucketAssignments", {}),
            "switchExitAngleSeparation": metadata.get("switchExitAngleSeparation", {}),
            "roadShapeWarnings": list(metadata.get("warnings", [])),
            "roadShapeIssues": list(metadata.get("issues", [])),
            "readabilityAdjustments": list(metadata.get("readabilityAdjustments", [])),
        }

    def _quality_breakdown_payload(self, level) -> dict[str, Any] | None:
        quality = getattr(level, "quality_score", None)
        if quality is None:
            return None
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

    def _difficulty_fit_payload(self, level) -> dict[str, Any]:
        quality = getattr(level, "quality_score", None)
        if quality is None:
            return {}
        return {
            "difficultyFitScore": quality.difficulty_fit,
            "estimatedDifficultyBand": quality.estimated_difficulty_band,
            "mechanicalDifficulty": quality.mechanical_difficulty,
            "visualDifficulty": quality.visual_difficulty,
            "presetContentFit": quality.details.get("presetContentFit", {}),
        }

    def _top_rejected_near_misses(self, result) -> list[dict[str, Any]]:
        rejected = list(getattr(result, "rejected_candidate_summaries", []) or [])
        return sorted(
            rejected,
            key=lambda item: (item.get("quality") or {}).get(
                "totalScore",
                (item.get("qualityScoreBreakdown") or {}).get("totalQualityScore") or 0.0,
            ),
            reverse=True,
        )[:10]

    def _actual_cycle_count(self, level) -> int:
        adjacency: dict[str, list[str]] = {}
        for edge in level.level_document.graph.edges:
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

    def _declared_count(self, metadata: dict[str, Any], count_keys: tuple[str, ...], node_keys: tuple[str, ...]) -> int | None:
        explicit = self._declared_int(metadata, count_keys)
        if explicit is not None:
            return explicit
        for key in node_keys:
            value = metadata.get(key)
            if isinstance(value, (list, tuple)):
                return len(value)
        return None

    def _declared_int(self, metadata: dict[str, Any], keys: tuple[str, ...]) -> int | None:
        for key in keys:
            value = metadata.get(key)
            if isinstance(value, int) and value >= 0:
                return value
        return None

    def _required_path_length(self, level) -> int | None:
        signature = getattr(level, "candidate_signature", None)
        if signature is not None and signature.required_path_length is not None:
            return signature.required_path_length
        metadata = getattr(level, "abstract_solution_metadata", None)
        if metadata is not None and getattr(metadata, "required_path", None):
            return max(len(metadata.required_path) - 1, 0)
        solution_metadata = dict(getattr(level.solution, "_extra", {}).get("metadata", {}))
        route = solution_metadata.get("solutionRoute") or []
        if route:
            return max(len(route) - 1, 0)
        return None

    def _layout_orientation(self, level) -> str:
        signature = getattr(level, "candidate_signature", None)
        if signature is not None:
            return signature.layout_orientation
        metadata = getattr(level, "layout_metadata", None) or {}
        explicit = metadata.get("orientation")
        if explicit:
            return str(explicit).strip().lower() or "unknown"
        strategy = str(metadata.get("strategy", "")).lower()
        if "vertical" in strategy:
            return "vertical"
        if "horizontal" in strategy:
            return "horizontal"
        variant = str(getattr(level, "selected_layout_variant", "") or metadata.get("variant", "")).lower()
        if variant == "tall":
            return "vertical"
        if variant == "wide":
            return "horizontal"
        return "unknown"

    def _diversity_audit(self, level) -> dict[str, float | None]:
        signature = getattr(level, "candidate_signature", None)
        return {
            "topologyDiversityScore": getattr(signature, "topology_diversity_score", None),
            "nearbyMechanicTagPenalty": getattr(signature, "nearby_mechanic_tag_penalty", None),
            "nearbyTopologyClassPenalty": getattr(signature, "nearby_topology_class_penalty", None),
            "diversityScore": getattr(signature, "diversity_score", None),
        }

    def _diversity_summary(self, audit: dict[str, Any]) -> str:
        return (
            f"topology {audit.get('topologyDiversityScore')}, "
            f"mechanic penalty {audit.get('nearbyMechanicTagPenalty')}, "
            f"topology penalty {audit.get('nearbyTopologyClassPenalty')}, "
            f"score {audit.get('diversityScore')}"
        )

    def _quality_payload(self, level) -> dict[str, Any] | None:
        quality = getattr(level, "quality_score", None)
        if quality is None:
            return None
        return {
            "totalScore": quality.total_score,
            "categoryScores": quality.category_scores,
            "total": quality.total,
            "abstractMechanicQuality": quality.abstract_mechanic_quality,
            "runtimeSolvability": quality.runtime_solvability,
            "readability": quality.readability,
            "switchClarity": quality.switch_clarity,
            "uniqueness": quality.uniqueness,
            "difficultyFit": quality.difficulty_fit,
            "routeInterest": quality.route_interest,
            "mobileTapComfort": quality.mobile_tap_comfort,
            "visualAppeal": quality.visual_appeal,
            "campaignPacing": quality.campaign_pacing,
            "topologyDiversityScore": quality.topology_diversity_score,
            "nearbyMechanicTagPenalty": quality.nearby_mechanic_tag_penalty,
            "nearbyTopologyClassPenalty": quality.nearby_topology_class_penalty,
            "diversityScore": quality.diversity_score,
            "mechanicalDifficulty": quality.mechanical_difficulty,
            "visualDifficulty": quality.visual_difficulty,
            "estimatedDifficultyBand": quality.estimated_difficulty_band,
            "topPositiveFactors": list(quality.top_positive_factors),
            "topNegativeFactors": list(quality.top_negative_factors),
            "penalties": list(quality.penalties),
            "baseQualityScore": quality.details.get("baseQualityScore", quality.total),
            "presetContentFit": quality.details.get("presetContentFit", {}),
            "campaignPacingDetails": quality.details.get("campaignPacing", {}),
            "details": quality.details,
        }

    def _pacing_penalties(self, level) -> list[str]:
        quality = getattr(level, "quality_score", None)
        if quality is None:
            return []
        return [penalty for penalty in quality.penalties if penalty.startswith("campaign_")]

    def _distribution(self, values) -> dict[str, int]:
        return dict(sorted(Counter(value for value in values if value).items()))

    def _dry_run_summary(self, config, result) -> dict[str, Any]:
        accepted_count = len(getattr(result, "accepted", []))
        rejected_count = int(getattr(result, "rejected_candidate_count", 0))
        attempted_count = int(getattr(result, "candidate_validation_count", 0)) or accepted_count + rejected_count
        return {
            "safeScratchRun": bool(config.dry_run),
            "acceptedCount": accepted_count,
            "candidateGenerationCount": int(getattr(result, "candidate_generation_count", 0)),
            "candidateValidationCount": int(getattr(result, "candidate_validation_count", 0)),
            "rejectedCandidateCount": rejected_count,
            "attemptedCandidateCount": attempted_count,
            "passRate": round(accepted_count / attempted_count, 4) if attempted_count else None,
            "candidateGenerationCountsByDifficulty": dict(
                sorted(getattr(result, "candidate_generation_counts_by_difficulty", {}).items())
            ),
            "candidateValidationCountsByDifficulty": dict(
                sorted(getattr(result, "candidate_validation_counts_by_difficulty", {}).items())
            ),
            "difficultyDistribution": self._distribution(level.difficulty for level in result.accepted),
            "recipeDistribution": self._distribution(level.recipe_family or level.template_name for level in result.accepted),
            "topologyDistribution": self._distribution(
                getattr(level, "topology_class", "") or "unknown" for level in result.accepted
            ),
            "familyStreaks": self._accepted_streaks(
                level.recipe_family or level.template_name for level in result.accepted
            ),
            "topologyStreaks": self._accepted_streaks(
                getattr(level, "topology_class", "") or "unknown" for level in result.accepted
            ),
            "mapSizeDistribution": self._distribution(
                (level.layout_metadata or {}).get("layoutSizeProfile", "unknown") for level in result.accepted
            ),
            "routeInterestScoreDistribution": self._score_distribution(
                self._route_interest_audit(level).get("score")
                for level in result.accepted
                if self._route_interest_audit(level)
            ),
            "routeInterestScoreByDifficulty": self._route_interest_by_difficulty(result),
            "rejectionReasons": dict(getattr(result, "rejection_reason_counts", {})),
            "rejectionStageCounts": dict(getattr(result, "rejection_stage_counts", {})),
            "rejectionReasonCountsByDifficulty": dict(
                sorted(getattr(result, "rejection_reason_counts_by_difficulty", {}).items())
            ),
            "similarityRejectionCountsByDifficulty": dict(
                sorted(getattr(result, "similarity_rejection_counts_by_difficulty", {}).items())
            ),
        }

    def _accepted_streaks(self, values) -> dict[str, Any]:
        streaks = []
        current_value = None
        current_count = 0
        for value in values:
            value = value or "unknown"
            if value == current_value:
                current_count += 1
                continue
            if current_value is not None:
                streaks.append({"value": current_value, "length": current_count})
            current_value = value
            current_count = 1
        if current_value is not None:
            streaks.append({"value": current_value, "length": current_count})
        longest = max(streaks, key=lambda item: item["length"], default=None)
        return {
            "longest": longest,
            "repeatedStreaks": [streak for streak in streaks if streak["length"] > 1],
        }

    def _route_interest_by_difficulty(self, result) -> dict[str, dict[str, Any]]:
        scores_by_difficulty: dict[str, list[float]] = {}
        for level in result.accepted:
            audit = self._route_interest_audit(level)
            score = audit.get("score")
            if score is None:
                continue
            scores_by_difficulty.setdefault(level.difficulty, []).append(float(score))
        return {
            difficulty: {
                "minimum": round(min(scores), 4),
                "average": round(sum(scores) / len(scores), 4),
                "maximum": round(max(scores), 4),
                "count": len(scores),
                "distribution": self._score_distribution(scores),
            }
            for difficulty, scores in sorted(scores_by_difficulty.items())
            if scores
        }

    def _score_distribution(self, scores) -> dict[str, int]:
        buckets = Counter()
        for score in scores:
            if score is None:
                continue
            value = float(score)
            if value < 0.42:
                bucket = "below_medium"
            elif value < 0.54:
                bucket = "medium_gate"
            elif value < 0.58:
                bucket = "hard_gate"
            elif value < 0.75:
                bucket = "expert_gate"
            elif value < 0.90:
                bucket = "strong"
            else:
                bucket = "excellent"
            buckets[bucket] += 1
        return dict(sorted(buckets.items()))

    def _accepted_rejected_counts_by_difficulty(self, result) -> dict[str, dict[str, int]]:
        accepted = Counter(level.difficulty for level in result.accepted)
        rejected_by_difficulty = {
            difficulty: sum(reasons.values())
            for difficulty, reasons in getattr(result, "rejection_reason_counts_by_difficulty", {}).items()
        }
        difficulties = sorted(set(accepted) | set(rejected_by_difficulty))
        if not difficulties:
            total_rejected = int(getattr(result, "rejected_candidate_count", 0))
            return {"unknown": {"accepted": 0, "rejected": total_rejected}}
        counts = {}
        for difficulty in difficulties:
            counts[difficulty] = {
                "accepted": accepted.get(difficulty, 0),
                "rejected": rejected_by_difficulty.get(difficulty, 0),
            }
        return counts

    def _starvation_cause_summary(self, result) -> dict[str, Any]:
        counts = Counter(getattr(result, "rejection_reason_counts", {}) or {})
        total = sum(counts.values())
        categories = {
            "batchSimilarity": sum(count for reason, count in counts.items() if "similar" in reason or "duplicate" in reason),
            "readabilityBlockedRoads": counts.get("important_node_readability_blocked_by_road", 0),
            "tapTiming": sum(count for reason, count in counts.items() if "tap" in reason or "arrival" in reason),
            "layoutValidity": sum(
                count
                for reason, count in counts.items()
                if reason.startswith("layout_")
                or reason.startswith("portrait_layout")
                or reason in {
                    "implicit_intersection_without_graph_node",
                    "same_switch_first_segments_overlap",
                    "implicit_intersection_without_node",
                    "switch_exit_overlap",
                    "node_spacing_failure",
                    "start_goal_separation_failure",
                    "portrait_safety_failure",
                    "road_proximity_failure",
                    "important_node_visibility_failure",
                }
            ),
            "routeInterestGate": sum(count for reason, count in counts.items() if "route_interest" in reason or "boring_topology" in reason),
            "largePortraitNeedGate": counts.get("large_portrait_without_puzzle_need", 0),
        }
        sorted_categories = sorted(categories.items(), key=lambda item: item[1], reverse=True)
        return {
            "totalRejections": total,
            "phaseCounts": {
                "generationErrors": int(getattr(result, "generation_error_count", 0)),
                "validationFailures": int(getattr(result, "validation_rejection_count", 0)),
                "selectionFilters": int(getattr(result, "filter_rejection_count", 0)),
            },
            "topCategories": [
                {
                    "category": category,
                    "count": count,
                    "share": round(count / total, 4) if total else 0.0,
                }
                for category, count in sorted_categories
                if count
            ][:5],
            "topReasons": [
                {"reason": reason, "count": count, "share": round(count / total, 4) if total else 0.0}
                for reason, count in counts.most_common(5)
            ],
        }

    def _route_interest_audit(self, level) -> dict[str, Any]:
        quality = getattr(level, "quality_score", None)
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

    def _selection_for_level(self, selection_summaries: list[dict[str, Any]], level_id: str) -> dict[str, Any] | None:
        return next(
            (summary for summary in selection_summaries if summary.get("levelID") == level_id),
            None,
        )

    def _abstract_solution_payload(self, level) -> dict[str, Any] | None:
        metadata = getattr(level, "abstract_solution_metadata", None)
        if metadata is None:
            return None
        return metadata.to_dict()

    def _simulation_payload(self, level) -> dict[str, Any] | None:
        simulation = getattr(level, "simulation_result", None)
        if simulation is None:
            return None
        return {
            "passed": simulation.passed,
            "outcome": simulation.outcome,
            "failureReason": simulation.failure_reason,
            "elapsedTimeSeconds": simulation.elapsed_time_seconds,
            "tapCount": simulation.tap_count,
            "reachedPackage": simulation.reached_package,
            "reachedDestination": simulation.reached_destination,
        }

    def _runtime_parity_payload(self, level) -> dict[str, Any]:
        result = getattr(level, "runtime_parity_validation_result", None)
        if result is not None:
            return result.to_metadata()
        return {
            "runtimeValidationRequired": bool(getattr(level, "requires_swift_validation", False)),
            "runtimeValidationStatus": "unknown",
            "runtimeValidationReason": "Runtime parity gate has not evaluated this level.",
            "swiftValidationCommand": [],
            "swiftValidationEnvironment": {},
            "swiftValidationPassed": None,
            "swiftValidationSkippedReason": None,
            "riskyMechanicTags": [],
            "requiresSwiftRuntimeValidation": bool(getattr(level, "requires_swift_validation", False)),
            "failureReason": None,
            "failureDetails": [],
        }

    def _unique_solution_payload(self, level) -> dict[str, Any] | None:
        result = getattr(level, "unique_solution_validation_result", None)
        if result is None:
            return None
        bypass_summary = result.bypass_path_summary.to_dict() if result.bypass_path_summary else None
        terminal_reason_counts = dict(result.terminal_reason_counts)
        return {
            "requiresUniqueSolution": result.requires_unique_solution,
            "isExhaustive": result.is_exhaustive,
            "solutionCount": result.solution_count,
            "exploredStates": result.explored_states,
            "maxDepthReached": result.max_depth_reached,
            "traversalLimitHit": (
                result.termination_reason in {"max_explored_states_reached", "max_traversal_depth_reached"}
                or terminal_reason_counts.get("max_traversal_depth_reached", 0) > 0
                or terminal_reason_counts.get("max_taps_reached", 0) > 0
            ),
            "terminationReason": result.termination_reason,
            "terminalReasonCounts": terminal_reason_counts,
            "shortcutDetected": result.shortcut_detected,
            "packageBypassDetected": result.package_bypass_detected,
            "wrongBranchReachedGoal": result.wrong_branch_reached_goal,
            "bypassPathSummary": bypass_summary,
            "intendedRouteLength": result.intended_route_length,
            "shortestValidRouteLength": result.shortest_valid_route_length,
            "packageReachabilityStatus": result.package_reachability_status,
            "rejoinDetected": result.rejoin_detected,
            "rejoinCount": result.rejoin_count,
            "declaredRejoinCount": result.declared_rejoin_count,
            "unsafeRejoinDetected": result.unsafe_rejoin_detected,
            "unsafeRejoinReason": result.unsafe_rejoin_reason,
            "revisitDetected": result.revisit_detected,
            "revisitCount": result.revisit_count,
            "declaredRevisitCount": result.declared_revisit_count,
            "unsafeRevisitDetected": result.unsafe_revisit_detected,
            "unsafeRevisitReason": result.unsafe_revisit_reason,
            "repeatedNodeIDs": list(result.repeated_node_ids),
            "repeatedSwitchIDs": list(result.repeated_switch_ids),
            "maxVisitCountByNode": dict(result.max_visit_count_by_node),
            "issues": [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "relatedNodeID": issue.related_node_id,
                    "relatedEdgeID": issue.related_edge_id,
                }
                for issue in result.issues
            ],
            "successfulPathSummaries": [
                summary.to_dict()
                for summary in result.successful_path_summaries[:3]
            ],
            "destinationBeforePackageSummaries": [
                summary.to_dict()
                for summary in result.destination_before_package_summaries[:3]
            ],
            "failurePathSummaries": [
                summary.to_dict()
                for summary in result.failure_path_summaries[:3]
            ],
            "notes": list(result.notes),
        }

    def _visual_clarity_payload(self, level) -> dict[str, Any]:
        report = self.visual_clarity_validation.report_for_generated_level(level)
        return {
            "score": report.score,
            "metadata": report.metadata,
            "issues": [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "relatedNodeID": issue.related_node_id,
                    "relatedEdgeID": issue.related_edge_id,
                    "relatedEdgeIDs": list(issue.related_edge_ids),
                }
                for issue in report.issues
            ],
        }

    def _layout_readability_payload(self, level) -> dict[str, Any]:
        report = getattr(level, "layout_readability_validation_result", None)
        if report is None:
            report = self.layout_readability_validator.report_for_generated_level(level)
        return {
            "passed": not report.has_errors,
            "metadata": report.metadata,
            "issues": [issue.to_dict() for issue in report.issues],
        }

    def _solution_payload(self, level) -> dict[str, Any]:
        solution = level.solution
        metadata = dict(getattr(solution, "_extra", {}).get("metadata", {}))
        abstract = getattr(level, "abstract_solution_metadata", None)
        route = list(metadata.get("solutionRoute") or (abstract.required_path if abstract else []))
        return {
            "description": solution.description,
            "metadata": metadata,
            "route": route,
            "requiredTapOrder": list(
                metadata.get("requiredTapOrder")
                or [action.tapNodeID for action in solution.actions]
            ),
            "actions": [
                {
                    "timeSeconds": float(action.timeSeconds),
                    "tapNodeID": action.tapNodeID,
                    **dict(getattr(action, "_extra", {})),
                }
                for action in sorted(solution.actions, key=lambda action: float(action.timeSeconds))
            ],
        }

    def _switch_preview_payload(self, level) -> list[dict[str, Any]]:
        level_document = level.level_document
        node_by_id = {node.id: node for node in level_document.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level_document.graph.edges}
        visual_reports_by_switch_id = {
            report.switch_id: report
            for report in self.switch_visual_clarity.report_for_level(level_document)
        }
        direction_by_edge_id = {
            direction.edge_id: direction
            for report in visual_reports_by_switch_id.values()
            for direction in report.directions
        }
        actions_by_node_id: dict[str, list[Any]] = {}
        for action in sorted(level.solution.actions, key=lambda action: float(action.timeSeconds)):
            actions_by_node_id.setdefault(action.tapNodeID, []).append(action)

        switch_previews: list[dict[str, Any]] = []
        for node in level_document.graph.nodes:
            valid_edges = [
                edge_by_id[edge_id]
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            if len(valid_edges) < 2:
                continue

            active_index = 0
            initial_edge = valid_edges[active_index]
            visual_report = visual_reports_by_switch_id.get(node.id)
            switch_preview = {
                "switchID": node.id,
                "initialActiveEdgeID": initial_edge.id,
                "initialTargetNodeID": initial_edge.toNodeID,
                "initialArrowDirection": self._edge_direction_label(initial_edge, direction_by_edge_id, node_by_id),
                "visualDirectionBuckets": [
                    {
                        "edgeID": direction.edge_id,
                        "targetNodeID": direction.target_node_id,
                        "bucket": direction.bucket,
                        "angle": direction.angle,
                        "ambiguous": direction.is_ambiguous,
                        "ambiguousReason": direction.ambiguous_reason,
                    }
                    for direction in (visual_report.directions if visual_report is not None else [])
                ],
                "tapTransitions": [],
            }

            for tap_index, action in enumerate(actions_by_node_id.get(node.id, []), start=1):
                active_index = (active_index + 1) % len(valid_edges)
                target_edge = valid_edges[active_index]
                switch_preview["tapTransitions"].append(
                    {
                        "tapSequence": tap_index,
                        "timeSeconds": float(action.timeSeconds),
                        "targetEdgeID": target_edge.id,
                        "targetNodeID": target_edge.toNodeID,
                        "postTapArrowDirection": self._edge_direction_label(
                            target_edge,
                            direction_by_edge_id,
                            node_by_id,
                        ),
                    }
                )

            switch_previews.append(switch_preview)
        return switch_previews

    def _edge_direction_label(self, edge, direction_by_edge_id, node_by_id) -> str:
        direction = direction_by_edge_id.get(edge.id)
        if direction is not None and direction.bucket is not None:
            return direction.bucket
        from_node = node_by_id.get(edge.fromNodeID)
        to_node = node_by_id.get(edge.toNodeID)
        if from_node is None or to_node is None:
            return "east"
        angle = self.route_timing.direction_angle(
            (from_node.x, from_node.y),
            (to_node.x, to_node.y),
            edge.roadShape,
        )
        return self.route_timing.direction_label(angle)

    def _recommendations(self, config, result) -> list[str]:
        if getattr(result, "passed", True):
            return []
        rejection_counts = dict(getattr(result, "rejection_reason_counts", {}))
        if not rejection_counts:
            return []

        most_common_reason = max(rejection_counts.items(), key=lambda item: item[1])[0]
        recommendations: list[str] = [f"Most common rejection: `{most_common_reason}`."]
        if most_common_reason == "candidate_too_similar_to_batch":
            recommendations.extend(
                [
                    "For playtest batches, rerun with `--playtest-mode`.",
                    "Increase `--candidate-pool-size`.",
                    "Enable more hard templates with `--swift-tests`.",
                    "Use `--difficulty auto` instead of hard-only.",
                    "Generate fewer levels per batch.",
                    "Add a new hard template variant.",
                ]
            )
        elif most_common_reason == "solution_tap_not_before_switch_arrival":
            recommendations.extend(
                [
                    "Increase timed-tap lead time or route the switch earlier in the path.",
                    "Review switch preview metadata for dead-end-first defaults.",
                    "Run with `--swift-tests` before writing production files.",
                ]
            )
        elif most_common_reason == "missing_required_swift_validation":
            recommendations.extend(
                [
                    "Rerun production generation with `--swift-tests`.",
                    "Use `--dry-run` when you only need Python-side reporting for risky mechanics.",
                    "Review `riskyMechanicTags` and `runtimeValidationReason` in the JSON report.",
                ]
            )
        elif most_common_reason in {
            "swift_runtime_parity_failed",
            "solution_sidecar_runtime_mismatch",
            "switch_tap_runtime_mismatch",
            "package_order_runtime_mismatch",
        }:
            recommendations.extend(
                [
                    "Inspect the Swift test failure details for the affected level.",
                    "Compare the sidecar `expectedEdgeAfterTap` metadata against RouteEngine replay.",
                    "Regenerate or reject the candidate before committing production files.",
                ]
            )
        return recommendations
