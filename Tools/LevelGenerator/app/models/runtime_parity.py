from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuntimeParityValidationResult:
    runtime_validation_required: bool
    runtime_validation_status: str
    runtime_validation_reason: str
    swift_validation_command: list[str] = field(default_factory=list)
    swift_validation_environment: dict[str, str] = field(default_factory=dict)
    swift_validation_passed: bool | None = None
    swift_validation_skipped_reason: str | None = None
    risky_mechanic_tags: tuple[str, ...] = field(default_factory=tuple)
    requires_swift_runtime_validation: bool = False
    failure_reason: str | None = None
    failure_details: tuple[str, ...] = field(default_factory=tuple)

    def to_metadata(self) -> dict[str, object]:
        return {
            "runtimeValidationRequired": self.runtime_validation_required,
            "runtimeValidationStatus": self.runtime_validation_status,
            "runtimeValidationReason": self.runtime_validation_reason,
            "swiftValidationCommand": list(self.swift_validation_command),
            "swiftValidationEnvironment": dict(self.swift_validation_environment),
            "swiftValidationPassed": self.swift_validation_passed,
            "swiftValidationSkippedReason": self.swift_validation_skipped_reason,
            "riskyMechanicTags": list(self.risky_mechanic_tags),
            "requiresSwiftRuntimeValidation": self.requires_swift_runtime_validation,
            "failureReason": self.failure_reason,
            "failureDetails": list(self.failure_details),
        }
