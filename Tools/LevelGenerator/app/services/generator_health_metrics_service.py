"""Aggregate production V3 yield, quality, robustness, and diversity metrics."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..models.generator_health import (
    GeneratorHealthReport,
    GeneratorHealthSlice,
    PortfolioDiversityMetrics,
)


class GeneratorHealthMetricsService:
    """Build stable health snapshots from retained candidate-pool evidence."""

    _DECISION_FIELDS = (
        "meaningful_decisions",
        "planning_decisions",
        "adaptive_decisions",
        "dependency_depth",
        "objective_phases",
        "state_changes",
        "revisits",
        "successful_strategy_classes",
    )

    def build(
        self,
        pool_result: object,
        *,
        root_seed: int,
        selected_candidates: Iterable[object] = (),
        run_completed: bool = False,
    ) -> GeneratorHealthReport:
        if not isinstance(root_seed, int) or isinstance(root_seed, bool):
            raise ValueError("root_seed must be an integer")
        diagnostics = self._diagnostics(pool_result)
        if not diagnostics:
            raise ValueError("generator health requires at least one candidate attempt")
        difficulties = sorted(
            {str(item.get("difficulty", "unknown")).lower() for item in diagnostics}
        )
        archetypes = sorted(
            {
                archetype
                for item in diagnostics
                if (archetype := self._archetype(item)) is not None
            }
        )
        selected = tuple(selected_candidates)
        return GeneratorHealthReport(
            root_seed=root_seed,
            run_completed=run_completed,
            overall=self._slice("all", diagnostics),
            by_difficulty=tuple(
                self._slice(
                    difficulty,
                    [
                        item
                        for item in diagnostics
                        if str(item.get("difficulty", "unknown")).lower() == difficulty
                    ],
                )
                for difficulty in difficulties
            ),
            by_archetype=tuple(
                self._slice(
                    archetype,
                    [item for item in diagnostics if self._archetype(item) == archetype],
                )
                for archetype in archetypes
            ),
            portfolio_diversity=self._portfolio_diversity(selected),
        )

    def write(self, report: GeneratorHealthReport, path: Path) -> Path:
        if not isinstance(report, GeneratorHealthReport):
            raise TypeError("report must be a GeneratorHealthReport")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    def _slice(
        self,
        key: str,
        diagnostics: list[Mapping[str, Any]],
    ) -> GeneratorHealthSlice:
        attempt_count = len(diagnostics)
        completed_count = sum(
            str(item.get("terminalStage", "")) == "quality" for item in diagnostics
        )
        accepted_count = sum(bool(item.get("passed", False)) for item in diagnostics)
        rejection_counts: dict[str, int] = defaultdict(int)
        for item in diagnostics:
            if not item.get("passed", False):
                rejection_counts[str(item.get("code", "unknown_rejection"))] += 1
        dominant = tuple(
            sorted(rejection_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        )
        static_rejections = sum(
            "static_policy" in str(item.get("code", ""))
            for item in diagnostics
            if not item.get("passed", False)
        )
        agent_values: dict[str, list[float]] = defaultdict(list)
        decision_values: dict[str, list[float]] = defaultdict(list)
        layout_reached = 0
        layout_repaired = 0
        runtime_reached = 0
        runtime_robust = 0

        for item in diagnostics:
            for policy, success_rate in self._agent_performance(item).items():
                agent_values[policy].append(success_rate)
            analysis = self._analysis(item)
            if analysis:
                for field_name in self._DECISION_FIELDS:
                    value = analysis.get(field_name)
                    if self._number(value):
                        decision_values[field_name].append(float(value))
            layout = self._stage(item, "layout")
            if layout is not None:
                layout_reached += 1
                if self._layout_was_repaired(layout):
                    layout_repaired += 1
            runtime = self._stage(item, "runtime")
            if runtime is not None:
                runtime_reached += 1
                if self._runtime_was_robust(runtime):
                    runtime_robust += 1

        return GeneratorHealthSlice(
            key=key,
            attempt_count=attempt_count,
            completed_pipeline_count=completed_count,
            accepted_candidate_count=accepted_count,
            completion_rate=self._ratio(completed_count, attempt_count),
            candidate_yield=self._ratio(accepted_count, attempt_count),
            dominant_rejections=dominant,
            static_policy_rejection_rate=self._ratio(static_rejections, attempt_count),
            agent_performance=tuple(
                (policy, self._mean(values))
                for policy, values in sorted(agent_values.items())
            ),
            mean_decision_metrics=tuple(
                (field_name, self._mean(values))
                for field_name, values in sorted(decision_values.items())
            ),
            layout_repair_rate=self._ratio(layout_repaired, layout_reached),
            runtime_robustness_rate=self._ratio(runtime_robust, runtime_reached),
        )

    @staticmethod
    def _portfolio_diversity(
        selected_candidates: tuple[object, ...],
    ) -> PortfolioDiversityMetrics:
        count = len(selected_candidates)
        if count == 0:
            return PortfolioDiversityMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0)

        signatures = [getattr(candidate, "candidate_signature", None) for candidate in selected_candidates]

        def ratio(values: list[object]) -> float:
            normalized = [value for value in values if value not in {None, "", ()}]
            return len(set(normalized)) / count if normalized else 0.0

        topology = ratio([getattr(item, "topology_hash", None) for item in signatures])
        behavior = ratio(
            [getattr(item, "structural_behavior_signature", None) for item in signatures]
        )
        archetype = ratio([getattr(item, "blueprint_archetype", None) for item in signatures])
        mechanics = ratio(
            [tuple(getattr(item, "mechanic_tags", ())) for item in signatures]
        )
        aggregate = round((topology + behavior + archetype + mechanics) / 4.0, 9)
        return PortfolioDiversityMetrics(
            selected_count=count,
            topology_ratio=topology,
            behavior_ratio=behavior,
            archetype_ratio=archetype,
            mechanic_ratio=mechanics,
            aggregate_score=aggregate,
        )

    def _diagnostics(self, pool_result: object) -> list[Mapping[str, Any]]:
        retained = tuple(getattr(pool_result, "attempt_diagnostics", ()))
        if retained:
            return [dict(item) for item in retained]
        diagnostics = []
        for attempt in tuple(getattr(pool_result, "attempts", ())):
            report = getattr(attempt, "to_report_dict", None)
            diagnostics.append(report() if callable(report) else dict(attempt))
        return diagnostics

    @staticmethod
    def _stage(
        diagnostic: Mapping[str, Any],
        stage_name: str,
    ) -> Mapping[str, Any] | None:
        for stage in diagnostic.get("stages", ()):
            if isinstance(stage, Mapping) and stage.get("stage") == stage_name:
                return stage
        return None

    def _archetype(self, diagnostic: Mapping[str, Any]) -> str | None:
        blueprint = self._stage(diagnostic, "blueprint")
        if blueprint is None:
            return None
        value = self._deep_value(blueprint, ("archetype", "blueprintArchetype"))
        return str(value).strip().lower() if value not in {None, ""} else None

    def _analysis(self, diagnostic: Mapping[str, Any]) -> Mapping[str, Any] | None:
        quality = self._stage(diagnostic, "quality")
        if quality is None:
            return None
        analysis = self._deep_value(quality, ("puzzle_analysis", "analysis"))
        return analysis if isinstance(analysis, Mapping) else None

    def _agent_performance(self, diagnostic: Mapping[str, Any]) -> dict[str, float]:
        result: dict[str, float] = {}
        strategy = self._stage(diagnostic, "strategy")
        if strategy is None:
            return result
        evaluations = self._deep_value(strategy, ("evaluations", "agent_results"))
        if not isinstance(evaluations, (list, tuple)):
            return result
        for evaluation in evaluations:
            if not isinstance(evaluation, Mapping):
                continue
            name = evaluation.get("policy_name", evaluation.get("policyName"))
            success_rate = evaluation.get("success_rate", evaluation.get("successRate"))
            if success_rate is None:
                runs = evaluation.get("runs", ())
                if isinstance(runs, (list, tuple)) and runs:
                    successes = sum(
                        bool(run.get("succeeded", False))
                        for run in runs
                        if isinstance(run, Mapping)
                    )
                    success_rate = successes / len(runs)
            if name not in {None, ""} and self._number(success_rate):
                result[str(name)] = float(success_rate)
        return result

    def _layout_was_repaired(self, layout: Mapping[str, Any]) -> bool:
        count = self._deep_value(
            layout,
            ("repairCount", "repair_count", "repairsApplied"),
        )
        if self._number(count):
            return float(count) > 0
        operations = self._deep_value(
            layout,
            ("repair_operations", "repairOperations"),
        )
        return isinstance(operations, (list, tuple)) and bool(operations)

    def _runtime_was_robust(self, runtime: Mapping[str, Any]) -> bool:
        value = self._deep_value(
            runtime,
            ("jitterPassed", "jitter_passed", "robust", "robustnessPassed"),
        )
        if isinstance(value, bool):
            return value
        jitter = self._deep_value(runtime, ("jitter_report", "jitterReport"))
        if isinstance(jitter, Mapping) and isinstance(jitter.get("passed"), bool):
            return bool(jitter["passed"])
        return bool(runtime.get("passed", False))

    @staticmethod
    def _deep_value(value: object, keys: tuple[str, ...]) -> object | None:
        if isinstance(value, Mapping):
            for key in keys:
                if key in value:
                    return value[key]
            for child in value.values():
                found = GeneratorHealthMetricsService._deep_value(child, keys)
                if found is not None:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = GeneratorHealthMetricsService._deep_value(child, keys)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 9) if denominator else 0.0

    @staticmethod
    def _mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 9) if values else 0.0
