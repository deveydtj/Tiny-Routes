#!/usr/bin/env python3
"""Run the Phase 18 fixed-seed generator release suites."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED_CORE_ROOT = Path(__file__).resolve().parents[1] / "TinyRoutesCore"
if str(_SHARED_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_CORE_ROOT))

from app.paths import find_repo_root
from app.services.fixed_seed_regression_service import (
    DEFAULT_SUITES,
    FixedSeedRegressionService,
)


def main(argv: list[str] | None = None) -> int:
    root = find_repo_root()
    default_baselines = root / "Tools/LevelGenerator/fixtures/fixed_seed_regression_hashes.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        action="append",
        choices=[suite.name for suite in DEFAULT_SUITES],
        help="Run only the named suite. Repeat to select multiple suites.",
    )
    parser.add_argument("--baselines", type=Path, default=default_baselines)
    parser.add_argument("--update-baselines", action="store_true")
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args(argv)

    selected_names = set(args.suite or ())
    suites = [suite for suite in DEFAULT_SUITES if not selected_names or suite.name in selected_names]
    baselines = _read_baselines(args.baselines)
    service = FixedSeedRegressionService()
    results = []
    for suite in suites:
        print(f"==> fixed-seed suite {suite.name} (seed={suite.seed}, count={suite.count})", flush=True)
        item = service.run_suite(suite, baselines.get(suite.name))
        results.append(item)
        print(
            f"    {'PASS' if item['passed'] else 'FAIL'} accepted={item['acceptedCount']}/"
            f"{item['requestedCount']} rejected={item['rejectedCandidateCount']} "
            f"hash={item['outputHash']}",
            flush=True,
        )
        for failure in item["failures"]:
            print(f"    failed: {failure}", file=sys.stderr)

    if args.update_baselines:
        updated = dict(baselines)
        updated.update({item["name"]: item["outputHash"] for item in results})
        args.baselines.parent.mkdir(parents=True, exist_ok=True)
        args.baselines.write_text(
            json.dumps(updated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for item in results:
            item["expectedHash"] = item["outputHash"]
            item["assertions"]["deterministicOutputHashMatches"] = True
            item["failures"] = [
                failure for failure in item["failures"]
                if failure != "deterministicOutputHashMatches"
            ]
            item["passed"] = not item["failures"]

    report = {
        "schemaVersion": 1,
        "passed": all(item["passed"] for item in results),
        "suiteCount": len(results),
        "suites": results,
    }
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0 if report["passed"] else 1


def _read_baselines(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in payload.items()
    ):
        raise ValueError(f"Expected a string-to-string JSON object in {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
