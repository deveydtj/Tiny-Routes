from __future__ import annotations


class SolutionEquivalenceService:
    """Compares solutions by their ordered switch-decision profile."""

    def decision_signature(self, path_summary) -> tuple[str, ...]:
        return tuple(path_summary.tap_history)

    def are_equivalent(self, first, second) -> bool:
        return self.decision_signature(first) == self.decision_signature(second)
