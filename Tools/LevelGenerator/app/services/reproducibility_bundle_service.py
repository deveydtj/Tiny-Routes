"""Self-contained diagnostic bundles for production V3 failures and runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..paths import find_repo_root
from .production_staging_service import ProductionStagingWorkspace


_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


class ReproducibilityBundleService:
    """Capture exact attempt evidence and emit a one-command reproduction tree."""

    schema_version = 1

    def capture_pipeline_result(self, result: object) -> dict[str, Any]:
        """Reduce a live pipeline result to deterministic JSON-safe evidence."""

        request = getattr(result, "request", None)
        stages = tuple(getattr(result, "stage_results", ()))
        if stages:
            stage_payloads = [self._json_safe(stage) for stage in stages]
        else:
            report = getattr(result, "to_report_dict", None)
            payload = self._json_safe(report() if callable(report) else result)
            stage_payloads = list(payload.get("stages", ())) if isinstance(payload, dict) else []
        return {
            "candidateID": str(
                getattr(request, "candidate_id", getattr(result, "candidate_id", "unknown"))
            ),
            "levelID": str(
                getattr(request, "level_id", getattr(result, "level_id", "unknown"))
            ),
            "difficulty": str(
                getattr(request, "difficulty", getattr(result, "difficulty", "unknown"))
            ).lower(),
            "seed": self._integer_or_none(
                getattr(request, "seed", getattr(result, "seed", None))
            ),
            "attemptIndex": self._integer_or_none(
                getattr(request, "attempt_index", getattr(result, "attempt_index", None))
            ),
            "passed": bool(getattr(result, "passed", False)),
            "terminalStage": str(getattr(result, "terminal_stage", "pipeline")),
            "code": str(getattr(result, "code", "pipeline_result_invalid")),
            "stages": stage_payloads,
        }

    def capture_pipeline_exception(
        self,
        request: object,
        error: Exception,
    ) -> dict[str, Any]:
        return {
            "candidateID": str(getattr(request, "candidate_id", "unknown")),
            "levelID": str(getattr(request, "level_id", "unknown")),
            "difficulty": str(getattr(request, "difficulty", "unknown")).lower(),
            "seed": self._integer_or_none(getattr(request, "seed", None)),
            "attemptIndex": self._integer_or_none(
                getattr(request, "attempt_index", None)
            ),
            "passed": False,
            "terminalStage": "pipeline",
            "code": "candidate_pipeline_error",
            "exception": {
                "type": error.__class__.__name__,
                "message": str(error) or error.__class__.__name__,
            },
            "stages": [],
        }

    def write_run_bundle(
        self,
        workspace: ProductionStagingWorkspace,
        *,
        root_seed: int,
        request_configuration: Mapping[str, Any],
        pool_result: object | None,
        selected_pipeline_results: tuple[object, ...] = (),
        run_status: str,
        failure_reason: str | None = None,
    ) -> Path:
        """Write immutable run evidence and return its bundle manifest path."""

        if not isinstance(workspace, ProductionStagingWorkspace):
            raise TypeError("workspace must be a ProductionStagingWorkspace")
        if not isinstance(root_seed, int) or isinstance(root_seed, bool):
            raise ValueError("root_seed must be an integer")
        if not isinstance(request_configuration, Mapping):
            raise TypeError("request_configuration must be a mapping")

        final_root = workspace.require_path(
            workspace.reports_dir / "reproducibility_bundle"
        )
        final_manifest = final_root / "bundle_manifest.json"
        if final_manifest.is_file():
            return final_manifest
        temporary_root = workspace.require_path(
            workspace.reports_dir / ".reproducibility_bundle.creating"
        )
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
        temporary_root.mkdir()
        try:
            self._write_json(
                temporary_root / "request_configuration.json",
                {
                    "schemaVersion": self.schema_version,
                    "rootSeed": root_seed,
                    "configuration": self._json_safe(dict(request_configuration)),
                },
            )
            diagnostics = self._diagnostics(pool_result)
            self._write_json(
                temporary_root / "derived_seeds.json",
                {
                    "rootSeed": root_seed,
                    "derivedSeeds": [
                        {
                            "candidateID": item.get("candidateID"),
                            "levelID": item.get("levelID"),
                            "attemptIndex": item.get("attemptIndex"),
                            "seed": item.get("seed"),
                        }
                        for item in diagnostics
                    ],
                },
            )
            candidate_root = temporary_root / "candidates"
            candidate_root.mkdir()
            for index, diagnostic in enumerate(diagnostics):
                self._write_candidate_evidence(candidate_root, index, diagnostic)

            selected = [
                self.capture_pipeline_result(result)
                for result in selected_pipeline_results
            ]
            self._write_json(
                temporary_root / "selected_candidates.json",
                {"candidates": selected},
            )
            self._write_json(
                temporary_root / "rejection_details.json",
                {
                    "runStatus": run_status,
                    "failureReason": failure_reason,
                    "candidateRejections": [
                        {
                            "candidateID": item.get("candidateID"),
                            "levelID": item.get("levelID"),
                            "seed": item.get("seed"),
                            "terminalStage": item.get("terminalStage"),
                            "code": item.get("code"),
                        }
                        for item in diagnostics
                        if not item.get("passed", False)
                    ],
                },
            )
            reproduce_command = self._write_reproduction_script(
                temporary_root,
                request_configuration,
                root_seed,
            )
            (temporary_root / "README.md").write_text(
                "# Tiny Routes reproduction bundle\n\n"
                "Run `./reproduce.sh` from this directory to replay the exact "
                "root seed and production request into the isolated "
                "`reproduction/` output tree. Candidate subdirectories retain "
                "the blueprint, composed graph, solver, rejection, layout, and "
                "runtime evidence reached by each attempt.\n",
                encoding="utf-8",
            )
            content_files = tuple(
                sorted(
                    (
                        path
                        for path in temporary_root.rglob("*")
                        if path.is_file() and path.name != "bundle_manifest.json"
                    ),
                    key=lambda path: path.relative_to(temporary_root).as_posix(),
                )
            )
            self._write_json(
                temporary_root / "bundle_manifest.json",
                {
                    "schemaVersion": self.schema_version,
                    "runID": workspace.run_id,
                    "runStatus": run_status,
                    "rootSeed": root_seed,
                    "attemptCount": len(diagnostics),
                    "reproduceCommand": reproduce_command,
                    "files": [
                        {
                            "path": path.relative_to(temporary_root).as_posix(),
                            "sha256": self._digest(path),
                            "byteCount": path.stat().st_size,
                        }
                        for path in content_files
                    ],
                },
            )
            temporary_root.replace(final_root)
            return final_manifest
        except Exception:
            if temporary_root.exists():
                shutil.rmtree(temporary_root)
            raise

    def _write_candidate_evidence(
        self,
        candidate_root: Path,
        index: int,
        diagnostic: Mapping[str, Any],
    ) -> None:
        candidate_id = self._safe_component(str(diagnostic.get("candidateID", "unknown")))
        root = candidate_root / f"{index:04d}_{candidate_id}"
        root.mkdir()
        stages = {
            str(stage.get("stage")): stage
            for stage in diagnostic.get("stages", ())
            if isinstance(stage, Mapping) and stage.get("stage")
        }
        blueprint = stages.get("blueprint")
        composition = stages.get("composition")
        strategy = stages.get("strategy")
        layout = stages.get("layout")
        runtime = stages.get("runtime")
        self._write_json(root / "request.json", {
            key: diagnostic.get(key)
            for key in ("candidateID", "levelID", "difficulty", "seed", "attemptIndex")
        })
        self._write_json(
            root / "blueprint.json",
            self._reached_payload(blueprint, preferred_keys=("blueprint",)),
        )
        self._write_json(
            root / "composed_graph.json",
            self._reached_payload(
                composition,
                preferred_keys=("composed_graph", "composition_graph", "graph"),
            ),
        )
        self._write_json(
            root / "solver_summary.json",
            self._reached_payload(strategy),
        )
        self._write_json(
            root / "rejection_details.json",
            {
                "passed": bool(diagnostic.get("passed", False)),
                "terminalStage": diagnostic.get("terminalStage"),
                "code": diagnostic.get("code"),
                "terminalEvidence": stages.get(str(diagnostic.get("terminalStage"))),
                "exception": diagnostic.get("exception"),
            },
        )
        self._write_json(
            root / "layout_state.json",
            self._reached_payload(
                layout,
                preferred_keys=("layout_state", "layout_result", "layout"),
            ),
        )
        self._write_json(
            root / "runtime_trace.json",
            self._reached_payload(
                runtime,
                preferred_keys=("runtime_trace", "trace", "simulation_result"),
            ),
        )

    @staticmethod
    def _reached_payload(
        stage: Mapping[str, Any] | None,
        preferred_keys: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if stage is None:
            return {"reached": False, "evidence": None}
        for key in preferred_keys:
            found = ReproducibilityBundleService._find_key(stage, key)
            if found is not None:
                return {"reached": True, "evidence": found, "stageSummary": stage}
        return {"reached": True, "evidence": stage}

    @staticmethod
    def _find_key(value: object, key: str) -> object | None:
        if isinstance(value, Mapping):
            if key in value:
                return value[key]
            for child in value.values():
                found = ReproducibilityBundleService._find_key(child, key)
                if found is not None:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = ReproducibilityBundleService._find_key(child, key)
                if found is not None:
                    return found
        return None

    def _diagnostics(self, pool_result: object | None) -> list[dict[str, Any]]:
        if pool_result is None:
            return []
        retained = tuple(getattr(pool_result, "attempt_diagnostics", ()))
        if retained:
            return [self._json_safe(item) for item in retained]
        return [
            {
                **self._json_safe(attempt),
                "stages": [],
            }
            for attempt in tuple(getattr(pool_result, "attempts", ()))
        ]

    def _write_reproduction_script(
        self,
        root: Path,
        configuration: Mapping[str, Any],
        root_seed: int,
    ) -> str:
        generator = (
            find_repo_root() / "Tools" / "LevelGenerator" / "generate_production_campaign.py"
        ).resolve(strict=False)
        start = int(configuration.get("startLevelNumber", 1))
        count = int(configuration.get("count", 1))
        difficulty = str(configuration.get("difficulty", "auto"))
        pool_size = int(configuration.get("candidatesPerSlot", 4))
        attempts = int(configuration.get("maxAttemptsPerSlot", 120))
        wave_size = int(configuration.get("waveSize", 1))
        command = (
            f"python3 {shlex.quote(str(generator))} --start {start} --count {count} "
            f"--difficulty {shlex.quote(difficulty)} --seed {root_seed} "
            f"--candidate-pool-size {pool_size} --max-attempts-per-level {attempts} "
            f"--wave-size {wave_size} --output-levels \"$BUNDLE_DIR/reproduction/levels\" "
            f"--output-solutions \"$BUNDLE_DIR/reproduction/solutions\" "
            f"--production-manifest \"$BUNDLE_DIR/reproduction/production_manifest.json\" "
            f"--staging-root \"$BUNDLE_DIR/reproduction/staging\""
        )
        script = (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            'mkdir -p "$BUNDLE_DIR/reproduction"\n'
            f"{command}\n"
        )
        path = root / "reproduce.sh"
        path.write_text(script, encoding="utf-8")
        os.chmod(path, 0o755)
        return command

    def _json_safe(self, value: object, seen: set[int] | None = None) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return self._json_safe(value.value, seen)
        if isinstance(value, bytes):
            return {"byteCount": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        seen = set() if seen is None else seen
        identity = id(value)
        if identity in seen:
            return {"cycle": value.__class__.__name__}
        seen.add(identity)
        try:
            if is_dataclass(value) and not isinstance(value, type):
                return {
                    field.name: self._json_safe(getattr(value, field.name), seen)
                    for field in fields(value)
                }
            if isinstance(value, Mapping):
                return {
                    str(key): self._json_safe(child, seen)
                    for key, child in sorted(value.items(), key=lambda item: str(item[0]))
                }
            if isinstance(value, (list, tuple)):
                return [self._json_safe(child, seen) for child in value]
            if isinstance(value, (set, frozenset)):
                normalized = [self._json_safe(child, seen) for child in value]
                return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
            dictionary = getattr(value, "__dict__", None)
            if isinstance(dictionary, dict) and dictionary:
                return {
                    str(key): self._json_safe(child, seen)
                    for key, child in sorted(dictionary.items())
                    if not str(key).startswith("_")
                }
            report = getattr(value, "to_report_dict", None)
            if callable(report):
                return self._json_safe(report(), seen)
            to_dict = getattr(value, "to_dict", None)
            if callable(to_dict):
                return self._json_safe(to_dict(), seen)
            return {"type": value.__class__.__name__}
        finally:
            seen.discard(identity)

    @staticmethod
    def _integer_or_none(value: object) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @staticmethod
    def _safe_component(value: str) -> str:
        normalized = _SAFE_COMPONENT.sub("_", value).strip("._-")
        return (normalized or "unknown")[:96]

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
