"""Ordered route objectives used by schema-3 levels."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class RouteObjectiveKind(str, Enum):
    """The initial objective behaviors supported by the schema-3 contract."""

    PICKUP = "pickup"
    CHECKPOINT = "checkpoint"
    DELIVERY = "delivery"
    DESTINATION = "destination"


@dataclass
class RouteObjective:
    """A stable, ordered objective with lossless extension-field handling."""

    id: str
    nodeID: str
    kind: RouteObjectiveKind
    sequenceIndex: int
    revealPolicy: str
    displayMetadata: dict[str, Any] | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    _display_metadata_present: bool = field(default=False, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RouteObjective":
        known = {
            "id",
            "nodeID",
            "kind",
            "sequenceIndex",
            "revealPolicy",
            "displayMetadata",
        }
        display_metadata = data.get("displayMetadata")
        if display_metadata is not None and not isinstance(display_metadata, Mapping):
            raise TypeError("displayMetadata must be an object or null")

        return cls(
            id=str(data["id"]),
            nodeID=str(data["nodeID"]),
            kind=RouteObjectiveKind(str(data["kind"])),
            sequenceIndex=int(data["sequenceIndex"]),
            revealPolicy=str(data["revealPolicy"]),
            displayMetadata=deepcopy(dict(display_metadata)) if display_metadata is not None else None,
            _extra=deepcopy({key: value for key, value in data.items() if key not in known}),
            _display_metadata_present="displayMetadata" in data,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            **deepcopy(self._extra),
            "id": self.id,
            "nodeID": self.nodeID,
            "kind": self.kind.value,
            "sequenceIndex": self.sequenceIndex,
            "revealPolicy": self.revealPolicy,
        }
        if self._display_metadata_present or self.displayMetadata is not None:
            result["displayMetadata"] = deepcopy(self.displayMetadata)
        return result

    def clone(self) -> "RouteObjective":
        return deepcopy(self)
