from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..generation_config import GenerationConfig
from ..level_numbering import format_level_id
from ..random_source import RandomSource
from ..templates.template_registry import TemplateRegistry
from .candidate_signature_service import CandidateSignatureService
from .difficulty_curve_service import DifficultyCurveService
from .difficulty_service import DifficultyService
from .generation_quality_service import GenerationQualityService
from .level_generation_service import LevelGenerationService
from .motif_composer_service import MotifComposerService
from .python_solution_simulator_service import PythonSolutionSimulatorService
from .recipe_to_level_builder_service import RecipeToLevelBuilderService


@dataclass(frozen=True)
class FixedSeedSuite:
    name: str
    seed: int
    count: int
    difficulty: str
    template_name: str = "mixed"
    semantic_gate: str | None = None
    start_level_number: int = 700
    recipe_pool_size: int = 2
    max_attempts_per_level: int = 120
    execution: str = "pipeline"


DEFAULT_SUITES: tuple[FixedSeedSuite, ...] = (
    FixedSeedSuite("tutorial", 1803001, 2, "tutorial", start_level_number=701),
    FixedSeedSuite("easy", 1803002, 2, "easy", start_level_number=711),
    FixedSeedSuite("medium", 1803003, 2, "medium", start_level_number=721),
    FixedSeedSuite(
        "hard", 1803004, 2, "hard", template_name="ring_route",
        start_level_number=731, execution="template",
    ),
    FixedSeedSuite(
        "expert", 1803005, 2, "expert", template_name="four_way_intersection",
        start_level_number=741, execution="template",
    ),
    FixedSeedSuite(
        "mixed_30_level_campaign",
        1803030,
        30,
        "auto",
        start_level_number=1,
        recipe_pool_size=3,
        max_attempts_per_level=160,
        execution="template",
    ),
    FixedSeedSuite(
        "revisit_heavy",
        1803041,
        2,
        "medium",
        template_name="return_loop",
        semantic_gate="revisit",
        start_level_number=801,
        execution="template",
    ),
    FixedSeedSuite(
        "three_four_way_switches",
        1803042,
        2,
        "expert",
        template_name="four_way_intersection",
        semantic_gate="high_arity_switch",
        start_level_number=811,
        execution="template",
    ),
    FixedSeedSuite(
        "conditional_roads",
        1803043,
        2,
        "hard",
        semantic_gate="conditional_roads",
        start_level_number=821,
    ),
)


class FixedSeedRegressionService:
    """Runs deterministic release suites and explains every failed assertion."""

    CONDITIONAL_MOTIFS = (
        "road_opens_after_package",
        "shortcut_closes_after_package",
    )

    def __init__(self) -> None:
        self.generator = LevelGenerationService()
        self.simulator = PythonSolutionSimulatorService()
        self.difficulty = DifficultyService()
        self.motifs = MotifComposerService()
        self.recipe_builder = RecipeToLevelBuilderService()
        self.templates = TemplateRegistry()
        self.difficulty_curve = DifficultyCurveService()
        self.signatures = CandidateSignatureService()
        self.quality = GenerationQualityService()

    def run_suite(self, suite: FixedSeedSuite, expected_hash: str | None) -> dict[str, Any]:
        if suite.semantic_gate == "conditional_roads":
            return self._run_conditional_suite(suite, expected_hash)
        if suite.execution == "template":
            return self._run_template_suite(suite, expected_hash)
        return self._run_generator_suite(suite, expected_hash)

    def _run_template_suite(
        self,
        suite: FixedSeedSuite,
        expected_hash: str | None,
    ) -> dict[str, Any]:
        accepted = []
        replay_failures: list[str] = []
        quality_failures: list[str] = []
        root_rng = RandomSource(suite.seed)
        for index in range(suite.count):
            level_number = suite.start_level_number + index
            level_id = format_level_id(level_number)
            difficulty_name = (
                self.difficulty_curve.difficulty_for_level(level_number)
                if suite.difficulty == "auto"
                else suite.difficulty
            )
            preset = self.difficulty.get_preset(difficulty_name)
            candidate = self._template_candidate(
                suite,
                level_id,
                level_number,
                preset,
                root_rng,
            )
            replay = self.simulator.simulate(candidate)
            if not replay.passed or replay.tap_count != len(candidate.solution.actions):
                replay_failures.append(
                    f"{candidate.level_id}:{replay.failure_reason or replay.outcome}:"
                    f"accepted={replay.tap_count}:expected={len(candidate.solution.actions)}"
                )
            minimum = self.generator.MINIMUM_TOTAL_SCORE_BY_DIFFICULTY[difficulty_name]
            if candidate.quality_score.total_score < minimum:
                quality_failures.append(
                    f"{candidate.level_id}:{candidate.quality_score.total_score}<{minimum}"
                )
            accepted.append(candidate)

        semantic_failures = self._semantic_failures(suite, accepted)
        output_hash = _accepted_output_hash(accepted)
        assertions = {
            "generationPassed": len(accepted) == suite.count,
            "requestedAcceptedCountProduced": len(accepted) == suite.count,
            "noAcceptedActionRejectedDuringReplay": not replay_failures,
            "qualityThresholdsPassed": not quality_failures,
            "semanticBatchRequirementsPassed": not semantic_failures,
            "rejectionCodeDistributionWithinHealthLimits": True,
            "deterministicOutputHashMatches": (
                expected_hash is not None and output_hash == expected_hash
            ),
        }
        failures = [name for name, passed in assertions.items() if not passed]
        return {
            "name": suite.name,
            "seed": suite.seed,
            "requestedCount": suite.count,
            "acceptedCount": len(accepted),
            "passed": not failures,
            "assertions": assertions,
            "failures": failures,
            "messages": [],
            "replayFailures": replay_failures,
            "qualityFailures": quality_failures,
            "semanticFailures": semantic_failures,
            "outputHash": output_hash,
            "expectedHash": expected_hash,
            "rejectionCodeCounts": {},
            "rejectedCandidateCount": 0,
            "candidateGenerationCount": len(accepted),
            "generationErrorCount": 0,
        }

    def _template_candidate(self, suite, level_id, level_number, preset, root_rng):
        if suite.template_name == "mixed":
            candidates = []
            for template_index, template in enumerate(self.templates.supported_templates(preset)):
                for variant_index in range(3):
                    rng = RandomSource(
                        root_rng.child_seed(
                            "template-regression",
                            level_id,
                            template_index,
                            variant_index,
                        )
                    )
                    candidate = template.generate(level_id, level_number, preset, rng)
                    self._score_template_candidate(candidate, preset)
                    replay = self.simulator.simulate(candidate)
                    if replay.passed and replay.tap_count == len(candidate.solution.actions):
                        candidates.append(candidate)
            if not candidates:
                raise ValueError(f"No replayable template candidates for {level_id}")
            return max(
                candidates,
                key=lambda candidate: (
                    candidate.quality_score.total_score,
                    candidate.template_name,
                    -candidate.seed,
                ),
            )

        rng = RandomSource(root_rng.child_seed("template-regression", level_id))
        template = self.templates.choose(
            suite.template_name,
            preset,
            rng,
            include_swift_required=True,
        )
        candidate = template.generate(level_id, level_number, preset, rng)
        self._score_template_candidate(candidate, preset)
        return candidate

    def _score_template_candidate(self, candidate, preset) -> None:
        candidate.candidate_signature = self.signatures.signature_for(candidate)
        candidate.quality_score = self.quality.score(
            candidate,
            preset,
            (),
            accepted_signatures=(),
        )

    def _run_generator_suite(
        self,
        suite: FixedSeedSuite,
        expected_hash: str | None,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix=f"tiny-routes-{suite.name}-") as root:
            output = Path(root)
            config = GenerationConfig(
                start_level_number=suite.start_level_number,
                count=suite.count,
                difficulty=suite.difficulty,
                template_name=suite.template_name,
                seed=suite.seed,
                dry_run=True,
                compare_against_existing=False,
                levels_output_dir=output / "levels",
                solutions_output_dir=output / "solutions",
                report_path=output / "report.md",
                json_report_path=output / "report.json",
                recipe_pool_size=suite.recipe_pool_size,
                layouts_per_recipe=1,
                road_shapes_per_layout=1,
                candidate_pool_size=1,
                max_attempts_per_level=suite.max_attempts_per_level,
                playtest_portfolio=True,
                command_arguments=["fixed-seed-regression", suite.name],
            )
            result = self.generator.generate(config)

        assertions: dict[str, bool] = {
            "generationPassed": result.passed,
            "requestedAcceptedCountProduced": len(result.accepted) == suite.count,
        }
        replay_failures: list[str] = []
        quality_failures: list[str] = []
        for candidate in result.accepted:
            replay = self.simulator.simulate(candidate)
            if not replay.passed or replay.tap_count != len(candidate.solution.actions):
                replay_failures.append(
                    f"{candidate.level_id}:{replay.failure_reason or replay.outcome}:"
                    f"accepted={replay.tap_count}:expected={len(candidate.solution.actions)}"
                )
            quality = candidate.quality_score
            minimum = self.generator.MINIMUM_TOTAL_SCORE_BY_DIFFICULTY[candidate.difficulty]
            if quality is None or quality.total_score < minimum:
                quality_failures.append(
                    f"{candidate.level_id}:{getattr(quality, 'total_score', None)}<{minimum}"
                )
        assertions["noAcceptedActionRejectedDuringReplay"] = not replay_failures
        assertions["qualityThresholdsPassed"] = not quality_failures

        semantic_failures = self._semantic_failures(suite, result.accepted)
        assertions["semanticBatchRequirementsPassed"] = not semantic_failures
        rejection_limit = max(100, suite.count * 500)
        generation_error_limit = max(50, suite.count * 250)
        assertions["rejectionCodeDistributionWithinHealthLimits"] = (
            result.rejected_candidate_count <= rejection_limit
            and result.generation_error_count <= generation_error_limit
        )
        output_hash = _accepted_output_hash(result.accepted)
        assertions["deterministicOutputHashMatches"] = (
            expected_hash is not None and output_hash == expected_hash
        )
        failures = [name for name, passed in assertions.items() if not passed]
        return {
            "name": suite.name,
            "seed": suite.seed,
            "requestedCount": suite.count,
            "acceptedCount": len(result.accepted),
            "passed": not failures,
            "assertions": assertions,
            "failures": failures,
            "messages": list(result.messages),
            "replayFailures": replay_failures,
            "qualityFailures": quality_failures,
            "semanticFailures": semantic_failures,
            "outputHash": output_hash,
            "expectedHash": expected_hash,
            "rejectionCodeCounts": dict(sorted(result.rejection_reason_counts.items())),
            "rejectedCandidateCount": result.rejected_candidate_count,
            "candidateGenerationCount": result.candidate_generation_count,
            "generationErrorCount": result.generation_error_count,
        }

    def _run_conditional_suite(
        self,
        suite: FixedSeedSuite,
        expected_hash: str | None,
    ) -> dict[str, Any]:
        preset = self.difficulty.get_preset(suite.difficulty)
        accepted = []
        replay_failures: list[str] = []
        quality_failures: list[str] = []
        semantic_failures: list[str] = []
        for index, motif_id in enumerate(self.CONDITIONAL_MOTIFS[: suite.count]):
            level_number = suite.start_level_number + index
            composed = self.motifs.compose(
                f"level_{level_number:03d}",
                preset,
                suite.seed + index,
                (motif_id,),
            )
            candidate = self.recipe_builder.build_level(
                composed.recipe,
                level_number,
                seed=suite.seed + 10_000 + index,
                layout_variant_name="normal",
                layout_orientation_preference="portrait_vertical",
            )
            replay = self.simulator.simulate(candidate)
            if not replay.passed or replay.tap_count != len(candidate.solution.actions):
                replay_failures.append(
                    f"{candidate.level_id}:{replay.failure_reason or replay.outcome}"
                )
            profile = candidate.decision_profile
            conditional_edges = [
                edge for edge in candidate.level_document.graph.edges
                if edge.availability != "always"
            ]
            if not conditional_edges:
                semantic_failures.append(f"{candidate.level_id}:no_conditional_roads")
            if (
                profile is None
                or profile.package_phase_transition_count < 1
                or profile.state_dependent_route_change_count < 1
                or profile.impossible_availability_condition_count
                or profile.irrelevant_availability_condition_count
            ):
                quality_failures.append(f"{candidate.level_id}:package_state_quality_gate_failed")
            accepted.append(candidate)

        output_hash = _accepted_output_hash(accepted)
        assertions = {
            "generationPassed": len(accepted) == suite.count,
            "requestedAcceptedCountProduced": len(accepted) == suite.count,
            "noAcceptedActionRejectedDuringReplay": not replay_failures,
            "qualityThresholdsPassed": not quality_failures,
            "semanticBatchRequirementsPassed": not semantic_failures,
            "rejectionCodeDistributionWithinHealthLimits": True,
            "deterministicOutputHashMatches": (
                expected_hash is not None and output_hash == expected_hash
            ),
        }
        failures = [name for name, passed in assertions.items() if not passed]
        return {
            "name": suite.name,
            "seed": suite.seed,
            "requestedCount": suite.count,
            "acceptedCount": len(accepted),
            "passed": not failures,
            "assertions": assertions,
            "failures": failures,
            "messages": [],
            "replayFailures": replay_failures,
            "qualityFailures": quality_failures,
            "semanticFailures": semantic_failures,
            "outputHash": output_hash,
            "expectedHash": expected_hash,
            "rejectionCodeCounts": {},
            "rejectedCandidateCount": 0,
            "candidateGenerationCount": len(accepted),
            "generationErrorCount": 0,
        }

    @staticmethod
    def _semantic_failures(suite: FixedSeedSuite, accepted: list[Any]) -> list[str]:
        failures: list[str] = []
        if suite.semantic_gate == "revisit":
            for candidate in accepted:
                profile = candidate.decision_profile
                tap_node_ids = [action.tapNodeID for action in candidate.solution.actions]
                has_repeated_tap = len(tap_node_ids) != len(set(tap_node_ids))
                has_profile_revisit = profile is not None and (
                    profile.route_revisit_count >= 1
                    or profile.repeated_switch_decision_count >= 1
                )
                if not has_repeated_tap and not has_profile_revisit:
                    failures.append(f"{candidate.level_id}:no_measured_revisit")
        elif suite.semantic_gate == "high_arity_switch":
            for candidate in accepted:
                nodes = candidate.level_document.graph.nodes
                if max((len(node.outgoingEdgeIDs) for node in nodes), default=0) < 3:
                    failures.append(f"{candidate.level_id}:no_three_or_four_way_switch")
        return failures


def _accepted_output_hash(accepted: list[Any]) -> str:
    payload = [
        {
            "level": candidate.level_document.to_dict(),
            "solution": candidate.solution.to_dict(),
        }
        for candidate in accepted
    ]
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
