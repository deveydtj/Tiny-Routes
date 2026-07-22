from __future__ import annotations

from types import SimpleNamespace

from app.models.production_campaign import ProductionCampaignConfig
from app.services.production_campaign_service import ProductionCampaignService


class _PoolResult:
    complete = True
    constrained_level_ids = ()

    def __init__(self, candidate) -> None:
        self.candidate = candidate
        self.attempt_diagnostics = (
            {
                "candidateID": f"{candidate.level_id}:candidate:0000",
                "levelID": candidate.level_id,
                "difficulty": "hard",
                "seed": candidate.seed,
                "attemptIndex": 0,
                "passed": True,
                "terminalStage": "quality",
                "code": "quality_accepted",
                "stages": [],
            },
        )

    def pipeline_result_for(self, candidate):
        assert candidate is self.candidate
        return SimpleNamespace(candidate=candidate, passed=True)


class _PoolService:
    def __init__(self, candidate, *, failure: Exception | None = None) -> None:
        self.candidate = candidate
        self.failure = failure
        self.requests = []

    def build(self, request):
        self.requests.append(request)
        if self.failure:
            raise self.failure
        return _PoolResult(self.candidate)

    def expand(self, *args, **kwargs):  # pragma: no cover - protocol surface
        raise AssertionError("portfolio expansion was not expected")


class _PortfolioService:
    def select_with_backtracking(self, pool, request, **kwargs):
        return SimpleNamespace(candidates=[pool.candidate], candidate_pools=pool)


class _StagedOutputService:
    def __init__(self, *, fail_reports: bool = False) -> None:
        self.staged = False
        self.fail_reports = fail_reports

    def write_selected_candidates(self, workspace, candidates, **kwargs):
        self.staged = True

    def write_report(self, workspace, filename, content):
        if self.fail_reports:
            raise OSError("report disk unavailable")
        path = workspace.reports_dir / filename
        path.write_text(content, encoding="utf-8")
        return path


class _ValidationService:
    def validate(self, workspace, pipeline_results, **kwargs):
        assert len(tuple(pipeline_results)) == 1
        return SimpleNamespace(passed=True)


class _PromotionService:
    def __init__(self) -> None:
        self.called = False

    def promote(self, workspace):
        self.called = True
        return SimpleNamespace(
            completed=True,
            status="completed",
            promoted_paths=(workspace.root / "promoted",),
            failure_reason=None,
        )


class _ExistingRepository:
    def load_existing_levels(self, *args):
        return SimpleNamespace(signatures=[])


def _config(tmp_path) -> ProductionCampaignConfig:
    return ProductionCampaignConfig(
        start_level_number=31,
        count=1,
        difficulty="hard",
        seed=12345,
        candidates_per_slot=2,
        max_attempts_per_slot=2,
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        production_manifest_path=tmp_path / "production_manifest.json",
        staging_root=tmp_path / "staging",
    )


def test_complete_campaign_uses_one_transactional_path(tmp_path) -> None:
    candidate = SimpleNamespace(level_id="level_031", seed=7)
    pool = _PoolService(candidate)
    staged = _StagedOutputService()
    promotion = _PromotionService()
    progress = []
    service = ProductionCampaignService(
        candidate_pool_service=pool,
        portfolio_service=_PortfolioService(),
        staged_output_service=staged,
        validation_service=_ValidationService(),
        promotion_service=promotion,
        existing_level_repository=_ExistingRepository(),
        run_id_factory=lambda seed: f"run-{seed}",
    )

    result = service.run(_config(tmp_path), progress=lambda stage, message: progress.append(stage))

    assert result.passed
    assert result.status == "completed"
    assert result.selected_count == result.requested_count == 1
    assert result.report_path.is_file()
    assert result.reproducibility_bundle_path.is_file()
    assert result.health_report_path.is_file()
    assert result.quality_profile_version == "1.0.0"
    assert len(result.quality_profile_fingerprint) == 64
    assert staged.staged
    assert promotion.called
    assert progress == [
        "planning",
        "candidate_pool",
        "portfolio",
        "staging",
        "validation",
        "promotion",
        "completed",
    ]
    assert pool.requests[0].slots[0].level_id == "level_031"
    assert pool.requests[0].slots[0].difficulty == "hard"
    report = result.report_path.read_text(encoding="utf-8")
    assert '"qualityProfileVersion": "1.0.0"' in report
    bundle_request = (
        result.reproducibility_bundle_path.parent / "request_configuration.json"
    )
    assert '"qualityProfileVersion": "1.0.0"' in bundle_request.read_text(
        encoding="utf-8"
    )


def test_candidate_failure_leaves_production_untouched(tmp_path) -> None:
    candidate = SimpleNamespace(level_id="level_031", seed=7)
    staged = _StagedOutputService()
    promotion = _PromotionService()
    service = ProductionCampaignService(
        candidate_pool_service=_PoolService(
            candidate, failure=RuntimeError("candidate pipeline failed")
        ),
        portfolio_service=_PortfolioService(),
        staged_output_service=staged,
        validation_service=_ValidationService(),
        promotion_service=promotion,
        existing_level_repository=_ExistingRepository(),
        run_id_factory=lambda seed: f"run-{seed}",
    )

    result = service.run(_config(tmp_path))

    assert result.status == "failed_no_changes"
    assert "candidate pipeline failed" in result.failure_reason
    assert not staged.staged
    assert not promotion.called
    assert result.report_path.is_file()


def test_report_failure_cannot_relabel_completed_promotion(tmp_path) -> None:
    candidate = SimpleNamespace(level_id="level_031", seed=7)
    service = ProductionCampaignService(
        candidate_pool_service=_PoolService(candidate),
        portfolio_service=_PortfolioService(),
        staged_output_service=_StagedOutputService(fail_reports=True),
        validation_service=_ValidationService(),
        promotion_service=_PromotionService(),
        existing_level_repository=_ExistingRepository(),
        run_id_factory=lambda seed: f"run-{seed}",
    )

    result = service.run(_config(tmp_path))

    assert result.status == "completed"
    assert result.report_path is None
