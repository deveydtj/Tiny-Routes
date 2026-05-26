from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..level_editor_imports import LevelDocument, SolutionActionModel, SolutionModel
from ..models.candidate_signature import CandidateSignature
from ..models.generated_level import GeneratedLevel
from ..services.candidate_signature_service import CandidateSignatureService


@dataclass(frozen=True)
class ExistingLevelRecord:
    level_id: str
    level_path: Path
    solution_path: Path | None
    generated_level: GeneratedLevel


@dataclass
class ExistingLevelLoadResult:
    records: list[ExistingLevelRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manifest_signatures: list[CandidateSignature] = field(default_factory=list)

    @property
    def signatures(self):
        return [
            record.generated_level.candidate_signature
            for record in self.records
            if record.generated_level.candidate_signature is not None
        ] + list(self.manifest_signatures)


class ExistingLevelRepository:
    def __init__(self, signature_service: CandidateSignatureService | None = None) -> None:
        self.signature_service = signature_service or CandidateSignatureService()

    def load_existing_levels(
        self,
        levels_dir: Path,
        solutions_dir: Path,
        manifest_path: Path | None = None,
    ) -> ExistingLevelLoadResult:
        result = ExistingLevelLoadResult()
        levels_path = Path(levels_dir)
        solutions_path = Path(solutions_dir)

        if not levels_path.exists():
            result.warnings.append(f"Existing level comparison skipped missing directory: {levels_path}")
            return result

        if manifest_path is not None and self._manifest_is_fresh(Path(manifest_path), levels_path, solutions_path):
            result.manifest_signatures = self._load_manifest_signatures(Path(manifest_path), result)
            if result.manifest_signatures:
                return result

        for level_path in sorted(levels_path.glob("level_*.json")):
            if level_path.name.endswith(".solution.json"):
                continue
            try:
                level = LevelDocument.from_dict(self._read_json_object(level_path))
            except Exception as exc:
                result.warnings.append(f"Could not load existing level {level_path}: {exc}")
                continue

            solution_path = solutions_path / f"{level.id}.solution.json"
            solution: SolutionModel
            resolved_solution_path: Path | None = solution_path
            if solution_path.exists():
                try:
                    solution = SolutionModel.from_dict(self._read_json_object(solution_path))
                except Exception as exc:
                    result.warnings.append(f"Could not load existing solution {solution_path}: {exc}")
                    solution = self._solution_from_embedded_or_empty(level)
                    resolved_solution_path = None
            else:
                result.warnings.append(f"Missing existing solution sidecar for {level.id}: {solution_path}")
                solution = self._solution_from_embedded_or_empty(level)
                resolved_solution_path = None

            generated_level = GeneratedLevel(
                level_document=level,
                solution=solution,
                template_name="existing",
                difficulty="existing",
                seed=0,
            )
            generated_level.candidate_signature = self.signature_service.signature_for(generated_level)
            result.records.append(
                ExistingLevelRecord(
                    level_id=level.id,
                    level_path=level_path,
                    solution_path=resolved_solution_path,
                    generated_level=generated_level,
                )
            )

        return result

    def _manifest_is_fresh(self, manifest_path: Path, levels_path: Path, solutions_path: Path) -> bool:
        if not manifest_path.exists():
            return False
        latest_resource_mtime = 0.0
        for directory in [levels_path, solutions_path]:
            if not directory.exists():
                continue
            for path in directory.glob("level_*.json"):
                latest_resource_mtime = max(latest_resource_mtime, path.stat().st_mtime)
        return manifest_path.stat().st_mtime >= latest_resource_mtime

    def _load_manifest_signatures(self, manifest_path: Path, result: ExistingLevelLoadResult) -> list[CandidateSignature]:
        try:
            payload = self._read_json_object(manifest_path)
            entries = payload.get("levels", [])
            signatures = []
            for entry in entries:
                signatures.append(
                    CandidateSignature(
                        level_id=entry["levelID"],
                        template_name=entry.get("template", "existing"),
                        difficulty=entry.get("difficultyEstimate", "existing"),
                        node_count=int(entry["nodes"]),
                        edge_count=int(entry["edges"]),
                        switch_count=int(entry["switches"]),
                        required_tap_count=int(entry["tapCount"]),
                        dead_end_count=int(entry.get("deadEndCount", 0)),
                        topology_hash=entry["topologyHash"],
                        layout_hash=entry["layoutHash"],
                        solution_hash=entry["solutionHash"],
                        normalized_positions=tuple(
                            (node_id, float(x), float(y))
                            for node_id, x, y in entry.get("normalizedPositions", [])
                        ),
                    )
                )
            return signatures
        except Exception as exc:
            result.warnings.append(f"Could not load production manifest {manifest_path}: {exc}")
            return []

    def _solution_from_embedded_or_empty(self, level: LevelDocument) -> SolutionModel:
        actions = []
        if level.solution is not None:
            actions = [
                SolutionActionModel(timeSeconds=round(0.4 + (index * 0.4), 2), tapNodeID=node_id)
                for index, node_id in enumerate(level.solution.tapNodeIDs)
            ]
        return SolutionModel(
            levelID=level.id,
            description="Generated from embedded or missing existing solution data for comparison only.",
            expectedOutcome="completed",
            maxTaps=len(actions),
            requiresWithinTimeLimit=True,
            actions=actions,
            isPlaceholder=None,
        )

    def _read_json_object(self, path: Path) -> dict:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected top-level JSON object.")
        return payload
