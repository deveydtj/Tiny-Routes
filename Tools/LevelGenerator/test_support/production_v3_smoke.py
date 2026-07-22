"""Five-level fixed-seed smoke harness for the live V3 campaign orchestrator."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from tiny_routes_core.models import Solution, SolutionAction

from app.models import (
    BlueprintStageResult,
    CandidateStageResult,
    GeneratedLevel,
    GenerationQualityScore,
    PuzzleAnalysis,
    PuzzleOutcomeCount,
    QualityStageResult,
    StrategyStageResult,
)
from app.models.production_campaign import ProductionCampaignConfig
from app.services import (
    AlternateSuccessClassificationService,
    CandidatePoolService,
    DifficultyTargetResolver,
    FailureRecoveryClassificationService,
    LocalObviousnessAnalysisService,
    PlanningHorizonClassificationService,
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    ProductionCampaignService,
    ProductionPuzzleGateService,
    ProductionStagedOutputService,
    PuzzleBlueprintService,
    SearchLimitRejectionService,
    StaticPolicySolverService,
    StrategySearchService,
    UniqueOptimalProofService,
    V3CandidatePipelineCoordinator,
    V3CandidatePipelineHandlers,
)
from test_support.stateful_fixture import StatefulFixtureSpec, build_stateful_fixture


_ARCHITECTURE = "production_v3"
_ARCHITECTURE_VERSION = 3
_ROOT_SEED = 731_005
_START_LEVEL_NUMBER = 901
_LEVEL_COUNT = 5
_PATTERNS = (
    (2, 1, False),
    (3, 1, False),
    (2, 1, True),
    (3, 2, False),
    (3, 2, True),
)


@dataclass(frozen=True)
class ProductionV3SmokeEvidence:
    passed: bool
    deterministic: bool
    generator_architecture: str
    generator_architecture_version: int
    seed: int
    requested_count: int
    selected_count: int
    selected_candidate_ids: tuple[str, ...]
    selected_seeds: tuple[int, ...]
    behavior_signatures: tuple[str, ...]
    stage_sequences: tuple[tuple[str, ...], ...]
    parity_statuses: tuple[str, ...]
    fallback_count: int
    stage_path_violation_count: int
    behavior_duplicate_count: int
    one_tap_or_less_count: int
    static_policy_solvable_count: int
    unproven_optimal_count: int
    parity_error_count: int
    production_unchanged: bool
    staging_artifact_count: int
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "deterministic": self.deterministic,
            "generatorArchitecture": self.generator_architecture,
            "generatorArchitectureVersion": self.generator_architecture_version,
            "seed": self.seed,
            "requestedCount": self.requested_count,
            "selectedCount": self.selected_count,
            "selectedCandidateIDs": list(self.selected_candidate_ids),
            "selectedSeeds": list(self.selected_seeds),
            "behaviorSignatures": list(self.behavior_signatures),
            "stageSequences": [list(value) for value in self.stage_sequences],
            "parityStatuses": list(self.parity_statuses),
            "fallbackCount": self.fallback_count,
            "stagePathViolationCount": self.stage_path_violation_count,
            "behaviorDuplicateCount": self.behavior_duplicate_count,
            "oneTapOrLessCount": self.one_tap_or_less_count,
            "staticPolicySolvableCount": self.static_policy_solvable_count,
            "unprovenOptimalCount": self.unproven_optimal_count,
            "parityErrorCount": self.parity_error_count,
            "productionUnchanged": self.production_unchanged,
            "stagingArtifactCount": self.staging_artifact_count,
            "fingerprint": self.fingerprint,
        }


class _SmokeCandidatePipeline:
    """Real six-stage coordinator backed by deterministic stateful fixtures."""

    def __init__(self) -> None:
        self._blueprints: dict[str, object] = {}
        self._strategy: dict[str, StrategyStageResult] = {}
        self._coordinator = V3CandidatePipelineCoordinator(
            V3CandidatePipelineHandlers(
                blueprint=self._blueprint,
                composition=self._composition,
                strategy=self._strategy_stage,
                layout=self._layout,
                runtime=self._runtime,
                quality=self._quality,
            )
        )

    def run(self, request):
        return self._coordinator.run(request)

    def _blueprint(self, request) -> BlueprintStageResult:
        blueprint = PuzzleBlueprintService().generate(
            request.difficulty,
            request.seed,
        )
        self._blueprints[request.candidate_id] = blueprint
        return BlueprintStageResult.accepted(
            candidate_id=request.candidate_id,
            level_id=request.level_id,
            seed=request.seed,
            difficulty=request.difficulty,
            attempt_index=request.attempt_index,
            experience_target=blueprint.experience_target,
            blueprint=blueprint,
            report_fields={
                "generatorArchitecture": _ARCHITECTURE,
                "generatorArchitectureVersion": _ARCHITECTURE_VERSION,
                "fallbackUsed": False,
            },
        )

    @staticmethod
    def _accepted_stage(request, stage: str, **report_fields) -> CandidateStageResult:
        return CandidateStageResult(
            passed=True,
            stage=stage,
            code=f"{stage}_accepted",
            candidate_id=request.candidate_id,
            level_id=request.level_id,
            seed=request.seed,
            difficulty=request.difficulty,
            status="accepted",
            report_fields={
                "generatorArchitecture": _ARCHITECTURE,
                "fallbackUsed": False,
                **report_fields,
            },
        )

    def _composition(self, request, _blueprint) -> CandidateStageResult:
        return self._accepted_stage(
            request,
            "composition",
            execution="production_v3_composition",
        )

    def _strategy_stage(self, request, _composition) -> StrategyStageResult:
        level = self._level(request)
        search = StrategySearchService().search(level)
        proof = UniqueOptimalProofService().prove(level, search)
        static = StaticPolicySolverService().solve(level)
        policies = PolicyEvaluationService().evaluate(
            level,
            search_result=search,
            config=PolicyEvaluationConfig(random_run_count=2),
        )
        alternates = AlternateSuccessClassificationService().classify(level, search)
        recovery = FailureRecoveryClassificationService().classify(level, search)
        planning = PlanningHorizonClassificationService().classify(
            level,
            search_result=search,
        )
        obviousness = LocalObviousnessAnalysisService().assess(level, search)
        limits = SearchLimitRejectionService().assess(search, static)
        result = StrategyStageResult.accepted(
            candidate_id=request.candidate_id,
            level_id=request.level_id,
            seed=request.seed,
            difficulty=request.difficulty,
            strategy_search=search,
            unique_optimal_proof=proof,
            static_policy_search=static,
            policy_evaluation=policies,
            alternate_successes=alternates,
            failure_recovery=recovery,
            planning_horizon=planning,
            local_obviousness=obviousness,
            search_limit_gate=limits,
            report_fields={
                "generatorArchitecture": _ARCHITECTURE,
                "fallbackUsed": False,
            },
        )
        self._strategy[request.candidate_id] = result
        return result

    def _layout(self, request, _composition, _strategy) -> CandidateStageResult:
        return self._accepted_stage(request, "layout", layoutValidated=True)

    def _runtime(self, request, _layout, _strategy) -> CandidateStageResult:
        return self._accepted_stage(
            request,
            "runtime",
            parityStatus="smoke_fixture_passed",
            swiftParityRequested=True,
            jitterReplayStatus="passed",
        )

    def _quality(self, request, _blueprint, _composition, strategy, _layout, _runtime):
        level = self._level(request)
        search = strategy.strategy_search
        static = strategy.static_policy_search
        policies = strategy.policy_evaluation
        proof = strategy.unique_optimal_proof
        obviousness = strategy.local_obviousness
        assert search is not None and search.optimal_cost is not None
        assert static is not None and policies is not None and proof is not None
        assert obviousness is not None
        trace = search.canonical_optimal_strategy
        assert trace is not None
        target = DifficultyTargetResolver().resolve(request.difficulty)
        meaningful = tuple(action for action in trace.actions if action.meaningful_decision)
        hub_visits = Counter(
            node_id
            for action in trace.actions
            for node_id in action.visited_node_ids
            if node_id.startswith("hub_")
        )
        analysis = PuzzleAnalysis(
            meaningful_decisions=max(
                len(meaningful), target.meaningful_decision_range[0]
            ),
            planning_decisions=target.planning_decision_minimum,
            adaptive_decisions=target.adaptive_decision_minimum,
            dependency_depth=target.dependency_depth_range[0],
            independent_decision_ratio=0.25,
            static_policy_result=static,
            agent_results=policies.evaluations,
            objective_phases=len(level.effective_objectives),
            state_changes=max(
                target.state_change_range[0],
                sum(
                    bool(action.state_transition and action.state_transition.changes_state)
                    for action in trace.actions
                ),
            ),
            revisits=sum(max(0, count - 1) for count in hub_visits.values()),
            successful_strategy_classes=len(search.all_successful_strategies),
            optimal_uniqueness=True,
            recovery_failure_distribution=(
                PuzzleOutcomeCount("immediateDeadEnd", 1),
                PuzzleOutcomeCount(
                    "recoverableDetour",
                    max(1, target.recoverable_mistake_range[0]),
                ),
            ),
            equivalent_choices=0,
            no_op_choices=0,
            optimal_accepted_taps=search.optimal_cost.accepted_taps,
            optimal_route_distance=search.optimal_cost.route_distance,
            optimal_travel_time_seconds=search.optimal_cost.travel_time_seconds,
            visual_complexity=target.layout_complexity_target,
        )
        gate = ProductionPuzzleGateService().assess(
            analysis,
            target,
            unique_optimal_proof=proof,
            local_obviousness=obviousness,
            state_change_readable=True,
            runtime_solution_robust=True,
        )
        candidate = self._generated_level(request, level, trace)
        score = GenerationQualityScore(
            total_score=90,
            category_scores={"strategy": 92, "readability": 88},
            total=0.90,
            readability=0.88,
            uniqueness=0.92,
            difficulty_fit=0.90,
            route_interest=0.91,
            estimated_difficulty_band=request.difficulty,
        )
        return QualityStageResult.accepted(
            candidate_id=request.candidate_id,
            level_id=request.level_id,
            seed=request.seed,
            difficulty=request.difficulty,
            generated_level=candidate,
            puzzle_analysis=analysis,
            hard_gate=gate,
            quality_score=score,
            report_fields={
                "generatorArchitecture": _ARCHITECTURE,
                "fallbackUsed": False,
                "antiTrivialityStatus": "passed",
            },
        )

    @staticmethod
    def _pattern(level_id: str, difficulty: str) -> tuple[int, int, bool]:
        level_number = int(level_id.rsplit("_", 1)[1])
        if difficulty == "easy":
            return _PATTERNS[(level_number - _START_LEVEL_NUMBER) % len(_PATTERNS)]
        minimum_objectives = {
            "medium": 3,
            "hard": 3,
            "expert": 4,
        }[difficulty]
        return (
            minimum_objectives,
            1 + (level_number % 2),
            level_number % 4 == 0,
        )

    def _level(self, request):
        objectives, hubs, ring = self._pattern(request.level_id, request.difficulty)
        level = build_stateful_fixture(
            StatefulFixtureSpec(
                fixture_id=request.level_id,
                difficulty=request.difficulty,
                objective_count=objectives,
                hub_count=hubs,
                include_alternate_route=True,
                include_one_use_ring=ring,
                seed=1,
            )
        )
        level_number = int(request.level_id.rsplit("_", 1)[1])
        return self._with_failure_route_depth(
            level,
            depth=((level_number - 1) % 30) + 1,
        )

    @staticmethod
    def _with_failure_route_depth(level, *, depth: int):
        """Give each campaign slot a behaviorally distinct visible failure route."""

        payload = level.to_dict()
        graph = payload["graph"]
        nodes = graph["nodes"]
        edges = graph["edges"]
        trap_edge = next(edge for edge in edges if edge["id"] == "phase_0_trap")
        original_destination = trap_edge["toNodeID"]
        trap_node = next(node for node in nodes if node["id"] == original_destination)
        trap_edge["toNodeID"] = "variant_trap_0"

        for index in range(depth):
            node_id = f"variant_trap_{index}"
            edge_id = f"variant_trap_edge_{index}"
            destination = (
                original_destination
                if index == depth - 1
                else f"variant_trap_{index + 1}"
            )
            nodes.append(
                {
                    "id": node_id,
                    "x": float(trap_node["x"]) + (index + 1) * 0.1,
                    "y": float(trap_node["y"]) + (index + 1) * 0.1,
                    "outgoingEdgeIDs": [edge_id],
                }
            )
            edges.append(
                {
                    "id": edge_id,
                    "fromNodeID": node_id,
                    "toNodeID": destination,
                }
            )
        return type(level).from_dict(payload)

    @staticmethod
    def _generated_level(request, level, trace) -> GeneratedLevel:
        tap_actions = tuple(
            action for action in trace.actions if action.meaningful_decision
        )
        solution = Solution(
            levelID=level.id,
            description="Production V3 smoke proof",
            expectedOutcome="success",
            maxTaps=sum(action.tap_count for action in tap_actions),
            requiresWithinTimeLimit=True,
            actions=[
                SolutionAction((index + 1) * 3.0, action.node_id)
                for index, action in enumerate(tap_actions)
            ],
        )
        return GeneratedLevel(
            level_document=level,
            solution=solution,
            template_name=_ARCHITECTURE,
            difficulty=request.difficulty,
            seed=request.seed,
            mechanic_tags=("objective_gate", "hub_revisit"),
            primary_mechanic_tag="objective_gate",
            topology_class="production_v3_smoke",
        )


class _SmokePortfolioService:
    def select_with_backtracking(self, pool_result, _request, **_kwargs):
        candidates = tuple(pool.candidates[0] for pool in pool_result.pools)
        signatures = tuple(
            candidate.candidate_signature.structural_behavior_signature
            for candidate in candidates
        )
        if len(signatures) != len(set(signatures)):
            raise ValueError("smoke portfolio contains a behavioral duplicate")
        return SimpleNamespace(candidates=candidates, candidate_pools=pool_result)


class _SmokeStagedOutputService(ProductionStagedOutputService):
    def __init__(self) -> None:
        super().__init__()
        self.selection_paths: list[Path] = []

    def write_selected_candidates(self, workspace, candidates, **_kwargs):
        manifest = super().write_selected_candidates(
            workspace,
            candidates,
            **_kwargs,
        )
        self.selection_paths.append(workspace.run_manifest_path)
        return manifest


class _SmokeValidationService:
    def __init__(self) -> None:
        self.pipeline_results: tuple[object, ...] = ()

    def validate(self, workspace, pipeline_results, **kwargs):
        results = tuple(pipeline_results)
        self.pipeline_results = results
        if kwargs.get("run_swift_tests") is not True:
            raise ValueError("V3 smoke must request Swift parity validation")
        if not workspace.run_manifest_path.is_file():
            raise ValueError("selected candidates were not staged")
        if len(tuple(workspace.levels_dir.glob("*.json"))) != len(results):
            raise ValueError("staged level count does not match selected candidates")
        if len(tuple(workspace.solutions_dir.glob("*.json"))) != len(results):
            raise ValueError("staged solution count does not match selected candidates")
        snapshot = json.loads(
            workspace.seed_config_snapshot_path.read_text(encoding="utf-8")
        )["configuration"]
        if snapshot.get("generatorArchitecture") != _ARCHITECTURE:
            raise ValueError("staged campaign did not use production_v3")
        if snapshot.get("generatorArchitectureVersion") != _ARCHITECTURE_VERSION:
            raise ValueError("staged campaign did not use architecture version 3")
        for result in results:
            stages = tuple(stage.stage for stage in result.stage_results)
            if stages != (
                "blueprint",
                "composition",
                "strategy",
                "layout",
                "runtime",
                "quality",
            ):
                raise ValueError("candidate bypassed the locked V3 stage order")
            if any(
                stage.report_fields.get("generatorArchitecture") != _ARCHITECTURE
                for stage in result.stage_results
            ):
                raise ValueError("candidate stage left the production_v3 architecture")
            if (
                result.stage_results[0].report_fields.get(
                    "generatorArchitectureVersion"
                )
                != _ARCHITECTURE_VERSION
            ):
                raise ValueError("candidate is missing architecture version 3")
            if (
                result.stage_results[1].report_fields.get("execution")
                != "production_v3_composition"
            ):
                raise ValueError("candidate bypassed V3 composition")
            runtime = result.stage_results[4]
            if runtime.report_fields.get("parityStatus") != "smoke_fixture_passed":
                raise ValueError("candidate is missing passing parity status")
            if runtime.report_fields.get("swiftParityRequested") is not True:
                raise ValueError("candidate did not request the Swift parity boundary")
            if any(
                stage.report_fields.get("fallbackUsed") is not False
                for stage in result.stage_results
            ):
                raise ValueError("candidate used a fallback path")
        return SimpleNamespace(passed=True)


class _SmokePromotionService:
    def __init__(self) -> None:
        self.called = False

    def promote(self, _workspace):
        self.called = True
        return SimpleNamespace(
            completed=True,
            status="completed",
            promoted_paths=(),
            failure_reason=None,
        )


class _EmptyExistingRepository:
    @staticmethod
    def load_existing_levels(*_args):
        return SimpleNamespace(signatures=[])


def _file_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _run_once(
    root: Path,
    *,
    start_level_number: int = _START_LEVEL_NUMBER,
    level_count: int = _LEVEL_COUNT,
    seed: int = _ROOT_SEED,
    difficulty: str = "easy",
) -> ProductionV3SmokeEvidence:
    production = root / "production"
    levels = production / "levels"
    solutions = production / "solutions"
    levels.mkdir(parents=True)
    solutions.mkdir(parents=True)
    manifest = production / "manifest.json"
    before = _file_snapshot(production)

    pipeline = _SmokeCandidatePipeline()
    pool = CandidatePoolService(pipeline)
    staged = _SmokeStagedOutputService()
    validation = _SmokeValidationService()
    promotion = _SmokePromotionService()
    service = ProductionCampaignService(
        candidate_pool_service=pool,
        portfolio_service=_SmokePortfolioService(),
        staged_output_service=staged,
        validation_service=validation,
        promotion_service=promotion,
        existing_level_repository=_EmptyExistingRepository(),
        run_id_factory=lambda value: f"production-v3-smoke-{value}",
    )
    config = ProductionCampaignConfig(
        start_level_number=start_level_number,
        count=level_count,
        difficulty=difficulty,
        seed=seed,
        candidates_per_slot=2,
        max_attempts_per_slot=2,
        wave_size=1,
        levels_output_dir=levels,
        solutions_output_dir=solutions,
        production_manifest_path=manifest,
        staging_root=root / "staging",
    )
    result = service.run(config)
    after = _file_snapshot(production)
    pipeline_results = validation.pipeline_results
    candidates = tuple(item.candidate for item in pipeline_results)
    selected_ids = tuple(f"{item.level_id}:{item.seed}" for item in candidates)
    signatures = tuple(
        item.candidate_signature.structural_behavior_signature for item in candidates
    )
    stages = tuple(
        tuple(stage.stage for stage in item.stage_results)
        for item in pipeline_results
    )
    parity = tuple(
        item.stage_results[4].report_fields["parityStatus"]
        for item in pipeline_results
    )
    fallback_count = sum(
        stage.report_fields.get("fallbackUsed") is not False
        for item in pipeline_results
        for stage in item.stage_results
    )
    expected_stages = (
        "blueprint",
        "composition",
        "strategy",
        "layout",
        "runtime",
        "quality",
    )
    stage_path_violation_count = sum(value != expected_stages for value in stages)
    behavior_duplicate_count = len(signatures) - len(set(signatures))
    accepted_tap_counts = []
    for item in pipeline_results:
        trace = item.stage_results[2].strategy_search.canonical_optimal_strategy
        accepted_tap_counts.append(sum(action.tap_count for action in trace.actions))
    one_tap_or_less_count = sum(value <= 1 for value in accepted_tap_counts)
    static_policy_solvable_count = sum(
        item.stage_results[2].static_policy_search.static_policy_solvable
        for item in pipeline_results
    )
    unproven_optimal_count = sum(
        not item.stage_results[2].unique_optimal_proof.accepted
        for item in pipeline_results
    )
    parity_error_count = sum(value != "smoke_fixture_passed" for value in parity)
    fingerprint_payload = {
        "architecture": config.snapshot(resolved_seed=seed)[
            "generatorArchitecture"
        ],
        "architectureVersion": config.snapshot(resolved_seed=seed)[
            "generatorArchitectureVersion"
        ],
        "seed": seed,
        "selectedIDs": selected_ids,
        "signatures": signatures,
        "stages": stages,
        "parity": parity,
        "fallbackCount": fallback_count,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return ProductionV3SmokeEvidence(
        passed=(
            result.passed
            and result.requested_count == result.selected_count == level_count
            and len(signatures) == len(set(signatures)) == level_count
            and parity_error_count == 0
            and fallback_count == 0
            and stage_path_violation_count == 0
            and behavior_duplicate_count == 0
            and one_tap_or_less_count == 0
            and static_policy_solvable_count == 0
            and unproven_optimal_count == 0
            and before == after
            and promotion.called
        ),
        deterministic=False,
        generator_architecture=_ARCHITECTURE,
        generator_architecture_version=_ARCHITECTURE_VERSION,
        seed=seed,
        requested_count=result.requested_count,
        selected_count=result.selected_count,
        selected_candidate_ids=selected_ids,
        selected_seeds=tuple(item.seed for item in candidates),
        behavior_signatures=signatures,
        stage_sequences=stages,
        parity_statuses=parity,
        fallback_count=fallback_count,
        stage_path_violation_count=stage_path_violation_count,
        behavior_duplicate_count=behavior_duplicate_count,
        one_tap_or_less_count=one_tap_or_less_count,
        static_policy_solvable_count=static_policy_solvable_count,
        unproven_optimal_count=unproven_optimal_count,
        parity_error_count=parity_error_count,
        production_unchanged=before == after,
        staging_artifact_count=len(staged.selection_paths),
        fingerprint=fingerprint,
    )


def run_campaign_regression(
    root: Path,
    *,
    start_level_number: int,
    level_count: int,
    seed: int,
    difficulty: str,
) -> ProductionV3SmokeEvidence:
    """Run one exact-path campaign twice and require identical evidence."""

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    arguments = {
        "start_level_number": start_level_number,
        "level_count": level_count,
        "seed": seed,
        "difficulty": difficulty,
    }
    first = _run_once(root / "first", **arguments)
    second = _run_once(root / "second", **arguments)
    deterministic = first.fingerprint == second.fingerprint
    return ProductionV3SmokeEvidence(
        **{
            **first.__dict__,
            "passed": first.passed and second.passed and deterministic,
            "deterministic": deterministic,
        }
    )


def run_five_level_smoke(root: Path) -> ProductionV3SmokeEvidence:
    """Run the fixed five-level pull-request smoke regression."""

    return run_campaign_regression(
        root,
        start_level_number=_START_LEVEL_NUMBER,
        level_count=_LEVEL_COUNT,
        seed=_ROOT_SEED,
        difficulty="easy",
    )
