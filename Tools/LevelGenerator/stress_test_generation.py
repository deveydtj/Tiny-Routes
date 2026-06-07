#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.generation_config import GenerationConfig
from app.services.level_generation_service import LevelGenerationService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run many Tiny Routes generator candidates into a scratch folder."
    )
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--difficulty", default="auto")
    parser.add_argument("--template", default="mixed")
    parser.add_argument("--seed", type=int, default=9001)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/tiny-routes-generator-stress"))
    parser.add_argument("--recipe-pool-size", type=int, default=4)
    parser.add_argument("--layouts-per-recipe", type=int, default=2)
    parser.add_argument("--road-shapes-per-layout", type=int, default=2)
    parser.add_argument("--candidate-pool-size", type=int, default=8)
    parser.add_argument("--max-attempts-per-level", type=int, default=120)
    parser.add_argument(
        "--production-profile",
        action="store_true",
        help=(
            "Use production portfolio filters. By default stress runs use the playtest "
            "portfolio profile so large dry-run batches still keep strict validation "
            "without starving on full-batch similarity."
        ),
    )
    args = parser.parse_args(argv)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config = GenerationConfig(
        start_level_number=args.start,
        count=args.count,
        difficulty=args.difficulty,
        template_name=args.template,
        seed=args.seed,
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
        command_arguments=list(argv) if argv is not None else sys.argv[1:],
    )
    result = LevelGenerationService().generate(config)
    report_payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    summary = {
        "passed": result.passed,
        "scratchOutputDir": str(output_dir),
        "reportPath": str(config.report_path),
        "jsonReportPath": str(config.json_report_path),
        "dryRunSummary": report_payload["dryRunSummary"],
        "acceptedDifficultyDistribution": report_payload["acceptedDifficultyDistribution"],
        "acceptedRecipeDistribution": report_payload["acceptedRecipeDistribution"],
        "acceptedTopologyDistribution": report_payload["acceptedTopologyDistribution"],
        "acceptedMapSizeDistribution": report_payload["acceptedMapSizeDistribution"],
        "rejectionReasonCounts": report_payload["rejectionReasonCounts"],
    }
    summary_path = output_dir / "stress_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
