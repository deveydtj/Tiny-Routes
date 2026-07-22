"""Command-line entry point for transactional production V3 campaigns."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models.production_campaign import ProductionCampaignConfig
from .paths import (
    get_default_levels_directory,
    get_default_production_staging_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)
from .services.production_campaign_service import ProductionCampaignService
from .services.quality_profile_service import CURRENT_QUALITY_PROFILE_VERSION


def build_production_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate, verify, and atomically promote a complete Tiny Routes "
            "production V3 campaign."
        )
    )
    parser.add_argument(
        "--start", type=int, required=True, help="First production level number."
    )
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of levels in the complete batch.",
    )
    parser.add_argument(
        "--difficulty",
        required=True,
        choices=("auto", "easy", "medium", "hard", "expert"),
        help="Production difficulty or campaign curve.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional deterministic campaign seed.",
    )
    parser.add_argument(
        "--swift-tests",
        action="store_true",
        default=True,
        help="Run required Swift parity tests against staging (always enabled).",
    )
    parser.add_argument("--swift-timeout-seconds", type=int, default=180)
    parser.add_argument("--candidate-pool-size", type=int, default=4)
    parser.add_argument("--max-attempts-per-level", type=int, default=120)
    parser.add_argument("--wave-size", type=int, default=1)
    parser.add_argument(
        "--quality-profile",
        default=CURRENT_QUALITY_PROFILE_VERSION,
        help="Versioned calibrated quality profile (default: current).",
    )
    parser.add_argument(
        "--output-levels", type=Path, default=get_default_levels_directory()
    )
    parser.add_argument(
        "--output-solutions", type=Path, default=get_default_solutions_directory()
    )
    parser.add_argument(
        "--production-manifest",
        type=Path,
        default=get_default_reports_directory() / "production_manifest.json",
    )
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=get_default_production_staging_directory(),
    )
    return parser


def main_production(
    argv: list[str] | None = None,
    *,
    service: ProductionCampaignService | None = None,
) -> int:
    parser = build_production_parser()
    try:
        args = parser.parse_args(argv)
        config = ProductionCampaignConfig(
            start_level_number=args.start,
            count=args.count,
            difficulty=args.difficulty,
            seed=args.seed,
            run_swift_tests=args.swift_tests,
            swift_timeout_seconds=args.swift_timeout_seconds,
            candidates_per_slot=args.candidate_pool_size,
            max_attempts_per_slot=args.max_attempts_per_level,
            wave_size=args.wave_size,
            quality_profile_version=args.quality_profile,
            levels_output_dir=args.output_levels,
            solutions_output_dir=args.output_solutions,
            production_manifest_path=args.production_manifest,
            staging_root=args.staging_root,
        )
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 2
    except ValueError as error:
        parser.print_usage(sys.stderr)
        print(f"{parser.prog}: error: {error}", file=sys.stderr)
        return 2

    try:
        result = (service or ProductionCampaignService()).run(config)
    except (OSError, TypeError, ValueError) as error:
        print(f"{parser.prog}: error: {error}", file=sys.stderr)
        return 2
    report = str(result.report_path) if result.report_path else "none"
    detail = f" failure={result.failure_reason}" if result.failure_reason else ""
    print(
        f"status={result.status} run={result.run_id} seed={result.seed} "
        f"levels={result.selected_count}/{result.requested_count} "
        f"report={report}{detail}"
    )
    return 0 if result.passed else 1
