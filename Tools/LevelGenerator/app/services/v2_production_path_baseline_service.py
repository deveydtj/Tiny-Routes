from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..generation_config import GenerationConfig
from ..random_source import RandomSource
from ..recipes.recipe_family_registry import RecipeFamilyRegistry
from .decision_profile_service import DecisionProfileService
from .difficulty_service import DifficultyService
from .level_generation_service import LevelGenerationService
from .topology_solver_service import TopologySolverService


@dataclass(frozen=True)
class V2ProductionPathBaselineSuite:
    name: str
    difficulty: str
    start_level_number: int
    seed: int
    count: int = 1
    max_attempts_per_level: int = 40


DEFAULT_V2_PRODUCTION_PATH_BASELINE_SUITES: tuple[V2ProductionPathBaselineSuite, ...] = (
    V2ProductionPathBaselineSuite("tutorial_production_path", "tutorial", 701, 1803001),
    V2ProductionPathBaselineSuite("easy_production_path", "easy", 711, 1803002),
    V2ProductionPathBaselineSuite("medium_production_path", "medium", 721, 1803003),
    V2ProductionPathBaselineSuite("hard_production_path", "hard", 731, 1803004),
    V2ProductionPathBaselineSuite("expert_production_path", "expert", 741, 1803005),
)


class V2ProductionPathBaselineService:
    """Captures V2 limitations without template or fixed-motif execution shortcuts."""

    KNOWN_MISMATCHES: tuple[dict[str, str], ...] = (
        {
            "family": "return_loop_intro",
            "classification": "mislabeled",
            "evidence": "Delegates to the ordinary medium two-switch chain builder.",
        },
        {
            "family": "ring_route_gate",
            "classification": "mislabeled",
            "evidence": "Uses non-ring topology rules and a simple chain builder.",
        },
        {
            "family": "return_loop_with_gate,multi_switch_revisit",
            "classification": "behavior_isomorphic_alias",
            "evidence": "Both use the repeated-tap builder.",
        },
        {
            "family": "multi_four_way_route,four_way_package_gate",
            "classification": "behavior_isomorphic_alias",
            "evidence": "Both use the four-way package-gate builder.",
        },
        {
            "family": "late_route_reversal,controlled_repeated_taps",
            "classification": "behavior_isomorphic_alias",
            "evidence": "Both use the controlled repeated-taps builder.",
        },
        {
            "family": "branch_then_rejoin_with_wrong_order",
            "classification": "mislabeled",
            "evidence": "Declares a rejoin concept without a true alternate branch rejoin.",
        },
    )

    def __init__(self, generation_service: LevelGenerationService | None = None) -> None:
        self.generation_service = generation_service or LevelGenerationService()
        self.registry = RecipeFamilyRegistry()
        self.difficulty = DifficultyService()
        self.topology_solver = TopologySolverService()
        self.decision_profiles = DecisionProfileService()

    def capture(
        self,
        suites: tuple[V2ProductionPathBaselineSuite, ...] = DEFAULT_V2_PRODUCTION_PATH_BASELINE_SUITES,
    ) -> dict[str, Any]:
        suite_results = [self._run_suite(suite) for suite in suites]
        snapshots = self._recipe_family_snapshots()
        return {
            "schemaVersion": 1,
            "generatorArchitecture": "v2_legacy",
            "generatorArchitectureVersion": 2,
            "baselineCommit": self._git_commit(),
            "usesLevelGenerationService": True,
            "usesBatchOrchestrationService": True,
            "templateBypassUsed": False,
            "suites": suite_results,
            "difficultySuccessRates": {
                suite["difficulty"]: suite["acceptedCount"] / suite["requestedCount"]
                for suite in suite_results
            },
            "recipeFamilySnapshots": snapshots,
            "duplicateSignatureGroups": self._duplicate_groups(snapshots),
            "knownMismatches": list(self.KNOWN_MISMATCHES),
            "antiTrivialityFixtures": {
                "oneTap": "one_tap_recipe.json",
                "staticPolicy": "static_policy_recipe.json",
            },
        }

    def write(self, path: Path, payload: dict[str, Any] | None = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        captured = payload if payload is not None else self.capture()
        path.write_text(json.dumps(captured, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _run_suite(self, suite: V2ProductionPathBaselineSuite) -> dict[str, Any]:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix=f"tiny-routes-v2-baseline-{suite.difficulty}-") as root:
            output = Path(root)
            config = GenerationConfig(
                start_level_number=suite.start_level_number,
                count=suite.count,
                difficulty=suite.difficulty,
                generator_architecture="v2_legacy",
                template_name="mixed",
                seed=suite.seed,
                dry_run=True,
                compare_against_existing=False,
                levels_output_dir=output / "levels",
                solutions_output_dir=output / "solutions",
                report_path=output / "report.md",
                json_report_path=output / "report.json",
                recipe_pool_size=2,
                layouts_per_recipe=1,
                road_shapes_per_layout=1,
                candidate_pool_size=1,
                max_attempts_per_level=suite.max_attempts_per_level,
                command_arguments=["v2-production-path-baseline", suite.name],
            )
            result = self.generation_service.generate(config)

        rejection_counts = dict(sorted(result.rejection_reason_counts.items()))
        return {
            "name": suite.name,
            "difficulty": suite.difficulty,
            "seed": suite.seed,
            "requestedCount": suite.count,
            "acceptedCount": len(result.accepted),
            "fullBatchCompleted": result.passed and len(result.accepted) == suite.count,
            "durationSeconds": round(time.monotonic() - started, 3),
            "candidateGenerationCount": result.candidate_generation_count,
            "candidateValidationCount": result.candidate_validation_count,
            "generationErrorCount": result.generation_error_count,
            "rejectedCandidateCount": result.rejected_candidate_count,
            "rejectionCodeCounts": rejection_counts,
            "strategicRejectionCount": self._category_count(rejection_counts, "strategic"),
            "layoutTimingRejectionCount": self._category_count(rejection_counts, "layout_timing"),
            "accepted": [self._accepted_snapshot(candidate) for candidate in result.accepted],
            "messageCount": len(result.messages),
            "messageSamples": list(result.messages[:5]),
        }

    def _accepted_snapshot(self, candidate) -> dict[str, Any]:
        signature = candidate.candidate_signature
        profile = candidate.decision_profile
        return {
            "levelID": candidate.level_id,
            "recipeFamily": candidate.recipe_family,
            "recipeVariant": candidate.recipe_variant,
            "topologyClass": candidate.topology_class,
            "seed": candidate.seed,
            "nodeCount": candidate.node_count,
            "edgeCount": candidate.edge_count,
            "switchCount": candidate.switch_count,
            "requiredTapCount": candidate.required_tap_count,
            "oneTapOrLess": candidate.required_tap_count <= 1,
            "staticPolicySolvable": bool(
                profile and profile.front_loaded_legacy_solution_possible
            ),
            "structuralSignature": {
                "topologyHash": getattr(signature, "topology_hash", None),
                "layoutHash": getattr(signature, "layout_hash", None),
            },
            "behavioralSignature": profile.to_dict() if profile is not None else None,
        }

    def _recipe_family_snapshots(self) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for family_name in self.registry.valid_family_names():
            if family_name == "mixed":
                continue
            family = self.registry.get_family(family_name)
            variant, recipe, generation_errors = self._representative_recipe(family)
            difficulty_name = variant.difficulty_names[0]
            if recipe is None:
                failure_payload = {"generationErrors": generation_errors}
                snapshots.append(
                    {
                        "family": family_name,
                        "variant": variant.name,
                        "difficulty": difficulty_name,
                        "topologyClass": variant.topology_class,
                        "mechanicTags": list(variant.mechanic_tags),
                        "nodeCount": None,
                        "edgeCount": None,
                        "validationIssues": generation_errors,
                        "solverSucceeded": False,
                        "structureHash": self._hash(failure_payload),
                        "behaviorHash": self._hash(failure_payload),
                        "decisionProfile": None,
                        "solverFailures": generation_errors,
                    }
                )
                continue
            preset = self.difficulty.get_preset(difficulty_name)
            search = self.topology_solver.search(recipe, preset)
            profile = (
                self.decision_profiles.analyze(recipe, search.solutions)
                if search.succeeded
                else None
            )
            structure_payload = {
                "nodes": [(node.id, node.role) for node in recipe.nodes],
                "edges": [
                    (edge.from_node_id, edge.to_node_id, edge.availability)
                    for edge in recipe.edges
                ],
                "requiredPath": list(recipe.required_path),
            }
            behavior_payload = profile.to_dict() if profile is not None else {
                "solverFailures": list(search.failure_reasons)
            }
            snapshots.append(
                {
                    "family": family_name,
                    "variant": variant.name,
                    "difficulty": difficulty_name,
                    "topologyClass": recipe.topology_class,
                    "mechanicTags": list(recipe.mechanic_tags),
                    "nodeCount": len(recipe.nodes),
                    "edgeCount": len(recipe.edges),
                    "validationIssues": recipe.validate(),
                    "solverSucceeded": search.succeeded,
                    "structureHash": self._hash(structure_payload),
                    "behaviorHash": self._hash(behavior_payload),
                    "decisionProfile": profile.to_dict() if profile is not None else None,
                    "solverFailures": list(search.failure_reasons),
                }
            )
        return snapshots

    def _representative_recipe(self, family):
        errors: list[str] = []
        for variant in family.variants:
            difficulty_name = variant.difficulty_names[0]
            preset = self.difficulty.get_preset(difficulty_name)
            first_error: str | None = None
            for offset in range(8):
                try:
                    recipe = family.generate_recipe(
                        "level_999",
                        preset,
                        RandomSource(304003 + offset),
                        variant,
                    )
                except ValueError as exc:
                    if first_error is None:
                        first_error = str(exc)
                    continue
                return variant, recipe, errors
            errors.append(
                f"{variant.name}:failed seeds 304003-304010:{first_error or 'unknown generation error'}"
            )
        return family.variants[0], None, errors

    def _duplicate_groups(self, snapshots: list[dict[str, Any]]) -> dict[str, list[list[str]]]:
        return {
            "structural": self._groups_for(snapshots, "structureHash"),
            "behavioral": self._groups_for(snapshots, "behaviorHash"),
        }

    def _groups_for(self, snapshots: list[dict[str, Any]], key: str) -> list[list[str]]:
        grouped: defaultdict[str, list[str]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[str(snapshot[key])].append(str(snapshot["family"]))
        return sorted(
            (sorted(families) for families in grouped.values() if len(families) > 1),
            key=lambda group: (group[0], len(group)),
        )

    def _category_count(self, counts: dict[str, int], category: str) -> int:
        if category == "strategic":
            terms = ("abstract", "decision", "strategy", "boring", "route_interest", "quality")
        else:
            terms = ("layout", "road", "visual", "geometry", "runtime", "timing", "simulation")
        return sum(count for code, count in counts.items() if any(term in code for term in terms))

    def _hash(self, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _git_commit(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return "unknown"
        return completed.stdout.strip()
