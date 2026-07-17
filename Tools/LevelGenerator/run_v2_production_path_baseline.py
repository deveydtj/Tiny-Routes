#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR_ROOT = ROOT / "Tools" / "LevelGenerator"
CORE_ROOT = ROOT / "Tools" / "TinyRoutesCore"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))
if str(GENERATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_ROOT))

from app.services.v2_production_path_baseline_service import (  # noqa: E402
    V2ProductionPathBaselineService,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the deterministic V2 production-path limitation baseline."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=GENERATOR_ROOT / "tests" / "fixtures" / "v2_generator_baseline" / "baseline.json",
    )
    args = parser.parse_args(argv)
    output = V2ProductionPathBaselineService().write(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
