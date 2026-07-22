"""CLI for producing a blinded V3 calibration package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .services.blinded_playtest_export_service import BlindedPlaytestExportService


def build_playtest_export_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export an anonymized Tiny Routes playtest corpus and rubric."
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser


def main_playtest_export(argv: list[str] | None = None) -> int:
    parser = build_playtest_export_parser()
    try:
        args = parser.parse_args(argv)
        service = BlindedPlaytestExportService()
        samples, expected_archetypes = service.from_source_manifest(
            args.source_manifest
        )
        result = service.export(
            samples,
            args.output,
            seed=args.seed,
            expected_archetypes=expected_archetypes,
        )
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 2
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"playtest export failed: {error}", file=sys.stderr)
        return 1
    print(
        f"samples={result.sample_count} tester={result.tester_directory} "
        f"researcher={result.researcher_directory} fingerprint={result.fingerprint}"
    )
    return 0
