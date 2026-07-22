#!/usr/bin/env python3
"""Run legacy dry-run stress or exact-path V3 campaign regressions."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


GENERATOR_ROOT = Path(__file__).resolve().parent
CORE_ROOT = GENERATOR_ROOT.parent / "TinyRoutesCore"
for source_root in (GENERATOR_ROOT, CORE_ROOT):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from app.generation_config import GenerationConfig
from app.services.level_generation_service import LevelGenerationService
from test_support.production_v3_stress import (
    resolve_campaign_seeds,
    run_production_v3_stress,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("v2_legacy", "production_v3"),
        default="production_v3",
    )
    parser.add_argument("--start", type=int)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--difficulty", default="auto")
    parser.add_argument("--template", default="mixed")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--recipe-pool-size", type=int, default=4)
    parser.add_argument("--layouts-per-recipe", type=int, default=2)
    parser.add_argument("--road-shapes-per-layout", type=int, default=2)
    parser.add_argument("--candidate-pool-size", type=int, default=8)
    parser.add_argument("--max-attempts-per-level", type=int, default=120)
    parser.add_argument(
        "--production-profile",
        action="store_true",
        help=(
            "Use production portfolio filters for legacy dry runs. By default "
            "legacy stress runs use the playtest portfolio profile."
        ),
    )
    parser.add_argument("--campaign-count", type=int, default=1)
    parser.add_argument("--levels-per-campaign", type=int, default=30)
    parser.add_argument("--seed-range")
    parser.add_argument("--require-complete-batches", action="store_true")
    parser.add_argument("--fail-on-one-tap", action="store_true")
    parser.add_argument("--fail-on-static-policy", action="store_true")
    parser.add_argument("--fail-on-parity-error", action="store_true")
    parser.add_argument("--retain-campaign-artifacts", action="store_true")
    return parser


def _run_legacy(args: argparse.Namespace, argv: list[str]) -> int:
    output_dir = args.output_dir or Path("/tmp/tiny-routes-generator-stress")
    output_dir.mkdir(parents=True, exist_ok=True)
    config = GenerationConfig(
        start_level_number=args.start if args.start is not None else 1,
        count=args.count,
        difficulty=args.difficulty,
        generator_architecture="v2_legacy",
        template_name=args.template,
        seed=args.seed if args.seed is not None else 9001,
        dry_run=True,
        compare_against_existing=False,
        levels_output_dir=output_dir / "levels",
        solutions_output_dir=output_dir / "solutions",
        report_path=output_dir / "generation_report.md",
        json_report_path=output_dir / "generation_report.json",
        recipe_pool_size=args.recipe_pool_size,
        layouts_per_recipe=args.layouts_per_recipe,
        road_shapes_per_layout=args.road_shapes_per_layout,
        candidate_pool_size=args.candidate_pool_size,
        max_attempts_per_level=args.max_attempts_per_level,
        playtest_portfolio=not args.production_profile,
        command_arguments=argv,
    )
    result = LevelGenerationService().generate(config)
    report_payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    summary = {
        "passed": result.passed,
        "mode": "v2_legacy",
        "scratchOutputDir": str(output_dir),
        "reportPath": str(config.report_path),
        "jsonReportPath": str(config.json_report_path),
        "dryRunSummary": report_payload["dryRunSummary"],
        "acceptedDifficultyDistribution": report_payload[
            "acceptedDifficultyDistribution"
        ],
        "acceptedRecipeDistribution": report_payload["acceptedRecipeDistribution"],
        "acceptedTopologyDistribution": report_payload[
            "acceptedTopologyDistribution"
        ],
        "acceptedMapSizeDistribution": report_payload[
            "acceptedMapSizeDistribution"
        ],
        "rejectionReasonCounts": report_payload["rejectionReasonCounts"],
    }
    summary_path = output_dir / "stress_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"Passed: {result.passed}")
    print(f"Accepted: {summary['dryRunSummary']['acceptedCount']}")
    print(f"Rejected candidates: {summary['dryRunSummary']['rejectedCandidateCount']}")
    print(f"Pass rate: {summary['dryRunSummary']['passRate']}")
    print(f"Difficulty distribution: {summary['acceptedDifficultyDistribution']}")
    print(f"Recipe distribution: {summary['acceptedRecipeDistribution']}")
    print(f"Topology distribution: {summary['acceptedTopologyDistribution']}")
    print(f"Map-size distribution: {summary['acceptedMapSizeDistribution']}")
    print(f"Rejection reasons: {summary['rejectionReasonCounts']}")
    print(f"Summary: {summary_path}")
    print(f"Report: {config.report_path}")
    print(f"JSON report: {config.json_report_path}")
    return 0 if result.passed else 1


def _run_production_v3(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else Path(tempfile.mkdtemp(prefix="tiny-routes-production-v3-stress-"))
    )
    if output_dir.exists() and not output_dir.is_dir():
        parser.error("production_v3 --output-dir must be a directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        parser.error(
            "production_v3 --output-dir must be empty so staged evidence "
            "cannot collide with an earlier run"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        seeds = resolve_campaign_seeds(
            args.campaign_count,
            seed=args.seed,
            seed_range=args.seed_range,
        )
    except ValueError as error:
        parser.error(str(error))
    evidence = run_production_v3_stress(
        output_dir / "campaign_runs",
        campaign_count=args.campaign_count,
        levels_per_campaign=args.levels_per_campaign,
        start_level_number=args.start if args.start is not None else 901,
        difficulty=args.difficulty,
        seeds=seeds,
        retain_campaign_artifacts=args.retain_campaign_artifacts,
    )
    summary = evidence.to_dict()
    summary["requirements"] = {
        "completeBatches": args.require_complete_batches,
        "failOnOneTap": args.fail_on_one_tap,
        "failOnStaticPolicy": args.fail_on_static_policy,
        "failOnParityError": args.fail_on_parity_error,
        "fallbackDetection": True,
        "deterministicRerun": True,
        "stagingOnly": True,
        "retainCampaignArtifacts": args.retain_campaign_artifacts,
    }
    summary_path = output_dir / "stress_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Passed: {evidence.passed}")
    print(
        "Complete campaigns: "
        f"{evidence.complete_batch_count}/{evidence.campaign_count}"
    )
    print(f"Executed campaigns: {evidence.executed_campaign_count}")
    print(
        "Selected levels: "
        f"{evidence.selected_level_count}/{evidence.requested_level_count}"
    )
    print(f"Deterministic campaigns: {evidence.deterministic_batch_count}")
    print(f"Fallback paths: {evidence.fallback_count}")
    print(f"One-tap-or-less levels: {evidence.one_tap_or_less_count}")
    print(f"Static-policy-solvable levels: {evidence.static_policy_solvable_count}")
    print(f"Unproven optimal strategies: {evidence.unproven_optimal_count}")
    print(f"Parity errors: {evidence.parity_error_count}")
    print(f"Production mutations: {evidence.production_mutation_count}")
    print(f"Summary: {summary_path}")
    return 0 if evidence.passed else 1


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = _parser()
    args = parser.parse_args(arguments)
    if args.mode == "production_v3":
        return _run_production_v3(args, parser)
    if args.seed_range is not None:
        parser.error("--seed-range requires --mode production_v3")
    return _run_legacy(args, arguments)


if __name__ == "__main__":
    raise SystemExit(main())
