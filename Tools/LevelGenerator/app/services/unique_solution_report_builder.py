from __future__ import annotations

from typing import Callable


class UniqueSolutionReportBuilder:
    """Formats uniqueness outcomes while remaining independent from state search."""

    def build_issues(self, result, issue_factory: Callable[..., object]) -> tuple[object, ...]:
        if result.solution_count > 1:
            code = "unique_solution_multiple_solutions"
            message = (
                "Unique solution search found more than one valid package-before-destination solution "
                f"(solutions={result.solution_count}, exploredStates={result.explored_states})."
            )
        elif not result.is_exhaustive:
            code = "unique_solution_search_limit_reached"
            message = (
                "Unique solution search hit a traversal limit before proving uniqueness "
                f"(solutions={result.solution_count}, exploredStates={result.explored_states}, "
                f"maxDepthReached={result.max_depth_reached}, termination={result.termination_reason})."
            )
        elif result.solution_count == 0:
            code = "unique_solution_not_found"
            message = (
                "Unique solution search found no valid package-before-destination solution "
                f"(exploredStates={result.explored_states})."
            )
        else:
            return ()
        return (issue_factory(severity="error", code=code, message=message),)
