# Switch Interaction Contract

This document is the normative gameplay contract for switch eligibility in Tiny Routes. Swift is the production source of truth, and Python implementations must produce the same externally observable result for the same level, state, taps, and elapsed-time steps. “Must” statements are requirements.

## Terms

### Switchable node

A node is switchable when it has between two and four usable outgoing roads, inclusive. Zero outgoing roads is a terminal node; one is a pass-through node; more than four is invalid level data. Only switchable nodes can be eligible or rotate.

### Usable outgoing road

An outgoing road is usable when its edge exists, its `fromNodeID` equals the node being inspected, and every gameplay availability condition on that road is currently satisfied. Until conditional roads are introduced, all structurally valid outgoing roads are available. Implementations must preserve serialized outgoing-road order after filtering; that order defines rotation.

### Active outgoing road

Every nonterminal node has one active outgoing road. If a stored active road is absent or unusable, it is normalized to the first usable outgoing road before traversal or rotation. A rotation advances to the next usable road in serialized order and wraps from the last to the first.

### First upcoming switch

Starting at the delivery dot, follow only the currently selected route:

1. If the dot is on a road, include the remaining portion of that road and continue at its destination node.
2. At each node, calculate its usable outgoing roads.
3. Stop if the node is switchable; this is the first upcoming switch.
4. Stop with no upcoming switch at a terminal or invalid node.
5. At a pass-through node, follow its sole usable road.

Do not inspect alternative branches or a switch beyond the first switch. The switch at the dot's current node is upcoming only until the dot commits to leaving that node.

## Travel time

Travel time to the first upcoming switch is route distance divided by the dot's current movement speed. Route distance is the sum of each road path's geometric segment lengths. For a road already in progress, use only `roadLength - progressAlongRoad`; node transitions contribute their actual remaining runtime duration if transitions consume time. A stationary or nonfinite/nonpositive speed yields no eligible switch.

Implementations must use binary 64-bit floating-point arithmetic. They must not round intermediate path lengths, distances, speeds, or times for gameplay decisions.

## Live look-ahead eligibility

In `liveLookahead` mode, at most one switch is eligible. The first upcoming switch becomes eligible when all of these conditions hold:

- gameplay is running, not paused;
- the level has neither completed nor failed;
- look-ahead traversal ended at a switchable node without hitting a safety limit; and
- `travelTime <= switchLookaheadSeconds` under the comparison tolerance below.

The window opens on the first update for which that comparison succeeds. A tap at that exact boundary is accepted.

The window closes immediately when the dot commits to an outgoing road from that switch. Commitment occurs when the runtime assigns that outgoing edge as the dot's current edge, before movement along it. The window also closes immediately on pause, completion, failure, an invalidated route, or loss of road usability. A tap at or after commitment is rejected even if the dot remains visually close to the node.

Changing the eligible switch can change the selected downstream route. After every accepted tap, implementations must recompute look-ahead state; however, the current switch remains the first upcoming switch until commitment.

## Taps and cooldown

An accepted tap rotates the eligible switch exactly once and increments the gameplay tap count exactly once. Two-, three-, and four-way switches use the same ordered wraparound rule. Multiple intentional taps during one open window are allowed.

Cooldown is measured in simulation/gameplay time from the most recent accepted tap. A tap is accepted when `currentTime - lastAcceptedTapTime >= switchTapCooldownSeconds`, subject to the comparison tolerance. A rejected tap does not start or extend cooldown, rotate a road, or increment tap count. Paused wall-clock time does not advance gameplay time or cooldown.

Taps are rejected when the target is not the current eligible switch, the cooldown remains active, gameplay is paused, the level is complete or failed, or the dot has committed at that switch. Implementations should expose a stable rejection reason rather than only a Boolean.

## Pause, completion, and failure

While paused, dot movement, gameplay time, eligibility-window progression, and cooldown progression are frozen. All taps are rejected. Resuming recomputes eligibility from the unchanged runtime state.

Completion and failure are terminal for switch interaction. Once either outcome is set, all taps are rejected and no switch is eligible. Package collection and destination checks that occur during the same update must be resolved before publishing eligibility for the next input.

## Traversal safety

Look-ahead traversal must track visited traversal states and enforce a hard limit of 1,024 followed roads. A traversal state consists of the node ID and its selected usable outgoing road ID. Repeating a state before finding a switch, or reaching the hard limit, returns no eligible switch and records a cycle/safety-limit diagnostic. It must never hang, guess a switch, or mutate route selection.

## Legacy mode

The compatibility decision is to retain `legacyGlobal` decoding and replay for archived version-1 files. It is not available for newly authored editor, generator, or production content, and production gates reject it. Levels without `rules` use the Swift-compatible legacy defaults so they can be inspected, replayed, and migrated without changing their historical behavior.

In legacy mode, any switchable node may rotate while gameplay is running, provided the dot has not committed to an outgoing road from that same node. Look-ahead distance and first-upcoming-switch restrictions do not apply. Cooldown is not applied, preserving archived replay semantics. Paused and terminal-state taps remain rejected. No new gameplay features should be added specifically to legacy mode beyond what is required to keep archived decoding and replay safe.

## UI feedback

In live mode, the UI must visibly distinguish the sole eligible switch and remove that state as soon as its window closes. An accepted tap should immediately show the new active road. A rejected tap may provide subtle, non-blocking feedback and must not look like a successful rotation. Accessibility state must identify the active option and whether the switch is currently actionable.

Archived legacy replay may display every switchable node as actionable. UI presentation must consume eligibility published by the engine and must not reimplement the eligibility algorithm.

## Numeric parity and event ordering

Swift and Python compare gameplay times with an absolute tolerance of `1e-9` seconds: `a <= b` is treated as true when `a <= b + 1e-9`, and elapsed cooldown is sufficient when `elapsed + 1e-9 >= cooldown`. Values written to reports may be rounded for display only.

For each elapsed-time step, both runtimes apply events in this order:

1. Reject input immediately if the pre-step state is paused or terminal.
2. Apply taps scheduled at the step's current gameplay timestamp, in fixture order.
3. Advance gameplay by the requested elapsed time, processing road arrivals, package collection, destination outcome, and time-limit failure chronologically.
4. Recompute and publish eligibility from the resulting state.

Shared parity fixtures must avoid relying on timestamps that differ by more than the stated tolerance but fall within a platform scheduler's wall-clock jitter. Simulation uses gameplay timestamps, never UI animation frame timestamps.
