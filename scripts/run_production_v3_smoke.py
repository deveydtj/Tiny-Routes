#!/usr/bin/env python3
"""Run the deterministic five-level V3 production-path smoke suite."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
for source_root in (
    REPO_ROOT / "Tools" / "LevelGenerator",
    REPO_ROOT / "Tools" / "TinyRoutesCore",
):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from test_support.production_v3_smoke import run_five_level_smoke


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tiny-routes-v3-smoke-") as directory:
        evidence = run_five_level_smoke(Path(directory))
        print(json.dumps(evidence.to_dict(), indent=2, sort_keys=True))
        return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
