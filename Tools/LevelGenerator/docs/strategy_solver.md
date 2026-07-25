# Strategy Solver

The production solver is an exact structural proof system. It evaluates puzzle
behavior before layout and runtime timing consume expensive work.

## Canonical state and transitions

`PuzzleState` contains the current node, ordered objective progress/reveal
state, active switch exits, conditional/consumed edge state, and any bounded
history required to distinguish future behavior. The structural transition
service is the single authority for available actions and successor states.
Canonical state keys make repeated-state pruning deterministic.

Weighted search minimizes the declared route cost tuple and retains predecessor
evidence for replay. Production budgets are explicit. Reaching a state/search
limit is uncertainty, not a weak pass, and therefore produces a hard rejection.

## Required proofs

Every accepted candidate provides:

- an optimal successful strategy and its exact cost;
- replay evidence for the optimal trace;
- equivalence classes for equal/further-cost successful alternatives;
- proof that exactly one strategy class has optimal cost when required;
- classified fatal and recoverable failures;
- an exhaustive static-policy result showing no permanent switch assignment
  solves the puzzle;
- an exact decision profile used by later quality and timing stages.

Multiple successful routes are allowed. They are desirable when alternatives
are understandable and recoverable, provided the declared unique optimum is
proved. Equivalent branches with identical future consequences are collapsed
and cannot count toward difficulty.

Every structural action carries `DecisionConsequenceEvidence`. The solver
compares all roads available at the same boundary across six locked dimensions:
future route state, objective progress, route cost, failure risk,
recoverability, and the next switch requirements. At least two distinct
consequence classes are required before the action is meaningful. The evidence
also exposes redundant equivalent choices, so a decorative split cannot be
hidden by a mutable analysis counter. Missing, incomplete, inconsistent, or
equivalent-choice evidence fails the final production policy before staging.

## Policy separation

Random, greedy-objective, one-step, two-step, and optimal agents run against the
same transition model. Their results measure planning horizon and local
obviousness; they do not replace the exact proof. Medium and harder production
candidates must separate from greedy local behavior according to the active
quality target.

Before staging, the production policy aligns every planning-horizon entry with
the canonical optimal action. Every selected level must contain a meaningful
choice whose correct road depends on more than its immediately adjacent edge.
Medium, hard, and expert selections must additionally contain a meaningful
choice classified at two-transition, objective-state, or cross-phase depth;
missing, incomplete, or stale horizon evidence fails closed.

When debugging, start with the strategy stage code, explored-state count,
termination reason, optimal cost, successful strategy classes, static-policy
result, and replay trace. Never raise proof budgets or weaken gates silently;
record a budget change in configuration and reproduce the candidate seed.
