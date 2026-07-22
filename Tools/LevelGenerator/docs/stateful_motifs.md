# Stateful Motifs

Motifs are small, typed graph fragments used by the composer to realize
blueprint roles. Their contracts are executable; names and free-form metadata
never establish production eligibility.

## Contract surface

`PuzzleMotif` declares graph nodes and edges plus typed `MotifPort` values.
Ports identify main-route entry/exit, branch, rejoin, objective attachment,
return, and state-transition connection roles. A motif also declares:

- difficulty and objective-phase preconditions;
- required incoming/completed objective state;
- structural and gameplay effects;
- objective completions and edge-state changes;
- cycle, revisit, rejoin, and failure behavior;
- compatibility exclusions and maximum instance counts;
- layout footprint/metadata needed by later validation.

The contract helper verifies that declared decisions really branch, rejoins
really merge, state changes reference the correct objective and road, one-use
connectors carry a usage limit, and legacy flags agree with typed effects.

## Composition

The composer can insert a fragment on an edge, expand a branch, create a
rejoin, add a cross-phase return, and attach an objective. Typed port validation
runs before every connection. Deterministic backtracking prunes partial graphs
that cannot satisfy blueprint dependencies, and graph/behavior isomorphism
rejects duplicates. Layout spacer motifs may improve readability but cannot
count as strategic decisions.

## Adding a motif

1. Define nodes, edges, typed ports, preconditions, and effects in the motif
   registry/service; keep concrete IDs local to the fragment.
2. Add the motif contract helper test and assert each declared topology/effect
   from graph evidence.
3. Demonstrate at least one compatible composition operation and one invalid
   context that is rejected with a stable code.
4. Prove behavior with exact solver and static-policy evidence.
5. Add phase-aware layout coverage when the motif opens/closes roads or revisits
   a hub.
6. Run behavior-isomorphism checks before assigning production status.

Use fixture or deprecated registry status for tutorial-only, mislabeled,
behavior-isomorphic, or legacy recipe support. Production V3 never falls back to
those entries.
