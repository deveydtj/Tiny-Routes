from __future__ import annotations

from collections.abc import Iterable

from .base_motif import BaseMotif


class MotifRegistry:
    def __init__(self, motifs: Iterable[BaseMotif] = ()) -> None:
        self._motifs: dict[str, BaseMotif] = {}
        for motif in motifs:
            self.register(motif)

    def register(self, motif: BaseMotif) -> None:
        if motif.motif_id in self._motifs:
            raise ValueError(f"duplicate_motif_id:{motif.motif_id}")
        issues = motif.validate()
        if issues:
            raise ValueError(f"invalid_motif:{motif.motif_id}:{','.join(issues)}")
        self._motifs[motif.motif_id] = motif

    def get(self, motif_id: str) -> BaseMotif:
        try:
            return self._motifs[motif_id]
        except KeyError as exc:
            raise KeyError(f"unknown_motif_id:{motif_id}") from exc

    def all(self) -> tuple[BaseMotif, ...]:
        return tuple(self._motifs[motif_id] for motif_id in sorted(self._motifs))
