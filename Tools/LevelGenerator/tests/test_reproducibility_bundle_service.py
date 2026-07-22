from __future__ import annotations

import json
from types import SimpleNamespace

from app.services.production_staging_service import ProductionStagingService
from app.services.reproducibility_bundle_service import ReproducibilityBundleService


def test_bundle_retains_every_reached_artifact_and_one_command_replay(tmp_path) -> None:
    service = ReproducibilityBundleService()
    request = SimpleNamespace(
        candidate_id="level_031:candidate:0000",
        level_id="level_031",
        difficulty="hard",
        seed=7788,
        attempt_index=0,
    )
    stages = (
        SimpleNamespace(
            stage="blueprint",
            passed=True,
            blueprint={"id": "bp-1", "archetype": "return_to_hub"},
        ),
        SimpleNamespace(
            stage="composition",
            passed=True,
            report_fields={"composed_graph": {"nodes": ["start", "hub"]}},
        ),
        SimpleNamespace(
            stage="strategy",
            passed=False,
            code="static_policy_solution_exists",
            strategy_search={"exhaustive": True, "expanded_states": 42},
        ),
    )
    pipeline_result = SimpleNamespace(
        request=request,
        stage_results=stages,
        passed=False,
        terminal_stage="strategy",
        code="static_policy_solution_exists",
    )
    diagnostic = service.capture_pipeline_result(pipeline_result)
    pool_result = SimpleNamespace(attempt_diagnostics=(diagnostic,))
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "run-7788",
        seed=7788,
        config_snapshot={"generatorArchitecture": "production_v3"},
    )
    configuration = {
        "startLevelNumber": 31,
        "count": 1,
        "difficulty": "hard",
        "candidatesPerSlot": 4,
        "maxAttemptsPerSlot": 20,
        "waveSize": 2,
    }

    manifest_path = service.write_run_bundle(
        workspace,
        root_seed=7788,
        request_configuration=configuration,
        pool_result=pool_result,
        run_status="failed_no_changes",
        failure_reason="candidate_pool_incomplete",
    )

    bundle = manifest_path.parent
    candidate = next((bundle / "candidates").iterdir())
    assert json.loads((candidate / "blueprint.json").read_text())["evidence"]["id"] == "bp-1"
    assert json.loads((candidate / "composed_graph.json").read_text())["evidence"] == {
        "nodes": ["start", "hub"]
    }
    assert json.loads((candidate / "solver_summary.json").read_text())["reached"]
    assert not json.loads((candidate / "layout_state.json").read_text())["reached"]
    assert not json.loads((candidate / "runtime_trace.json").read_text())["reached"]
    rejection = json.loads((candidate / "rejection_details.json").read_text())
    assert rejection["code"] == "static_policy_solution_exists"
    script = (bundle / "reproduce.sh").read_text()
    assert "--seed 7788" in script
    assert '"$BUNDLE_DIR/reproduction/levels"' in script
    assert (bundle / "reproduce.sh").stat().st_mode & 0o111
    manifest = json.loads(manifest_path.read_text())
    assert manifest["attemptCount"] == 1
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])


def test_pipeline_exception_is_captured_without_nondeterministic_repr() -> None:
    request = SimpleNamespace(
        candidate_id="candidate-1",
        level_id="level_031",
        difficulty="expert",
        seed=17,
        attempt_index=2,
    )

    payload = ReproducibilityBundleService().capture_pipeline_exception(
        request,
        RuntimeError("composition exploded"),
    )

    assert payload["code"] == "candidate_pipeline_error"
    assert payload["exception"] == {
        "type": "RuntimeError",
        "message": "composition exploded",
    }
