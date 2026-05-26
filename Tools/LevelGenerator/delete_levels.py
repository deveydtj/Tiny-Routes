#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.paths import get_default_levels_directory, get_default_solutions_directory
from app.services.level_resource_sync_service import LevelResourceSyncService, parse_level_selectors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delete Tiny Routes level JSON and matching solution sidecars.")
    parser.add_argument("levels", nargs="+", help="Level IDs/numbers/ranges, e.g. level_012 13 20-25.")
    parser.add_argument("--output-levels", type=Path, default=get_default_levels_directory())
    parser.add_argument("--output-solutions", type=Path, default=get_default_solutions_directory())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--xcodegen", action="store_true", dest="xcodegen", help="Run xcodegen after deletion. Default: enabled.")
    parser.add_argument("--no-xcodegen", action="store_false", dest="xcodegen", help="Skip xcodegen after deletion.")
    parser.set_defaults(xcodegen=True)
    args = parser.parse_args(argv)

    level_ids = parse_level_selectors(args.levels)
    result = LevelResourceSyncService().delete_levels(
        level_ids,
        args.output_levels,
        args.output_solutions,
        dry_run=args.dry_run,
        run_xcodegen=args.xcodegen,
    )
    for message in result.messages:
        print(message)
    for path in result.deleted_paths:
        print(f"Deleted {path}")
    for path in result.missing_paths:
        print(f"Missing {path}", file=sys.stderr)
    if result.xcodegen_message:
        print(result.xcodegen_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
