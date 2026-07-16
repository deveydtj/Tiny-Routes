#!/usr/bin/env python3
"""Analyze production levels for migration to live look-ahead routing.

This command is intentionally read-only. It replays the current solution,
searches for a legal live-routing schedule, measures decision quality against
the campaign difficulty curve, and recommends one documented migration class.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any

# Keep the documented one-file CLI invocation working from a clean checkout;
# the shared package is source-controlled beside the generator, not a required
# global installation.
_SHARED_CORE_ROOT = Path(__file__).resolve().parents[1] / "TinyRoutesCore"
if str(_SHARED_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_CORE_ROOT))

from tiny_routes_core.models import LevelRules, SwitchInteractionMode

from app.level_editor_imports import LevelDocument, Solution
from app.models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from app.models.generated_level import GeneratedLevel
from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.paths import find_repo_root, get_default_levels_directory, get_default_solutions_directory
from app.services.decision_profile_service import DecisionProfileService
from app.services.difficulty_curve_service import DifficultyCurveService
from app.services.difficulty_service import DifficultyService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.services.runtime_solution_search_service import RuntimeSolutionSearchService


class MigrationCategory(str, Enum):
    AUTOMATIC_CONVERSION = "automatic_conversion"
    TIMING_LAYOUT_ADJUSTMENT = "timing_layout_adjustment"
    MANUAL_REDESIGN = "manual_redesign"
    REGENERATION = "regeneration"


MIGRATION_CATEGORY_DEFINITIONS: dict[MigrationCategory, str] = {
    MigrationCategory.AUTOMATIC_CONVERSION: (
        "Existing topology works under live routing and meets campaign decision-quality rules."
    ),
    MigrationCategory.TIMING_LAYOUT_ADJUSTMENT: (
        "Topology works, but road lengths or live-routing window settings need adjustment."
    ),
    MigrationCategory.MANUAL_REDESIGN: (
        "Topology is too trivial or cannot provide a legal live-routing decision schedule."
    ),
    MigrationCategory.REGENERATION: (
        "The level can be replaced while retaining its stable level ID and campaign position."
    ),
}

MIGRATION_CATEGORY_TITLES: dict[MigrationCategory, str] = {
    MigrationCategory.AUTOMATIC_CONVERSION: "Automatic Conversion",
    MigrationCategory.TIMING_LAYOUT_ADJUSTMENT: "Timing/Layout Adjustment",
    MigrationCategory.MANUAL_REDESIGN: "Manual Redesign",
    MigrationCategory.REGENERATION: "Regeneration",
}

_TIMING_QUALITY_CODES = {"decision_window_below_preset_minimum"}
_TRIVIAL_QUALITY_CODES = {
    "insufficient_strategic_decision_evidence",
    "independent_decision_ratio_above_preset_maximum",
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _result_payload(result) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "outcome": result.outcome,
        "failureReason": result.failure_reason,
        "elapsedTimeSeconds": result.elapsed_time_seconds,
        "tapCount": result.tap_count,
        "reachedPackage": result.reached_package,
        "reachedDestination": result.reached_destination,
    }


def _level_number(level_id: str) -> int:
    try:
        return int(level_id.rsplit("_", 1)[1])
    except (IndexError, ValueError) as error:
        raise ValueError(f"Level ID does not end in a numeric campaign position: {level_id}") from error


def _solution_metadata(solution: Solution) -> dict[str, Any]:
    metadata = solution._extra.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _solution_route(level: LevelDocument, solution: Solution, current_result) -> tuple[str, ...]:
    raw_route = _solution_metadata(solution).get("solutionRoute")
    if isinstance(raw_route, list) and all(isinstance(item, str) for item in raw_route):
        route = tuple(raw_route)
    else:
        arrivals = tuple(
            step.node_id
            for step in current_result.steps
            if step.event == "arrive_node" and step.node_id is not None
        )
        route = (level.startNodeID, *arrivals)
    if not route or route[0] != level.startNodeID or route[-1] != level.destinationNodeID:
        raise ValueError(f"Solution route for {level.id} does not run from start to destination")
    edge_pairs = {(edge.fromNodeID, edge.toNodeID) for edge in level.graph.edges}
    missing = [pair for pair in zip(route, route[1:]) if pair not in edge_pairs]
    if missing:
        detail = ", ".join(f"{source}->{target}" for source, target in missing)
        raise ValueError(f"Solution route for {level.id} references missing edges: {detail}")
    return route


def _topology_solution(level: LevelDocument, solution: Solution, route: tuple[str, ...]):
    decisions = tuple(action.tapNodeID for action in solution.actions)
    return AbstractPuzzleSolutionMetadata(
        decision_node_ids=decisions,
        solution_switch_states=(),
        required_path=route,
        alternate_path_count=0,
        dead_end_count=0,
        failure_path_count=0,
        false_route_count=0,
        loop_count=sum(count - 1 for count in Counter(route).values() if count > 1),
        minimum_required_decisions=len(decisions),
        optional_tap_count=0,
        repeated_switch_usage=len(set(decisions)) < len(decisions),
        package_before_destination=(
            level.packageNodeID in route
            and route.index(level.packageNodeID) < route.index(level.destinationNodeID)
        ),
    )


def _recipe(level: LevelDocument, route: tuple[str, ...], decisions: tuple[str, ...], difficulty: str) -> GraphRecipe:
    return GraphRecipe(
        level_id=level.id,
        difficulty=difficulty,
        nodes=tuple(GraphRecipeNode(node.id) for node in level.graph.nodes),
        edges=tuple(GraphRecipeEdge(edge.fromNodeID, edge.toNodeID) for edge in level.graph.edges),
        required_path=route,
        tap_node_ids=decisions,
        package_node_id=level.packageNodeID,
        destination_node_id=level.destinationNodeID,
    )


def _live_level(level: LevelDocument, lookahead_seconds: float) -> LevelDocument:
    candidate = level.clone()
    candidate.rules = LevelRules(
        SwitchInteractionMode.LIVE_LOOKAHEAD,
        round(float(lookahead_seconds), 6),
        float(level.rules.switch_tap_cooldown_seconds),
    )
    candidate._rules_present = True
    return candidate


def _runtime_search_payload(result) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "failureReason": result.failure_reason,
        "actions": [
            {
                "timeSeconds": round(action.time_seconds, 6),
                "tapNodeID": action.tap_node_id,
                "expectedEdgeAfterTap": action.expected_edge_after_tap,
            }
            for action in result.actions
        ],
        "diagnostics": [diagnostic.to_dict() for diagnostic in result.diagnostics],
    }


def _decision_encounters(level: LevelDocument, route: tuple[str, ...]) -> tuple[tuple[str, int, int], ...]:
    edges = {edge.id: edge for edge in level.graph.edges}
    nodes = {node.id: node for node in level.graph.nodes}
    active_indices: dict[str, int] = {}
    visits: Counter[str] = Counter()
    encounters: list[tuple[str, int, int]] = []
    for node_id, next_node_id in zip(route, route[1:]):
        node = nodes[node_id]
        outgoing = [edges[edge_id] for edge_id in node.outgoingEdgeIDs if edge_id in edges]
        if len(outgoing) < 2:
            continue
        current_index = active_indices.get(node_id, 0)
        desired_index = next(
            (index for index, edge in enumerate(outgoing) if edge.toNodeID == next_node_id),
            None,
        )
        if desired_index is None:
            continue
        visits[node_id] += 1
        rotations = (desired_index - current_index) % len(outgoing)
        active_indices[node_id] = desired_index
        if rotations:
            encounters.append((node_id, visits[node_id], rotations))
    return tuple(encounters)


def _required_windows(level: LevelDocument, route: tuple[str, ...], runtime_result) -> list[dict[str, Any]]:
    available_by_visit = {
        (item.node_id, item.visit_index): (
            None
            if item.window_open_seconds is None or item.window_close_seconds is None
            else round(item.window_close_seconds - item.window_open_seconds, 6)
        )
        for item in runtime_result.diagnostics
    }
    safety_margin = RuntimeSolutionSearchService().safety_margin_seconds
    cooldown = max(float(level.rules.switch_tap_cooldown_seconds), 0.0)
    records = []
    for node_id, visit_index, rotations in _decision_encounters(level, route):
        required = (2 * safety_margin) + (max(0, rotations - 1) * (cooldown + 0.001))
        records.append({
            "nodeID": node_id,
            "visitIndex": visit_index,
            "rotationCount": rotations,
            "requiredWindowSeconds": round(required, 6),
            "availableWindowSeconds": available_by_visit.get((node_id, visit_index)),
        })
    return records


def _quality_code(issue: str) -> str:
    return issue.split(":", 1)[0]


def recommend_migration(
    *,
    current_solution_passed: bool,
    current_live_passed: bool,
    adjusted_live_passed: bool,
    live_failure_reason: str | None,
    decision_quality_issues: list[str] | tuple[str, ...],
    windows_legalizable: bool,
) -> tuple[MigrationCategory, tuple[str, ...]]:
    """Choose one migration category using the documented precedence rules."""

    if not current_solution_passed:
        return MigrationCategory.MANUAL_REDESIGN, ("current_solution_failed",)

    quality_codes = {_quality_code(issue) for issue in decision_quality_issues}
    trivial = {
        code for code in quality_codes
        if code in _TRIVIAL_QUALITY_CODES or code == "decision_count_outside_difficulty_range"
    }
    if trivial:
        return MigrationCategory.MANUAL_REDESIGN, tuple(sorted(trivial))

    if not current_live_passed:
        if adjusted_live_passed:
            return MigrationCategory.TIMING_LAYOUT_ADJUSTMENT, ("expanded_lookahead_succeeds",)
        if live_failure_reason == "insufficient_rotation_window" and windows_legalizable:
            return MigrationCategory.TIMING_LAYOUT_ADJUSTMENT, ("road_length_window_too_short",)
        return MigrationCategory.MANUAL_REDESIGN, (
            live_failure_reason or "no_live_routing_solution",
        )

    if quality_codes and quality_codes <= _TIMING_QUALITY_CODES:
        return MigrationCategory.TIMING_LAYOUT_ADJUSTMENT, tuple(sorted(quality_codes))
    if quality_codes:
        return MigrationCategory.REGENERATION, tuple(sorted(quality_codes))
    return MigrationCategory.AUTOMATIC_CONVERSION, ("live_solution_and_quality_pass",)


def analyze_level(
    level_payload: dict[str, Any],
    solution_payload: dict[str, Any],
    *,
    expanded_lookahead_seconds: float | None = None,
) -> dict[str, Any]:
    level = LevelDocument.from_dict(level_payload)
    solution = Solution.from_dict(solution_payload)
    if solution.levelID != level.id:
        raise ValueError(f"Solution targets {solution.levelID}, not {level.id}")

    number = _level_number(level.id)
    difficulty = DifficultyCurveService().difficulty_for_level(number)
    preset = DifficultyService().get_preset(difficulty)
    generated = GeneratedLevel(level, solution, "production", difficulty, 0)
    simulator = PythonSolutionSimulatorService()
    current_result = simulator.simulate(generated)
    route = _solution_route(level, solution, current_result)
    topology = _topology_solution(level, solution, route)

    configured_lookahead = float(level.rules.switch_lookahead_seconds)
    current_live_level = _live_level(level, configured_lookahead)
    search_service = RuntimeSolutionSearchService()
    current_live = search_service.search(current_live_level, topology)
    expanded_lookahead = max(
        configured_lookahead,
        float(expanded_lookahead_seconds or 0.0),
        float(preset.minimum_decision_window_seconds),
        float(level.timeLimitSeconds),
    )
    adjusted_live = search_service.search(_live_level(level, expanded_lookahead), topology)
    evidence_result = current_live if current_live.passed else adjusted_live

    recipe = _recipe(level, route, topology.decision_node_ids, difficulty)
    zero_time_candidate = copy.deepcopy(generated)
    for action in zero_time_candidate.solution.actions:
        action.timeSeconds = 0.0
    zero_time_passed = simulator.simulate(zero_time_candidate).passed
    decision_profile = DecisionProfileService().analyze(
        recipe,
        (topology,),
        evidence_result if evidence_result.passed else None,
        legacy_frontload_check=lambda: zero_time_passed,
    )
    decision_issues = DifficultyService().check_decision_profile_matches_difficulty(
        decision_profile,
        preset,
        configured_lookahead_seconds=configured_lookahead,
    )
    windows = _required_windows(level, route, evidence_result)
    windows_legalizable = all(
        item["requiredWindowSeconds"] <= float(level.timeLimitSeconds)
        for item in windows
    )
    category, reason_codes = recommend_migration(
        current_solution_passed=current_result.passed,
        current_live_passed=current_live.passed,
        adjusted_live_passed=adjusted_live.passed,
        live_failure_reason=current_live.failure_reason,
        decision_quality_issues=decision_issues,
        windows_legalizable=windows_legalizable,
    )

    raw_rules = level_payload.get("rules")
    return {
        "levelID": level.id,
        "campaignPosition": number,
        "campaignDifficulty": difficulty,
        "currentSchemaAndRules": {
            "schemaVersion": level_payload.get("schemaVersion", 1),
            "rulesPresent": "rules" in level_payload,
            "serializedRules": raw_rules,
            "effectiveRules": {
                "switchInteractionMode": level.rules.switch_interaction_mode.value,
                "switchLookaheadSeconds": configured_lookahead,
                "switchTapCooldownSeconds": float(level.rules.switch_tap_cooldown_seconds),
            },
        },
        "currentSolutionResult": _result_payload(current_result),
        "liveRoutingSolution": {
            "exists": current_live.passed or adjusted_live.passed,
            "existsWithCurrentSettings": current_live.passed,
            "existsWithExpandedLookahead": adjusted_live.passed,
            "configuredLookaheadSeconds": configured_lookahead,
            "expandedLookaheadTestedSeconds": round(expanded_lookahead, 6),
            "currentSettingsSearch": _runtime_search_payload(current_live),
            "expandedSettingsSearch": _runtime_search_payload(adjusted_live),
        },
        "requiredWindowSizes": windows,
        "repeatedDecisionBehavior": {
            "hasRepeatedDecisions": decision_profile.repeated_switch_decision_count > 0,
            "repeatedDecisionCount": decision_profile.repeated_switch_decision_count,
            "stateChangesOnRevisitCount": decision_profile.switch_state_change_on_revisit_count,
            "routeRevisitCount": decision_profile.route_revisit_count,
            "decisionNodeCounts": dict(sorted(Counter(topology.decision_node_ids).items())),
        },
        "decisionQuality": {
            "campaignDifficulty": difficulty,
            "passed": not decision_issues,
            "issues": decision_issues,
            "profile": decision_profile.to_dict(),
        },
        "recommendation": {
            "category": category.value,
            "title": MIGRATION_CATEGORY_TITLES[category],
            "reasonCodes": list(reason_codes),
            "definition": MIGRATION_CATEGORY_DEFINITIONS[category],
        },
    }


def analyze(
    levels_dir: Path,
    solutions_dir: Path,
    *,
    expanded_lookahead_seconds: float | None = None,
) -> dict[str, Any]:
    level_paths = sorted(
        path for path in levels_dir.glob("level_*.json")
        if not path.name.endswith(".solution.json")
    )
    levels = []
    for level_path in level_paths:
        solution_path = solutions_dir / f"{level_path.stem}.solution.json"
        if not solution_path.is_file():
            raise FileNotFoundError(
                f"Missing solution sidecar for {level_path.stem}: {solution_path}"
            )
        levels.append(analyze_level(
            _load_object(level_path),
            _load_object(solution_path),
            expanded_lookahead_seconds=expanded_lookahead_seconds,
        ))
    category_counts = Counter(item["recommendation"]["category"] for item in levels)
    return {
        "schemaVersion": 1,
        "migrationCategories": {
            category.value: MIGRATION_CATEGORY_DEFINITIONS[category]
            for category in MigrationCategory
        },
        "analysis": {
            "levelCount": len(levels),
            "currentSolutionPassCount": sum(item["currentSolutionResult"]["passed"] for item in levels),
            "liveSolutionCount": sum(item["liveRoutingSolution"]["exists"] for item in levels),
            "decisionQualityPassCount": sum(item["decisionQuality"]["passed"] for item in levels),
            "recommendationCounts": {
                category.value: category_counts.get(category.value, 0)
                for category in MigrationCategory
            },
        },
        "levels": levels,
    }


def render_markdown(report: dict[str, Any]) -> str:
    analysis = report["analysis"]
    lines = [
        "# Live-Routing Migration Analysis",
        "",
        "Generated deterministically by `Tools/LevelGenerator/migrate_levels_to_live_routing.py`.",
        "The analyzer is read-only; recommendations do not modify production content.",
        "",
        f"- Levels analyzed: {analysis['levelCount']}",
        f"- Current solutions passing: {analysis['currentSolutionPassCount']}",
        f"- Topologies with a live-routing solution: {analysis['liveSolutionCount']}",
        f"- Levels meeting campaign decision quality: {analysis['decisionQualityPassCount']}",
        "",
        "## Migration categories",
        "",
    ]
    for category in MigrationCategory:
        count = analysis["recommendationCounts"][category.value]
        lines.append(
            f"- **{MIGRATION_CATEGORY_TITLES[category]} ({count}):** "
            f"{report['migrationCategories'][category.value]}"
        )
    lines.extend([
        "",
        "## Per-level recommendations",
        "",
        "| Level | Difficulty | Current | Live current | Live adjusted | Decision quality | Required window | Recommendation | Reasons |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
    ])
    for item in report["levels"]:
        windows = item["requiredWindowSizes"]
        required = max((window["requiredWindowSeconds"] for window in windows), default=0.0)
        recommendation = item["recommendation"]
        lines.append(
            f"| {item['levelID']} | {item['campaignDifficulty']} | "
            f"{'pass' if item['currentSolutionResult']['passed'] else 'fail'} | "
            f"{'yes' if item['liveRoutingSolution']['existsWithCurrentSettings'] else 'no'} | "
            f"{'yes' if item['liveRoutingSolution']['existsWithExpandedLookahead'] else 'no'} | "
            f"{'pass' if item['decisionQuality']['passed'] else 'fail'} | {required:.3f} | "
            f"{recommendation['title']} | {', '.join(recommendation['reasonCodes'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    root = find_repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels-dir", type=Path, default=get_default_levels_directory())
    parser.add_argument("--solutions-dir", type=Path, default=get_default_solutions_directory())
    parser.add_argument(
        "--expanded-lookahead-seconds",
        type=float,
        help="Minimum look-ahead used for the adjustment probe; defaults to each level time limit.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "docs/quality/live_routing_migration_report.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "docs/quality/live_routing_migration_report.md",
    )
    args = parser.parse_args()
    if args.expanded_lookahead_seconds is not None and args.expanded_lookahead_seconds < 0:
        parser.error("--expanded-lookahead-seconds must be nonnegative")
    try:
        report = analyze(
            args.levels_dir,
            args.solutions_dir,
            expanded_lookahead_seconds=args.expanded_lookahead_seconds,
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.exit(1, f"Migration analysis failed: {error}\n")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(f"Analyzed {report['analysis']['levelCount']} levels")
    for category, count in report["analysis"]["recommendationCounts"].items():
        print(f"{category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
