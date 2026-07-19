"""Structured objective-state availability rules for schema-3 route edges."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .route_objective import LEGACY_PICKUP_OBJECTIVE_ID


@dataclass
class EdgeAvailabilityRule:
    """A small, serializable condition model with no embedded expressions."""

    requiredCompletedObjectiveIDs: list[str] = field(default_factory=list)
    forbiddenCompletedObjectiveIDs: list[str] = field(default_factory=list)
    minimumObjectiveIndex: int | None = None
    maximumObjectiveIndex: int | None = None
    usageLimit: int | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    _present_fields: set[str] = field(default_factory=set, repr=False, compare=False)

    _KNOWN_FIELDS = {
        "requiredCompletedObjectiveIDs",
        "forbiddenCompletedObjectiveIDs",
        "minimumObjectiveIndex",
        "maximumObjectiveIndex",
        "usageLimit",
    }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EdgeAvailabilityRule":
        if not isinstance(data, Mapping):
            raise TypeError("availabilityRule must be an object")

        return cls(
            requiredCompletedObjectiveIDs=[
                str(value) for value in data.get("requiredCompletedObjectiveIDs", ())
            ],
            forbiddenCompletedObjectiveIDs=[
                str(value) for value in data.get("forbiddenCompletedObjectiveIDs", ())
            ],
            minimumObjectiveIndex=(
                int(data["minimumObjectiveIndex"])
                if data.get("minimumObjectiveIndex") is not None
                else None
            ),
            maximumObjectiveIndex=(
                int(data["maximumObjectiveIndex"])
                if data.get("maximumObjectiveIndex") is not None
                else None
            ),
            usageLimit=(
                int(data["usageLimit"])
                if data.get("usageLimit") is not None
                else None
            ),
            _extra=deepcopy(
                {key: value for key, value in data.items() if key not in cls._KNOWN_FIELDS}
            ),
            _present_fields=set(data).intersection(cls._KNOWN_FIELDS),
        )

    @classmethod
    def adapting_legacy_availability(
        cls,
        availability: str,
        package_objective_id: str = LEGACY_PICKUP_OBJECTIVE_ID,
    ) -> "EdgeAvailabilityRule":
        """Map schema-2 package phases to the equivalent objective condition."""

        if availability == "always":
            return cls()
        if availability == "beforePackage":
            return cls(forbiddenCompletedObjectiveIDs=[package_objective_id])
        if availability == "afterPackage":
            return cls(requiredCompletedObjectiveIDs=[package_objective_id])
        raise ValueError(f"Unknown road availability: {availability}")

    def to_dict(self) -> dict[str, Any]:
        result = deepcopy(self._extra)
        values: dict[str, Any] = {
            "requiredCompletedObjectiveIDs": list(self.requiredCompletedObjectiveIDs),
            "forbiddenCompletedObjectiveIDs": list(self.forbiddenCompletedObjectiveIDs),
            "minimumObjectiveIndex": self.minimumObjectiveIndex,
            "maximumObjectiveIndex": self.maximumObjectiveIndex,
            "usageLimit": self.usageLimit,
        }
        for name, value in values.items():
            if name in self._present_fields or value not in (None, []):
                result[name] = value
        return result

    def clone(self) -> "EdgeAvailabilityRule":
        return deepcopy(self)
