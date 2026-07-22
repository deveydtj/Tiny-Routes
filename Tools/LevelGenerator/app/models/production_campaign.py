"""Typed request and terminal result for one automatic production campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..paths import (
    get_default_levels_directory,
    get_default_production_staging_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)
from .quality_profile import CURRENT_QUALITY_PROFILE_VERSION


@dataclass(frozen=True)
class ProductionCampaignConfig:
    start_level_number: int
    count: int
    difficulty: str
    seed: int | None = None
    run_swift_tests: bool = True
    swift_timeout_seconds: int = 180
    candidates_per_slot: int = 4
    max_attempts_per_slot: int = 120
    wave_size: int = 1
    quality_profile_version: str = CURRENT_QUALITY_PROFILE_VERSION
    levels_output_dir: Path = field(default_factory=get_default_levels_directory)
    solutions_output_dir: Path = field(default_factory=get_default_solutions_directory)
    production_manifest_path: Path = field(
        default_factory=lambda: get_default_reports_directory()
        / "production_manifest.json"
    )
    staging_root: Path = field(default_factory=get_default_production_staging_directory)

    def __post_init__(self) -> None:
        for field_name in (
            "start_level_number",
            "count",
            "swift_timeout_seconds",
            "candidates_per_slot",
            "max_attempts_per_slot",
            "wave_size",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if self.candidates_per_slot < 2:
            raise ValueError("candidates_per_slot must be at least two")
        if self.max_attempts_per_slot < self.candidates_per_slot:
            raise ValueError(
                "max_attempts_per_slot cannot be smaller than candidates_per_slot"
            )
        difficulty = self.difficulty.strip().lower()
        if difficulty not in {"auto", "easy", "medium", "hard", "expert"}:
            raise ValueError(f"Unknown production V3 difficulty: {self.difficulty}")
        if self.seed is not None and (
            not isinstance(self.seed, int) or isinstance(self.seed, bool)
        ):
            raise ValueError("seed must be an integer or None")
        if (
            not isinstance(self.quality_profile_version, str)
            or not self.quality_profile_version.strip()
        ):
            raise ValueError("quality_profile_version cannot be empty")
        object.__setattr__(
            self, "quality_profile_version", self.quality_profile_version.strip()
        )
        if not self.run_swift_tests:
            raise ValueError("production V3 campaigns require Swift staged validation")
        object.__setattr__(self, "difficulty", difficulty)
        for field_name in (
            "levels_output_dir",
            "solutions_output_dir",
            "production_manifest_path",
            "staging_root",
        ):
            object.__setattr__(self, field_name, Path(getattr(self, field_name)))

    def snapshot(self, *, resolved_seed: int) -> dict[str, Any]:
        return {
            "generatorArchitecture": "production_v3",
            "generatorArchitectureVersion": 3,
            "startLevelNumber": self.start_level_number,
            "count": self.count,
            "difficulty": self.difficulty,
            "seed": resolved_seed,
            "runSwiftTests": self.run_swift_tests,
            "swiftTimeoutSeconds": self.swift_timeout_seconds,
            "candidatesPerSlot": self.candidates_per_slot,
            "maxAttemptsPerSlot": self.max_attempts_per_slot,
            "waveSize": self.wave_size,
            "qualityProfileVersion": self.quality_profile_version,
            "levelsOutputDirectory": str(self.levels_output_dir.resolve(strict=False)),
            "solutionsOutputDirectory": str(
                self.solutions_output_dir.resolve(strict=False)
            ),
            "productionManifestPath": str(
                self.production_manifest_path.resolve(strict=False)
            ),
        }


@dataclass(frozen=True)
class ProductionCampaignResult:
    status: str
    run_id: str
    seed: int
    requested_count: int
    selected_count: int = 0
    report_path: Path | None = None
    reproducibility_bundle_path: Path | None = None
    health_report_path: Path | None = None
    workspace_path: Path | None = None
    quality_profile_version: str | None = None
    quality_profile_fingerprint: str | None = None
    promoted_paths: tuple[Path, ...] = ()
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"completed", "failed_no_changes", "rolled_back"}:
            raise ValueError("unsupported production campaign status")
        if self.status == "completed" and self.selected_count != self.requested_count:
            raise ValueError("completed campaign must contain the full requested count")
        if self.status == "completed" and self.failure_reason is not None:
            raise ValueError("completed campaign cannot have a failure reason")
        if self.status != "completed" and not self.failure_reason:
            raise ValueError("failed campaign requires a failure reason")

    @property
    def passed(self) -> bool:
        return self.status == "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "runID": self.run_id,
            "seed": self.seed,
            "requestedCount": self.requested_count,
            "selectedCount": self.selected_count,
            "reportPath": str(self.report_path) if self.report_path else None,
            "reproducibilityBundlePath": (
                str(self.reproducibility_bundle_path)
                if self.reproducibility_bundle_path
                else None
            ),
            "healthReportPath": (
                str(self.health_report_path) if self.health_report_path else None
            ),
            "workspacePath": str(self.workspace_path) if self.workspace_path else None,
            "qualityProfileVersion": self.quality_profile_version,
            "qualityProfileFingerprint": self.quality_profile_fingerprint,
            "promotedPaths": [str(path) for path in self.promoted_paths],
            "failureReason": self.failure_reason,
        }
