#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.paths import get_default_levels_directory, get_default_reports_directory, get_default_solutions_directory
from app.services.production_migration_service import ProductionMigrationError, ProductionMigrationService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply reviewed production level and sidecar replacements without changing campaign identity."
    )
    parser.add_argument("--replacement-levels", type=Path, required=True)
    parser.add_argument("--replacement-solutions", type=Path, required=True)
    parser.add_argument("--output-levels", type=Path, default=get_default_levels_directory())
    parser.add_argument("--output-solutions", type=Path, default=get_default_solutions_directory())
    parser.add_argument(
        "--manifest",
        type=Path,
        default=get_default_reports_directory() / "production_manifest.json",
    )
    parser.add_argument(
        "--review-name-change",
        action="append",
        default=[],
        metavar="LEVEL_ID",
        help="Explicitly approve a changed display name; repeat for multiple levels.",
    )
    args = parser.parse_args(argv)
    try:
        result = ProductionMigrationService().apply(
            args.replacement_levels,
            args.replacement_solutions,
            args.output_levels,
            args.output_solutions,
            args.manifest,
            reviewed_name_changes=args.review_name_change,
        )
    except (ProductionMigrationError, OSError) as error:
        parser.exit(1, f"Production migration failed: {error}\n")
    print("Migrated: " + ", ".join(result.migrated_level_ids))
    print(f"Rebuilt manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
