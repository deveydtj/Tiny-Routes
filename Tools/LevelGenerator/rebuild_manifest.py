#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.paths import get_default_levels_directory, get_default_reports_directory, get_default_solutions_directory
from app.services.production_manifest_service import ProductionManifestService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the Tiny Routes production level manifest.")
    parser.add_argument("--output-levels", type=Path, default=get_default_levels_directory())
    parser.add_argument("--output-solutions", type=Path, default=get_default_solutions_directory())
    parser.add_argument("--output", type=Path, default=get_default_reports_directory() / "production_manifest.json")
    args = parser.parse_args(argv)

    path = ProductionManifestService().rebuild(args.output_levels, args.output_solutions, args.output)
    print(f"Wrote manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
