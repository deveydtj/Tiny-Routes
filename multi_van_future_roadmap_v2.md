# TinyRoutes — Future Roadmap V2

**Design synthesis and development strategy · 2026-11-03 · Proposal for owner review**

This is the recommended planning reference for future Multi-Van development, subject to approval. It supersedes V1's proposed sequencing, not its source files or any implemented behavior. This task created only this document and did not modify levels, solutions, tuning, source, settings or Git metadata. No builds, simulations, human sessions or subagents were run for this review. Referenced test assertions are source evidence, not newly executed results.

## 1. Executive direction

**Make Multi-Van the lasting foundation of TinyRoutes. Expand the decisions players make before expanding the rules they must remember.** The central pleasure is examining a miniature delivery network, composing a plan, watching it work, intervening deliberately when appropriate, understanding failures, and enjoying the delivery payoff.

The preferred first addition is **optional, fixed-owner package pickup**, tested as a complete but small three-board experiment. Some vans need one pickup; others begin ready to deliver. Houses remain terminal destinations. Collection is automatic and instantaneous. There is no inventory management, loading delay or change in vehicle physics.

The development strategy is:

1. Approve and build the bounded package experiment in Sections 4–5. All three boards use static planning; current live-switch tuning is not a dependency.
2. Evaluate a separate pause / inspect / change / resume prototype before authoring more mandatory live-switch puzzles. Observe current timing levels alongside it without changing their content.
3. Keep only puzzle concepts that earn their place. Introduce alternate valid plans early, and preserve quiet delivery-only boards.
4. If one-package play succeeds, test two pickups in either order before investing in signals. This is a later experiment, not part of the first package implementation.
5. Keep traffic lights as one later automatic-signal experiment. No signal chapter or manual-dispatch system is committed.
6. Audit and complete production integration separately. **The working source already routes normal play through Multi-Van.** The remaining issue is safe preservation, compatibility and release readiness, not starting that transition from zero.

Sixty levels is an aspiration. A strong twelve-level foundation plus a small accepted expansion is a useful milestone. A first release may stop at 18, 24 or another justified count; those numbers are examples, not release targets. Rejected chapters disappear rather than receiving filler replacements.

### Evidence and terminology

The distinctions below apply throughout:

| Label | Meaning |
|---|---|
| **Implemented** | Verified in the current working source or authored content. This need not match V1, the critique, the prototype specification, or a shipped build. |
| **Confirmed constraint** | A consequence of that implementation, such as a shared switch having one selected exit for every van. |
| **Proposed** | Recommended behavior requiring approval and future implementation. |
| **Hypothesis** | Expected player value or authoring feasibility requiring experimentation. No playtest result is implied. |

Primary repository evidence reviewed:

| Sources | Purpose |
|---|---|
| [V1 roadmap](multi_van_future_roadmap.md), [Astra critique](multi_van_roadmap_critique.md), [original specification](docs/prototype/multi_van_prototype_plan.md) | Compare intent, independent criticism and original prototype boundaries. |
| [MV-46 assessment](docs/prototype/mv46_tuning_assessment.md), especially its opening Rush correction; [solution tests](TinyRoutesTests/Prototype/PrototypeSolutionTests.swift) | Separate obsolete measurements from current retained assertions. |
| All twelve [level definitions](TinyRoutes/Resources/PrototypeLevels/) and all twelve [solution scripts](TinyRoutesTests/Resources/PrototypeSolutions/) | Actual topology, ordered exits, initial selections, vans, delays, pars and intended actions. All 24 files were read. |
| [Level/tuning model](TinyRoutes/Prototype/MultiVanLevel.swift), [engine](TinyRoutes/Prototype/MultiVanEngine.swift), [runtime graph](TinyRoutes/Gameplay/RuntimeRouteGraph.swift), [preview](TinyRoutes/Prototype/MultiVanRoutePreview.swift) | Current simulation and schema authority. |
| [Validation tests](TinyRoutesTests/Prototype/MultiVanLevelTests.swift), [script model](TinyRoutesTests/Support/PrototypeSolutionScript.swift), [runner](TinyRoutesTests/Support/PrototypeSolutionRunner.swift) | Actual validation coverage, input order and test-horizon semantics. |
| [Gameplay/frame driver](TinyRoutes/Prototype/MultiVanGameplayScreen.swift), [feedback](TinyRoutes/Prototype/MultiVanFeedback.swift), [flat board](TinyRoutes/Prototype/MultiVanBoardView.swift), [diorama board](TinyRoutes/Prototype/MultiVanDioramaBoardView.swift), [diorama snapshot](TinyRoutes/Prototype/MultiVanDioramaSync.swift), [board switcher](TinyRoutes/Prototype/MultiVanBoardSwitcher.swift) | Real presentation, reset, event, accessibility and renderer integration boundaries. |
| [Logger](TinyRoutes/Prototype/MultiVanPlaytestLog.swift), [internal session](TinyRoutes/Prototype/MultiVanPrototypeScreen.swift) | Local logging and isolation from production progress. |
| [Root navigation](TinyRoutes/App/ContentView.swift), [main gameplay host](TinyRoutes/UI/LevelPlayScreen.swift), [profile](TinyRoutes/Domain/PlayerProfile.swift), [save repository](TinyRoutes/Infrastructure/SaveDataRepository.swift), [progress service](TinyRoutes/Services/ProgressService.swift), [save tests](TinyRoutesTests/SaveDataRepositoryTests.swift), [build definition](project.yml) | Verify the already-implemented main-campaign transition and its data implications. |

The workspace remained active during review: unrelated diorama/scenery files and their tests/documentation changed concurrently. This task neither edited nor reverted them. A before/after content check confirmed that the original roadmaps/specification, all twelve levels and solutions, engine and tuning model were unchanged during document creation. This is a working-source review, not an assertion that the entire repository was frozen or that every earlier document remains current.

### Current behavior that changes the planning baseline

- The engine uses fixed 1/120-second steps by default, a fractional accumulator, one speed, actual `RoadPath` geometry and carried-over movement distance. Defaults in source are speed 1.5, collision distance 0.35 and live lock radius 0.4. Internal engines can receive persisted debug overrides; this review did not inspect or change device settings.
- All switches are configurable during planning. Ordinary switches freeze during a run. Listed live switches rotate only when no driving van is within the inclusive Euclidean lock radius. A van already on an edge keeps it after a switch changes.
- Only driving vans participate in pairwise sampled collisions. Waiting departures and parked vans do not. Arrival failures precede crash checks within a step; authored van order resolves arrival and pair ties. This is deterministic sampled simulation, not continuous collision detection.
- Houses terminate movement. The current arrival method sets a van to parked before checking house color; a wrong-color arrival still fails. A new missing-cargo result must not accidentally count a matching house as delivered.
- Stop returns to planning and resets the run. Retry and Replay use the same run reset and **retain final current switch settings**, including live changes. Retry retains the failure point until the next Go. Reset switches restores authored selections; it is a different action.
- Previews trace selected exits to a house, dead end or 40-edge limit. Running previews include the committed edge. They predict destination routing, not collision timing or future player inputs. The current glyph is ✓ only for a matching house; loop limits currently use ✗ too. Describing loops as unfinished in future summaries is a proposal, not an existing UI distinction.
- `changeCount` is cyclic forward distance from authored selections to the **current configuration**, not cumulative taps or planning taps plus live history. Existing stars use that value: three at par, two at par + 2, otherwise one for a win.
- There is no gameplay cargo, pickup event, pause control or traffic-light admission in Multi-Van. Shared edge availability fields exist but Multi-Van departure, switching and preview do not evaluate their objective conditions. The old single-vehicle objective machinery does not supply Multi-Van cargo support.
- **Both flat and native SceneKit diorama boards exist now.** V1's description of a diorama stand-in is stale. Both consume the same engine. The flat delivery popup already draws a decorative parcel; adapt that visual language where useful. Decoration is not a package lifecycle, and renderer parity is real work for future pickups.
- Normal level selection already uses `MultiVanLevelRepository`, and `LevelPlayScreen` records stars, unlocks and completion rewards. The internal prototype session remains separate, with optional logs and debug tuning. Normal gameplay currently creates a default-tuned engine and does not pass a playtest logger.
- Profile schema version 3 explicitly resets pre-v3 level progress because the old and new campaigns reused `level_001`-style IDs. It preserves other profile fields. A separate legacy stars-only import currently lacks that reset distinction. Section 10 treats this as a compatibility risk to resolve before rollout, not an instruction to edit it now.

### The twelve-level teaching baseline

The scripts establish what future teaching can assume. They are not measurements of player comprehension.

| Existing level | Verified lesson / intended input | Future implication |
|---|---|---|
| 1 Go! | One van, no taps, delivery payoff. | Preserve simple pleasure and zero-input relief where useful. |
| 2 Pick a Lane | One static fork correction. | Cargo teaching may build on branch selection. |
| 3 Two Turns | Two static corrections; wrong route may loop safely. | Safe looping and dead ends are different outcomes. |
| 4 Roundabout | Two taps through a three-way switch. | Exit order and physical tap count already matter to controls. |
| 5 Two Colours | Independent matching routes for two vans. | Color plus symbol identity precedes cargo. |
| 6 Convoy | Shared start; Blue delayed 1.5 seconds; live flip at 2.75 seconds. | Live switching is already introduced here, despite the original specification naming level 8. |
| 7 Merge | Red's static detour prevents a geometric conflict. | ✓ does not mean traffic-safe. |
| 8 Hold the Loop | Static entry correction, live release at 5 seconds. | Repeating opportunities are a useful existing tool. |
| 9 Split | Entry correction, live flip at 2.25 seconds. | Two vans need opposite exits at different visits. |
| 10 Three's Company | Three static matching corrections; no live input. | A planning respite is already part of the game's rhythm. |
| 11 Rush | Blue detour, Yellow's three-way correction, initial split correction; live flip at **4.95 seconds**. | Use corrected geometry and tests, not the old 5.25-second script. |
| 12 Big Delivery | Four vans, five switches; intended Blue route is the detour; live flip at 5.25 seconds. | Its loop branch is not the recorded solution. Reset difficulty at 13. |

## 2. Original roadmap versus Astra critique — decision table

These judgments are independent design recommendations. “Accept” accepts the recommendation, not implementation authorization.

| Major recommendation | Decision | Reason and practical consequence |
|---|---|---|
| Do not commit to sixty levels before demonstrating variety. | **Accept** | V1's six-slot fallbacks contradict its own quality principle. Keep a flexible horizon; remove weak concepts without replacing their slots. |
| Make packages optional per van and per level. | **Accept** | Mixed cargo focuses attention, and plain deliveries support pacing. Zero assigned packages means ready to deliver; no separate authored readiness flag is needed. |
| Compress repetitive introductory pickup boards. | **Accept with modifications** | Combine ownership and two-van teaching, but retain one very easy pickup board and optional reinforcement if observation shows a need. Calm reinforcement has value even when it introduces no new rule. |
| Test cargo interactions before building a chapter. | **Accept** | Experiment B exercises a changed coordination decision immediately. Learning the pickup icon alone cannot justify a campaign system. |
| Use package-free/mixed comparisons to establish incremental value. | **Accept** | Experiment C matches B's topology without cargo. Distinguish extra reasoning, thematic satisfaction and extra travel instead of attributing all coordination depth to packages. |
| Derive requirements from ownership; use one lifecycle authority. | **Accept** | Fixed ownership plus universally required assigned items makes per-van requirement arrays redundant. Derive requirements and carrying views from package definitions/state. |
| Investigate narrow live windows. | **Accept** | Current level 6 and corrected Rush have subsecond simulation intervals. Test comprehension separately from execution; do not infer unfairness from duration alone or change existing tuning here. |
| Prefer understandable planning over reflex pressure. | **Accept with modifications** | Preserve occasional satisfying real-time interventions for players who enjoy them. Prototype deliberate play with equal completion recognition; do not remove live switching by doctrine. |
| Three seconds is the right new-window target; existing windows need widening. | **Requires player testing** | Three seconds at normal speed after a clear cue is a useful starting authoring target, not a universal accessibility threshold. Existing changes require separate approval and evidence. Repeating opportunities and pause can matter more than a nominal duration. |
| Validate existing coordination before allowing any package trial. | **Reject as a mandatory dependency** | Observing levels 7–9 is valuable, but static package experiments do not depend on solving live timing. Run those observations alongside cargo work. If static coordination itself proves confusing, simplify B; do not impose unrelated engine/tuning work first. |
| Defer signals until their value is demonstrated. | **Accept** | Preserve the traffic-light idea, remove guaranteed automatic/manual chapters, and test one bounded automatic board later. |
| Move a two-package experiment ahead of signals. | **Accept with modifications** | Only after single-package value and presentation succeed. It is a cheap next hypothesis relative to stopping/occupancy, not a reason to broaden the initial cargo implementation. |
| Accept alternate valid solutions to deepen puzzles. | **Accept with modifications** | Validate and celebrate coherent alternatives early. Do not require every tutorial to have several solutions or force replays to advance. A clear single-insight puzzle can be excellent. |
| Avoid engine rewrites, generic inventory and traffic AI. | **Accept** | No demonstrated constraint requires them. Use current arrival handling, paths, shared switch state, deterministic steps and event dispatch. |
| Avoid rigid attempt-count success targets. | **Accept** | An elegant first-try solve is not a defect. Observe reasoning, correction and desire for another board; attempts diagnose friction rather than define fun. |
| Delay production promotion until late mastery content / expansion validation. | **Accept with modifications** | The source already contains promotion. Audit data preservation now, validate release readiness soon, and separate rollout from cargo acceptance. Waiting for levels 49–60 buys no migration safety. |

V1 ideas worth preserving over a more aggressive cut: a calm first pickup tutorial; visible cargo-to-house payoff; rare recoverable live loops; explicit spatial direction teaching; small chapters that reset difficulty; and a readable finale in two episodes. These supply rhythm and identity. Remove their repetitive versions, not their purposes.

## 3. Core gameplay design principles

1. **The plan belongs to the player.** Show objectives and selected routes before Go. Favor choices with explainable consequences over hidden switches or trial-and-error timing.
2. **Rules stay small; relationships deepen.** A shared switch, one crossing, or two complete route options can produce a stronger puzzle than another entity type.
3. **Failure teaches a cause.** Name the van, destination, missing pickup or conflicting pair and show the relevant place. A correct verbal plan blocked by touch execution calls for control work, not a harder puzzle.
4. **Watching is part of playing.** Preserve anticipation, visible collection and distinct deliveries. Shorten empty travel when it adds no thought or payoff. Fast-forward can be sensible on retries; it is not automatically evidence of boredom.
5. **Intervention should feel deliberate.** One time-sensitive control at once; durable cues; repeatable opportunities where practical. Do not create difficulty by shrinking the opportunity to act.
6. **Keep quiet levels.** Include delivery-only or gentle static boards after intensive puzzles. Not every level must introduce or recombine a rule.
7. **Do not confuse more vans with more depth.** Prefer two meaningful interacting vans to four crowded tours. Retain color plus identity symbols across vans, houses and cargo.
8. **One readable miniature board.** Retain the current 5×7 coordinate envelope initially. Do not enlarge it or shrink controls to rescue a weak layout. Actual layout, Dynamic Type, diorama camera angles and nonvisual route comprehension still need device checks.
9. **Previews explain their scope.** A route can satisfy destination and cargo while colliding. “Current route unfinished” differs from a proven failure, especially before a future live change.
10. **Completion comes before mastery.** No timers, assistance penalties or repeated optimization requirements in pickup teaching. Existing stars/pars remain unchanged.

## 4. Recommended package pickup system

### 4.1 Player contract — proposed

- Each package has a stable ID, one pickup node and one fixed owner van ID. Color and symbol communicate ownership; they are not keys.
- A van has **zero or one assigned required package** in the initial experiment. Zero means ready to deliver. A level may have no packages at all.
- The correct van collects automatically on actual node arrival. Another van passes without collecting or failing. A road crossing near the marker is not arrival.
- Collection is immediate and idempotent. Revisiting does not duplicate cargo. Cargo changes neither speed, collision geometry, switch locks nor road availability.
- Houses remain final terminal destinations. A wrong house fails as today. A matching house reached without its required package produces a distinct missing-package failure and no delivery credit.
- Make “Pickup needed,” “Carrying,” “Ready to deliver,” and “Delivered” inspectable. The moving roof attachment is reinforcement; the persistent chip/summary is authoritative presentation.

This adopts Astra's bounded proposal, including reuse of decorative parcel styling. It rejects a generic inventory, a loading button, optional collectible stock and a separate cargo-capacity concept. One-item validation is a supported-content limit, not a mechanic presented to players.

### 4.2 Minimal schema and state

| Area | Minimum recommended change | Compatibility / constraint |
|---|---|---|
| Level JSON | Optional `packages` collection with `id`, `nodeID`, `ownerVanID`. Add one explicit supported feature schema version for package-bearing content, e.g. implicit legacy v1 and explicit v2. | Missing packages decodes to empty. Preserve all existing files and ordered exits. Level content version is separate from profile schema version 3. |
| Van definitions | No authored requirement array and no authored ready flag. Derive the required item from packages owned by that van. | Reject more than one package per owner initially. No duplicate sources of truth. |
| Package identity | Nonempty unique IDs, valid owner van ID, valid pickup node. | Validate unique van IDs before keyed ownership lookups. Keep identities stable when content is reordered. |
| Runtime authority | One engine-owned table keyed by package ID: `atPickup`, `carried`, `delivered`. Owner is immutable in the definition. | “Carried by whom?” is derived from fixed ownership. No independently mutable per-van inventory or renderer cargo copy. |
| Per-van cargo view | Derive needed/carried/delivered status from required package plus lifecycle. | Small scans are sufficient for this board size; an inventory index/service is unnecessary. |
| Persistence | Save successful level progress only; no partial cargo across attempts or app relaunch. | Mid-run save/restore is outside this proposal. Existing progress records need no package inventory fields. |

An old binary can ignore unknown JSON keys; adding a version field today cannot retroactively change that binary. Future loaders must reject unsupported versions/features before play, and package content must be bundled only with a compatible binary. There is no need to build remote content delivery for this experiment. `MultiVanLevel` is currently Decodable, not a full editor/export model; preserve exit order and add round-trip support only if an actual authoring tool requires it.

First authored boards keep pickups off starts, houses and switches, and use at most one pickup per node. Define engine ordering for start-node and pickup-plus-house fixtures anyway; authoring validation may reject those combinations for the experiment. This separates robust arrival semantics from permission to author cluttered boards.

### 4.3 Arrival and lifecycle transaction

Extend the existing node-arrival/departure seam; do not replace movement:

1. Process an assigned available pickup on entering the node, including processing the start when the van actually departs. A positive-delay van does not collect during idle planning or before its departure.
2. At a house, check wrong-house identity first for outcome precedence. A wrong owner passing a colocated pickup does nothing. Initial authored boards avoid this ambiguity.
3. At a matching house, check its derived cargo requirement. If absent, fail with van ID, package ID and pickup node ID. **Do not mark it parked or delivered.** A small explicit missing-cargo van status is recommended so existing status-based board rules cannot show a successful matching-house checkmark; update status consumers in both renderers and accessibility.
4. On a valid matching arrival, change any carried required package to delivered, park the van, increment the existing combo and emit delivery. Only all valid deliveries may win. A ready-to-deliver van follows the old success path.
5. On ordinary nodes, use the selected outgoing edge exactly as today. Pickups consume no distance and preserve leftovers, including pickup then house within one fixed step.

Preserve existing package-free traces, wrong-house behavior, arrival-failure-before-crash precedence and authored tie order. Do not globally reorder all vans' arrivals to implement cargo. Two owners collecting in the same tick have independent lifecycle transitions, in stable authored van/event order. Reversing van definitions may change tie/event order by contract, but must not change ownership or duplicate items.

The engine currently advances **local van copies across multiple steps before publishing**. Package state must participate in that same transaction. Pass the current local lifecycle through arrival/movement and publish it with the vans; do not read stale `self.vans` to decide pickups during `advance`. If using a local package copy, every transition in later steps must read that copy, not the last published table.

A pickup and then crash in one tick may produce pickup followed by crash. One van may deliver in a step where another causes failure, as existing event behavior permits. Lifecycle records retain those completed transitions until reset; the attempt still fails. Failure suppresses conflicting celebration. An animation completion can clear cosmetic tokens but must never change package ownership, delivery eligibility or victory.

### 4.4 Previewing hypothetical cargo

Use a small pure pickup/requirement check shared with tracing if that prevents real semantic duplication. Do not introduce a general objective interpreter.

- Planning traces start with hypothetical empty cargo for pickup vans and ready status for others. Visiting an owned pickup changes only the trace-local state.
- Running traces seed from actual lifecycle state and follow the current committed edge before considering future selections. Process its destination, including a pickup there. A live flip cannot redirect the current edge.
- Return a distinct missing-package ending with the item/location needed; distinguish wrong house, dead end and loop/current-route unfinished. A ✓ means the selected route can satisfy cargo and destination, not that traffic or an unperformed live action is safe.
- A package collected in a trace never disappears from the real board. Tracing other owners cannot consume their cargo, and a trace does not reserve simultaneous arrivals.
- Invalidate/rebuild previews on objective-state transitions as well as edge/status/selection changes. Current publication compares only final edge ID and status; a complete lap can change cargo while ending on the same edge in a multi-step frame.
- Status summaries list named stops and remaining pickup, not just ✓/✗. Do not simulate a full timing future or predict unknown live inputs for the first cargo trial.

### 4.5 Reset, Stop, Retry and Replay

| Action | Proposed cargo behavior | Existing switch/run contract to retain |
|---|---|---|
| Load / initial plan | All packages at pickup; readiness derived. | Authored initial settings. |
| Go | Fresh lifecycle, fresh vans; then real departures may collect. | Use current planned selections; start simulation time at zero. |
| Reset switches in plan | Recompute hypothetical preview; packages remain at pickup. | Restore authored settings only. |
| Stop | All cargo/deliveries reset to initial availability; return to planning. | Keep the current settings, not the settings from Go. |
| Retry after failure | Same fresh cargo/van state; clear missing-cargo presentation. | Keep current settings and existing failure-point behavior until Go. |
| Replay after win | Fresh cargo and deliveries. | Same retained-selection behavior as Retry; opening a fresh level/session restores authored settings. |

**Retained live settings are a design hazard, not a cargo-state bug.** A loop exited on a successful or failed run may still point home on Retry. Its next run can arrive empty unless the player re-arms it. Future live-cargo boards must show that in the preview and status, expose the selected exit clearly, and test Retry from the final live configuration. Prefer layouts whose retained exit remains cargo-valid where possible. If manual re-arming repeatedly surprises players, redesign that board or separately trial “restore Go plan”; do not silently change all existing Retry semantics.

### 4.6 Events, logging, validation and presentation

| Integration | Required future work |
|---|---|
| Events | Add semantic collection and missing-package data to the existing single-drain stream. Capture simulation tick at the transition, plus stable sequence and package/van/node IDs. Use an explicit local step tick: published `runTime` can be stale during `advance`. Departure at a step boundary and arrival at its end have defined stamps; Go departures use tick 0. Preserve current ordered event semantics rather than inventing substep floating-time sorting. |
| Dispatcher | Extend the existing feedback path for pickup sound/haptic, visuals and optional announcement. Logging observes the same dispatch. Never add a second consumer that drains events first. |
| Validation | Check unique IDs, owner existence, zero/one item per owner, marker placement policy, valid references, supported schema/features, nonnegative finite delays/par and supported van counts. Check start→pickup→house reachability without passing through a terminal house. Then prove an actual joint solution; independent reachability does not prove compatible shared settings or collision safety. |
| Graph conditions | Explicitly reject unsupported objective-dependent/usage-limited edges in new Multi-Van content. Metadata carried by `RuntimeRouteGraph` is not implemented behavior. Cargo never normalizes the shared graph for all vans. |
| Scripts | Existing planning/live tap format suffices for cargo. Keep stable time sorting, rounding to an eligible tick and the 120-second harness horizon. Add package assertions and full-state snapshots to the runner/tests; the horizon is not a gameplay deadline. No new pickup command. |
| Trial discovery | Keep A/B/C in an explicit internal experiment set with distinct IDs and no progress/rewards. The current loader selects canonical `level_` files and tests pin exactly twelve. Do not add experiments to that folder and weaken count assertions. Accepted levels later receive campaign IDs and deliberate catalog/test updates. |
| Logs | Version new local rows compatibly; include experiment/variant, content identity, build, effective tuning, initial and Go switch settings, assist/facilitator flags, pickup/failure IDs and exact semantic ticks. Keep observed batch time and real elapsed time under their existing meanings. Existing events cap at 1,024 with omitted count; do not silently treat a truncated event history as complete. Manual notes can carry trial metadata initially. |
| Actual log wiring | The internal host passes a logger; the main host currently does not. Run the experiment internally. Adding logs to normal play is separate scope, not an existing capability to assume. |
| Visuals | Adapt the existing small parcel styling for a persistent pickup marker and unobtrusive carried attachment. Distinguish world pickup from decorative unload effects. Add the same lifecycle representation to the flat board and native diorama snapshot/scene. No renderer decides collection. |
| Accessibility | Preserve van symbols; label owner, location, needed/carried/delivered state. Provide a stable per-van route/objective summary and once-only collection announcement. Test muted play, Reduce Motion, larger text, touch targets, contrast and diorama occlusion. No state may depend on a parcel flight, tiny roof box, pulse or sound. |

## 5. Three-level pickup experiment

**These are experiments A/B/C, provisionally occupying design slots 13/14/15. They are not guaranteed campaign entries.** No geometry, JSON, timing or par has been authored or verified here. Node counts and motion lengths are authoring targets. Use actual engine geometry to establish margins later; do not treat the sketches as solved levels.

All three use current speeds/collisions, ordinary switches, terminal matching houses and unlimited planning. They require no pause feature, signal or live input. Test full pickup/reset/preview feedback in this vertical slice; postponing those pieces would invalidate the gameplay comparison.

### Experiment A / provisional 13 — Pick Up First

- **Learning objective:** understand start → own pickup → matching house, and see a satisfying loaded state without traffic pressure.
- **Nodes/entities:** one Red circle van, one circle house, one owned package, one two-exit ordinary fork. Topology: start → fork; direct branch → downstream join → house; other branch → pickup → downstream join → house. Allow one or two bend nodes for clean geometry: approximately 5–7 nodes, one switch, one package. The join is downstream of the fork, so no frozen switch must change on a return visit.
- **Player decision:** choose the marked cargo tour rather than the empty direct route. This is one meaningful validity choice, intentionally easy; it teaches a rule, not deep coordination.
- **Successful concept:** select pickup route, Go, collect once, visibly carry, deliver once. No downstream barrier puzzle is needed.
- **Failures:** bypass reaches matching house empty; preview names missing pickup and failure points back to it. No win, house checkmark or combo on missing cargo. Stop before/after pickup and Retry after failure must restore the item while retaining selections.
- **Complexity:** very low; one route correction, roughly 6–10 seconds of ordinary motion as a trial target. No timer or exact duration requirement.
- **Dependencies:** minimal cargo schema/lifecycle/arrival handling, missing outcome, hypothetical preview, both renderer states, chip/summary, reset/events and internal fixture loading.
- **Deterministic checks:** both fork settings; preview/runtime agreement; exactly one collection and delivery on success; no collection on bypass; no mutation from repeated preview; correct Stop/Go/Retry/Replay; start-node fixture ordering; unchanged twelve-level regressions. Repeat with regular/uneven frame budgets and 1×/2× for equivalent tick inputs.
- **Human questions:** before Go, can the player identify what is needed? Does the preview explain the empty route without a forced failure? Is collection noticeable without covering the road? Do they understand that pickup is progress toward home, not the final goal?
- **Retain/reject:** retain a short teaching board if the rule and payoff read clearly. Simplify markers/copy if they do not. Do not retain extra introductory boards solely because A is easy; if even this presentation feels like an unwanted errand, investigate before expanding.

### Experiment B / provisional 14 — Make Room for a Pickup

- **Learning objective:** a package requirement can change which plan works for another van. Pickup is a route constraint with a coordination consequence.
- **Nodes/entities:** Red circle requires one package; Blue triangle begins ready to deliver. Two houses, two ordinary route forks, one clearly marked geometric crossing between separate directed paths. Red's fork offers a direct empty route or pickup tour before the crossing; Blue's offers short or long routes before its crossing. Use separate downstream joins and exits; do not use a frozen shared split that requires different exits. Approximately 12–16 nodes including bends, two switches, two vans, one package. Reduce decorative bends if the board cannot fit cleanly.
- **Player decisions:** Red must collect; then choose Blue's route so the two complete deliveries coexist. Both Blue choices are destination-valid. Merely following the package preview cannot answer Blue's choice.
- **Successful concept / authoring targets:** Red's direct route crosses earlier than Blue's short route and would be safe without cargo. Red's pickup tour reaches the crossing near Blue's short route and conflicts. Blue's longer route clears that conflict by arriving clearly later. Thus Red pickup + Blue long wins. Derive actual timings/separation from `RoadPath` and the engine; require broad visible separation on the winner, not a near miss.
- **Failures:** Red direct + either Blue route reaches home empty if otherwise safe; Red pickup + Blue short has cargo-valid routes but collides. Arrange the empty-route variants to reach their missing-package outcome without an earlier incidental crash, so each lesson can be inspected. Wrong-owner passing is a separate engine fixture, not another visual bait puzzle here.
- **Complexity:** low–medium; two related static choices, one crossing, roughly 8–15 seconds of motion. No precision delay or reaction window.
- **Dependencies:** A's complete slice; no new engine rules. Actual geometry validation and four-configuration enumeration are essential authoring work.
- **Deterministic checks:** enumerate all four branch pairings, pin intended outcomes, full objective states/event order and robust winning separation. Verify Blue never needs or steals Red's item; no early win after Blue parks; same-tick independent arrival fixtures; retained selections after Stop/Retry; regular/uneven and mixed-speed replay. If unintended safe alternatives exist, document them and judge whether they preserve the insight before changing anything.
- **Human questions:** can players explain why collecting changes Blue's useful route? After a crash, do they change the relevant plan rather than tap randomly? Is it clear Blue is already ready? Is the extra route satisfying, or is the interesting part entirely the familiar detour puzzle?
- **Retain/reject:** retain the mechanic if cargo creates an understandable dependency and players value it. Redesign B if the pickup branch itself solves everything, Blue's fork is irrelevant, or geometry obscures the crossing. Reject this board if it needs a timing trick to make the intended relationship work.

### Experiment C / provisional 15 — The Same Streets, Ready to Deliver

- **Learning objective:** compare cargo's incremental value with ordinary delivery planning; this is an experimental control, not another pickup tutorial.
- **Nodes/entities:** B's identical graph, departures, switches, houses, initial settings and tuning; both vans ready to deliver and no pickup entity. Retain the former pickup road as an ordinary longer road. Distinct internal experiment ID/variant; no campaign rewards. Same approximate node count and motion range.
- **Player decisions:** the previously invalid Red direct + Blue short plan is now a valid safe choice. Red long + Blue long remains another valid plan. The player may discover a simpler solution or prefer a different delivery sequence.
- **Successful concept:** direct Red + short Blue; also accept every verified safe alternative. Compare decision structure, not merely whether C finishes faster.
- **Failures:** Red long + Blue short should preserve B's collision under identical geometry. No cargo-related result is legal. If the expected valid-set difference does not exist, B/C have failed their experimental design and must be re-authored before player comparison.
- **Complexity:** low–medium reasoning with less objective tracking; no new implementation beyond package-free compatibility and variant metadata.
- **Dependencies:** B geometry plus empty package definitions. No new graph or scoring system.
- **Deterministic checks:** enumerate the same four pairings and compare valid-plan sets. Only cargo eligibility should differ for identical routes; paths, collision positions and simulation timings remain equal until an outcome terminates the run. Check no invisible package requirement or stale pickup after switching variants.
- **Human questions:** which version would they choose to play again, and why? Does cargo prompt a new useful inference or simply prohibit the attractive shortcut? Do they enjoy collection enough to justify its scanning/travel cost? Can they describe two safe package-free plans?
- **Retain/reject:** cargo can earn a place through a combination of added decisions and delivery satisfaction; it need not revolutionize every board. Do not claim increased puzzle depth if preference is only for the animation. Keep cargo optional if some boards benefit and others do not. Redesign or drop it if repeated trials add bookkeeping, confusion or waiting without compensating pleasure.

### Trial method and keep/drop decision

Start with about five new-to-cargo players, including at least two infrequent game players; separately include people using the intended accessibility interactions. This is a directional study, not statistical proof. A teaches everyone the rule; vary whether B or C appears next to reduce learning-order bias, and record that order. A short crossover can reveal preference, but reused geometry and remembered solutions confound completion-time comparisons. Use matched fresh layouts only in a later study if this bias affects the decision.

Record unassisted explanation, first plan, causal correction, assistance, time inspecting versus watching, Stop/Retry comprehension and voluntary desire for another board. Ask for preference and reasons after both versions; do not tell players that packages are expected to be better. No speed or star target is part of this experiment.

Proposed expansion gate: at least four of five explain pickup-before-home after A and can make a relevant B correction without solution coaching; at least three express interest in another cargo puzzle with reasons beyond “the next button is there”; no recurring inaccessible or misleading state remains. Treat a split B/C preference as evidence for selective use, not automatic failure. A successful script alone passes none of these human gates. Section 13 supplies the broader quality criteria.

## 6. Live-switch and deliberate-play recommendations

### Verified source baseline

MV-46's opening correction explicitly supersedes its older Rush tables. The current Rush JSON merges at (2, 2), its script taps at 4.95 seconds, and retained tests assert the corrected interval. The default-window tuples in `testMV46EveryStepOfMeasuredLiveWindowsWinsAndAdjacentStepsReject` are:

| Level | Current retained default tick interval | Simulation interval / width | Ideal continuous 2× wall interval |
|---|---|---|---|
| 6 Convoy | [272, 388) | [2.266667, 3.233333), **0.966667 s** | 0.483333 s |
| 9 Split | [192, 362) | [1.600000, 3.016667), **1.416667 s** | 0.708333 s |
| 11 Rush | [506, 609) | [4.216667, 5.075000), **0.858333 s** | 0.429167 s |

These figures are consistent with the current files and test assertions at `.default`; they were not freshly measured in this review. Bounds refer to eligible tick boundaries, with the end excluded. The test sweeps winning ticks and adjacent lock rejection. They do not measure cue recognition, touch latency, frame stalls, finger occlusion or any individual's response. A user's current experimental tuning may differ. Rush's old 2.183333-second interval and 5.25-second tap must not be presented as current Rush behavior.

The MV-46 speed/radius comparisons are also experiments, not approved tuning: slowing level 6 can narrow its interval because its departure offset remains fixed. Reducing a physical lock radius changes touch/vehicle semantics. Neither is a universal accessibility fix.

### Three future models

| Dimension | 1. Current real-time live switching | 2. Wider opportunities | 3. Pause / inspect / change / resume |
|---|---|---|---|
| Pleasure | Immediate agency and lively shared-route payoff; may reward execution after understanding. | Retains moving-world anticipation while reducing pressure. Repeatable opportunities can feel reassuring. | Emphasizes choosing and explaining an intervention; can interrupt the delight of uninterrupted motion if overused. |
| Accessibility | Narrow gaps may obstruct motor, attention and screen-reader operation even with good labels. | More recognition/activation time helps many players; no finite target proves nonvisual usability. Long loops can become tedious. | Stable board and route summaries allow inspection/focus. Pausing alone may still require catching a useful moment; validate this explicitly. |
| Engineering | Already implemented; no new work to preserve it. | Usually content-only through lengths, spacing or repeatable loops; optional cues are a small UI extension. Global speed/lock changes have broader consequences. | Moderate integration across engine command legality, frame driver, input order, UI, lifecycle, logs and accessibility; no movement rewrite. |
| Determinism | Same tuning/content/tick-bound commands reproduce outcomes. Wall-clock human taps are not equivalent replay inputs. | Same deterministic engine; new content needs new interval sweeps. | Freeze completed steps and accumulator; legal commands occur in stable order at a recorded boundary. Resuming must not apply paused wall time. |
| Locks | Ordinary frozen; live proximity locks; committed edges retained. | Same semantics. Broader geometry should create room, not silently waive locks. | Same run locks while paused. Paused must not act like plan phase and unlock all switches. A blocked van must move clear before a legal change. |
| Stars | Current configuration scoring remains. | No changes to existing stars/pars. New pars require real solution analysis. | Recommend equal completion and stars, no pause penalty. Pause is not a route change. Any future time-based records need separate semantics. |
| Existing twelve levels | Remain exactly as authored. | Do not widen them under this roadmap. Any later approved tuning/layout changes need their own regression and player review. | Can be trialled on unchanged boards in an internal mode. Broader inspection makes them easier to operate; geometry and legal solution space stay the same. Main-path adoption requires approval. |

**Recommendation: prototype deliberate play separately before adding more mandatory live-switch levels.** Compare current real time, forgiving repeatable content and deliberate operation on existing levels 8/9 plus corrected Rush or Convoy. Use the existing levels as fixtures, without overwriting them or their pars. Observe level 7 as the static comparison.

The smallest prototype offers an explicit Pause button, stable named route/status inspection, legal live-switch changes while paused, Resume and the existing separate Stop. Pause freezes motion, departure delays and any future signal clocks. Reset frame timestamps on pause/resume/background transitions; retain engine fractional time rather than accumulating a wall-time catch-up. Clear fast-forward on pause and make resumption speed explicit. Record pause/resume and command tick/order. Pausing on a physical lock must explain the blocking van and how to continue.

Do not declare the accessibility problem solved by that button. Test whether people can stop at a useful legal state. If they still know the plan but cannot reach that state, a second tightly scoped trial can add a controlled advance-to-availability action or short simulation-time advance while paused. Such an action must use the same engine, stop on failures, and reveal no predicted winning decision; it must not bypass locks. That additional control is contingent, not part of the initial package slice or a commitment to a scheduling UI.

For **new** live content, start authoring around at least three seconds of usable normal-speed opportunity following an understandable cue, and prefer another legal lap or indefinite inspection. This is a test target, not an accessibility guarantee or a new global tuning value. Measure actual useful time after competing pickup/delivery feedback and test fast-forward behavior. Do not assume a three-second simulation interval remains three wall seconds at 2×. Trial an explicit option to return to 1× around intervention, if needed; no automatic speed changes are approved here.

The approaches can coexist as one puzzle campaign with a player-selected deliberate control preference and occasional optional real-time mastery play. Do not present two game modes on first launch or require a faster mode for full stars. Keep the live/static visual distinction regardless of preference. A design requiring a narrow deadline should stay out of future mandatory progression until its intended control model is usable.

The package experiment remains independent: A/B/C have no live actions, so no concrete dependency requires waiting for this prototype or a global tuning decision.

## 7. Traffic-light evaluation

**Traffic lights remain worthwhile to investigate, but are not yet earned campaign content.** They can express admission and useful waiting in a way an exit switch cannot. Their cost is substantially greater than a visual lamp.

| Approach | Potential genuinely new decision | Overlap / failure risk | Recommendation |
|---|---|---|---|
| Automatic signals | Choose routes with respect to repeatable admission phases, or trade a safe wait against a longer route that changes downstream order. Waiting can occur mid-route, after different approach choices. | If all the light does is safely serialize the only crossing, it may remove the puzzle. Passive waits and phase arithmetic can replace insight. | Best first candidate; one later bounded experiment. |
| Player-controlled release | Decide which already-routed van enters first from a visible held state; can support deliberate dispatch without a tap deadline. | Indefinite holding can make “send each van home separately” universal. Making an order fail via a waiting van blocking an unrelated road is easy to misunderstand. | Defer pending a concrete board where order matters naturally. No committed manual-light chapter. |
| Planning-only choice | Select one of two initial phase offsets or first-served approaches, then execute a deterministic schedule. | Often equivalent to changing an authored departure delay. Permanently red is deadlock, not a puzzle. A schedule editor is disproportionate. | Compare conceptually or via a fixed-phase variant of the automatic trial. No standalone subsystem until the choice creates value. |
| Live signal changes | Request a future admission while vans are moving; could make a chosen route order tangible. | Adds controls, pending-state explanation and attention competition; can recreate narrow live switching. | Defer. If tested later, requests wait safely for clearance, with no mandatory rapid toggle. |

The distinctions matter: a switch chooses **where to go next**; a signal controls **when a van may enter a particular area**; departure delay controls **when the van first moves**. A mid-route hold can depend on which route it took and which other van occupies the crossing. That is a possible new relationship. It does not let one frozen shared switch choose different exits for two vans.

### One small future experiment — Wait or Wander

Use two ready-to-deliver vans, no packages or live switches, one automatic signal group with two exclusive approaches to a clearly bounded crossing, and one static short-route/bypass choice. If needed for real puzzle value, include **one clearly separate ordinary downstream crossing** where route/phase changes alter spacing. No queues, multiple signal groups or controller editor.

Target a board where the signal changes the useful route choice or creates two meaningfully different safe plans: a short route with a visible wait and a longer moving route with a different arrival order. The alternate route must be destination-valid; cargo completeness cannot decide the answer. Compare the same topology with the automatic hold absent and, cheaply, with the other initial phase offset. The chosen route's consequence should be explainable as “let that van clear first,” without counting exact seconds.

An acceptable stronger version makes one complete route pairing conflict at the ordinary downstream crossing while a different pairing works with the wait. Do not add that second crossing merely to make the signal seem necessary: if it cannot fit honestly in the board or players interpret green as protection there too, reject that version. A simple crossing where every route wins after automatic serialization is sufficient for an engineering fixture, but insufficient evidence for a signal puzzle chapter.

**Winning criterion for the idea:** players can predict a useful wait/order relationship, choose between genuinely different routes, understand the controlled area's boundary and prefer another such puzzle to an equivalent detour board. Two valid routes differing only by a few seconds of passive animation are weak evidence. If novelty requires unexplained downstream crashes, exact phase chasing or more traffic machinery, stop rather than rescue the experiment with scope.

### Minimum engineering contract if that experiment is approved

- Authored approaches reference directed edges and stop distances along their actual paths, plus a simple conflict area and phase table in positive integer ticks. One common schedule starts from its authored phase on Go.
- A red light consumes movement only up to its stop line. Held time builds no travel credit. On green, resume from that position; no overshoot or leap after a long wait.
- A held on-road van is an explicit physical state, distinct from current off-road departure waiting. It participates in moving/held and held/held collision checks and nearby switch locks. Initially place stop lines away from switches and forbid multiple waiting vans on one approach.
- Vehicles admitted under green finish clearing even if nominal red returns. Track occupancy until the van clears the protected area plus safe separation. All-red timing supports clearance but does not replace occupancy protection.
- Keep a **fixed nominal tick schedule** with occupancy as an additional admission gate. A blocked interval may be shortened or missed; do not drift later phases invisibly. Show effective permission, not nominal green when entry is denied. Useful intervals must be long enough that repeated skipped greens are exceptional; reject the board if not.
- Compute simultaneous permissions from one common prior-occupancy snapshot. Stable tick sequence: apply commands → evaluate nominal phase/effective safe admission → move and handle arrivals → existing arrival failure / collision precedence → update clearance for next tick → victory/events. No van may gain priority merely because its array entry was visited first.
- Signals protect their marked area, not every road afterward. Preserve ordinary collision behavior outside it and communicate that without a long tutorial. Avoid relying on surprise rear-end collisions into held vans.
- Previews remain spatial: show stop locations and “automatic wait,” not a promised exact timeline. Add distinct stop/go shapes/text and approach names. Requested/effective states are unnecessary until manual signals exist.
- Emit exact held/released/effective-phase ticks through the single dispatcher; reset schedule, held state and occupancy on Stop/Retry/Replay. Manual requests, if ever added, use one bounded pending desired group, not a request queue.

Test tick-before/at/after phase boundaries, zero-distance-at-line, large frame partitions, both approaches arriving simultaneously, green→red occupancy, conservative next-tick release, held collisions/locks, no waiting credit, reset, background/resume, renderer parity and deterministic replay. Include representative wrong route configurations to detect accidental queue needs.

This is a **moderate movement subsystem**, even with one light. If normal use requires queues, following AI, multiple reservations or permissive turning rules, it has exceeded this experiment. Traffic signals need no cargo dependency; doing them later is a value/cost priority, not a technical prerequisite chain.

## 8. Revised chapter and level progression

### How to read the numbers

All future numbers are **provisional design addresses**, not permanent IDs, guaranteed slots or validated layouts. Experiments 13–15 may become one or two campaign boards, become internal-only comparisons, or disappear. Accepted content will receive a contiguous display order later without changing already-earned level identities. A removed concept does not require a replacement.

The core path uses only accepted mechanics. Live content waits for its control gate; two-item content waits for its own trial. Signals never block finishing a good campaign. Keep a simple static or delivery-only respite after roughly two or three intensive boards, adjusting to observation rather than enforcing a formula.

### Flexible chapters

| Provisional region / chapter | Main challenge and genuinely new idea | Inherited concepts / important interactions | Approximate accepted count / difficulty | Memorable opportunities | Dependencies and playtest acceptance |
|---|---|---|---|---|---|
| **13–18 Parcel Row** | New optional pickup-before-home; then selective cargo changes another van's useful route. | Static forks, identity, directed travel, one crossing; mixed readiness. | **3–5**, excluding the matched control if redundant in campaign. Easy reset → first interaction → calm spatial board → composition. | “My pickup trip means Blue should go around”; visible collection and final unload. | Complete cargo slice and A/B/C gate. Players distinguish ready/needed and explain one coordination consequence. No live dependency. |
| **19–23 Shared Streets** | New reasoning emphasis: one shared physical plan and deliberate release; no new routing rule. | Pickup when useful, ready vans, committed edges, known loops/crossings. | **3–4**; shared static insight → recoverable release → quiet delivery → optional finite split. | A cargo-valid shared exit that both vans can use; waiting an extra lap succeeds. | Static boards can proceed immediately after cargo acceptance. Live boards require deliberate-play/fairness gate. Players explain shared settings and retained Retry. |
| **24–27 Canal Streets** | Spatial approach/return reasoning and recognizing which nearby places are actually connected. | Existing directed edges, distinct junctions, barriers/omitted links, optional cargo. | **2–4**; simple direction reset → route relation → spatial finale. | A return road beside the entry is a distinct junction; two coordinated safe tours. | Content and restrained sign/summary work. Players read direction and crossings correctly; no six-board quota and no dynamic closures. |
| **28–30 Collection Orders** | Conditional two pickups in either order; tour order affects a neighbor. | Fixed ownership, one terminal house, static configuration, route completeness and crossing spacing. | **0–3**; one collector → two valid orders → interaction. | Two complete tours with different crossing order; both-item unload. | Single-item gate, then two-item extension and legible either-order UI. Both orders must be actually realizable; players explain order without treating labels as mandatory sequence. |
| **31–38 Routes in Common** | Alternate complete plans and interdependent shared configurations; no required new system. | Accepted cargo counts, static shared exits, directed bypasses and optional deliberate live release. | **3–6**; easy remix → two safe plans → dependency chain, with a quiet board. | Two Good Plans; one van's route choice changes which bypass is useful for another. | Bounded configuration enumeration, alternate scripts and comparison playtests. Keep a level only if its inference differs from neighboring detour drills. |
| **39–44 Signal Square, optional** | Conditional automatic admission and route-versus-wait reasoning. | Directed paths, safe spacing, spatial previews; cargo unnecessary at introduction. | **0–3**, starting with one experimental board. One group only until earned. | Wait or Wander; initial phase variant that changes useful routing. | Section 7 engineering and human gates. If rejected, shorten the campaign; do not fill six slots or substitute loop repetitions. |
| **45–52 Old Town Dependencies** | Multi-step causal plans; no mandatory new mechanic. | Only retained systems; two interacting vans first, third only with a role. | **3–6**; pairwise reasoning → chain → readable mastery, with 1–2 quiet boards. | A clears B's road; B's chosen route establishes room for C. | Every van/control has a role; cause/fix remains explainable. Signals/multiple pickups are variants, not dependencies. |
| **53–60 Delivery Day** | Mastery, alternate strategies and a satisfying final composition; no new rules. | Accepted planning/coordination language and optional deliberate intervention. | **3–5**; confidence reset → mastery alternatives → quiet delivery → finale. | A compact two-episode finale, probably three vans; four only if clearly readable. | Sustained player interest, alternate-plan coverage, device/accessibility fit. Rehearsal is optional; end before 60 if stronger. |

These ranges intentionally do not add up to forty-eight new levels. They describe a pool of roughly 17–36 accepted candidates, with expansion beyond it earned by new puzzle ideas. The possible endpoint is a consequence of quality, not a target derived from this arithmetic.

### Detailed concepts — provisional levels 13–18

**13 — Pick Up First:** Experiment A, exactly as Section 5. Keep if needed as the short cargo introduction. One van, one meaningful fork; no extra barrier/second fork disguised as cargo depth.

**14 — Make Room for a Pickup:** Experiment B, exactly as Section 5. One pickup van and one ready van; two planning forks and one honest geometric crossing. Reuse ownership symbols here instead of spending separate campaign levels on two independent pickup copies and a wrong-owner visual trick.

**15 — The Same Streets:** Experiment C. A matched package-free control; likely internal-only after the experiment. If retained as a relaxing alternate-plan board, move it away from its identical cargo layout to avoid immediate repetition. Do not sell a repeated control as guaranteed campaign content.

**16 — Around the Block:** one pickup van, one house, a directed approach that reaches the pickup from the far side, and a distinct downstream return junction. About 1–2 static choices, no traffic deadline. The nearby apparent reverse link is visibly absent; no fake road or hidden cargo-sensitive exit. Select the valid approach and the homeward route. Wrong choices produce a clearly labeled loop or barrier, not a surprise wrong owner. This combines V1's downstream-home reinforcement with early direction teaching. Validate pickup→house reachability and every small static setting. Retain only if it supplies a spatial insight or a welcome easy board; it is not another required pickup tutorial.

**17 — Shared Choice:** delivery-only, two vans, two houses, one shared static fork with a common safe exit, and a distinct downstream bypass/house routing arrangement. Plan the one exit both can actually use; do not assume different static settings per van. Target two coherent safe configurations using companion downstream choices, rather than one “designer answer.” No live actions, no cargo. Test all configurations and at least two complete scripts before calling it an alternate-solution puzzle. This moves the strong V1 level 50 idea forward and provides cargo relief. If the alternate-plan geometry cannot fit, retain a single clear shared-setting lesson and move alternatives to 26.

**18 — Neighborhood Round:** two vans with one pickup each only if ownership remains legible; otherwise one pickup and one ready van. Each complete tour offers a meaningful downstream route option before one crossing. Both-short is cargo-valid but conflicts; a complementary pairing gives broad clearance. Do not let a missing-pickup preview choose the whole traffic answer. Approximately 2–3 static decisions; no live input. Enumerate valid pairings, test cargo independently from collision, and include at least one omitted-choice failure for each relevant decision. This is a small composition anchor adapted from V1's strongest early package board. Keep it only if it differs meaningfully from B: both tours and their choices must matter, not merely repeat Red pickup + Blue detour.

No new par is specified here. Future authors establish feasible geometry, valid strategy sets and a provisional minimum before stars are reviewed. Do not change the twelve existing pars.

### Proposed progression — provisional levels 19–30

| Slot / concept | Clear puzzle objective and interaction | Intended success / important negative case | Dependencies and disposition |
|---|---|---|---|
| **19 Leave Loaded** | One van collects inside a loop, then deliberately chooses home. Cargo state is a durable release cue. | Let pickup occur, select home while away from the live fork; later laps also win. Early home lacks cargo; never release remains unfinished. Retry's retained home exit is explicitly tested. | Cargo + approved deliberate/live controls. Keep as a short bridge only if it teaches more than controls already learned. |
| **20 Collect, Then Clear** | One pickup-loop van waits for a ready van to clear its release crossing. | Release on either of at least two later safe laps; first-pass release can conflict. Extra lap is allowed, never a hidden failure. | Combines V1 20/23. One live control, broad/repeating opportunity; no signals. Drop rather than add a second nearly identical loop board. |
| **21 A Quiet Delivery** | Relaxed static matching on two short separate routes; no cargo or shared crossing. | One or two obvious corrections, then uninterrupted paired payoff. Wrong house/barrier is understandable. | Content only. Preserve its relief even though it adds no rule. No deceptive difficulty from extra taps. |
| **22 Commitments** | Two vans need opposite exits of one shared live fork; no pickups unless they create a distinct route choice. | Prepare for the first van, change after it commits and clears, before the second. Earlier van keeps its edge. Early/late/locked/no-input variants explain the rule. | Move V1 21/52 here after recoverable loops and quiet board. Mandatory only if deliberate control is usable; otherwise keep as an optional internal/challenge candidate. |
| **23 Saturday Deliveries** | Two-van composition: one static route dependency and one already-known deliberate intervention. | Choose the complete safe routes, then one cued release/split. The two choices must each have a clear reason. | Simplify V1 24 to two vans. No independent Yellow unless observation shows added payoff without attention cost. May be omitted if 20/22 already provide the same experience. |
| **24 Follow the Arrows** | Calm spatial reset: reach one pickup through its legal directed approach. | Go around the block and return through a distinct junction. Apparent nearby reverse travel is visibly unavailable. | Existing direction + optional cargo. Use either this or 16 if they teach the same inference; not both by quota. |
| **25 Works Ahead** | Find a valid delivery route around an honestly absent connection or barrier spur. | Choose a route that still reaches the house; if cargo is used, make its position change the useful alternative. | Content only, small optional sign/route-description work. No drawn closed through-edge that the engine still traverses; no dynamic closure rule. |
| **26 Two Good Plans** | Find coherent companion settings for two vans, with at least two safe complete strategies. | Either van can take the alternate corridor if the other selections match; mixed companion choices collide or misroute. | Moves V1 56 forward. Record both strategies and all small static outcomes. Different final configurations alone do not prove different strategies. |
| **27 Canal Circuit** | Combine direction and route compatibility at two spatially distinct crossings, without a live deadline. | Whole-route choices separate each conflict; one tempting local shortcut breaks the second relationship. | V1 26/29/30 synthesis, initially mixed or no cargo. Reduce to one crossing if two cannot be read; skip if it only repeats 18. |
| **28 A Pair of Parcels — experiment** | One van needs two fixed-owner pickups, either order, before one house. | Choose a complete tour; one-item shortcut exposes the remaining item. | Conditional two-item extension. Zero traffic initially. Distinct item names, explicit “either order,” count/remaining summary. No inventory capacity. |
| **29 Either Way Round — experiment** | Demonstrate two genuinely different complete pickup orders rather than a forced chain. | A→B→home and B→A→home both work under different complete switch plans. A wrong setting may cycle safely; Stop remains clear. | Both orders must be realizable with static shared selections and distinct directed corridors. A fixed plan cannot revisit a node and depart differently. If pickup/switch colocation is needed, explicitly validate presentation rather than hiding it. |
| **30 One Collector, One Neighbor — experiment** | Two-item order changes a second ready van's useful route or crossing relationship. | Both orders collect everything; only a compatible route pairing clears the crossing. Accept all safe pairings. | Adapt V1 45; a true depth test. Compare with two routes to a single pickup. If no new inference or marker fit, omit 28–30 and continue with accepted one-item content. |

A/B/C acceptance does not pre-approve all these boards. Author anchors 18, 20 and 26 before filling gaps; retain at most the distinct lessons and desired pacing. Static spatial boards can move ahead if new live content is still under evaluation.

### Flexible horizon — provisional levels 31–60

The chapter table defines dependencies/counts/gates. Promising individual anchors below are candidates inside those regions, not a request to author every intervening integer.

- **31 Familiar Streets:** easy mixed-cargo/static reset after any two-item trial. No new rule. Omit if 28–30 never enter the campaign and no reset is needed.
- **33 Shared Choice, Deeper:** two vans approach one frozen setting from different routes; choose a common exit and complementary downstream bypasses. Use this only if it adds a new relationship beyond 17/26.
- **35 Two Ways Home:** equal-completion alternatives with different delivery orders, neither requiring a deadline. A useful mastery revisit without a new medal system.
- **37 Waiting Is Working:** one repeatable deliberate release variant only if it differs from 20, for example the player chooses which of two complete approach routes enters the holding loop. Do not repeat the same loaded-loop release with more scenery.
- **39 Wait or Wander:** Section 7's automatic-signal experiment, internal until accepted. The surrounding region may contain only one or two further signal boards, or none.
- **42 Phase and Path:** conditional fixed initial-phase variant of the same signal group. Retain only if route reasoning changes, not merely wait duration. No manual controls by default.
- **45 Who Shares This Road?:** delivery-only two-van shared setting puzzle to reset visual load. The decision concerns common topology, not another required long route.
- **48 Town Routes:** strongest V1 54 dependency chain, introduced with two relationships and then possibly a third van. Every participant must constrain a meaningful part of the plan; an independent passenger is optional spectacle, not depth.
- **51 Postcard Delivery:** one van, simple static route and one satisfying unload. A quiet level between mastery boards is intentional.
- **54 Two Good Plans, Mastered:** an alternate-strategy anchor using only retained systems. One route family may use a deliberate hold and another static spacing, if both can be understood and validated. Equal completion recognition.
- **57 Set the Order:** arrange an interesting delivery sequence through existing paths or an approved repeatable hold. Accept other safe orders; no mandatory priority-delivery rule is smuggled in.
- **60 TinyRoutes:** compact final composition in two visibly separated episodes. Prefer three readable vans. Four are justified only if the last van contributes a clear relationship and markers/controls remain legible. One intervention at once; no new mechanic. Combine rehearsal and finale if they are substantially the same puzzle.

### Disposition of V1 concepts

| V1 levels | V2 action / reason |
|---|---|
| 13 | **Retain** as A: simple cargo reset is strong. |
| 14–16 | **Combine** homeward reinforcement and ownership into A/B/16. **Remove** two independent pickup copies and proximity bait as guaranteed separate lessons. Optional reinforcement only if needed. |
| 17 | **Replace central choice** with B's change to the other van's route. A forced cargo detour that also happens to avoid a crash does not independently test coordination. |
| 18 | **Retain and test early**, then differentiate the later composition from B. |
| 19 | **Retain conditionally** as loaded release with repeatable opportunities and Retry comprehension. |
| 20/23 | **Combine** into V2 20; keep the permission-to-wait lesson once. |
| 21/52 | **Combine/move** to V2 22 after recoverable release. Cargo optional. |
| 22/41/47/55 | **Preserve pacing roles**, often package-free; remove their rule-teaching obligations. Do not retain all if redundant. |
| 24/53/58 | **Reduce vehicle padding**. Two interacting vans first; third only if useful or clearly valued spectacle. |
| 25–30 | **Compress/move** direction earlier; retain selected spatial anchors at 16/24–27. Combine entry/return and frozen-switch limitations into a positive route insight. |
| 31–36 | **Defer/compress** to one automatic trial and up to two earned follow-ups. Remove guaranteed second signal group. |
| 37–42 | **Remove as a committed chapter**. Requested/effective release is engineering behavior, not by itself a puzzle; blocked-bay dispatch remains a later hypothesis. |
| 43/47, 44/45 | **Move experiment earlier** to 28–30: completeness, alternate order, meaningful neighbor interaction. **Combine** duplicate completeness lessons. |
| 46/48/49 | **Combine or remove** repeated far-first/detour assignments unless their causal relationship is distinct from 30/18. |
| 50/54 | **Retain anchors**: shared choice moves earlier to 17/33; dependency chain remains a later payoff. |
| 51 | **Merge its recoverable-loop purpose** into 20 or one differentiated mastery board. |
| 56 | **Retain and move forward** to 26; alternative plans should not wait until the finale. |
| 57/60 | **Retain intent**: compose order through familiar rules, then a readable finale. No new priority/deadline system. |
| 59/60 | **Combine if redundant**. A rehearsal is optional, and four vans are not a finale requirement. |

## 9. Replayability and scoring strategy

Replay value should come from understanding a different plan, refining a meaningful decision, or enjoying a short mastered run. More levels alone supply length, not replayability.

| Candidate | Value / practical use | Recommendation |
|---|---|---|
| Multiple valid routing strategies | Different safe corridors or companion settings reward exploration and reduce “guess the author's answer.” | Introduce by 17/26; enumerate small spaces and preserve several scripts. Accept surprising valid plans that preserve the rules. |
| Different optimal solutions | Two efficient plans with different tradeoffs can sustain mastery. | Test after route families exist. “Optimal” needs an explicit metric and evidence; different tap sequences ending identically are not necessarily different strategies. |
| Optional efficiency goals | “Use the shorter total driven route” or “finish without a holding lap” may support a voluntary second solve. | Later local experiment on one mastery board. Goals must be legible and compatible with assistance; no new global score economy. |
| Alternate delivery orders | Seeing either van lead can be satisfying and changes how the board is read. | Accept all safe orders now; use existing routes to create variation. An optional “try the other order” prompt can precede any formal badge. |
| Stars for meaningful decisions | Existing stars provide a familiar completion/mastery signal. | Preserve current behavior now. Review the future contract before signals, deliberate holds or optional optimization become scored campaign content. |
| Short challenge / mastery boards | Compact known-rule puzzles can invite voluntary replays without a large chapter. | Prototype one with two coherent solutions; observe actual revisits and reasons. No daily service, timer or leaderboard required. |
| Watching the payoff again | A playful successful run can be its own reward. | Keep Replay and make short known runs pleasant. Do not infer durable replay value solely from celebratory animation. |

### Is `changeCount` appropriate?

It is a consistent measure of **current configuration distance** from authored settings. It is suitable for some static boards, although it measures relation to the initial plan rather than route distance, traffic elegance or total effort. It is not a general execution-efficiency metric. Returning a live switch to its starting exit reduces the score even after several accepted taps. Existing Rush/Big Delivery scripts use five/seven physical inputs but finish at change counts three/five.

Cargo introduces no new player action, so the package trial can keep existing scoring without a new formula. Do not base its acceptance on stars or assign minimum pars from an unverified sketch. Trials should log physical tap count separately from `changeCount` and avoid optimization pressure.

A **future scoring review is warranted before scoring new control types or making mastery a major product promise**. Compare a configuration objective, a clearly named route-efficiency objective, and actual accepted actions. Reject raw action count if it discourages safe exploration or makes accessibility operation cost stars. Do not score pause/resume or reject taps. Do not combine unrelated quantities into a hidden weighted score.

Preserve all existing pars, stars and records now. Any new scoring contract needs owner approval, player explanation and record/content-version compatibility. A historic three-star completion remains earned; do not silently downgrade it. Time optimization, if ever used, measures simulation-time route consequences and states how deliberate holds are treated; human inspection speed is not a default skill test.

## 10. Production migration strategy

### 10.1 Current implementation versus remaining decisions

**Promotion has already been implemented in the working tree. Shipping status is unknown.** `ContentView` uses `MultiVanLevelRepository`; the main map accepts Multi-Van levels; `LevelPlayScreen` creates a Multi-Van engine, persists best stars/completion/unlocks and awards existing completion rewards. The twelve canonical IDs are already `level_001`…`level_012`. This is source evidence, not evidence that an App Store or TestFlight audience received it.

The older `RouteEngine`, `LevelData`, repository and supporting code remain. The inspected current app resource tree contains the twelve Multi-Van level files; the former 27 production JSON levels are not present there. Historical generated previews are not a substitute for preserving the exact old playable content. Do not claim that an intact archived 27-level implementation/content snapshot has already been verified.

The most consequential migration behavior is in `PlayerProfile.normalized()`:

- For a decoded profile below schema 3, clear unlocked/completed IDs, stars and fastest times, reset to the first level and remove `levelComplete:` reward claim keys. Other profile fields remain, subject to normal normalization.
- `SaveDataRepository.load()` returns that normalized profile without immediately rewriting an existing profile blob; a subsequent update/save persists normalization and can overwrite the old records. There is no inspected archive of the removed progression in this path.
- The separate stars-only import creates a default current-version profile and copies the unversioned dictionary. Consequently old stars can be treated as new Multi-Van stars. This source-supported risk also affects future IDs 13–27 if imported legacy records remain in active maps. It is not evidence that a particular user's save was affected.

Never equate old level 7 with new level 7 because their strings match. Do not promise recovery of data already overwritten without a retained backup. This document changes none of these behaviors or any saved data.

### 10.2 Recommended staged order

| Stage | Concrete future work | Decision gate / safe outcome |
|---|---|---|
| **P0 — Establish release and preservation facts** | Determine whether schema-3/Multi-Van builds have reached players; identify the exact previous production source and 27 resources from retained history/artifacts. Preserve a reproducible legacy snapshot, including schema and solution evidence, outside normal discovery. Retain the current implementation too. | An owner-reviewed inventory identifies what exists, which save populations exist and what can actually be recovered. No cleanup or data rewrite before this. Package experimentation can proceed independently. |
| **P1 — Agree on campaign identity and progress policy** | Treat campaign identity + stable level ID as the logical key, even if existing active maps remain simple. Preserve genuine schema-3 Multi-Van records. Archive legacy stars/completions/times/reward claims under legacy campaign identity rather than assigning them to new puzzles. Choose how archived achievements appear, if at all. | Approve what “preserve progress” means: keep earned history and account value, without claiming old puzzles solve new ones. No automatic star conversion is recommended. |
| **P2 — Make save transition non-destructive** | On a future migration, durably preserve raw supported old payloads before normalization and writing the new format; include the separate legacy-stars source. Make migration idempotent and interruption-safe. Retain unsupported/corrupt payloads for recovery instead of silently overwriting them with fresh defaults. Version the active campaign association. | Fixture tests cover old structured profiles, stars-only saves, empty/corrupt/unknown versions, repeated migrations and interrupted writes. Raw archive success precedes destructive replacement. No current-device settings/data are used as test fixtures. |
| **P3 — Verify the already-promoted twelve-level campaign** | Keep current levels and intended scripts unchanged. Verify main navigation, unlocks, Next after 12, Replay, reward idempotency, settings, app lifecycle and both boards. Check the release build excludes developer controls. | Existing Multi-Van stars remain, old stars cannot grant new completions, normal users see one coherent campaign, and no duplicate rewards/unintended locks occur. Human onboarding/timing/accessibility limitations are explicitly addressed before broad release. |
| **P4 — Roll out the main campaign** | Use an internal/release-candidate upgrade rehearsal and attributable device playtests, then an owner-approved staged release if applicable. Provide concise returning-player explanation of the new campaign and retained account items/history. | Release readiness is established without waiting for packages or sixty levels. If the source transition has already shipped, use a forward compatibility repair; do not pretend to rerun a clean prelaunch migration. |
| **P5 — Integrate accepted package content** | Only accepted experiment outcomes enter the main catalog. Assign stable canonical IDs and an explicit ordered campaign list if order must differ from ID sorting. Add package-capable content version checks, solutions, validation and progression coverage. | Current 1–12 records/pars remain valid; trial wins did not grant production rewards; completing 12 unlocks the first accepted addition on upgrade. No chapter of untested experimental files is exposed automatically. |
| **P6 — Retire obsolete code deliberately** | After retention/rollback needs end, audit callers, tests, editor/generator tools, shared geometry/models and bundles. Remove only unreachable obsolete gameplay pieces in a separate change. | A retained legacy artifact remains reproducible, no required tool/shared dependency is removed, and new runtime behavior remains stable. Do not delete tests simply because old levels are hidden. |

P0/P1 are high-priority planning/compatibility work now because promotion exists in source. P2/P3 should precede any further rollout to legacy players. They do not block the internal package trial. P4 may ship the twelve-level game before or after the accepted small package pack, based on readiness; neither mechanic acceptance nor level 60 is a prerequisite for migration safety.

### 10.3 ID, save and upgrade details

- **Keep current Multi-Van identities stable.** Do not renumber 1–12 to solve a collision retrospectively. Add a campaign association to progress/archive/reward identity at the save boundary. Display numbers and chapter membership may change independently of stable IDs.
- **Legacy history is history.** Archive all 27 old records when available, including earned stars and times; do not map them onto new objectives. New-campaign completion begins from its actual earned records. A separate courtesy unlock policy is an owner choice, never disguised as earned stars.
- **Preserve account value.** Carry name, dates, coins, cosmetics, entitlements, streaks and relevant daily-bonus data under their existing semantics. Keep already-owned items; introducing cargo does not create a new economy. Review reward claim keys so campaign separation neither suppresses legitimate new rewards nor grants repeat rewards on upgrade/replay.
- **Already-written schema-3 profiles need provenance caution.** If old records were imported through the stars-only path, matching IDs may be ambiguous. Do not wipe all schema-3 stars to repair that ambiguity. Use retained origin/build evidence where available; otherwise require an explicit owner-approved recovery policy and preserve questionable history separately. Data already erased cannot be reconstructed by schema design alone.
- **Appending content must unlock it for eligible existing players.** Today `completeLevel` unlocks the supplied next ID when a win is recorded. A player who completed 12 before 13 existed may never have received that ID. Add a narrow idempotent catalog-upgrade entitlement check or equivalent reconciliation based on valid completion, not a requirement to replay 12. Do not grant stars for the new level.
- **Experiment IDs must not become accidental campaign records.** Use explicit internal discovery, separate logs and no calls into `ProgressService`/completion rewards. On acceptance, map content into its permanent campaign identity; do not migrate experimental completions as stars.
- **Hide the old campaign from normal selection.** Preserve it in an archive/reproducible development context, not as a competing initial mode. Existing old resource discovery also scans bundle-root JSON; verify that archives and package fixtures never enter either normal repository accidentally.
- **Keep tuning isolated.** The main host currently uses `.default`; internal Debug sessions inject overrides, and the prototype entry is gated by Debug/internal compilation. Preserve that separation. Log the effective internal snapshot; do not copy debug overrides into production preferences or reset the user's settings as part of migration.

The simplest safe architecture is a concrete active Multi-Van catalog and a preserved legacy record/snapshot boundary. No common engine adapter, dual-mode product UI, generator rewrite or abstract campaign platform is required.

## 11. Architecture changes and dependencies

### 11.1 Engineering impact by proposed mechanic

Impact includes schema, validation, UI, authoring and tests, not just the number of movement lines changed.

| Mechanic / capability | Classification | Minimum scope and principal risks |
|---|---|---|
| New static forks, shared exits, route-length spacing, authored departure order | **Level content only** | Existing rules. Joint solvability, plausible alternatives, path clearance and human explanation still require verification. Players do not currently edit departure delay. |
| Directed approaches and honest static barriers/absent connections | **Level content only**; **small extension** for better signs/summaries | No dynamic blocked-edge state. Avoid visual false connections and nonvisual ambiguity. |
| Wider or repeating live opportunities through layout | **Level content only** | Requires engine-derived interval sweeps and device operation; slowing everything is not an equivalent change. No change to existing twelve levels. |
| One fixed-owner package | **Moderate subsystem** | Arrival lifecycle, missing outcome/status, hypothetical preview, reset, renderer/UI/accessibility, validation/events/logging. No movement physics change. |
| Two owned packages, either order, one final house | **Small extension after cargo**; moderate from today's engine | Raise supported item count only after approval; count/remaining UI, both-order layouts, partial delivery rejection and marker density. No slots/capacity. |
| Pause / inspect / legal change / resume | **Moderate subsystem integration** | Clock/frame lifecycle, legality in paused run, stable focus and replay inputs. A paused Boolean alone does not establish usability. Optional controlled advance adds bounded further scope. |
| Alternative safe route strategies | **Level content only** | Search/enumeration and multiple scripts. Do not introduce special win predicates solely to force the preferred answer. |
| Optional local efficiency goals / revised stars | **Small extension** for one goal; **moderate subsystem** for a new persisted scoring contract | Goal clarity, actual optimality, record/version compatibility and accessibility. Preserve current scoring now. |
| Automatic signal / timed intersection | **Moderate subsystem** | Stop-line movement, held physical state, phase ticks, occupancy, admissions, preview markers and validation. One subsystem, not separate light and timed-junction features. |
| Planning initial phase choice | **Small extension after signals** | One explicit initial choice, resetting predictably. Requires a decision beyond authored delay; no schedule editor. |
| Manual or live signal requests | **Moderate subsystem extension** | Typed input, bounded pending state, safe effective release, scoring/UI. Deferred until automatic value and control accessibility pass. |
| Static priority / relative delivery order | **Small extension** | Explicit precedence and same-tick semantics; changes objectives and may restrict enjoyable alternatives. Deferred, optional experiment only. |
| Deadlines / expiring cargo | **Moderate subsystem** | Timed failure, UI pressure, accessibility and scoring conflicts. Deferred; not needed to create progression. |
| Different van speeds | **Small movement extension**, moderate overall | Relative timing, catch-up collisions, live windows, displacement bounds, UI identity and every script margin. Use existing paths/delays first. |
| Dynamic closures / one-use roads | **Moderate subsystem** | Edge availability actually enforced per traversal, committed-edge policy, preview, graph validity and resets. Existing shared fields do not implement this in Multi-Van. |
| Coupled / conditional / cargo-sensitive switches | **Moderate subsystem** | Shared selection atomicity, per-van eligibility, lock scope, preview and control explanation. Defer until a specific puzzle cannot be expressed simply. |
| Multiple destinations / intermediate unloading | **Significant architectural change** | Houses currently terminate motion and parking removes collision participation. Needs service versus terminal destinations, partial work and revised win/feedback. Deferred. |
| Shared-stock assignment, transfers, cargo races | **Significant architectural change** | Ownership competition, transactions, objectives and UI memory. Fixed ownership avoids these concerns. Deferred. |
| Queues, following traffic, lanes/overtaking, many interacting signal reservations | **Significant architectural change** | Changes physical occupancy and traffic expectations. Outside the recommended roadmap; never add to rescue the first light trial. |
| Production progress preservation / campaign catalog | **Moderate subsystem**, data-sensitive | Already-partial integration, reused IDs, legacy archive, idempotent upgrade, rewards and append unlocks. Separate from gameplay mechanics and engine schema. |

No approved direction demonstrates a need for a full engine rewrite. The current engine is the preferred authority throughout.

### 11.2 Cross-cutting hazards and required safeguards

| Area | Confirmed boundary / risk | Recommended safeguard |
|---|---|---|
| Determinism | The UI frame driver clamps real frame stalls to 0.25 seconds; the engine retains all time it receives. Equal wall elapsed time across arbitrary frames is not a deterministic-input promise. | Compare equal tick command streams/content/tuning under varied partitions; capture local transition ticks. Keep gameplay timers out of views and animation callbacks. |
| Preview | Currently spatial and cached by final edge/status changes. | Trace temporary cargo state, invalidate on objectives, preserve committed edges, and never promise collision safety. Future signal summaries disclose waits rather than forecasting unknown actions. |
| Collision / arrival ordering | Driving-only distance sampling and authored tie order; arrivals can precede collisions and emit delivery on a failed attempt. | Pin feature-disabled traces. Package events preserve ordering. Signals deliberately add held pairs and snapshot admission; do not silently change old precedence. |
| Sampling bounds | Default van travel is 0.0125 units/tick; pair closure can be 0.025 versus threshold 0.35. This is not proof of continuous grazing-collision detection. | Retain current method for unchanged rules. Reassess bounds only if speed, radius, teleports or geometry assumptions change; add swept checks only for a demonstrated problem. |
| Graph validity | A frozen selected exit is shared. Re-entering a node under the same configuration repeats its future, regardless of newly acquired cargo. Geometry can collide without a shared node. | Validate realizable complete tours and joint scripts, not just independent reachability. Do not author “collect then take another exit” without an actual live change or distinct return junction. |
| Serialization / feature boundary | Optional fields can be ignored by older decoders. Multi-Van currently decodes rather than comprehensively validating on load. | Explicit supported feature version, focused load-time checks before play, compatible bundled content, and ordered exits. No generic rules registry or remote format platform. |
| Save compatibility | Content/profile versions are different; old and new IDs collide; appending a level does not necessarily unlock it for existing finishers. | Campaign-aware archive/progress boundary, preserve genuine records, idempotent reconciliation and upgrade fixtures. No partial runtime save for cargo. |
| Test infrastructure | Tests pin a twelve-file corpus and scripts; current historical MV-46 results are not fresh evidence. | Keep original corpus as a regression set and add an explicit trial set. Verify the intended current test route during implementation; historical notes about duplicate declarations/skipped bundle checks are limitations to check, not a reason to discard coverage. |
| UI complexity | Two real renderers, symbols, routes, cargo and future lights compete for one board. | Add engine-derived state to both, parity assertions and actual smallest-phone checks. Reduce entities before controls. Do not add a second gameplay authority to the browser visual reference. |
| Accessibility | Labels and symbols exist; graph comprehension and live operation remain unproven. | Named route/objective relationships, stable focus, meaningful status inspection and real device testing with intended users. Wider windows alone do not establish access. |
| Logging | Dispatch timestamps are not arrival ticks; default main host lacks logger; event rows may truncate. | Internal experiment host, explicit variant/build/tuning metadata, exact semantic ticks, initial/Go configuration, assistance and omission handling. Pair logs with observed reasoning. |

### 11.3 Dependency sequence for small later Codex tasks

Each row is a potential approved task boundary with an observable output. It is not a task file or authorization to start.

| Task boundary | Depends on | Reviewable output / meaningful verification |
|---|---|---|
| **C1 Cargo definitions and content checks** | Approved one-item contract | Backward-compatible decoding, derived requirements, focused validation and invalid fixtures; twelve original files unchanged. |
| **C2 Engine lifecycle and arrival** | C1 | Collection/missing/success/reset state and exact transition metadata, local transaction handling; independent/same-tick/leftover-distance and legacy regression evidence. |
| **C3 Cargo-aware preview** | C1–C2 | Pure hypothetical objective trace, missing ending, committed-edge and invalidation behavior; no engine mutation and traversal/preview agreement. |
| **C4 One playable A in internal host** | C1–C3 | Flat+diorama marker/carrying state, summary/chip, feedback/failure copy and all reset actions; device review plus deterministic A script. |
| **C5 B/C and attributable trial** | C4 | Matched internal boards, four-setting outcome maps, logs/metadata and qualitative observations; explicit keep/redesign/drop decision before campaign authoring. |
| **D1 Deliberate control prototype** | Approved control contract; existing engine | Pause/resume legality, frame timestamps, stable inspection/focus and logged command order on unchanged existing fixtures; no cargo dependency. |
| **P1 Preservation/progress audit and migration implementation, separately approved** | Release facts and owner-approved data policy | Saved fixture matrix, archive/idempotency/reward/unlock checks and release build verification. Can proceed alongside C/D; required before further rollout to legacy players. |
| **L1 Accepted small content pack** | C5 acceptance; D1 only for live boards; production gates for release | A few distinct levels, complete scripts/negative cases, alternate strategies and device/accessibility review. No automatic 13–30 build-out. |
| **C6 Two-item trial** | Stable accepted C5 cargo | Two counts/orders, readable summary and B/C-style value comparison with a neighbor; no signal dependency. |
| **S1 One automatic signal trial** | Approved Section 7 contract; stable engine; gameplay priority decision | Held occupancy/admission tests and one worthwhile playable comparison; no cargo or two-item technical dependency. |
| **R1 Mastery/scoring review** | Actual alternate-solution boards and observations | Clear proposed objective/record policy and one optional goal trial; preserve historic stars. Manual signal scoring waits for this decision. |

Do not turn these boundaries into interfaces/services in advance. Reuse the existing graph/path/board/event seams. Share a small pure rule when engine and preview actually need it; keep the native engine authoritative.

## 12. Implementation phases and milestones

All implementation below is proposed for later approval. Current tuning work continues under its existing scope; this roadmap does not replace or freeze the owner's tuning choices.

| Phase | Scope | Exit milestone / decision |
|---|---|---|
| **0 — Direction and compatibility facts** | Owner reviews this document; identify rollout/save populations; observe current static/live comprehension when practical. No requirement to finish a global tuning pass before cargo. | Cargo/control contracts selected; current migration risk and preservation source understood. No engine rewrite or chapter commitment. |
| **1 — Bounded cargo experiment** | C1–C5 only: zero/one assigned package, complete preview/reset/presentation, A/B/C internally. | Engineering acceptance plus player-value decision. Accept selective cargo, revise once for a diagnosed issue, or stop. No campaign JSON expansion merely because code passes. |
| **2 — Deliberate-play experiment** | D1 on unchanged current boards, alongside or after Phase 1 according to available effort. | Determine whether deliberate inspection improves agency without destroying run satisfaction, and whether finite live gaps remain a barrier. Required before new mandatory live content, independent of static cargo. |
| **3 — Complete production safety / release readiness** | P0–P4 in Section 10, begun early because source promotion already exists. | Preserve recoverable history and genuine new stars, prevent false imports, validate upgrade/rewards/unlocks and release controls. Decide whether to release twelve levels or add an already-accepted small pack. |
| **4 — Earn a small expansion** | Select a few 13–27 concepts around strong anchors; add only distinct puzzles and quiet pacing boards. | Players understand failures and ask for more; each retained level has a purpose. Accepted package content integrates through P5. Stop at a coherent smaller campaign if appropriate. |
| **5 — Test collection order** | C6: up to three internal concepts corresponding to 28–30. | Two-item order adds usable spatial reasoning and an interaction beyond extra errands. Otherwise stay with zero/one. |
| **6 — Optional automatic-light trial** | S1 only; no manual chapter. | A new admission/route choice earns the subsystem. If not, remove the optional region and continue mastery content with existing rules. |
| **7 — Mastery and selective growth** | Alternate plans, dependency chains, a few short replay boards and readable finale; scoring review only for an identified need. | Strong retained campaign and replay evidence, with no obligation to reach 60. Legacy cleanup is a separate final task after preservation/compatibility needs end. |

### First three implementation milestones proposed

1. **M1 — Deterministic cargo core:** C1–C3. Old files still decode and behave identically; ownership has one lifecycle authority; missing cargo is distinct; previews simulate hypothetical cargo correctly. This is the minimum trustworthy foundation.
2. **M2 — Complete three-board pickup trial:** C4–C5. A/B/C are playable internally with both board styles, clear statuses, complete resets and attributable logs; enumerate configuration outcomes and then gather human feedback before expanding.
3. **M3 — Deliberate-play controls trial:** D1. Pause/inspect/legal change/resume on unchanged timing fixtures, equal proposed star treatment, no catch-up and real accessibility operation checks. Results govern new live puzzles, not whether M2 may happen.

Production preservation is an independent early workstream and a rollout gate. It should not be delayed to M3 if a legacy-player release is imminent. These milestone labels describe reviewable chunks, not calendar estimates or an instruction to run work in parallel agents.

## 13. Playtesting and quality gates

**Engineering acceptance and human acceptance are separate.** A deterministic win proves a route/input sequence works. It does not prove readable objectives, fair input, interesting decisions, satisfaction or replay desire. No player statistics or enjoyment claims are fabricated here. The assessment records historical engineering runs and later Rush readability feedback, not a complete attributed usability dataset.

### Shared engineering and content gate

Before an experimental board is evaluated as gameplay, it needs supported decoding/validation, intended positive and representative negative scripts, reset/lifecycle invariants, frame-partition replay, accurate previews, both renderer state representations, intelligible failure copy and controls that can be operated on the target device. Timed content also needs full useful-interval sweeps and boundary rejection tests. Small static graphs should enumerate their configurations rather than merely verify one author solution.

Before campaign acceptance, additionally verify content/solution coverage, valid permanent identity, version compatibility, correct unlock/reward behavior and a main-path accessibility/control model. Prove known alternate strategies with scripts; do not impose uniqueness unless the lesson genuinely requires it. No near-miss route should be labeled robust from rounded diagram distances.

### Experiment-specific decision gates

| Major experiment | 1. Engineering acceptance | 2. Gameplay behavior acceptance | 3. Human questions | 4. Accessibility concerns | 5. Expand when… | 6. Redesign / abandon when… |
|---|---|---|---|---|---|---|
| **A: basic pickup** | Both route outcomes correct; preview pure; one pickup/delivery; no missing-cargo delivery credit; all resets restore one item. | The visible branch choice teaches pickup-before-home and ends in a readable payoff. | “What must happen before home?” “What changed at pickup?” “What would you change after this failure?” | Stable chip/summary; symbol not obscured; collection understandable with no sound/motion. | Players understand the rule and operate the board without solution coaching. | Repeated confusion survives simpler status/markers, or mandatory extra travel is the only effect people notice. |
| **B: cargo coordination** | All four branch combinations mapped; winning separation measured; Blue ready; no cross-owner leakage; causal failures separated. | A cargo constraint changes another van's useful route. The traffic choice remains after cargo validity is understood. | “Why does Blue need that road?” “Why did this pair conflict?” “Would you like another?” | Crossing readable visually/nonvisually; no two urgent events; readiness explicit. | Players infer or correct the relationship and value the complete run. | Package preview dictates the entire answer, one fork is irrelevant, or the geometry needs misleading overlap/precision. |
| **C: matched control** | Same topology/tuning and collision traces for same paths; no cargo state; expected safe-plan-set difference proven. | Separates routing depth, cargo constraint and collection pleasure. | “Which version would you replay, and why?” “What extra decision did cargo add?” | Lower marker count comparison; record presentation/focus differences rather than treating them as identical experience. | B's additional constraint/payoff is worth its cost on selected boards; preference reasons are understood. | Cargo adds only bookkeeping or waiting. Mixed preference suggests optional use; strong repeated aversion calls for rejection/rework. |
| **Deliberate play** | Frozen clock/accumulator; same legal switch checks; stable command order; no paused-time catch-up; Stop distinct; lifecycle/background/replay checks. | Player chooses an intervention deliberately and still enjoys seeing it unfold. | “Did pausing help you think or just make the run tedious?” “Could you act on the plan you understood?” | Stable focus/routes; pausing on a locked state has a usable recovery; screen-reader and motor operation tested. | Correct plans can be carried out with understandable legal controls, and uninterrupted play remains available. | The player must still catch a tiny pause window, cannot clear locks accessibly, or added controls overwhelm the puzzle. Try a bounded advance control before claiming access; defer new finite-window content if unresolved. |
| **Two pickups / order** | Both orders verified; exact required set; missing-one result; idempotence/reset; no fake static return logic; count/remaining preview parity. | Order changes a route relationship beyond a forced second errand. | “Are both orders allowed?” “Why this order with the neighbor?” “Was remembering items pleasant?” | Explicit either-order wording, named items, readable markers/count; pickup-switch roles if combined are clear. | A two-item board offers a distinct inference, and people track remaining work easily. | Every board is a forced chain, an equivalent single-pickup route is clearer, or marker density dominates. Keep zero/one. |
| **Automatic light** | Phase boundaries, common admission snapshot, red stop accuracy, occupancy clearance, held collisions/locks, resets and no queues; equivalent replay. | Light changes a useful route/order decision; waiting is safe/predictable; controlled area is understood. | “Why wait here?” “Which route would you choose next cycle?” “What does green protect?” | Stop/go shape/text, approach association, no countdown-reading requirement; useful planning without hearing announcements. | Players reason about admission qualitatively and want another; distinct benefit exceeds interface/stopping cost. | It auto-solves every crossing, adds only downtime, needs phase chasing, surprises with held traffic, or demands queue AI. Remove the optional region. |
| **Alternate-plan mastery / optional goal** | Multiple complete strategy scripts; goal computed explicitly; bounded optimum claim justified; existing records unchanged. | Revisiting reveals a new meaningful plan or preferred delivery sequence. | “Did you want to try another way?” “What did the goal change?” | No reward for faster physical activation or penalty for inspection/assistance; goal summary inspectable. | Voluntary replays have reasons tied to planning/mastery, not rewards alone. | Goals encourage tedious tap minimization, stars feel arbitrary, or people prefer fresh boards. Keep alternatives without a new score system. |
| **Production upgrade rehearsal** | Save fixture matrix, raw preservation, idempotent transition, distinct campaign provenance, genuine stars kept, append unlocks/rewards verified. | One clear campaign; returning players understand what their retained history and new stars mean. | “Where are your old achievements?” “What does this new completion mean?” “Can you continue where expected?” | Settings and entitlements preserved; no inaccessible recovery dialogue; controls remain reachable after upgrade. | All recoverable data has a documented outcome and upgrade expectations match the product. | Old stars masquerade as new wins, history is overwritten, duplicate rewards occur, or provenance cannot support the proposed conversion. Resolve before rollout, independently of cargo fun. |

### Human evidence protocol

- Begin with a small directional group around five people, including infrequent game players. Recruit separately for relevant accessibility operation; a five-person convenience sample is not representative certification.
- Observe before explaining. Ask players to describe their intended plan and the cause of a failure; distinguish a wrong plan, a misread state and a known plan they could not execute. Record prompts/coaching and facilitator-assisted attempts separately.
- Capture level/variant, content/build identity, actual tuning, control mode, trial order and initial/Go selections. Never infer experimental tuning from elapsed time. Until logging metadata exists, attach consistent manual notes to internal exports.
- Keep wall/real inspection time, engine ticks, dispatch-observed time and animation duration distinct. Record omitted events. A long loop or pause is not automatically boredom; ask why it happened.
- Compare preference and voluntary replay, not only completion and average attempts. A first-try solve may be elegant or trivial; observation distinguishes them. Several retries may be productive or frustrating.
- Use the proposed four-of-five comprehension and three-of-five continued-interest thresholds as review prompts, not statistical guarantees or a reason to ignore a serious recurring accessibility barrier. Report individual observations and uncertainty alongside counts.
- If a gate fails, diagnose the concrete issue and test a bounded revision. Do not automatically change global speed, add more tutorial levels or install another subsystem. Repeated failure to add player value is permission to stop the feature.

## 14. Deferred or rejected features

| Feature / commitment | Disposition and reason to revisit |
|---|---|
| Sixty levels as release requirement; fixed six-level chapter replacements | **Rejected.** More distinct good concepts could earn sixty later; vacant numbers do not. |
| Mandatory package on every van / every future level | **Rejected.** Mixed readiness and delivery-only pacing are core tools. |
| Generic inventory, weight, capacity slots, loading minigames or pickup delays | **Rejected for this expansion.** No demonstrated decision needs them. Revisit only for a specific separately approved puzzle, not “future proofing.” |
| Multiple pickup ownership sources / independently writable inventories | **Rejected.** One package definition and lifecycle authority suffice. |
| Mandatory two-item campaign | **Deferred.** Test either-order value after single-item acceptance; no capacity, sorting or intermediate unload. |
| Automatic-light chapter, second signal group and manual-light chapter | **Deferred.** One automatic experiment first; manual requests need independent value and safety/scoring/control review. |
| Queues, traffic AI, lanes, overtaking or general reservation controller | **Outside scope.** If the small signal trial requires them, reduce or abandon it. |
| Cargo transfer, shared stock, any-van ownership, moving handoffs | **Deferred significant change.** Fixed ownership is clearer and avoids contested transactions. |
| Multiple destinations and nonterminal deliveries | **Deferred significant change.** Would change house, parking, victory and cargo semantics. |
| Speed classes, mandatory priority orders, deadlines and expiring cargo | **Deferred.** Existing path lengths/departures offer cheaper relationships; optional relative-order trial only after a concrete need. |
| Dynamic closures, one-use roads, cargo-sensitive edges and special switches | **Deferred.** Shared model fields are not implemented rules. Use honest static topology first. |
| Full timeline/ghost-run preview or automatic solution prediction | **Deferred.** Improve current route/objective scope and failure explanation first; do not remove the central anticipation puzzle without evidence. |
| Currencies, upgrades, leaderboards, procedural generation and daily content service as replay solution | **Not recommended.** They do not establish whether solving another route plan is enjoyable. Existing account/economy data still must survive migration. |
| New engine, generic objective framework, unified old/new runtime or second browser gameplay authority | **Rejected without a demonstrated technical reason.** Current engine boundaries support the recommended work. |
| Mid-run save/restore | **Deferred.** Campaign completion saves suffice for these short experiments; serialization of a running simulation is a separate product feature. |
| Old gameplay deletion during cargo work | **Rejected.** Preserve first, verify callers/tools and release needs, then consider a separate cleanup. |

## 15. Open design decisions requiring owner approval

These are future approval points. No implementation starts automatically, and none requires an answer during this documentation task.

| Decision | Recommended choice | Needed before |
|---|---|---|
| First new mechanic / experiment scope | Approve zero/one fixed-owner pickup with automatic collection, terminal houses and A/B/C internally; no generic inventory. | Cargo implementation. Package-first preference is established; precise contract/experiment still needs review. |
| Missing-cargo behavior | Distinct matching-house failure, exposed in preview; no delivery credit. Wrong-house outcome remains distinct and takes precedence. | Engine/preview task. |
| Package-free and mixed boards | Keep them permanently available as content choices, with explicit ready status on mixed boards. | Accepted expansion authoring. |
| Product control promise | Planning-led game; trial deliberate controls with equal stars and preserve optional uninterrupted real-time operation. Decide whether any finite-window challenge belongs on the mandatory path only after tests. | New live content / deliberate-play rollout. |
| Retry contract if live-cargo re-arming confuses players | Preserve current settings now. Prefer board redesign; trial restoring the Go plan only as a separate explicit change. | Live-cargo campaign acceptance. No global Retry redesign is pre-approved. |
| Campaign scope | Variable chapter lengths and a shorter coherent release are allowed; sixty remains a horizon. Accept individual concepts only after verification. | Content-pack commitment. |
| Production rollout / history policy | Confirm already-shipped populations. Preserve legacy history separately, genuine Multi-Van stars and account value; no automatic old→new star conversion. | Any save migration/repair or further rollout to legacy players. |
| Legacy stars with ambiguous origin | Approve an explicit recovery/provenance policy after the audit; never wipe all current stars by assumption. | Compatibility repair. |
| Future scoring | Keep existing rules/pars now. Review a clear future metric only for demonstrated mastery/control needs; no assistance penalty or retroactive star downgrade. | Scored new control types or a new mastery goal. |
| Two-item collection | Authorize only a later either-order trial after one-item success, before signals if it remains the cheaper promising question. | C6, not initial cargo. |
| Traffic lights | Retain one later automatic admission experiment; no guaranteed chapter/manual sequel or queue simulation. | Signal implementation. Interest in lights is preserved, not treated as feature approval. |
| Legacy code retirement | Keep it through preservation, compatibility/release verification and tool audit; remove only in a separately reviewed cleanup. | Any deletion. |

### Recommended Next Development Milestone

**After reviewing and approving the proposed direction, authorize the small package vertical slice, starting with the deterministic cargo core and Experiment A, and ending with the complete A/B/C comparison.** Include reset, cargo-aware preview, both renderer states, failure explanation and internal logging in that milestone; those are necessary to evaluate the mechanic fairly.

Observe current coordination/live operation alongside it and schedule the separate deliberate-play prototype before more live puzzles. Audit the already-implemented production/save transition early, before further rollout, without making internal package evaluation depend on migration. Expand only after engineering evidence and human feedback support the next small step. This document is the stopping point for the present task.
