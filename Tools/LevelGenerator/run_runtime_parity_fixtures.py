#!/usr/bin/env python3
"""Export deterministic normalized Python traces for Swift parity comparison."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.paths import find_repo_root
from app.services.runtime_parity_validator import normalize_core_result
from tiny_routes_core.models import LevelDocument, SolutionAction
from tiny_routes_core.simulation import RuntimeSimulator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Write normalized trace JSON here; defaults to stdout.")
    args = parser.parse_args()
    root = find_repo_root() / "SharedFixtures" / "RuntimeParity"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    traces = {}
    for item in manifest["fixtures"]:
        directory = root / item["id"]
        level = LevelDocument.from_dict(json.loads((directory / "level.json").read_text(encoding="utf-8")))
        events = json.loads((directory / "events.json").read_text(encoding="utf-8"))
        expected = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
        actions = [SolutionAction.from_dict(action) for action in events["actions"]]
        result = RuntimeSimulator(speed=0.6, maximum_step_count=expected["safetyStepLimit"]).simulate(level, actions)
        traces[item["id"]] = asdict(normalize_core_result(result))
    payload = json.dumps({"traceVersion": 1, "fixtures": traces}, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
