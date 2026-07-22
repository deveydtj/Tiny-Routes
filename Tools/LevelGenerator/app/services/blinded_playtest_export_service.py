"""Create deterministic tester and researcher packages for V3 calibration."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from ..models.playtest_export import BlindedPlaytestExportResult, PlaytestSample


class BlindedPlaytestExportService:
    schema_version = 1
    required_difficulties = ("easy", "medium", "hard", "expert")
    required_archetypes = (
        "closed_return",
        "competing_success_routes",
        "ordered_checkpoint",
        "recoverable_loop",
        "return_to_hub",
        "unlock_shortcut",
    )

    rubric = (
        ("goalUnderstandable", "Was the goal understandable?", "1-5"),
        ("routePlanning", "Did the player need to plan a route?", "1-5"),
        (
            "routeChangedAfterObjective",
            "Did the correct route change after an objective?",
            "yes/no/unsure",
        ),
        ("wrongRoutesFair", "Were wrong routes fair?", "1-5/not_seen"),
        (
            "recoveryExperience",
            "Was recovery satisfying or tedious?",
            "satisfying/neutral/tedious/not_seen",
        ),
        (
            "overallImpression",
            "How did the level feel overall?",
            "boring/confusing/frustrating/engaging",
        ),
        (
            "perceivedDifficulty",
            "What was the perceived difficulty?",
            "easy/medium/hard/expert",
        ),
        ("replayDesire", "Would the player want to replay it?", "1-5"),
        ("notes", "Optional observation notes", "free_text"),
    )

    def export(
        self,
        samples: Iterable[PlaytestSample],
        output_directory: Path,
        *,
        seed: int,
        expected_archetypes: Iterable[str],
    ) -> BlindedPlaytestExportResult:
        samples = tuple(samples)
        output_directory = Path(output_directory)
        expected_archetypes = tuple(
            sorted({str(value).strip() for value in expected_archetypes if str(value).strip()})
        )
        if set(expected_archetypes) != set(self.required_archetypes):
            raise ValueError(
                "expected_archetypes must declare every supported production V3 archetype"
            )
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")
        if not samples:
            raise ValueError("playtest export requires at least one sample")
        if len({sample.source_id for sample in samples}) != len(samples):
            raise ValueError("playtest sample source IDs must be unique")
        self._validate_coverage(samples, expected_archetypes)
        if output_directory.exists() and any(output_directory.iterdir()):
            raise FileExistsError("playtest output directory must be absent or empty")

        tester = output_directory / "tester_package"
        researcher = output_directory / "researcher_package"
        levels = tester / "levels"
        levels.mkdir(parents=True, exist_ok=True)
        researcher.mkdir(parents=True, exist_ok=True)

        ordered = list(sorted(samples, key=lambda sample: sample.source_id))
        random.Random(seed).shuffle(ordered)
        tester_entries: list[dict[str, Any]] = []
        answer_entries: list[dict[str, Any]] = []
        for index, sample in enumerate(ordered, start=1):
            blind_id = f"TRP-{index:03d}"
            relative_path = Path("levels") / f"{blind_id}.json"
            level_payload = self._blinded_level(sample.level_payload, blind_id)
            (tester / relative_path).write_text(
                json.dumps(level_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tester_entries.append(
                {"blindID": blind_id, "levelPath": relative_path.as_posix()}
            )
            answer_entries.append(
                {
                    "blindID": blind_id,
                    "sourceID": sample.source_id,
                    "difficulty": sample.difficulty,
                    "blueprintArchetype": sample.blueprint_archetype,
                    "objectiveCount": sample.objective_count,
                    "recoveryPattern": sample.recovery_pattern,
                    "failurePattern": sample.failure_pattern,
                    "layoutProfile": sample.layout_profile,
                    "knownWeak": sample.known_weak,
                    "automatedMetrics": sample.automated_metrics,
                }
            )

        rubric_payload = {
            "schemaVersion": self.schema_version,
            "instructions": (
                "Complete one row immediately after playing each level. Do not "
                "consult solution or researcher metadata."
            ),
            "questions": [
                {"field": field, "prompt": prompt, "response": response}
                for field, prompt, response in self.rubric
            ],
        }
        tester_manifest = {
            "schemaVersion": self.schema_version,
            "sampleCount": len(tester_entries),
            "entries": tester_entries,
            "rubricPath": "rubric.json",
            "responseSheetPath": "responses.csv",
        }
        self._write_json(tester / "manifest.json", tester_manifest)
        self._write_json(tester / "rubric.json", rubric_payload)
        (tester / "responses.csv").write_text(
            self._response_csv(tuple(entry["blindID"] for entry in tester_entries)),
            encoding="utf-8",
        )
        (tester / "README.md").write_text(self._tester_readme(), encoding="utf-8")

        coverage = self._coverage(samples, expected_archetypes)
        answer_key = {
            "schemaVersion": self.schema_version,
            "assignmentSeed": seed,
            "testerPackage": "../tester_package",
            "coverage": coverage,
            "entries": answer_entries,
        }
        self._write_json(researcher / "answer_key.json", answer_key)
        self._write_json(researcher / "coverage_report.json", coverage)
        (researcher / "README.md").write_text(
            "# Researcher package\n\nKeep this directory separate from testers. "
            "It contains source identities, intended cohorts, automated metrics, "
            "and weak-control labels.\n",
            encoding="utf-8",
        )

        fingerprint = self._fingerprint(tester)
        self._write_json(
            output_directory / "export_summary.json",
            {
                "schemaVersion": self.schema_version,
                "sampleCount": len(samples),
                "testerFingerprint": fingerprint,
                "testerDirectory": "tester_package",
                "researcherDirectory": "researcher_package",
            },
        )
        return BlindedPlaytestExportResult(
            output_directory=output_directory,
            tester_directory=tester,
            researcher_directory=researcher,
            sample_count=len(samples),
            fingerprint=fingerprint,
        )

    @classmethod
    def from_source_manifest(
        cls, path: Path
    ) -> tuple[tuple[PlaytestSample, ...], tuple[str, ...]]:
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != 1:
            raise ValueError("unsupported playtest source manifest schema")
        samples = []
        for entry in payload.get("samples", []):
            level_path = (path.parent / entry["levelPath"]).resolve()
            samples.append(
                PlaytestSample(
                    source_id=entry["sourceID"],
                    level_payload=json.loads(level_path.read_text(encoding="utf-8")),
                    difficulty=entry["difficulty"],
                    blueprint_archetype=entry["blueprintArchetype"],
                    objective_count=entry["objectiveCount"],
                    recovery_pattern=entry["recoveryPattern"],
                    failure_pattern=entry["failurePattern"],
                    layout_profile=entry["layoutProfile"],
                    known_weak=entry.get("knownWeak", False),
                    automated_metrics=dict(entry.get("automatedMetrics", {})),
                )
            )
        return tuple(samples), tuple(payload.get("expectedArchetypes", ()))

    def _validate_coverage(
        self, samples: tuple[PlaytestSample, ...], expected_archetypes: tuple[str, ...]
    ) -> None:
        coverage = self._coverage(samples, expected_archetypes)
        if coverage["missingDifficulties"]:
            raise ValueError(
                "playtest corpus is missing difficulties: "
                + ", ".join(coverage["missingDifficulties"])
            )
        if coverage["missingArchetypes"]:
            raise ValueError(
                "playtest corpus is missing declared archetypes: "
                + ", ".join(coverage["missingArchetypes"])
            )
        if coverage["knownWeakCount"] < 1 or coverage["productionCandidateCount"] < 1:
            raise ValueError("playtest corpus needs both weak controls and production candidates")
        for key in (
            "objectiveCountValues",
            "recoveryPatterns",
            "failurePatterns",
            "layoutProfiles",
        ):
            if len(coverage[key]) < 2:
                raise ValueError(f"playtest corpus requires varied {key}")

    def _coverage(
        self, samples: tuple[PlaytestSample, ...], expected_archetypes: tuple[str, ...]
    ) -> dict[str, Any]:
        values = lambda attribute: sorted({getattr(sample, attribute) for sample in samples})
        difficulties = values("difficulty")
        archetypes = values("blueprint_archetype")
        return {
            "sampleCount": len(samples),
            "difficulties": difficulties,
            "missingDifficulties": sorted(set(self.required_difficulties) - set(difficulties)),
            "blueprintArchetypes": archetypes,
            "expectedArchetypes": list(expected_archetypes),
            "missingArchetypes": sorted(set(expected_archetypes) - set(archetypes)),
            "objectiveCountValues": values("objective_count"),
            "recoveryPatterns": values("recovery_pattern"),
            "failurePatterns": values("failure_pattern"),
            "layoutProfiles": values("layout_profile"),
            "knownWeakCount": sum(sample.known_weak for sample in samples),
            "productionCandidateCount": sum(not sample.known_weak for sample in samples),
        }

    @staticmethod
    def _blinded_level(payload: dict[str, Any], blind_id: str) -> dict[str, Any]:
        blinded = deepcopy(payload)
        blinded["id"] = blind_id
        blinded["name"] = f"Playtest {blind_id}"
        for key in (
            "seed",
            "difficulty",
            "templateName",
            "recipeFamily",
            "recipeVariant",
            "blueprintArchetype",
            "qualityScore",
            "generationNotes",
            "knownWeak",
            "sourceID",
            "automatedMetrics",
            "analysis",
        ):
            blinded.pop(key, None)
        metadata = blinded.get("metadata")
        if isinstance(metadata, dict):
            for key in tuple(metadata):
                lowered = key.lower()
                if any(
                    token in lowered
                    for token in (
                        "seed",
                        "difficulty",
                        "template",
                        "recipe",
                        "quality",
                        "blueprint",
                    )
                ):
                    metadata.pop(key, None)
        return blinded

    @classmethod
    def _response_csv(cls, blind_ids: tuple[str, ...]) -> str:
        stream = io.StringIO(newline="")
        fields = ["blindID", *(item[0] for item in cls.rubric)]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for blind_id in blind_ids:
            writer.writerow({"blindID": blind_id})
        return stream.getvalue()

    @staticmethod
    def _tester_readme() -> str:
        return (
            "# Tiny Routes blinded playtest\n\n"
            "Play the levels in manifest order and complete the matching row in "
            "`responses.csv` immediately after each attempt. The package intentionally "
            "contains no target difficulty, source identity, automated score, solution, "
            "or weak-control label.\n"
        )

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _fingerprint(directory: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
