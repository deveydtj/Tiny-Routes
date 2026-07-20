"""Typed pool evidence for V3 composition diversity and duplicate rejection."""

from __future__ import annotations

from dataclasses import dataclass


def _positive_integer(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


@dataclass(frozen=True)
class CompositionDiversityConstraints:
    """Hard repetition caps applied while building one candidate pool."""

    blueprint_archetype_cap: int = 3
    motif_multiset_cap: int = 2
    dependency_dag_cap: int = 2

    def __post_init__(self) -> None:
        for field_name in (
            "blueprint_archetype_cap",
            "motif_multiset_cap",
            "dependency_dag_cap",
        ):
            _positive_integer(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class CompositionPoolEntry:
    """Canonical diversity evidence retained for one accepted composition."""

    candidate_id: str
    blueprint_archetype: str
    motif_multiset: tuple[tuple[str, int], ...]
    dependency_dag_signature: str
    behavior_signature: str
    state_signature: str

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "blueprint_archetype",
            "dependency_dag_signature",
            "behavior_signature",
            "state_signature",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name),
            )
        motifs = tuple(self.motif_multiset)
        if tuple(sorted(motifs)) != motifs:
            raise ValueError("motif_multiset must be sorted")
        if len({motif_id for motif_id, _ in motifs}) != len(motifs):
            raise ValueError("motif_multiset motif IDs must be unique")
        for motif_id, count in motifs:
            _identifier(motif_id, "motif_id")
            _positive_integer(count, "motif_count")
        object.__setattr__(self, "motif_multiset", motifs)


@dataclass(frozen=True)
class CompositionDuplicateAssessment:
    """Deterministic decision for adding one composition to a pool."""

    entry: CompositionPoolEntry
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.entry, CompositionPoolEntry):
            raise TypeError("entry must be a CompositionPoolEntry")
        reasons = tuple(self.rejection_reasons)
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise ValueError("rejection_reasons cannot contain empty values")
        if len(reasons) != len(set(reasons)):
            raise ValueError("rejection_reasons must be unique")
        object.__setattr__(self, "rejection_reasons", reasons)

    @property
    def is_accepted(self) -> bool:
        return not self.rejection_reasons


@dataclass(frozen=True)
class CompositionPoolResult:
    """Stable accepted entries and evidence for every considered candidate."""

    accepted_entries: tuple[CompositionPoolEntry, ...]
    assessments: tuple[CompositionDuplicateAssessment, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_entries", tuple(self.accepted_entries))
        object.__setattr__(self, "assessments", tuple(self.assessments))
