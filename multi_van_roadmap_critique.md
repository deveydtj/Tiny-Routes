# TinyRoutes — Independent Game Design & Architecture Review

Date: 2026-11-03. Planning and critique only.

## 1. Executive verdict

**Proceed with the direction, but do not approve a sixty-level production commitment.** TinyRoutes has a promising compact puzzle language: configure routes, anticipate interactions, watch the plan succeed, and make a comprehensible correction when it fails. That can plausibly sustain sixty short levels. The proposal has not yet demonstrated sixty distinct reasons to play.

The roadmap is strongest as a set of conditional experiments. It becomes weaker when those experiments are assigned six-level chapters in advance. Several nominally different chapters return to the same answer: give one van the long route so the crossing clears. Packages can make that answer more legible and satisfying, but can also turn it into a mandatory errand. Signals risk automating the interesting coordination or replacing it with waiting and exceptions about where a green light actually protects you.

The three highest-impact changes are:

1. **Replace chapter quotas with demonstrated puzzle value.** Keep the numbering provisional; allow shorter chapters and a shorter first release. Do not fill rejected signal chapters with twelve variations of familiar detours and loops.
2. **Make pickups optional per van and per level, and test their depth earlier.** Replace the proposed 13/14/15 trial with teaching, interaction, and a package-free comparison. Understanding a pickup icon is insufficient evidence for adopting a campaign mechanic.
3. **Resolve deliberate play and failure comprehension before expanding live timing; defer signals.** A forgiving interaction model has broader value than a second traffic-control system.

No code, engine, tuning, level JSON, or existing roadmap changes were made for this review. No Git operations, subagents, builds, or simulations were used. The only deliverable is this document. Historical testing is evidence of engineering maturity, not freshly verified results or proof of enjoyment.

Evidence reviewed: [future roadmap](multi_van_future_roadmap.md), [original prototype plan](docs/prototype/multi_van_prototype_plan.md), all twelve [prototype level files](TinyRoutes/Resources/PrototypeLevels/) and corresponding [solution scripts](TinyRoutesTests/Resources/PrototypeSolutions/), the Multi-Van level model, engine, route preview, repository, shared runtime graph and relevant edge-schema definitions; prototype validation and solution-test coverage; feedback, input/frame-driving and logging implementations; and the relevant timing assessment. Findings distinguish implemented behavior from proposed concepts. No future layout has been proven feasible by this review.

## 2. Strengths worth preserving

- **A strong cause-and-effect loop.** Level 7's correct destinations but unsafe crossing separates spatial validity from coordination. Level 8 adds recoverable holding; Level 9 asks two vans to share one physical routing decision. These are genuinely different relationships.
- **A small vocabulary.** Directed roads, matching terminal houses, shared exits, one speed, and visible vans are sufficient to explain most existing puzzles. Preserve those constraints while testing depth.
- **Readable identity and satisfying completion.** Color plus circle/triangle/square/star, disappearing route traces, individual deliveries and the final payoff offer useful progression without inventory management.
- **A sound simulation foundation.** Fixed steps, carried-over movement distance, authoritative switch locks, deterministic script order and engine-owned outcomes are the right foundations. A rewrite is unwarranted.
- **Good restraint already present in the roadmap.** Fixed ownership, instantaneous pickup, no mandatory multiple destinations, no queue simulation, separate completion and optimization, and conditional acceptance gates are sensible.
- **Difficulty resets.** A calm Level 13 after four-van Level 12 is correct. Quiet static puzzles between live ones should remain a pacing tool.

The current files also correct assumptions in the original plan: Level 6 already requires a live change at 2.75 seconds, rather than being a static convoy payoff. Level 12's recorded solution takes the detour and changes the split at 5.25 seconds; its hold branch is not an intended loop-release solution. Rush uses a 4.95-second live tap. Future teaching must follow the actual player experience.

## 3. Three biggest gameplay risks

### 1. New objects without new decisions

Levels 13–17 spend considerable time validating “visit the marked branch.” Later, 18/22/28/49 and parts of 30/48 repeatedly assign a useful detour. Levels 20 and 23 substantially repeat the same loaded-loop release. Adding a package to a forced route increases animation and visual bookkeeping without increasing agency.

Require each retained level to identify what the player must infer that a nearby level did not already establish. A quiet repetition can provide relief, but several repetitions should not masquerade as a new chapter. Removing a pickup should sometimes change the useful route; if it never does, its value is presentation, not puzzle depth.

### 2. Understanding the solution but failing to execute it

The timing assessment reports a roughly 0.967-second window in Convoy. Its later correction gives current Rush a window of [4.216667, 5.075000), approximately 0.858 seconds. Earlier Rush tables are superseded. These are simulated opportunities, not human measurements; constant 2× playback would roughly halve their wall-clock duration.

More objectives create more things to inspect before acting. One active control can still be unfair when its cue competes with collection, a delivery celebration, another moving van, or a spoken announcement. The roadmap's two-second target is a useful floor for testing, not an accessibility guarantee.

### 3. Expanding rules faster than the board can communicate them

Four vans, four houses, pickups, switches, previews, closures and lights compete within a 5×7 envelope. Signals introduce stop lines, effective versus requested state, protected versus unprotected space, and stationary collision bodies. A casual player may reasonably expect traffic to queue at a red light. A game where the follower crashes instead must spend attention explaining an unfamiliar exception.

Reduce entity count and remove unnecessary rules before adding visual overlays. Do not spend a full chapter teaching machinery whose puzzle value is uncertain. A shorter, clear game is preferable to a sixty-level explanation burden.

## 4. Package pickup recommendation

**Approve a bounded experiment, not universal cargo.** Packages offer visible progress and a natural reason to visit a route segment before home. They are valuable when collection changes a shared route choice, establishes a dependency, or gives a useful detour meaning. They become tedious when the preview simply tells the player which compulsory branch to select.

Some future levels should remain delivery-only. Mixed boards should allow one van with a pickup and another already ready to deliver. This keeps attention on the relationship being taught and prevents package count from becoming a disguised difficulty metric. Explain the difference in stable van chips: “Pickup needed” versus “Ready to deliver.”

The simplest useful contract is:

- A package has a stable ID, pickup node and fixed owner van ID. Color/symbol communicate ownership but are not database keys.
- A participating van has zero or one assigned required package. Automatically collect it on node arrival, instantly, once. Passing another van's package does nothing.
- Cargo does not affect speed, size, locks or topology. The existing matching terminal house remains the only destination.
- An empty arrival at a house requiring cargo produces a distinct missing-package result. The planning preview must already identify the missing item; do not make this a hidden gotcha.
- A pickup disappears from its marker and appears as a compact cargo status, preserving the van's identity symbol. Keep a persistent textual status in the van chip; do not depend on a tiny moving roof parcel.

Simplify the roadmap's proposed authored redundancy: with fixed ownership and every assigned package required, derive required IDs from the package owner. Authoring both ownership and per-van requirement arrays creates two sources of truth without adding a decision. If both are retained for a concrete reason, validate exact consistency. Use one authoritative package lifecycle map; derive cargo views rather than maintaining independently mutable copies.

Multiple packages deserve an earlier *experiment* than their reserved Level 43 position if one-package play succeeds: one van, two pickups, either order, one home, then one traffic interaction. That does not mean introducing them earlier to players. The cost of learning the second item must buy a meaningful choice of tour. Two numbered packages must not accidentally imply a required order; use distinct labels plus “either order.”

**Cargo capacity is not currently worthwhile.** With one terminal unloading destination and mandatory packages, a capacity smaller than the required set makes the task impossible unless intermediate unloading or transfer is added. Capacity large enough for the set imposes no strategy. Validate supported package counts without exposing an inventory-capacity mechanic.

Do not implement yet: weight, loading time, cargo slots, shared stock, automatic reassignment, stealing, transfers, package races, optional collectible currencies, mandatory collection order, per-package destinations, intermediate unloading, cargo-dependent roads, or an inventory framework.

## 5. Traffic-light recommendation

**Defer traffic lights from the first expansion. Reserve a later experiment, not two guaranteed chapters.** Their safety engineering is feasible; their incremental fun is less certain than the roadmap implies.

| Approach | Puzzle value | Main cost or frustration | Judgment |
|---|---|---|---|
| Automatic timed signals | Route selection changes arrival relative to a repeatable phase; can reward a useful wait over a bypass. | Passive waits, opaque phase arithmetic, or a signal that solves every crossing automatically. | Best candidate if later tests show route-dependent consequences players can predict qualitatively. Start with one group. |
| Player-controlled release | Deliberate ordering with indefinite inspection can be accessible. | “Send A home, then B” trivializes coordination; constrained exceptions can feel contrived. | Only retain if both serialized orders do not make every board equivalent. No mandatory quick toggle. |
| Planning-only toggle | Choose the initial right of way or phase before Go; all execution follows the plan. | Permanently red approaches deadlock unless automatic release exists. Many settings merely reproduce an authored departure delay. | Worth a cheap conceptual comparison before building run controls; define whether the setting selects phase or a release sequence. Do not create a general schedule editor. |
| Signals changed during a run | Could combine route planning with deliberate dispatch. | Adds another live control, pending-state confusion, lock interaction and reflex pressure. | Defer. If trialled, requests wait safely for clearance and carry no deadline. |

Switches choose an exit. Signals decide when entry is permitted. Preserve that distinction in controls and explanations. A light cannot make a frozen shared switch send two vans in opposite directions.

The weakest proposed manual-light premise is Levels 37/39/42: a held van intentionally blocks another route outside the protected crossing. It creates an order puzzle, but its educational cost is high—“green is safe here, but you crash into someone waiting there.” Do not build a chapter around that exception before watching players interpret it. Level 38 primarily teaches the safety implementation; Level 41's single release may be a button press without a decision.

Automatic trials should compare a useful wait against a genuinely different route outcome, not merely a pickup route with a decorative red light. Levels 31 and 34 currently risk exactly that. Later misses should yield a short, repeatable wait; no expiry, urgency scoring or phase-chasing requirement. If meaningful lights require queues, several simultaneous countdowns or carefully hidden downstream collisions, abandon the trial rather than grow the traffic model.

## 6. Chapter-by-chapter critique

Ratings of implementation burden below include validation, UI and authoring, not just engine edits.

| Chapter | Learning and new rules | Curve, variety and repetition | Complexity and accessibility | Recommended disposition |
|---|---|---|---|---|
| 13–18 Parcel Row | Assigned pickup before home; static completeness, ownership, then traffic. | Correct reset; four introductory variations may be too slow for experienced players. 17's obligatory detour does not independently test spacing. 18 is the best depth test. | Moderate subsystem. Three matched markers per participating van increase scanning. | Keep the chapter hypothesis; compress 14–16 and expose a real interaction sooner. |
| 19–24 Market Loop | Cargo combined with already-known live loops and splits. | Plausible rise, but 19/20/23 repeat release; 21 is a finite gap amid otherwise recoverable waiting. 22 repeats 18. | Low new movement scope, substantial assist/UI work. Highest early execution risk. | Combine 20/23; use 22 as a package-free respite; reduce 24 to two interacting vans initially. |
| 25–30 Canal Streets | Existing directed routes and static blocked connections. | Spatial focus is useful, but teaching direction only here is late. 28/30 drift back to detour timing. 29 explains a graph limitation more than a new pleasure. | Mostly content and sign clarity. Arrows, false connections and return paths need nonvisual descriptions. | Move a simple direction lesson into early cargo teaching. Retain the strongest spatial boards, not six by default. |
| 31–36 Signal Square | Automatic holding and exclusive crossing admission. | Distinct observation rhythm is possible. 31/32/34 may be several demonstrations before 33 offers a real choice. Two signal groups at 35/36 may arrive too soon. | Largest near-term movement change. Phase state, clearance and held bodies must be readable. | Defer; trial a meaningful 33-like route choice with one signal before committing. Combine 31/34 if kept. |
| 37–42 Depot Junction | Manual requests and effective release. | Nominally dispatch, but three blocked-bay order puzzles repeat; safe serialization may erase difficulty. | Moderate extension after substantial signal work. Indefinite holds help access; pending states and crash exceptions hurt comprehension. | Remove as a committed chapter. Retain at most one later order experiment. Remove 38 as a standalone puzzle unless its fork adds a distinct insight. |
| 43–48 Two-Parcel Gardens | Two required pickups, flexible order, same house. | More promising new spatial decisions than another light tutorial. 43/44 are clear teaching; 45 is the real test; 46/48 overlap, 47 backtracks to completeness. | Small-to-moderate after cargo. Marker density and remaining-item memory matter more than code. | Move the experiment before signals; combine 43/47, retain 44/45, differentiate or combine 46/48. No capacity system. |
| 49–54 Old Town Routes | Recombine accepted rules; shared settings and dependency chains. | 50 and 54 have useful relational depth. 49 repeats detour assignment, 51 repeats 20/23, 52 repeats 21. Could feel like a review worksheet. | Mostly content, but test combinations and simultaneous attention. | Keep 50/54 as anchors. Replace repeated drills with alternate valid plans; use 53 only if the third van contributes. |
| 55–60 City Delivery Day | Mastery, alternatives and two episodes; no new rules. | 56's multiple coherent plans is a strong payoff and should appear earlier too. 58's independent third van may pad spectacle. 59/60 could be nearly identical. | Content complexity grows combinatorially even without new systems. Four cargo tours may not fit. | Keep 56/60 intent; make 59 optional rehearsal or combine it with 60. Prefer three readable vans over four for ceremony. |

The chapters do not yet all provide distinct experiences. Parcel Row and Two-Parcel Gardens have potentially distinct spatial objectives; Market Loop changes execution; Canal Streets changes route-reading emphasis. Signal Square could change planning around time, but Depot Junction depends on awkward obstruction puzzles. The last twelve levels need stronger contrast between solving a dependency chain and finding alternative complete plans.

The roadmap's fallback instruction to preserve six-slot shapes conflicts with its principle that numbering is not a quota. Remove that requirement. Rejected mechanics should reduce scope unless replacement levels independently earn their place.

## 7. Level 13–24 specific revisions

These are revisions to concepts, not replacement JSON or claims of solved geometry.

| Level | Action | Specific revision and reason |
|---|---|---|
| 13 Pick Up First | **Keep** | One fork, one parcel, one house, no traffic. Explain pickup through visible state and preview; do not require a failure to teach it. |
| 14 Loaded and Homeward | **Combine / simplify** | Fold post-pickup destination awareness into 13 if players already understand houses. Keep as optional reinforcement only if players actually forget the homeward route. A barrier correction repeats Level 3. |
| 15 Two Parcel Routes | **Keep briefly / simplify** | Use one new pickup van and one ready-to-deliver van first, unless human tests show independent cargo ownership needs two pickups. Two isolated copies of 13 should not consume a major progression beat. |
| 16 Know Your Parcel | **Move / combine** | Teach the ownership symbol with the first multi-van cargo board. Keep a distinct wrong-owner puzzle only if it produces a useful correction; proximity-based visual bait alone is weak depth. |
| 17 The Useful Pickup | **Replace its central choice** | Both candidate routes should be cargo-complete, with different traffic consequences, if this is meant to teach coordination. As written the missing-cargo preview already rejects the shortcut, so the collision adds no decision. Alternatively keep the current design as one short demonstration and merge its purpose into 18. |
| 18 Neighborhood Round | **Keep; prototype early** | This is the first convincing combined cargo/traffic test. Require a meaningful interaction among complete tours. Inspect whether removing the package changes any viable choice; if not, attribute the depth to routing. |
| 19 Leave Loaded | **Keep conditionally** | A durable “loaded” release cue is good. Require repeatable opportunities and explicit re-arming of the hold route after retry. Retained final switch settings otherwise send the next run home empty. |
| 20 Collect, Then Clear | **Combine with 23** | Teach clearance and permission to wait in one board. Require at least two later winning laps; indefinite waiting must not be a failure. |
| 21 Shared Exit, Separate Parcels | **Move later within the chapter** | Finite split timing is a harder execution demand than a recoverable loop. Put it after the quiet board and the combined 20/23. Packages may be omitted if their only role is extra things to watch. |
| 22 The Quiet Route | **Replace its presentation, keep its pacing role** | Make this a simple delivery-only or mixed-cargo static board. Preserve the calm interval; avoid another near-copy of 18 with two mandatory parcels. |
| 23 Another Lap Is Fine | **Remove as a separate mandatory slot** | Merge its reassurance and multi-lap acceptance criteria into 20. Do not replace it merely to maintain six levels. |
| 24 Saturday Deliveries | **Simplify** | Start with Red/Blue only. Add Yellow only if players value the independent payoff and it does not obscure the live cue. Retain the finale only if both the detour and split are explainable without timestamp knowledge. |

An effective shorter sequence could teach 13, a combined ownership board, a revised 17/18, a quiet spatial board, then 19, combined 20/23 and eventually 21/24. Final ordering should follow observed comprehension, not these provisional numbers.

## 8. Architectural risks and mitigations

### Preserve the current simulation boundary

[MultiVanEngine.swift](TinyRoutes/Prototype/MultiVanEngine.swift) already uses integer completed-step count and a fractional accumulator at default 1/120 second. `advance` moves all vans, selects arrival failures before collisions, then resolves victory. Authored van order determines ties. Movement follows actual `RoadPath` lengths and carries distance across edges. Houses terminate traversal. Locks and collisions currently consider only `.driving` vans.

Preserve those legacy semantics for unchanged levels. Determinism means equivalent tuning, content and tick-bound commands produce equivalent states; it does not mean arbitrary wall-clock taps during different frame schedules are equivalent. The UI clamps frame stalls to 0.25 seconds before applying the speed multiplier, while the engine preserves the interval received. A signal must use simulation ticks, never wall time or animation progress.

The engine steps local van copies and publishes afterward. New package/occupancy/event state must be updated within the same tick transaction; reading `self.vans` during a multi-step `advance` can observe stale published positions. This is a concrete integration hazard, not a reason for an entity-component system.

### Package state and delivery

| Concern | Minimal contract and mitigation |
|---|---|
| Identity / ownership | Stable package ID and owner van ID; validate unique van IDs before using them as keys. Keep identity independent from color. |
| Pickup state | One authoritative lifecycle: available, carried, delivered. Collection is idempotent; revisits cannot duplicate it. |
| Cargo state | Derive the per-van carried set from lifecycle state; avoid separately writable UI, van and package inventories. |
| Completion | Check wrong-house identity first, then missing required cargo. Only a successful matching arrival delivers cargo, parks the van and increments the delivery combo. Existing code parks before wrong-house validation; extend the arrival logic deliberately rather than hanging cargo off a delivery animation. |
| Ordering | Pickup at node arrival precedes home checking if co-location is supported; preserve actual traversal order and leftover distance. Stable authored van order handles simultaneous independent pickups. No contested ownership in this scope. |
| Reset / save | Reset all run package state on Go/Stop/Retry/Replay while retaining the established switch plan. Do not persist partial cargo across attempts. Future campaign saves need level completion/content identity, not serialized runtime object graphs. Mid-run persistence is a separate feature. |
| Retry semantics | A live switch's final selection is retained, not the original Go selection. Test retry after late failures on 19–24. Show any newly unmet pickup requirement and let the player re-arm the loop; do not silently change legacy retry behavior. |
| Events | Collection followed by same-tick failure can be represented in order, but failure should suppress celebratory presentation. Delivery may currently emit for one van on a tick another fails; do not assume all events imply successful attempts. |
| Preview | Trace local hypothetical cargo, never real inventory. Begin running previews from carried state and the committed edge. Include cargo in invalidation: current invalidation only compares edge/status between published frames. |

Keep a simple arrival check in Multi-Van and a small pure objective check shared with its preview if needed. Do not import global package normalization from the single-vehicle runtime: shared physical switch selections must not change because one van collects something.

### Graph, schema and validation

[RuntimeRouteGraph.swift](TinyRoutes/Gameplay/RuntimeRouteGraph.swift) carries availability fields, but Multi-Van departure, switching and preview logic do not enforce those rules. Accepting such JSON silently would misrepresent gameplay. Explicitly reject unsupported nontrivial road conditions in the Multi-Van content boundary rather than accidentally enabling the production engine's global objective machinery.

Use optional empty package data for legacy files and one explicit supported version for new feature-bearing content. Version checking belongs before use, not just in test fixtures; an older decoder ignoring unknown cargo fields could otherwise treat a pickup level as delivery-only. Preserve ordered exits during serialization because order changes taps and par. The current Multi-Van model is Decodable; a future editor/export path is separate work, not implied round-trip support.

[MultiVanLevelTests.swift](TinyRoutesTests/Prototype/MultiVanLevelTests.swift) supplies substantial test-side checks, but the repository loader primarily decodes. Before widening authoring, add focused checks for unique nonempty IDs, supported van count, finite nonnegative departure delays, nonnegative par, required reference integrity and feature compatibility. Packages additionally need owner existence, supported count, unambiguous pickup markers and start→pickup→house reachability without passing a terminal house prematurely.

Independent reachability is necessary but insufficient: routes may require contradictory settings at one frozen switch. A successful static route cannot revisit a node and then depart differently merely because cargo changed. Enumerate small configuration spaces and retain actual winning scripts. Check readability separately; graph disconnection does not prevent geometric collision.

The exact twelve-file test assertion and navigation expectation after Level 12 need an explicit future experiment boundary. Keep trial discovery separate or revise expectations deliberately when content is accepted; do not weaken corpus checks to make additions load.

### Traffic movement and safety

Use one concrete signal-group structure with directed approach references and tick durations. Automatic state needs a specified phase and safe effective admission; manual state additionally needs a clear pending request policy. Prefer one pending desired group, with deterministic handling of replacement/repeated requests, over an unbounded request queue.

Stop lines must be distances on actual paths. Consume movement only up to a red stop line and discard that tick's unused travel allowance while held. Do not accumulate waiting-time movement credit. Check a van at the line on the first permitted tick. Once admitted, it clears even if red returns.

A held van remains a physical occupant and locks nearby switches. Do not reuse off-road `.waiting`, which is excluded from collisions. Test moving/held and held/held pairs, committed-edge previews, turning indicators and result copy for every new status. Place stop lines away from live switches in trials.

The roadmap correctly proposes occupancy protection, but its cycle-plus-delayed-green semantics need one more decision: **does delayed admission shorten a nominal green, extend it, or postpone the rest of the cycle?** For the smallest automatic trial, keep the tick schedule fixed and treat occupancy as an extra gate; a blocked interval can be missed, and the next cycle returns. Validate sufficiently long useful green periods. Never show effective GO while entry remains denied. If skipped phases are common, reject the board rather than hide schedule drift.

For each tick: apply stable-ordered commands; calculate nominal phase and safe admissions from prior occupancy; move; handle arrivals; resolve existing failure/collision precedence; update clearance for the next tick; resolve victory and emit ordered events. Simultaneous entry permissions must come from one common snapshot, not whichever van is processed first. An all-red duration alone is not occupancy protection.

No queues initially. Test representative wrong plans as well as the winner for unexpected rear-end collisions. If avoiding queues requires unnatural roads or persistent explanation, the signal concept has failed its scope gate. Do not add following AI to rescue it.

At default speed, a van moves 0.0125 grid units per tick; two vans can close by up to 0.025, versus a 0.35 collision threshold. This supports retaining current sampling under current bounds, but is not proof that every arbitrarily grazing encounter is caught. New speeds, smaller radii or movement jumps require renewed bounds and possibly swept checks. Do not promise continuous collision accuracy from fixed steps alone.

### Scripts, scoring, events and logging

The [solution runner](TinyRoutesTests/Support/PrototypeSolutionRunner.swift) uses stable time-sorted live taps applied at eligible tick boundaries and a 120-second test horizon. The horizon is not an in-game deadline. A win at par demonstrates one script, not a human-safe window or universal minimality. Preserve existing script compatibility; add typed tick commands only for genuinely new actions. Compare full state and event order across frame partitions and playback speeds, including boundary and rejected commands.

`changeCount` computes cyclic distance from initial to **current** settings. It is not accumulated input history. Rush and Big Delivery can return the split to its initial selection, so five/seven physical inputs produce par three/five. Counting signal taps separately without explaining stars would compound the mismatch. Keep old behavior during trials, suppress optimization pressure in new teaching, and decide the future metric before scoring a new campaign. Do not build replayability around a counter that can reward undoing a live control.

[Feedback](TinyRoutes/Prototype/MultiVanFeedback.swift) drains one event stream. Add semantic pickup/held/released events there, with exact tick metadata captured during simulation. Do not create a second consumer that drains events before audio or logging sees them. Animation completion must never change cargo or release vehicles.

[Playtest logging](TinyRoutes/Prototype/MultiVanPlaytestLog.swift) records dispatch-observed simulation time, not exact arrival times, and caps events at 1,024 with an omission count. Add content/build identity, effective tuning and assist/facilitator flags when future trials require comparisons. Preserve real elapsed time separately. Long manual holds and extra loops must not quietly invalidate timing analysis through truncation. Annotated observation is still needed to distinguish boredom, delight and confusion.

No generic objective framework, graph rewrite, reservation service, unified production/prototype engine, generator migration or second JavaScript gameplay authority is justified by this expansion.

## 9. Revised implementation priorities

1. **First validate the existing interaction.** Run the small experiment concluding this review, alongside the existing onboarding playtest. Distinguish inability to predict a conflict from inability to operate a known solution. Current tests can remain untouched.
2. **Before new live content, decide the deliberate-play experience.** If live input remains mandatory, prototype tick-preserving pause/inspect/act/resume with legal locks and stable focus. This is more than a Boolean pause flag: input timing, backgrounding, frame timestamps, focus and resumption must agree. Do not resume with accumulated wall-time catch-up.
3. **Run a narrow cargo-value trial.** One teaching board based on 13, one interaction based on revised 18, and one comparable package-free/mixed-cargo board. Include reset, preview, feedback and validation in this small vertical slice. These are prerequisites to judging the mechanic, not polish to postpone.
4. **Ship only the strongest small pack after playtesting.** Compress repeated 13–24 concepts; move simple direction teaching forward. Author an easy board and a depth anchor before filling intervening levels. Keep some plain deliveries.
5. **If cargo succeeds, test two-item route order before building traffic signals.** The test is cheaper and more directly expands the spatial puzzle. No inventory capacity, destinations or loading times.
6. **Only then consider one automatic signal group.** Its test need not depend technically on cargo at all; mixing them immediately confounds the result. Compare route consequences with and without the hold. Manual signals are a separate keep/drop decision, not an automatic sequel.
7. **Build mastery and production integration only from retained systems.** Navigation, completion saves, schema identity and promotion out of the prototype need explicit product decisions. Do not spend months filling sixty slots before discovering the intended progression integration.

Expensive ideas with weak current value: two signal chapters, realistic queues, multi-destination delivery, dynamic road closures, speed classes, inventory capacity and parallel visual-runtime implementations. Missing dependencies: reliable event attribution, retry comprehension, preview semantics, validation at the content boundary, an agreed scoring contract, and accessible route inspection.

Keep the twelve existing levels, defaults, solutions and pars unchanged during these experiments. Preserve terminal houses, one speed, physical switch commitment, deterministic collisions, Stop, retained planning state, and the one-screen board. Any later change to those contracts deserves its own evidence and scope.

## 10. Accessibility and fairness concerns

**Comfortable windows:** For new mandatory live actions, start testing with at least three seconds of usable wall-clock time after a clear cue at normal speed, and prefer repeatable or indefinite opportunities. This is a proposed design target, not a measured universal threshold. The usable interval excludes lock time, cue recognition and competing feedback. A nominal two-second simulation window at 2× is only one second. Make slowing or pausing deliberate and inspectable; do not punish assistance with stars.

**Switch locks:** Show whether a control is frozen for the run or temporarily locked by a nearby van, and identify the blocker in the status view. The current Euclidean lock can involve a geometrically nearby road even if it does not feed the switch. Avoid these surprising arrangements in teaching. Pausing must not waive the physical lock; users need a clear way to resume until it clears.

**VoiceOver:** Labels alone do not communicate graph relationships. Supply stable named places, selected exits, remaining objectives, shared crossing relationships and an inspectable route sequence. Keep focus stable during motion. Announce significant state changes once; do not flood the user with phase countdowns or moving-position updates. Test operation with screen-reader users, including live resumption and replay. A wider timing window is not equivalent to accessible interaction.

**Reduced Motion and muted play:** Cargo, delivery, clearance and lock status must be visible as stable states. Do not rely on pulsing, parcel flight, bounce, sound or haptics for the only cue. Motion suppression must not suppress semantic feedback or change simulation timing.

**Color independence and small screens:** Reuse owner symbols consistently across van/package/house. Stop/go needs shape/text and approach association beyond red/green. Check overlapping previews, enlarged text, control hit regions and one-handed use on the smallest supported phone. Reduce vans before shrinking controls.

**Learnable failure:** Name the van pair and crossing or the specific missing pickup. Explain the causal error, not just “Crash.” Preserve the failed plan and point, while making the retained live configuration clear. First seeing ✓ and then crashing can teach the preview boundary, but only if ✓ is understood as “destination route valid.” Repeated surprise is misleading feedback, not desirable difficulty.

**Fair progression:** Teach one new reasoning burden at a time. Finite-window splits should follow recoverable loops, not be treated as equivalent because both use one button. Never compensate for an uninteresting puzzle by shortening its window. Avoid strict average-attempt targets: an elegant first-attempt solve is not automatically too easy, and several thoughtful retries are not automatically bad.

## 11. Critical scorecard

These are qualitative judgments of the proposal and current evidence, not measured player outcomes.

| Dimension | Score / 10 | Principal reason | Most valuable improvement |
|---|---:|---|---|
| Core gameplay potential | 8 | Shared routes and temporal coordination produce clear, compact causal puzzles. | Validate pleasure in planning and correction on current interaction levels before adding systems. |
| Mechanic variety | 6 | Several nouns conceal repeated detour/hold decisions; flexible collection order has promise. | Require a distinct decision from each chapter and cut duplicate concepts. |
| Difficulty progression | 6 | Good resets and consolidation, but long pickup onboarding and a finite-window jump within Market Loop. | Compress recognition drills and order challenges by reasoning plus execution demand. |
| Player accessibility | 5 | Good identity and presentation foundations; mandatory timing and spatial navigation remain unresolved. | Validate deliberate play and nonvisual route inspection before new live chapters. |
| Long-term replayability | 4 | Mostly authored single-insight solutions; current configuration stars are a weak replay motive. | Introduce occasional genuinely different valid plans and assess voluntary revisits. Sixty first-time solves alone are content length. |
| Technical feasibility | 8 | Fixed-step graph engine supports bounded cargo and deterministic extensions without replacement. | Keep held-road state and signal admission isolated and precisely specified; defer queues/destinations. |
| Implementation efficiency | 6 | Roadmap has good gates but reserves extensive content and two traffic chapters before value is known. | Shorten commitments, move the cheaper two-package test ahead of signals, and allow failed chapters to disappear. |

## 12. Questions requiring my decision

Before implementation, the owner should decide:

1. **Product promise:** Is TinyRoutes primarily a relaxed planning puzzle with optional intervention, or is timed execution essential? Recommendation: relaxed planning; deliberate play has equal completion and stars.
2. **Scope:** Is sixty an aspiration or a release requirement? Recommendation: aspiration; approve a small evidence-backed pack and permit shorter chapters.
3. **Cargo baseline:** May future vans and levels remain package-free? Recommendation: yes, with explicit ready-to-deliver status. Approve fixed ownership and instantaneous collection only for a trial.
4. **Signals:** Can the two signal chapters be removed from the committed plan? Recommendation: yes; one later automatic-light experiment, with manual dispatch undecided.
5. **Scoring:** Should future stars describe route configuration or actual execution effort? Recommendation: preserve existing behavior for trials; make completion primary and defer a new optimization contract until its player value is demonstrated. Do not silently migrate old pars.
6. **Promotion:** When does the prototype become the main campaign, and what existing progress must survive? Recommendation: decide after the first expansion trial succeeds, before production navigation/save work.

These are recommendations for future authorization. This review does not request or imply permission to implement them now.

### Single best next playable experiment: coordination versus execution

**Hypothesis:** Players enjoy choosing and understanding safe delivery order; live switching adds satisfaction only when it lets them carry out that understanding comfortably. If the basic coordination is opaque or unenjoyable, packages and signals will add load without fixing the foundation.

**Use three existing boards: 7 — Merge, 8 — Hold the Loop, 9 — Split.** Briefly establish the basic controls with the existing onboarding as necessary. These boards isolate static detour planning, recoverable release, and finite-gap switching without building another mechanic. This is the next experiment; the cargo trial is contingent on its result.

**Minimal implementation requirements:** none. Use the current build, current tuning, solution files as facilitator reference and existing local logs. Add manual observation notes and participant consent for any recording. Do not modify levels or secretly slow the simulation. If a player can explain a solution but cannot execute it, offer a clearly marked facilitator-assisted attempt following their directions; this diagnoses an execution barrier but does not validate an accessible control design.

**What would make it fun:** players predict an order, see their chosen detour or release cause it, understand a failure, then choose a useful correction. On Level 8, another lap should feel like available control, not punishment. Watching success should be rewarding without being the only reward.

**What would indicate failure:** correct verbal plans repeatedly fail on input timing; players change switches blindly until they win; ✓ is repeatedly interpreted as a safety promise; loops look like a broken game; or players solve comfortably but decline another coordination puzzle because the process feels mechanical.

**Human playtest measures:** initially observe roughly five new players, including at least two infrequent game players, and separately recruit people using the intended accessibility interactions. Record unassisted attempts, explanations before Go and after failure, whether corrections address the cause, accepted versus rejected taps, missed opportunities, extra laps, Stop/Retry understanding, assistance, fast-forward context, and voluntary preference for another static/loop/split puzzle. Ask what they enjoyed and what felt outside their control. Keep observation prompts consistent and avoid coaching the solution.

**Expansion criteria:** as a directional gate, at least four of five can explain a conflict and make a causal correction on the static or loop board without solution coaching; at least three choose to play another coordination puzzle; and no recurring “I knew what to do but could not act” pattern is left unresolved for the proposed main path. These small-sample thresholds guide the next decision, not population claims. Observe whether enthusiasm belongs to planning, watching or executing, rather than merging them into one success metric.

**Abandon or redirect criteria:** if static coordination is enjoyed but the split is repeatedly an execution barrier, defer new finite-window levels and prototype deliberate play. If players understand the loop but find repeated laps tedious, stop using loops as the default replacement for signals. If even understandable static coordination elicits little interest, pause the expansion commitment and investigate the core puzzle/payoff before adding cargo. Only a positive foundation result earns the small pickup-value trial described above.
