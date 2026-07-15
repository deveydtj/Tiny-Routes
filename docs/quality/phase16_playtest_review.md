# Phase 16 Production Playtest Review

**Review date:** July 14, 2026
**Scope:** Production levels changed for Task 16.5 (`level_005` and
`level_024`) plus campaign-section progression around each replacement.

## Level 005 — two-phase introduction

- Followed the visible route from start to `pickup_switch`, package,
  `delivery_switch`, and destination.
- Confirmed the pickup decision is made before package collection and the
  delivery decision is made afterward.
- Confirmed each default branch reaches a distinct dead end, making the two
  decisions readable without introducing a loop in the early campaign.
- Confirmed moving both required taps to time `0.0` fails because the second
  switch is not the active look-ahead switch.
- Result: complete in two accepted taps; no rejected taps required.

This creates a clear progression across levels 4–10: single choice, two-phase
choice, single package gate, detour, two-phase gate, fake shortcut, and a final
two-phase easy challenge.

## Level 024 — repeated ring state

- Followed the visible ring from start through `hub`, `ring_a`, and `ring_b`.
- Rotated `ring_b` toward `hub`, changed `hub` toward the package on revisit,
  then changed the revisited `ring_b` toward the gate.
- Confirmed the second `ring_b` decision depends on its state from the first
  visit and occurs after package collection.
- Confirmed the wrong ring branch is a readable dead end and alternate loop
  routes provide recoverable outcomes without satisfying the recorded
  three-tap solution.
- Confirmed moving all required taps to time `0.0` fails at the first live
  activation gate.
- Result: complete in three accepted taps with two route revisits and a switch
  state change on revisit.

This gives the late-medium section a revisit/phase puzzle between the
independent hub chain in level 23 and the fake-shortcut sequence in level 25.

## Automated evidence paired with the review

- Python live-routing replay passes for both levels.
- Swift production sidecar replay passes through the shared solvability
  harness.
- Decision-profile analysis records ordered package-phase decisions for level
  5 and repeated/revisit/state-change evidence for level 24.
- Visual-readability validation reports no errors for either level.
- Editor model and save/reopen round trips preserve both files exactly.
