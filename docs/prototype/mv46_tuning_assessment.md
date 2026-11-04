# MV-46 — Tuning assessment

Date: 2026-11-02. Scope: the twelve authored prototype levels, following
[MV-46](multi_van_tasks.md#mv-46--tuning-pass) and the
[prototype plan](multi_van_prototype_plan.md).

**Decision: retain every default, departure delay, layout, par and solution.**
The engineering checks pass. No demonstrated balancing defect justifies a
gameplay change. Human readability, enjoyment and the team's agreement that
each idea comes across remain unverified. This is engineering readiness for
MV-47, not completion of a two-person playtest or the source plan's broader
five-person playtest. MV-46's team-agreement acceptance condition remains open.

Later playtest feedback identified a readability defect in Rush: Blue's detour
overlapped the road into its house, implying a straight connection that the
directed graph did not allow. Rush now keeps the detour below the house roads
and merges at (2, 2). Its par remains 3; the recorded live tap is now 4.95 s.
At default tuning the winning switch window is [4.216667, 5.075000), and the
level finishes at 7.95 s. The tables and hashes below record the earlier layout;
current geometry, timing and parameter comparisons are checked in
`PrototypeSolutionTests`.

## Evidence and method

Baseline measurements preceded repository edits. All twelve scripts ran through
the actual `PrototypeSolutionRunner` with explicit `.default` tuning. An
additional diagnostic sampled the actual engine after every 1/120-second step:
positions, driving pairs, edge/status transitions, locks, outcomes and events.
Critical times below are engine observations, not Manhattan-distance estimates.

The complete twelve-level baseline traces matched the MV-45 traces byte for
byte, including event order: 2,545,727 bytes, SHA-256
`a53f13c636ba255d7aef6ca00507935d97f541ee7680807f8753037857795e5d`.
The 24 authored input files are unchanged. Their combined SHA-256 is
`52a5d8be300cc0941ba9833ba8e11ba2ed47b118390d38b3bbc19e1e803dec5b`
(sorted level paths, then sorted solution paths; append each relative path,
NUL, file bytes, NUL).

For each of three configurations, the diagnostic also tested every possible
single live tap on ticks 0 through 1440 inclusive for each of levels 6, 8, 9,
11 and 12: **21,615 probes**. Each probe started from the authored switch
configuration, applied the recorded plan taps, substituted the one live tap,
and simulated up to 20 seconds. Untouched and static configurations used a
120-second horizon. A loop reaching that horizon is unfinished, not an engine
failure or an imposed gameplay time limit.

The retained `testMV46…` checks in
[PrototypeSolutionTests.swift](../../TinyRoutesTests/Prototype/PrototypeSolutionTests.swift)
reproduce all three configurations, pin all twelve completion times, exercise
every step of each first winning window (4,409 winning probes), and test its
adjacent rejected steps. Existing trace/replay helpers now accept an optional
injected tuning snapshot; their default and the solution runner remain unchanged.

## Twelve-level baseline

Times are simulation seconds, rounded to six decimals. S includes live
switches. Plan/live lists the recorded physical taps, **not** the score.
Separation is the minimum sampled distance between any two driving vans;
waiting/parked vans are excluded, matching collision rules. Subtract 0.35 to
obtain clearance above the crash threshold. Every solution wins with three stars
and `changeCount == par`.

| Level | Vans | S | Par | Plan/live taps | Win time | Minimum driving separation | Untouched configuration |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 Go! | 1 | 0 | 0 | 0 / 0 | 6.616667 | — | Wins, intentionally |
| 2 Pick a Lane | 1 | 1 | 1 | 1 / 0 | 4.666667 | — | Red dead end, 4.000000 |
| 3 Two Turns | 1 | 2 | 2 | 2 / 0 | 5.333333 | — | Harmless loop; unfinished at 120 |
| 4 Roundabout | 1 | 1 | 2 | 2 / 0 | 3.333333 | — | Red dead end, 3.333333 |
| 5 Two Colours | 2 | 2 | 2 | 2 / 0 | 4.000000 | 2.000000 | Blue → red house, 2.616667 |
| 6 Convoy | 2 | 1 | 1 | 0 / 1 | 4.833333 | 1.590990 | Blue → red house, 4.833333 |
| 7 Merge | 2 | 1 | 1 | 1 / 0 | 7.950000 | 2.828427 | Red/Blue crash, 2.483333 |
| 8 Hold the Loop | 2 | 2 | 2 | 1 / 1 | 11.950000 | 1.360682 | Red dead end, 1.950000 |
| 9 Split | 2 | 2 | 2 | 1 / 1 | 5.283333 | 2.236068 | Blue dead end, 1.333333 |
| 10 Three's Company | 3 | 3 | 3 | 3 / 0 | 4.000000 | 2.000000 | Yellow dead end, 2.000000 |
| 11 Rush | 3 | 3 | 3 | 4 / 1 | 9.283333 | 1.000003 | Yellow → red house, 1.333333 |
| 12 Big Delivery | 4 | 5 | 5 | 6 / 1 | 9.233333 | 1.000000 | Yellow → red house, 1.333333 |

Levels 11 and 12 return the live switch to its authored setting. Existing
configuration-based scoring consequently reports 3 and 5 changes despite 5 and
7 physical taps. That behavior and its existing assertions are preserved.
All delays are zero except Blue's 1.5-second delay in level 6.

**Human evidence for every row: none supplied.** The observations below are
design/engine findings, not measured player difficulty or participant feedback.

| Level | Lesson and objective finding | Concern and recommended action |
|---|---|---|
| 1 | Press Go and see a matching delivery; deliberately zero input. | Keep. Test whether 6.62 seconds sustains attention and makes the payoff legible. |
| 2 | One planning switch fixes a visible barrier route. | Keep. The preview exposes the consequence before Go; check independent discovery. |
| 3 | Two sequential decisions; one wrong exit loops, the other hits a barrier. Both corrections are required. | Keep. An endless harmless loop gives no fail card; check whether Stop and the loop preview explain recovery. |
| 4 | A three-way switch requires two forward taps; a full cycle restores the initial score. | Keep. Test arrow/exit-order comprehension before three-way switches recur later. |
| 5 | Two colours, two independent corrections; either omitted correction fails. | Keep. A readable introduction to two vans, with no required timing interaction. |
| 6 | Authored Convoy requires opposite exits and one live tap between staggered departures; neither frozen setting wins. | Highest-priority human check. Its 0.97-second window is the narrowest and live input arrives earlier than the plan describes. Keep pending evidence. |
| 7 | Matching previews still crash; one detour removes the conflict with substantial spacing. | Keep. Confirm the overlapping merge/stem and longer route make the cause/fix visually explainable. Preview semantics intentionally do not predict crashes. |
| 8 | Planning admits Red to a loop; hold through the first pass, then release on a later pass. | Keep. No static setting wins. Check whether players understand that tapping while Red is elsewhere selects its NEXT passage, and that missing one opportunity permits another loop. |
| 9 | Red and Blue use opposite exits at one live switch, after a separate planning correction. | Keep the 1.42-second window. Test cue recognition, rejected taps and late flips before deciding to widen it. |
| 10 | Three independent colour decisions, two wrong-house traps and a barrier; all three corrections required. | Keep as a planning consolidation after two timing levels. More vans does not establish greater difficulty; test whether this feels like a welcome pause or an unexpected regression. |
| 11 | Merge detour + shared live split + a three-way Yellow correction. Shortcut, premature split or missing Red selection can crash; missing/late live input sends Blue to Red. | Keep. Planning combines earlier ideas, while the live window is wider than level 9's. Yellow delivers before that window, reducing simultaneous attention demands. |
| 12 | Four vans, five switches, a three-way loop/shortcut/detour choice and the same live split. Loop holds indefinitely; shortcut crashes; intended solution selects the long road during planning. | Keep. The authored solution does not require entering/releasing the loop. Yellow and Green deliver before live input; test whether extra planning is a satisfying finale despite timing close to level 11. |

The sequence teaches planning, safe looping, three-way cycling and colour
matching before the combined final boards. It is not a monotonic timing ramp:
level 6 is tighter than 9, level 10 removes live input, and levels 11–12 widen
the interaction while adding planning. This is a concrete progression question,
not proof that the authored order is unfair. In particular, the source plan's
Convoy sketch has both vans needing the same setting and introduces live input
in level 8; the existing authored level 6 instead needs a live split and has
an explicit hint. This discrepancy predates MV-46 and is retained for human
validation, without silently redesigning a validated level.

## Live-switch measurements

Bounds are exact engine ticks displayed as seconds. `[first, relock)` denotes
accepted fixed-step boundaries; **relock itself rejects**. Last is the last
accepted boundary, one step earlier. Width is `relock − first`, the scheduling
interval, rather than `last − first`. Arbitrary timestamps in scripts round up
to the next simulation step. These are simulation windows, not CPU execution
times or measured human reaction times.

| Level | Arrival(s) at live switch | Lock → unlock → relock → unlock | First | Last | Width | Authored tap |
|---|---|---|---:|---:|---:|---:|
| 6 | Red 2.000000; Blue 3.500000 | 1.733333 → 2.266667 → 3.233333 → 3.766667 | 2.266667 | 3.225000 | 0.966667 | 2.75 |
| 8 | Red enters hold 3.333333; returns/release 8.666667 | 3.075000 → 3.600000 → 8.408333 → 8.933333 | 3.600000 | 8.400000 | 4.808333 | 5.00 |
| 9 | Red 1.333333; Blue 3.283333 | 1.075000 → 1.600000 → 3.016667 → 3.550000 | 1.600000 | 3.008333 | 1.416667 | 2.25 |
| 11 | Red 3.950000; Blue 6.666667 | 3.683333 → 4.216667 → 6.400000 → 6.933333 | 4.216667 | 6.391667 | 2.183333 | 5.25 |
| 12 | Red 3.950000; Blue 6.616667 | 3.683333 → 4.216667 → 6.350000 → 6.883333 | 4.216667 | 6.341667 | 2.133333 | 5.25 |

For level 7 the untouched crash occurs at `(2.098872, 3.862500)` at 2.483333.
In the corrected run, Blue reaches the merge at 2.616667 and Red crosses its
shared-stem merge coordinate at 5.333333: 2.716667 seconds apart, exceeding the
plan's one-second safe-route target. The minimum winning separation is 2.828427.
Both matching previews, the untouched crash and the detour are deterministic.

In level 8, Blue reaches the merge at 3.950000 and parks at 6.566667.
An early 2.75 tap releases Red on the first pass and crashes. With the entry
corrected but no release, Red keeps looping while Blue parks. The first winning
interval is not a global deadline: the exhaustive sweep also wins from 8.933333
through the sweep limit of 12.000000. Untapped looping remains safe for 120
seconds. A later release opportunity should be explained by motion/route cues,
not by changing preview behavior.

In levels 11/12, Red reaches the merge at 3.283333; Blue arrives at 6.000000 /
5.950000. Merge spacing is 2.716667 / 2.666667 seconds. Yellow parks at
1.333333 in both; Green parks at 2.000000 in level 12. No timing puzzle requires
a second simultaneous switch interaction. Level 8's Blue delivery occurs within
its release window; the other additional deliveries precede the windows.

The implementation supplies an amber/lightning live marker, an
engine-authoritative lock, an availability pulse (0.9-second animation), a
level hint, and rejected-tap feedback. These expose **availability**, not whether
a tap will win: a switch can pulse before the correct time. At continuous 2×,
the ideal wall-clock windows halve: level 6 ≈0.483 seconds, 9 ≈0.708,
11 ≈1.092, 12 ≈1.067. Frame delivery, touch latency, finger occlusion and cue
perception require device testing; automated playback speed is not human evidence.

Failure copy names collided van colours, the incorrect house colours, or the
van hitting a dead end. Together with the frozen/highlighted failure point and
retry retaining settings, this explains the category of error. It does not
explicitly diagnose an early versus late accepted live tap. Test whether players
infer that distinction, especially in 6, 9 and 11, before changing copy.

## MV-45 controls and controlled trials

| Control | Original/current engine default | Debug panel bounds | Panel step |
|---|---:|---:|---:|
| `vanSpeed` | 1.5 grid units/s | 0.5–3.0 | 0.1 |
| `crashDistance` | 0.35 grid units | 0.1–0.75 | 0.05 |
| `liveSwitchLockRadius` | 0.4 grid units | 0–1.0 | 0.05 |

The panel writes validated persistent overrides under `multiVanPrototype.`.
The UI value represents the next configuration; an already open engine retains
its injected snapshot. Opening a new engine resolves valid overrides on top of
`.default`; resetting removes the three override keys. No claim is made about
the user's current device's persisted settings. Tests used isolated temporary
UserDefaults suites, reset before every trial and removed afterwards.

Effective `(speed, crash distance, lock radius)` configurations were:

- Baseline **(1.5, 0.35, 0.4)**.
- Slower-speed comparison **(1.3, 0.35, 0.4)**; all other values unchanged.
- Smaller-lock comparison **(1.5, 0.35, 0.3)**; all other values unchanged.

Every trial used the unchanged authored `initialSwitchEdges`, recorded plan taps
and recorded live timestamps from the matching `level_NNN.solution.json` (then named `proto_NN`).
All 36 intended runs won at authored par. Defaults were restored before the
next comparison. Crash distance was not varied: winning routes have at least
0.65 units of clearance above its threshold, and no evidence suggests its rule
is defective. No new parameter or expanded range was needed.

| Level | Baseline first window | Speed 1.3 first window | Radius 0.3 first window |
|---|---|---|---|
| 6 | [2.266667, 3.233333), 0.966667 wide | [2.616667, 3.508333), 0.891667 wide | [2.200000, 3.300000), 1.100000 wide |
| 8 | [3.600000, 8.408333), 4.808333 wide | [4.158333, 9.700000), 5.541667 wide | [3.533333, 8.475000), 4.941667 wide |
| 9 | [1.600000, 3.016667), 1.416667 wide | [1.850000, 3.483333), 1.633333 wide | [1.533333, 3.083333), 1.550000 wide |
| 11 | [4.216667, 6.400000), 2.183333 wide | [4.866667, 7.391667), 2.525000 wide | [4.150000, 6.466667), 2.316667 wide |
| 12 | [4.216667, 6.350000), 2.133333 wide | [4.866667, 7.333333), 2.466667 wide | [4.150000, 6.416667), 2.266667 wide |

Slower speed lengthened levels 1–12 to 7.633333, 5.391667, 6.158333, 3.850000,
4.616667, 5.350000, 9.175000, 13.791667, 6.100000, 4.616667, 10.716667 and
10.658333 seconds. The fixed 1.5-second Convoy departure spacing means slower
movement **narrows** its usable window and reduces its minimum separation to
1.378859; slowing the whole game is not a universal remedy. Other winning
minimum separations remain effectively unchanged (within 0.0004 grid units).
The intended merge crashes persist under both comparisons.

Radius 0.3 leaves paths, completion times, event sequences and collision
clearance identical for the recorded solutions, but changes lock/rejection
boundaries. It adds roughly 0.133333 seconds to each window. That gain alone
does not demonstrate fairer touch interaction near a van. Neither comparison
makes a static solution possible in the five timing levels (2, 4, 4, 12 and
48 static configurations respectively). No intended solution became impossible.

Keep both candidates as documented comparisons only. Retain defaults until
device observations distinguish missing understanding, missed availability
cues, and a genuinely insufficient execution window. Completion-time changes
alone do not establish an improvement in player experience.

## Human data and next validation

No actual exported participant records were supplied in the conversation or
the inspected prototype documentation/resources. Temporary JSONL files generated
by native tests are synthetic fixtures and were excluded. Consequently attempts,
success/failure rates, planning time, timing mistakes, rejected taps, fast-forward
use, stars, abandonment and player difficulty cannot be reported as human results.

MV-43/MV-44 schema inspection confirms those fields/events can support a later
analysis. There is **no tuning metadata** in the JSONL. An exported file must be
associated independently with trial notes recording the effective tuple,
baseline/experimental status, build/content identity and session/trial boundaries.
Never infer the configuration from completion time, selected routes or a session
UUID. Delivery event times are observed dispatch-batch times, not exact engine
arrival times; `omittedEventCount` can also limit event-level analysis.

Priorities for MV-47's two-person real-device session, without starting that task:

1. **Level 6 first exposure:** can each person discover the live interaction from
   its hint, distinguish locked from available, and flip in the 0.97-second gap?
   Observe retries, early/late accepted taps and rejected taps separately. Test
   normal speed first and note any voluntary fast-forward use.
2. **Level 7 explanation:** after the first matching-preview crash, can the player
   identify the shared space and explain why the detour fixes it? This is the M2
   exit criterion; no automated result establishes that it reads clearly.
3. **Levels 8–9 timing comprehension:** can a player wait for Blue, understand
   the loop's next-pass release, recover after missing one loop opportunity, and
   then apply the Red-clears/Blue-approaches cue in Split? Distinguish conceptual
   hesitation from touch execution before considering radius or speed trials.
4. **Levels 10–12 progression:** does 10 consolidate matching, and do the final
   boards feel meaningfully harder through planning? Check the three-way route
   choice, merge explanation and extra colours, rather than assuming van count
   or raw taps imply challenge. Verify the live target remains visible under a
   finger on the smallest intended physical screen.
5. **Feedback and payoff:** can players explain wrong-house versus late-switch
   mistakes and recover using retained settings? With sound on, assess the Go
   moment and chained deliveries (M3 exit), and whether fast-forward undermines
   timing cues. These questions require observation, not another engine-speed run.

Do not mix experimental trials into baseline participant results without the
separate notes above. Two people can expose usability problems; this does not
establish the broader plan's five-person success criteria.

## Validation and scope

- Before edits: 268 native test cases executed, **265 passed, 3 skipped**, zero
  failures, **16,544 executed assertions** across the two executables.
- After edits: 270 native test cases executed, **267 passed, 3 skipped**, zero
  failures, **51,060 executed assertions** (50,977 main + 83 validation).
- Existing twelve-level validation/at-par solutions, scoring, deterministic
  successes/failures, collision precedence, live rejection, event ordering,
  single-drain dispatcher and production/prototype discovery isolation pass.
- Added comparisons use the actual frame driver at regular/uneven partitions
  with normal, continuous 2× and mixed playback; authoritative state, tap order
  and event order agree separately for all three configurations. All 4,409 first
  window ticks win; their adjacent locked ticks reject without changing count
  or selected route. The offline full sweep additionally checked earlier/later
  possibilities through 12 seconds and repeated 216 state/event comparisons.
- Native host adapters stub hardware haptics/audio-session calls. Three skips
  remain: iOS gameplay-view construction and two actual app-bundle packaging
  checks. These are not reported as passes. Both duplicate `MultiVanLevelTests`
  declarations are preserved and executed in separate native executables.
- Focused arm64 iOS 17 typecheck of the changed solution-test source and its
  support passed. The first invocation omitted its existing shared live-switch
  fixture and failed; including that unchanged fixture resolved the diagnostic.
- One unsigned Debug generic-iOS build **succeeded**, using the existing scheme
  and `CODE_SIGNING_ALLOWED=NO`. The standard iOS test target remains blocked by
  the existing duplicate test declaration; no simulator repair/retries performed.

Reproduction in the current workspace: the reused native preparation script is
`/tmp/mv46/native-prepare.py`; run `python3 /tmp/mv46/native-prepare.py`.
It reads current sources, instruments only disposable test copies to count
executed assertions, and runs both existing native executables. Outputs and
compiler commands are in `/tmp/mv46/native/`; the baseline trace, full-sweep
diagnostic source (`Measure.swift`), 36 trial measurements (`measurements.json`),
and build/typecheck logs are in `/tmp/mv46/`. Temporary artifacts are local
evidence, not required repository files. Durable reproduction of the retained
comparisons is through the two `testMV46…` methods using the existing test
harness; full-sweep recipe and exact effective configurations are specified above.

Only this assessment and `PrototypeSolutionTests.swift` changed for MV-46.
No gameplay/production source, level, solution, fixed step, event dispatcher,
scoring rule, signing setting or shared scheme changed. No Git metadata was
modified; changes are unstaged/uncommitted. No MV-47 kit or later work was begun.
