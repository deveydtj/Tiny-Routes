#!/usr/bin/env python3
"""Replay the production level corpus and write a deterministic baseline report."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from app.level_editor_imports import LevelDocument, Solution
from app.models.generated_level import GeneratedLevel
from app.paths import find_repo_root, get_default_levels_directory, get_default_solutions_directory
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService


def _load_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _generated(level_path: Path, solution_path: Path) -> GeneratedLevel:
    level = LevelDocument.from_dict(_load_object(level_path))
    solution = Solution.from_dict(_load_object(solution_path))
    if solution.levelID != level.id:
        raise ValueError(f"Solution {solution_path} targets {solution.levelID}, not {level.id}")
    return GeneratedLevel(level, solution, "production", "baseline", 0)


def _variant(source: GeneratedLevel, mode: str) -> GeneratedLevel:
    candidate = copy.deepcopy(source)
    actions = sorted(candidate.solution.actions, key=lambda action: (float(action.timeSeconds), action.tapNodeID))
    for index, action in enumerate(actions):
        if mode == "time_zero":
            action.timeSeconds = 0.0
        elif mode == "compressed":
            action.timeSeconds = round(0.15 * index / max(len(actions) - 1, 1), 6)
    candidate.solution.actions = actions
    return candidate


def _result_payload(result) -> dict:
    return {
        "passed": result.passed,
        "outcome": result.outcome,
        "failureReason": result.failure_reason,
        "elapsedTimeSeconds": result.elapsed_time_seconds,
        "tapCount": result.tap_count,
        "reachedPackage": result.reached_package,
        "reachedDestination": result.reached_destination,
    }


def _route_length(level: GeneratedLevel, result, simulator: PythonSolutionSimulatorService) -> float:
    nodes = {node.id: node for node in level.level_document.graph.nodes}
    edges = {edge.id: edge for edge in level.level_document.graph.edges}
    total = 0.0
    for step in result.steps:
        if step.event != "arrive_node" or step.edge_id not in edges:
            continue
        edge = edges[step.edge_id]
        total += simulator.route_timing.edge_length(nodes[edge.fromNodeID], nodes[edge.toNodeID], edge.roadShape)
    return round(total, 6)


def analyze(levels_dir: Path, solutions_dir: Path) -> dict:
    simulator = PythonSolutionSimulatorService()
    level_paths = sorted(path for path in levels_dir.glob("level_*.json") if not path.name.endswith(".solution.json"))
    records = []
    for level_path in level_paths:
        level_id = level_path.stem
        solution_path = solutions_dir / f"{level_id}.solution.json"
        if not solution_path.is_file():
            raise FileNotFoundError(f"Missing solution sidecar for {level_id}: {solution_path}")
        generated = _generated(level_path, solution_path)
        original = simulator.simulate(_variant(generated, "original"))
        zero = simulator.simulate(_variant(generated, "time_zero"))
        compressed = simulator.simulate(_variant(generated, "compressed"))
        graph = generated.level_document.graph
        outgoing = Counter(len(node.outgoingEdgeIDs) for node in graph.nodes)
        tap_nodes = [action.tapNodeID for action in generated.solution.actions]
        repeated = {node_id: count for node_id, count in sorted(Counter(tap_nodes).items()) if count > 1}
        records.append({
            "levelID": level_id,
            "switchCount": sum(1 for node in graph.nodes if len(node.outgoingEdgeIDs) >= 2),
            "outgoingDegreeDistribution": {str(key): outgoing[key] for key in sorted(outgoing)},
            "requiredTapCount": len(tap_nodes),
            "repeatedSwitchTaps": repeated,
            "routeLength": _route_length(generated, original, simulator),
            "original": _result_payload(original),
            "allTapsAtZero": _result_payload(zero),
            "tapsCompressedToFirst0.15Seconds": _result_payload(compressed),
            "destinationBeforePackageUnderTestedState": any(
                result.failure_reason == "reached_destination_without_package"
                for result in (original, zero, compressed)
            ),
        })
    return {
        "schemaVersion": 1,
        "analysis": {
            "levelCount": len(records),
            "frontLoadableAtZeroCount": sum(record["allTapsAtZero"]["passed"] for record in records),
            "frontLoadableWithin0.15SecondsCount": sum(record["tapsCompressedToFirst0.15Seconds"]["passed"] for record in records),
            "destinationBeforePackageCount": sum(record["destinationBeforePackageUnderTestedState"] for record in records),
        },
        "levels": records,
    }


def render_markdown(report: dict) -> str:
    summary = report["analysis"]
    lines = [
        "# Current Production Level Corpus Baseline",
        "",
        "Generated deterministically by `Tools/LevelGenerator/analyze_level_corpus.py`.",
        "",
        f"- Levels analyzed: {summary['levelCount']}",
        f"- Solutions passing with every tap at `0.0`: {summary['frontLoadableAtZeroCount']}",
        f"- Solutions passing with taps compressed into `0.15` seconds: {summary['frontLoadableWithin0.15SecondsCount']}",
        f"- Levels reaching destination before package in a tested state: {summary['destinationBeforePackageCount']}",
        "",
        "| Level | Switches | Taps | Repeated taps | Route length | Original | At 0.0 | In 0.15s | Destination first |",
        "| --- | ---: | ---: | --- | ---: | --- | --- | --- | --- |",
    ]
    for record in report["levels"]:
        repeated = ", ".join(f"{key} x{value}" for key, value in record["repeatedSwitchTaps"].items()) or "—"
        result = lambda key: "pass" if record[key]["passed"] else f"fail ({record[key]['failureReason']})"
        lines.append(
            f"| {record['levelID']} | {record['switchCount']} | {record['requiredTapCount']} | {repeated} | "
            f"{record['routeLength']:.3f} | {result('original')} | {result('allTapsAtZero')} | "
            f"{result('tapsCompressedToFirst0.15Seconds')} | {'yes' if record['destinationBeforePackageUnderTestedState'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    root = find_repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels-dir", type=Path, default=get_default_levels_directory())
    parser.add_argument("--solutions-dir", type=Path, default=get_default_solutions_directory())
    parser.add_argument("--json-output", type=Path, default=root / "docs/quality/current_level_corpus_baseline.json")
    parser.add_argument("--markdown-output", type=Path, default=root / "docs/quality/current_level_corpus_baseline.md")
    args = parser.parse_args()
    try:
        report = analyze(args.levels_dir, args.solutions_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Corpus analysis failed: {exc}\n")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(f"Analyzed {report['analysis']['levelCount']} levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
