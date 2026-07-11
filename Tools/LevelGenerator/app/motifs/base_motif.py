from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.puzzle_motif import PuzzleMotif


class BaseMotif(ABC):
    """Factory interface for independently valid, composable puzzle fragments."""

    @property
    @abstractmethod
    def motif_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build(self) -> PuzzleMotif:
        raise NotImplementedError

    def validate(self) -> tuple[str, ...]:
        motif = self.build()
        issues = list(motif.validate())
        if motif.motif_id != self.motif_id:
            issues.append(f"motif_factory_id_mismatch:{self.motif_id}:{motif.motif_id}")
        return tuple(issues)
