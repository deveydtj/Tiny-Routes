from __future__ import annotations


class FailureOutcomeClassifier:
    """Classifies terminal search outcomes independently of traversal and reporting."""

    SUCCESS = frozenset({"success"})
    PACKAGE_BYPASS = frozenset({"destination_before_package"})
    SEARCH_LIMIT = frozenset({"max_traversal_depth_reached", "max_explored_states_reached"})

    def classify(self, terminal_reason: str) -> str:
        if terminal_reason in self.SUCCESS:
            return "success"
        if terminal_reason in self.PACKAGE_BYPASS:
            return "package_bypass"
        if terminal_reason in self.SEARCH_LIMIT:
            return "search_limit"
        return "wrong_branch_failure"
