# TinyRoutes — Multi-Van future gameplay and level roadmap

**Planning proposal · 2026-11-03 · Owner review required before implementation**

This document proposes an expansion of the current twelve-level Multi-Van game. It does not authorize implementation, create a task backlog, or change existing levels, solutions, defaults, scoring, or production behavior. Levels 13–60 below are design concepts, not authored or verified levels. Names and numbering are provisional.

## 1. Long-term gameplay vision

**Make TinyRoutes a game about composing a small, understandable delivery plan and enjoying its consequences.** The strongest expansion is to make route order matter: collect the right cargo, choose a safe path, and coordinate vans through shared space. Increase the relationships between familiar pieces before increasing the number of rules.

The preferred sequence is:

1. Preserve and validate the existing plan → Go → watch → understand → retry loop.
2. Add **one assigned package per van**, automatically collected at a marked pickup point before its existing matching house.
3. Build several good puzzles from pickup routes, crossings, detours, departure order, and the existing live switch.
4. Trial a deterministic traffic signal with a real stopping rule in a few small boards.
5. Expand only systems that demonstrably produce distinct decisions. Multiple packages are a later candidate; multiple destinations, speed classes, deadlines, and cargo transfers are optional experiments.

The desired feeling is “I see why that works” followed by “I want to watch it work.” A harder puzzle should ask the player to notice a dependency, choose which van takes a detour, or establish an order. It should rarely ask them to tap faster.

### Design boundaries

- Keep a readable portrait board within the current 5-column × 7-row coordinate envelope through this roadmap. Extra objectives compete for this space; they do not justify silently expanding it.
- Introduce one new rule at a time. A chapter begins below the previous finale's complexity, then builds back up.
- Use one or two vans for teaching. Three or four vans are occasional payoffs, not a difficulty metric.
- Preserve untimed planning, retained switch selections on retry, visible objectives, and immediate access to Stop.
- Keep live interventions sparse: at most one time-sensitive control to attend to at once in the proposed campaign.
- Separate completion from optimization. Solve the delivery problem first; stars should not turn every tutorial into a tap-accounting exercise.
- Prefer a useful detour over an arbitrary extra errand. A package should change a route decision or a traffic relationship.
- No random traffic, wall-clock signal cycles, hidden pickup requirements, or physics-driven outcomes.

## 2. Existing-system assessment

### Evidence and scope

The assessment uses the current working files, including existing in-progress changes, rather than assuming the original plan describes the implementation exactly. Focused sources:

| Source | What it establishes |
|---|---|
| [Original Multi-Van plan](docs/prototype/multi_van_prototype_plan.md) | Intended loop, presentation, prototype boundaries, and original playtest hypotheses. Some details are superseded by authored content/code. |
| [Tuning assessment](docs/prototype/mv46_tuning_assessment.md) and [playtest kit](docs/prototype/playtest_kit.md) | Recorded engineering measurements, known plan/content discrepancies, timing concerns, and missing human evidence. Rush's earlier measurements are explicitly superseded in the assessment. |
| [Twelve current levels](TinyRoutes/Resources/PrototypeLevels/) and [twelve solution scripts](TinyRoutesTests/Resources/PrototypeSolutions/) | Actual graphs, switch order, departure delays, houses, hints, and intended inputs. All 24 files were read. |
| [Level/tuning model](TinyRoutes/Prototype/MultiVanLevel.swift), [engine](TinyRoutes/Prototype/MultiVanEngine.swift), [runtime graph](TinyRoutes/Gameplay/RuntimeRouteGraph.swift), [preview tracing](TinyRoutes/Prototype/MultiVanRoutePreview.swift) | Authoritative simulation, model boundaries, and supported mechanics. |
| [Level checks](TinyRoutesTests/Prototype/MultiVanLevelTests.swift), [solution tests](TinyRoutesTests/Prototype/PrototypeSolutionTests.swift), [script runner](TinyRoutesTests/Support/PrototypeSolutionRunner.swift) | Prototype validation and deterministic solution evidence; these differ from the production validator. |
| [Gameplay screen](TinyRoutes/Prototype/MultiVanGameplayScreen.swift), [board](TinyRoutes/Prototype/MultiVanBoardView.swift), [feedback](TinyRoutes/Prototype/MultiVanFeedback.swift), [switch control](TinyRoutes/Prototype/MultiVanSwitchButton.swift), [van view](TinyRoutes/Prototype/MultiVanVanView.swift), [house view](TinyRoutes/Prototype/MultiVanHouseView.swift) | Current rendering, input, accessibility, and event presentation. |
| [Playtest logger](TinyRoutes/Prototype/MultiVanPlaytestLog.swift) | Available local attempt/event data and timestamp limitations. |
| [Legacy runtime description](docs/architecture/level_runtime.md), [single-vehicle engine](TinyRoutes/Gameplay/RouteEngine.swift), [objective types](TinyRoutes/Domain/RouteObjective.swift), [production rejection reference](docs/reference/level_validation_and_rejection_codes.md) | Existing package/objective concepts elsewhere in the repository; not Multi-Van capabilities. |
| [Miniature World port proposal](docs/prototype/miniature_world_port_plan.md), [browser visual prototype](prototypes/miniature-world/index.html), [sound notes](docs/prototype/prototype_sounds.md) | Proposed visual direction, decorative parcel delivery effect, and existing synthesized feedback assets. |

This was a source/design review. No gameplay tests, human sessions, builds, or new simulations were run for this document. Historical passing checks below are repository evidence, not fresh verification or proof of enjoyment. No external market or platform research is needed for these repository-specific proposals.

### Implemented in the current Multi-Van engine

| Area | Existing behavior | Design consequence |
|---|---|---|
| Simulation | Fixed steps, default 1/120 second; integer completed-step count plus a fractional accumulator. | Keep new rules in simulation time. Given the same tuning and tick-bound inputs, equivalent frame partitions should agree. This is not a claim of cross-platform bitwise floating-point identity. |
| Movement | One global speed, default 1.5 grid units/s; follows actual `RoadPath` geometry and carries leftover distance across roads. | Route length is already a timing tool. Measure paths through the engine, not Manhattan estimates. |
| Graph | Directed edges; ordered exits; 2–4 outgoing edges identify a switch. One active exit is shared by all vans. | One-way roads already exist. Static settings cannot send two arrivals at the same switch to different exits. |
| Vans/houses | Each van has ID, color, start and departure delay. Arrival at a house parks it; wrong color fails. Victory requires all vans parked. | No cargo, intermediate delivery, or continuing through a house exists in Multi-Van. |
| Timing | Per-van authored departure delays; delays become eligible at step boundaries. | Use staggered departure and travel distance before adding speed rules. Players cannot currently edit departure delays. |
| Switching | All switches work in planning; ordinary switches freeze during runs; listed live switches rotate if no driving van is within the inclusive lock radius. | A deliberate shared resource already exists. A committed van keeps its current edge when a switch changes. |
| Collisions | Pairwise Euclidean distance between driving vans after each step; strict distance below 0.35 fails. Waiting and parked vans are excluded. | Crossings can collide even without a shared graph node. There are no lanes, queues, reservations, overpasses, or following behavior. |
| Outcome order | All vans move; arrival failures precede collision failure in the same step; authored van order breaks arrival/pair ties. | Additions must specify boundary behavior and preserve old-level semantics. |
| Retry/Stop | Reset van motion and run time; keep current switch selections. Retry retains the failure point until Go. | Reset future cargo/signals too, while keeping the plan. Stop is a restart into planning, not a pause. |
| Preview | Traces selected roads to matching/wrong house, dead end, or 40-edge limit; driving traces follow the committed edge and remaining route. | Shows routing, not future timing, collisions, or scripted live changes. A checkmark is not a safety guarantee. |
| Feedback | Single-drain engine event stream; sound, configurable haptics, delivery combos, win stars/confetti, crash effects, rejected-switch feedback and failure copy. | New semantic events can feed this path; animation completion must never advance gameplay. |
| Presentation | Flat SwiftUI board, route lines, barriers, color-plus-symbol vans/houses, turning indicators; board-style selection and low-power handling. | The native diorama selection currently renders the flat stand-in with a 3D badge. A full diorama is still proposed. Turning indicators are not traffic signals. |

**Scoring discrepancy to preserve and resolve deliberately:** the source plan describes planning changes plus accepted live taps. The engine actually computes cyclic distance from initial settings to the **current** switch configuration. It does not accumulate live taps. Rush and Big Delivery have five/seven physical inputs in their scripts, yet finish at par three/five because their live switch returns to its initial setting. Do not design future pars as though input-history scoring already exists. Keep this behavior during an initial pickup trial; decide the long-term scoring contract separately before adding scored signal inputs.

### What the twelve levels actually teach

“P” lists planning node taps in script order, including repeated taps; “L” lists simulation timestamps. These are existing script facts, not new solutions.

| Level | Existing lesson and meaningful decision | Recorded solution; par |
|---|---|---|
| 1 — Go! | One van; zero-input demonstration of the payoff. | P: none; L: none; par 0. |
| 2 — Pick a Lane | Change a two-way switch away from a barrier. | P: `switch`; no L; par 1. |
| 3 — Two Turns | Correct two sequential switches; distinguish harmless looping from a barrier. | P: `loop_switch`, `house_switch`; no L; par 2. |
| 4 — Roundabout | Cycle a three-way switch twice to the matching house. | P: `switch` twice; no L; par 2. |
| 5 — Two Colours | Fix independent red/blue routes that initially swap houses. | P: `red_switch`, `blue_switch`; no L; par 2. |
| 6 — Convoy | Shared start, Blue delayed 1.5 s; opposite live exits needed. Live input is already introduced here. | No P; L: `switch` at 2.75 s; par 1. |
| 7 — Merge | Matching route previews can still collide; Red's longer route separates arrivals. | P: `route_switch`; no L; par 1. |
| 8 — Hold the Loop | Correct entry; keep Red looping until Blue clears, then release. Missing an opportunity can be recoverable. | P: `entry_switch`; L: `loop_switch` at 5 s; par 2. |
| 9 — Split | Correct Blue's entry; change a shared live exit after Red passes. | P: `entry_switch`; L: `switch` at 2.25 s; par 2. |
| 10 — Three's Company | Three independent matching decisions, including a barrier trap; consolidation without live input. | P: `red_switch`, `blue_switch`, `yellow_switch`; no L; par 3. |
| 11 — Rush | Blue detour, shared live split, Yellow's three-way correction. | P: `route_switch`, `yellow_switch` twice, `split_switch`; L: `split_switch` at 4.95 s; par 3. |
| 12 — Big Delivery | Four vans, five switches; distinguish hold/shortcut/detour and coordinate the live split. The intended solution uses the detour, not loop release. | P: `red_switch`, `route_switch` twice, `yellow_switch`, `green_switch`, `split_switch`; L: `split_switch` at 5.25 s; par 5. |

The tuning assessment records all twelve winning at par. It also records no supplied human session evidence. Convoy's approximately 0.967 s winning window is narrower than Split's approximately 1.417 s; current Rush's documented window is approximately 0.858 s after its geometry correction. These are simulation windows, not measured human response times. Constant 2× playback halves their wall-clock duration. The older Rush timing table in the assessment must not be reused as current geometry evidence.

**Implication:** Level 13 should be a calm conceptual reset after Big Delivery, not a fifth van or another tighter live window. Promotion into the main game remains a separate product decision after human validation.

### Existing validation and its limits

Prototype tests check duplicate node/edge IDs, consistent ordered outgoing references, at most four exits, finite whole-number node coordinates within x=0…4/y=0…6, existing endpoints, road total length at least one unit, valid initial/live switches, existing starts, exactly one matching house per van color, unique house nodes/colors, and terminal houses. Solution verification applies ordered planning taps, stable time-sorted live taps, default tuning, and a 120-second harness horizon; it requires a win at authored par.

These checks are largely test-side checks, not a comprehensive `MultiVanLevel` load-time validator. The shared graph builder checks edge endpoints and constructs geometry; it does not supply all authoring checks. The inspected prototype validator does not itself enforce every product constraint: explicit 1–4 van count, unique van IDs/colors, finite nonnegative departure delays, nonnegative par, pickup reachability, visual crossing clarity, or a useful human timing window. Nor does a total-length check prove each visible segment has sufficient space. These are future validation needs, not claims that the current corpus is defective.

The production editor/generator has more extensive package-state and readability rules, but it targets another runtime/schema. Its rejection codes and solution search cannot be assumed to validate Multi-Van. Reuse relevant graph/geometry checks selectively; do not migrate Multi-Van to the older gameplay loop to obtain them.

Expansion also meets deliberate twelve-level assumptions: prototype validation asserts the exact 1–12 resource list, and navigation tests explicitly expect Next after 12 to return to the list. Discovery itself sorts canonical `level_` files and is not the main limit. A future trial must have a deliberately isolated discovery/validation set, or explicitly revise corpus-count, script-coverage and navigation expectations when new levels are accepted. Do not disable legacy assertions merely to get an experimental file loaded. No such changes are made here.

### Packages: current reality versus reusable precedent

- **Multi-Van gameplay:** no pickup definitions, cargo state, package-conditioned win requirement, or pickup event exists. The browser miniature-world reference tosses a parcel on delivery as decoration. It does not prove collection support in the native engine.
- **Separate single-vehicle system:** `RouteEngine` supports pickup/objective progression; shared edge models contain before/after-package and ordered-objective availability rules. Multi-Van copies those edge fields into its runtime graph but does not evaluate them when departing, rotating, or tracing previews.
- **Reuse opportunity:** use existing geometry, identity conventions, and event patterns. Review the older objective semantics for lessons. Do not reuse its global package Boolean or global road normalization for multiple vans: Red collecting cargo must not silently alter Blue's route.

## 3. Future mechanic comparison

Complexity is relative to this codebase: **content-only** uses current rules; **small** adds a bounded rule/model field; **moderate** adds persistent runtime state across engine, validation, previews and UI; **major** changes central delivery/movement assumptions. These are scope judgments, not schedule estimates.

| Mechanic | Architecture class | Player learning | Recommendation |
|---|---|---|---|
| One assigned pickup before existing house | Moderate subsystem addition | Low | First new mechanic. |
| Multiple pickups for one final house | Small extension after cargo; moderate from today's engine | Medium | Trial later, initially two packages in either order. |
| Multiple destinations per van | Major architectural change | Medium–high | Defer from the core 13–60 commitment. |
| Automatic traffic lights | Moderate subsystem addition | Medium | Second major experiment, after pickup value is proven. |
| Timed intersections | Same subsystem as automatic lights; major if full lane traffic is required | Medium–high | Express as signal phases, not another mechanic. |
| Player-controlled signals | Moderate extension of signals | Medium | Prefer deliberate release order to frantic toggling. |
| Static road closures | Supported content; small presentation addition for explicit closed-road signs | Low | Use sparingly as topology constraints. |
| Dynamic road closures | Moderate state/availability addition | Medium | Defer; overlaps lights and can invalidate committed routes. |
| One-way roads | Supported by current directed graph; small optional sign work | Low | Teach direction more clearly; no new movement system. |
| Different vehicle speeds | Small movement change, moderate validation/UI impact | Medium–high | Optional late experiment; use route lengths/delays first. |
| Priority deliveries | Small for delivery precedence; moderate for deadlines/scoring | Medium | Prefer optional relative ordering; defer timers. |
| Additional routing/switch puzzles | Supported for existing switch/loop patterns | Low–medium | Primary source of inexpensive depth. |
| Coupled/one-use/conditional switches | Moderate; depends on exact rule | Medium–high | Defer until ordinary shared switches stop yielding distinct puzzles. |
| Cargo transfer/any-van assignment | Major architectural change | High | Do not implement in the first campaign expansion. |

### 3.1 One assigned pickup before delivery

**Problem and pleasure:** the shortest route to a matching house is no longer necessarily valid. The player must compose start → pickup → house and can watch an empty van become visibly loaded. This gives a reason for a detour beyond “avoid the crash.”

**Combination and changes:** combine with static forks first, then crossings and live release. Add package definitions, per-package lifecycle/per-van cargo, required-package delivery checks, preview objective tracing, feedback and validation. No new motion or player pickup button is needed. Implementation is moderate; the player rule is low complexity if shape/color matches are consistent.

**Teaching and deterministic tests:** show one bypass and one pickup route in Level 13; add a downstream route decision in 14 and a second van in 15. Test correct pickup, bypass failure, mismatched van passing a pickup, duplicate visits, start-node pickup, reset, preview parity, and frame-partition equality. Section 4 specifies the contract.

**Accessibility:** label pickup, assigned van, cargo and unmet requirement in words. Carry the existing symbol onto the package without hiding the van's symbol. Announce collection once; a chime alone is insufficient.

### 3.2 Multiple package pickups

**Problem and pleasure:** visit two useful branches before the final house; choose visit order or which route stays clear. A two-item checklist can make a compact board feel more interconnected.

**Combination and changes:** reuse package IDs/lifecycles, allow more required IDs and increase the tested cargo limit from one to two. First version accepts either pickup order and unloads both at one house. Do not add weight, slot sorting, or inventory management. A forced pickup sequence adds a separate objective-order rule and needs additional preview/error semantics. Small after the first cargo system, moderate from today; player learning is medium.

**Teaching and tests:** one van, two clearly numbered items, generous route choices; later combine one order choice with a crossing. Verify both legal orders, missing either item, repeated visits, no duplicate ownership, exact delivery set, and atomic reset. If the board has only one obvious chain, use it once as teaching rather than repeat it as puzzle content.

**Accessibility:** expose “1 of 2 collected” and named remaining stops. Avoid two tiny roof boxes as the only distinction. Do not require remembering an unspoken order.

### 3.3 Multiple destinations

**Problem and pleasure:** find an efficient tour and decide which customer to visit first while other vans use shared space. This can create richer route planning than gathering two objects for one terminal house.

**Combination and changes:** houses are currently terminal and parked vans are excluded from collisions. Intermediate delivery requires nonterminal service stops, package-to-destination mapping, partial unload, per-van outstanding work, revised victory/combo/house state, and continuing movement. Arrival at the wrong customer needs a new explicit rule. This is major; player learning is medium–high. It should follow proven multi-package puzzles, not launch with pickup.

**Teaching and tests:** an optional one-van two-stop experiment, no traffic or live input; then offer either order before any mandatory sequence. Test partial unloading, continuing after the first delivery, no early win, repeat-stop idempotence, unrelated cargo retained, correct final parking, and moving-versus-serving collision behavior.

**Accessibility:** announce the next stop and remaining stop count; provide an inspectable itinerary. Distinguish a service stop from a terminal home by shape and label, not color alone. Defer if these markers crowd the board.

### 3.4 Automatic traffic lights

**Problem and pleasure:** a short route may wait while a longer route stays in motion; an automatic hold can create a useful arrival order. The player predicts the schedule through visible phases instead of tapping on a deadline.

**Combination and changes:** use directed approach IDs, safe stop positions, tick-derived phases and occupancy clearance. Introduce stopped-but-collidable vans; update movement, locks, previews, indicators, logging and level validation. Moderate. Player learning is medium because green means permission to enter a specific area, not guaranteed delivery safety.

**Teaching and tests:** one isolated red light that automatically releases, plus a real route choice; then a two-approach crossing. Test stop accuracy, no overshoot on a large frame, exact red/green boundary ticks, clearance, restart phase, no stalled-time accumulation, and collision with a held van. Section 5 defines the proposed scope.

**Accessibility:** stable “stop/go” labels and approach names; light shape/position plus text, not red/green alone. Do not announce every countdown tick. Automatic lights must be solvable through planning without hearing a time-critical announcement.

### 3.5 Timed intersections

**Problem and pleasure:** two approaches take turns. The route choice determines whether a van catches this cycle or the next. This can make route length meaningful without a new speed class.

**Combination and changes:** use the same signal group and phase table as automatic lights. Do not add a separate timed-junction type, arbitrary opening windows, or realistic traffic phases. Start with two nonconflicting approach groups plus all-red clearance. Moderate within the signal subsystem; major only if expanded to lanes, permissive turns, or queue traffic, which is not recommended.

**Teaching and tests:** teach a single light first; then one crossing and finally offset signals. Verify phase wraparound, Go always resetting phase, an entered van clearing after red, and no opposing admissions during occupancy. A missed phase must mean a short repeatable wait, not instant failure.

**Accessibility:** inspectable phase order, approach-based naming, and an optional concise phase-change announcement. Do not require estimating a moving progress ring or reading several countdowns simultaneously.

### 3.6 Player-controlled traffic signals

**Problem and pleasure:** choose who gets the road first. A van held safely at red lets the player act when ready; the puzzle is release order rather than reflex speed.

**Combination and changes:** build on automatic signals; add distinct signal actions and requested-versus-effective state. Switches select exits; signals admit traffic. The engine must defer an unsafe conflicting release until clearance. Moderate after signals; player learning is medium. Begin with one held van per approach and no queues.

**Depth check:** indefinite holding can trivialize ordinary collision puzzles: send one van all the way home, then the next. Do not call release order a puzzle if both serialized orders work equally well. A trial can instead use a plainly visible on-road held van that obstructs another route outside the signal's protected crossing, so clearing that van first changes what is safe. This uses held-van collision rules, not a new priority objective. Teach that obstruction explicitly and accept any other safe order/timing. If useful order choices require contrived blockages or timers, drop manual signals from the main path and keep automatic lights or the existing loop.

**Teaching and tests:** two vans wait at separate stop lines; release the one whose route frees the useful path, then the other. Add packages only after that rule reads clearly. Test idempotent requests, requests during occupancy, same-tick action order, rejection without effects, held-van lock behavior, and replay under 2× playback.

**Accessibility:** a named 44-point control with “requested” and “effective” states; allow inspection while the simulation is paused in the proposed assist mode. Never require two sequential VoiceOver activations within a short passing gap.

### 3.7 Road closures

**Problem and pleasure:** remove an attractive shortcut and make the player recognize another connection. This is useful spatial variety if the remaining route contains a real decision.

**Combination and changes:** permanent closures need no dynamic engine rule: omit an unavailable connection, or route a visible branch to an existing barrier. A closure graphic should sit on a genuinely closed spur, not a decorative road that still carries vans. A visibly disabled through-edge needs a small model/presentation addition. Dynamic closure needs explicit edge state, preview availability and commitment semantics; moderate. Do not assume existing package-edge fields are honored in Multi-Van.

**Teaching and tests:** a clearly blocked shortcut and two remaining paths, then combine with package location. Verify no traversal of an omitted edge, preview/barrier agreement, a reachable solution, and meaningful alternative choices. For any later dynamic version, test closure while a van is already on the edge and reopening at exact ticks. Recommendation: static content only for now.

**Accessibility:** expose the closed connection and the affected endpoints in the route summary. A striped prop alone does not communicate topology nonvisually.

### 3.8 One-way roads

**Problem and pleasure:** a nearby pickup may require approaching from the far side. Recognizing a return path can be a satisfying spatial insight.

**Combination and changes:** directed edges already enforce this. Use restrained direction arrows and route descriptions as presentation work; do not add opposite overlapping edges, bidirectional lane physics, or U-turn controls. Implementation is content-only plus small optional UI work; learning is low when direction is legible.

**Teaching and tests:** a single directed loop with a bypass choice, then a pickup on its return leg. Test no implicit reverse traversal, agreement among arrows/preview/movement, and reachability from the pickup to the house.

**Accessibility:** describe “from the square to the depot” rather than only “up.” Keep board coordinates available, but give important places readable names.

### 3.9 Different vehicle speeds

**Problem and pleasure:** a faster van needs a longer route, or a slower van must depart first. Relative speed can change the useful arrival order.

**Combination and changes:** one validated speed multiplier per van is a small movement change. Readability, collision sampling, signal clearance, live windows, turn-indicator timing, solution margins and logging make the total impact moderate. Speed differences should be fixed and visible, with at most two classes. Player learning is medium–high because route previews currently omit time.

**Teaching and tests:** an optional two-van board with a simple short/long route choice and no live tap; then compare a crossing. Test actual distance per tick, catch-up collisions, large-frame partition parity, bounded maximum displacement, and fixed delays interacting with each speed. Prototype only if equal-speed route design feels exhausted.

**Accessibility:** a named speed class on each van and route summary; animation rate cannot be the only cue. Do not add a “fast van” that merely makes controls less accessible.

### 3.10 Priority deliveries

**Problem and pleasure:** choose which van should finish first, potentially giving another a detour. Relative order can introduce a dependency without a global countdown.

**Combination and changes:** a required delivery-precedence pair and exact delivery ticks is a small rule extension, including same-tick semantics. Deadlines, expiring packages, optional medals and related scoring are a moderate addition. Player learning is medium. Recommend testing optional relative priority before any deadline; keep both outside the initial campaign commitment.

**Teaching and tests:** two equally visible destinations, an explicit “circle before triangle” requirement, and broad route alternatives. Verify early/late/equal-tick results, correct cargo still required, deterministic ties, failure copy, and retry clearing order history. A deadline version would additionally need inclusive/exclusive boundary tests and sufficient route slack.

**Accessibility:** readable and spoken precedence, never a flashing urgency badge alone. No sound-only alarm or requirement to finish a screen-reader announcement before time expires.

### 3.11 Additional switch and routing challenges

**Problem and pleasure:** shared exits, bypasses, route-length tradeoffs, repeatable holding loops and three-way choices deepen the existing language. A route can be locally attractive yet make another van's route unsafe.

**Combination and changes:** most are content-only. Two static visits to one switch always use the same selected exit; a design requiring different exits needs a live switch or a distinct downstream fork. Avoid faking per-van routing at a shared node. Mechanically coupled switches, one-use switches, cargo-sensitive exits and automatic switching require explicit state/action rules and are moderate additions, not free content.

**Teaching and tests:** first make one shared choice affect two routes, then combine it with a known package decision. Enumerate small static configuration spaces, test the intended interaction's negative variants, and sweep any live window. For coupled controls, additionally test atomic changes and locks at every affected node. Defer special switch species until there is a concrete level they uniquely improve.

**Accessibility:** give every control a stable name, selected exit, affected routes and lock reason. Coupled controls must announce all affected switches. Increasing rotation count is not meaningful difficulty by itself.

### 3.12 Inter-van package assignment and transfers

**Problem and pleasure:** vans could divide collection work or relay a package across the map. This would turn routing into a small logistics problem.

**Combination and changes:** shared stock, assignment, capacity conflicts, transfer stops, ownership transactions and simultaneous claims are major changes. They increase both player memory and model complexity. They are not prerequisites for enjoying pickup with multiple vans.

**Teaching and tests if revisited:** a stationary depot transfer between two vans before a moving relay; test unique ownership, conservation of packages, simultaneous claims, full cargo, reset and transaction ordering. Do not prototype moving handoffs first.

**Accessibility:** an inspectable ownership list and explicit transfer action/state would be necessary. Recommendation: fixed ownership throughout Levels 13–60; no steals, swaps, or package races.

## 4. Package pickup architecture proposal

### Minimal first playable contract

**One assigned package, one pickup point, one existing terminal house per participating van; automatic pickup on node arrival; no loading delay.** This is a moderate addition with deliberately narrow rules.

Proposed authored information, described conceptually rather than as JSON:

- A package has a stable ID, pickup node ID and assigned van ID.
- Each van has an explicit required-package ID list. First-pass validation allows zero for legacy levels or exactly one for pickup-enabled vans. Package ownership is keyed by van ID, never inferred solely from color.
- The existing matching house remains the destination. Package destination IDs are unnecessary until multiple destinations are approved.
- Package identity uses the assigned van's color and symbol. Only one package per pickup node in the first trial; do not colocate pickups with starts, houses, or switches in authored teaching boards.
- Old files omit the package fields and retain exactly their existing behavior. An explicit future schema version separates new content and reports unsupported versions; missing version means the current legacy Multi-Van contract.

Proposed runtime state:

| Entity | State | Invariant |
|---|---|---|
| Package | At pickup, carried by assigned van, delivered | Exactly one lifecycle location; no duplication on revisits. |
| Van | Carried package IDs; required-package relationship from level data | First version has capacity one and cannot take another van's cargo. |
| House | Delivery result derived from successful arrival/objective completion | Cargo checks pass before a delivery event or success marker. |

Using IDs and explicit lifecycle state now avoids a global Boolean without building a general inventory framework. One engine-owned collection is authoritative; any per-van lookup must be derived or updated atomically from it. No independent UI cargo state.

### Arrival, reset, and preview semantics

1. On entering a node, including a valid start-node arrival, collect any available package assigned to this van exactly once. In first authored boards, separate roles make the order visually obvious; tests still cover unusual colocations.
2. Passing another van's package leaves it untouched and does not fail. Its ownership marker remains visible. Do not automatically steal a wrong package or reroute the van.
3. At a wrong-color house, preserve wrong-house failure precedence. At the matching house with a missing required package, fail with a distinct missing-package outcome identifying van, package and pickup. A terminal house cannot sensibly let the van continue; the preview should expose this before Go.
4. At a matching house with all required cargo, atomically deliver cargo, park, and emit the existing delivery/completion sequence. Cosmetic unloading may continue afterward without delaying victory.
5. Pickup is instantaneous, consumes no travel distance, and preserves leftover movement. Cargo does not change speed or collision radius.
6. Keep the current arrival-failure-before-collision convention. A pickup followed by a crash in the same tick may emit collection then crash; failure cancels transient celebration, and retry resets all package state. No post-failure animation may mutate ownership.
7. Go, Stop, Retry and Replay restore package availability and clear run cargo/delivery state as appropriate. Keep switch selections under the existing contract. No package progress survives a failed run.

The preview walks a **temporary per-van cargo state** along the currently selected route. It recognizes pickup visits and distinguishes “correct house, missing package” from “wrong house.” It never collects anything in the real engine. During a run, it starts with real carried cargo and the committed current edge. Recompute when cargo/objective state changes even if the current edge/status happens to remain unchanged; current preview invalidation does not cover this case.

Use an inspectable route summary such as “Circle pickup → circle house,” plus an unmet-pickup marker. Preserve the distinction between route validity and traffic safety. A loop controlled by a future live tap can still end in “loop/current route unfinished”; do not falsely predict a scripted release or mark it as an inevitable failure.

### Presentation and feedback

- The pickup marker visibly empties on collection; the van gains a small package attachment that leaves its identity symbol and turning indicators readable.
- The chip changes from “pickup needed” to “carrying,” and the house keeps a visible requirement indicator until delivered.
- Add an engine pickup event carrying package ID, van ID and exact simulation tick. Reuse the single dispatcher for a short distinct sound, optional haptic, small pickup motion and VoiceOver announcement.
- With Reduce Motion, change the marker/cargo/chip immediately and retain text feedback. Collection never depends on a flying parcel animation.
- For the native flat board, validate package readability first. A later diorama must consume identical engine state and controls; the browser parcel effect is a visual reference only.

### Expandability without premature systems

**Next candidate:** two assigned packages in either order, one terminal house, no cargo transfer. Reuse ID sets and lifecycle transitions, raise the approved capacity, and add count/remaining-item UI. This requires fresh validation, not merely accepting larger arrays.

**Separate later decisions:** mandatory pickup order, multiple destinations, pickup service times, capacity routing, shared depot stock, and any-van delivery. They should not be hidden extension flags in the initial package release. Cargo-conditioned road availability is also separate: keep physical switch selections shared, and never normalize the global graph from one van's cargo state.

### Deterministic acceptance coverage

- Collect exactly once at the correct node, including start-node pickup; crossing a drawn road near the marker is insufficient.
- Mismatched van leaves the package available; multiple vans retain independent state.
- Matching house without cargo fails with useful IDs and no delivery event; correct cargo succeeds once.
- Revisit a pickup, restart, Stop, Retry and Replay: no duplicates or state leakage; retained switch settings remain correct.
- Two pickups in one movement step and pickup immediately followed by house: process actual traversal order, not dictionary iteration order.
- Same-tick pickups by different assigned vans produce stable event ordering; no hidden competition.
- Preview predicts objective validity without mutating engine state; a live flip changes only uncommitted route portions.
- Equivalent regular/uneven frame budgets and identical tick inputs match package state, positions, outcomes and ordered events; test normal, 2× and mixed playback separately.
- Invalid references, duplicate IDs, inconsistent required/assigned relations, unreachable pickup/house, unsupported capacity and unsupported schema versions fail validation. Level 1–12 decoding and legacy behavior remain regression fixtures.

## 5. Traffic-light architecture proposal

### Recommended scope

**First trial: one automatic signal on a directed approach, a safe holding position, and at most one van waiting on that approach.** Then trial two exclusive approaches at one crossing. Player release controls come later. Do not start with an urban traffic simulator.

Signals govern permission to enter a road conflict area. They do not rotate a route switch. A geometric crossing can use separate directed routes; a shared graph node still has one shared selected exit. A signal cannot magically give different vans different exits.

### Proposed model and authoritative state

| Concern | Proposed contract |
|---|---|
| Authored approach | Identify incoming directed edge, stop distance along that path, relevant conflict area, and the signal group that controls admission. |
| Phase table | Ordered allowed approach groups and positive integer tick durations, including all-red clearance. All cycles start from the same authored phase at Go. |
| Runtime phase | Derived from completed simulation ticks, never a `Timer`, wall clock, animation, or view lifetime. |
| Held van | A distinct on-road held state, or equivalent explicit movement permission. It stays at the stop line, remains collision-active, and remains relevant to nearby live-switch locking. It is not the current off-road departure-waiting state. |
| Commitment | Once a van has entered under green, it finishes the crossing even if the phase changes. No teleporting back or braking inside the junction. |
| Clearance | Track admitted vans until their paths clear the authored conflict area plus required separation. A conflicting green is delayed until safe. A fixed all-red duration is also validated against path travel, but does not replace occupancy protection. |
| Manual request | A distinct signal action requests the next allowed approach group. Requested state and effective state can differ while occupied. No unsafe instant opposing green. |
| Restart | Go restarts phase/occupancy/held state deterministically. Retry keeps route selections; manual signal requests are reset to authored initial state in the first trial. |

The conflict area can be a simple authored geometric region for the first crossing, validated against both actual `RoadPath`s. This is bounded signal state, not a general-purpose reservation service. If safe clearance needs complex region chains or lane queues, reduce the trial board before enlarging the subsystem.

### Movement, collisions and live switches

- Movement consumes only available distance up to the stop line while red. Held time accumulates no travel credit; a van never leaps forward when green arrives.
- Check admission at a defined tick boundary and define a van exactly at the line as eligible on the first permitted tick. Within-tick leftover movement must respect a newly encountered stop line.
- Preserve current collision detection for moving vans and add held-vs-moving and held-vs-held pairs. A signal is not crash immunity. A rear van can hit a held van unless the board prevents it.
- Initially forbid two vans reaching one holding approach before the first clears. Validate this over intended runs and representative wrong plans. Use separate holding bays, not automatic queues. An explicitly unsafe alternative may fail with clear feedback; ordinary valid use must not surprise the player with unavoidable rear-end crashes.
- Held vans near a live switch must count toward its lock. Place the first stop lines well away from switches. If a design requires changing the exit while a van waits, move the bay upstream so the existing safety radius permits it; do not silently waive the lock.
- Keep current sampling for bounded existing speeds. Before admitting faster speed classes, prove the displacement bound and test near-miss crossings; adopt swept checks only if the new bounds require them.

### Tick/action order

For signal-enabled levels, document and test one order: apply stable-ordered commands at the tick boundary; evaluate scheduled phases and safe effective admissions from authoritative occupancy; move all vans with those permissions; process arrivals/objectives; evaluate failures/collisions; update cleared occupancy for subsequent admissions; resolve victory; publish ordered semantic events. A van clearing during a tick may permit the opposing approach on the next tick. Conservative clearance is preferable to iteration-order admission.

Inputs at the same tick retain script order. A request cannot override occupancy checks. Preserve the legacy path's established outcome/tie semantics rather than rewriting all simulation behavior to add signals. Use feature-disabled regression traces to catch accidental changes.

### Preview, UI, scripts, and logging

- Route previews remain spatial. Show a stop marker and “automatic wait” or “release needed” in the route summary. Do not add an exact future timeline to every board.
- Show effective stop/go with shape/text; show a pending manual request distinctly. A full red cycle is not a failure; the next legal opportunity should be visible.
- Reuse the input/event boundary with a typed signal command. Keep current plan-tap/live-tap scripts compatible; add a versioned action stream only when the signal trial needs it. Record integer ticks internally; timestamp compatibility adapters specify rounding to the next eligible tick.
- Emit exact-tick `held`, `released`, requested/effective phase and clearance events for testing/analysis. Do not infer arrival time from existing dispatch-batch timestamps.
- First signal experiments leave signal taps outside the existing configuration-based star calculation and log them separately. This is provisional and must be disclosed to testers. Decide a unified scoring policy before authoring scored manual-signal chapters; do not quietly add taps to `changeCount`.

### Deterministic acceptance coverage

Validate reference integrity, finite in-edge stop positions, reachable holding bays, positive phase ticks, permitted approach sets, phase wraparound, clearable conflict paths, and feature/schema compatibility. Test the tick before/at/after every phase boundary; crossing occupancy across green→red; large frame partitions; simultaneous arrivals; stop/restart resets; rejected and repeated manual requests; held-van collisions and switch locks; no progress while held; and all-delivered only after cargo/destination requirements.

For two approaches, deliberately request an opposing release before, during and after occupancy. No conflicting admission is legal. Check a van stopping at the line with exactly zero leftover distance and a van reaching two controlled points within one external frame. Verify board changes, backgrounding and animation suppression cannot change phase or occupancy.

## 6. Level-quality and accessibility contract

Every concept in Sections 7–8 inherits this contract. A concept is not accepted merely because a winning script exists.

| Gate | Proposed requirement before a level joins a pack |
|---|---|
| Learning/puzzle objective | State the single insight in one sentence. Remove a rule if it does not support that insight. |
| Meaningful decision | At least one plausible alternative changes objective validity, traffic order, or a clearly explained optimization. Avoid decorative switches with irrelevant choices. |
| Understandable solution | A player can explain the cause and fix without knowing exact timestamps. Accept multiple understandable solutions unless a specific constraint is taught. |
| Teachable failure | A representative wrong choice has a predictable cause: missing pickup, wrong house, collision at a visible crossing, blocked spur, or wrong release order. Safe waiting is not mislabeled as failure. |
| Timing | No live tap in pickup tutorials. New campaign live windows target at least 2 simulation seconds at normal speed with visible cues; repeating-loop release should allow another opportunity. This is a proposed authoring target, not a tuning change or proof of accessibility. Redesign geometry if it cannot meet it. |
| Attention | One time-sensitive decision at once; celebrations cannot cover it. Disable or release fast-forward before a necessary intervention where the player chooses assistance; never assume a wide simulation window remains wide at 2×. |
| Duration | Aim initially for roughly 6–15 seconds of motion for ordinary boards and under roughly 20 seconds for finales, excluding deliberate manual holds. These are trial targets, not gameplay time limits. Shorten roads or remove errands if observation shows empty waiting. |
| Readability | One screen, clear true connections, visibly separate nonconnections, unobscured markers and 44-point controls on the smallest intended phone. A geometric crossing is a collision point unless an explicit future overpass system exists. |
| Feedback | A collection, clearance, or sequence payoff reinforces the taught rule. Reduce Motion retains all information through stable state/text. Sound and haptics are optional reinforcement. |
| Validation | Winning script, relevant negative variants, timing-margin sweep where applicable, and deterministic replay. Establish par by bounded search/enumeration when feasible; otherwise call it provisional rather than claiming minimum. |
| Human understanding | Observe a player explaining a failed attempt and choosing a correction. Log assistance separately. Do not equate a successful replay, five-person directional trial, or a small mean attempt count with population-level validation. |

### Accessibility dependencies

The current game provides color-plus-symbol identity, labels for vans/houses/switches, selected exit/lock descriptions, focus changes for results, Reduce Motion handling, and a VoiceOver fast-forward toggle. These are useful foundations. They do not establish that the spatial puzzle or live timing is fully accessible.

Before shipping new timing content, propose an **optional deliberate-play mode**: pause without resetting at tick boundaries, inspect a stable board/route list, issue the same otherwise-legal commands, and resume. The clock, motion and signal schedule freeze together; it is distinct from existing Stop. No commands bypass physical switch locks. It benefits VoiceOver users and anyone who prefers planning between actions. This requires an input/frame-driver/UI extension and approval; it is not currently implemented.

Do not automatically pause every time accessibility focus changes. Keep focus stable as vans move; provide a separate status/route summary rather than many announcements. Player-controlled red lights should allow indefinite inspection before release. Build a logical focus order for named pickups, vans, houses and controls, with optional route-based navigation. Test Dynamic Type, muted play, Reduce Motion, larger controls, color vision differences and VoiceOver on device. No star penalty is recommended for deliberate-play assistance; that scoring decision requires approval.

Until this mode or an equally usable alternative is validated, timing-dependent new chapters are not ready to ship as an accessible main path. Static pickup chapters can still be evaluated independently.

## 7. Chapter roadmap — Levels 13–60

These eight six-level neighborhoods cover 48 proposed slots. Only the first pickup trial is a firm next recommendation. Signal and multi-package chapters are conditional on their playable milestones. Names do not imply additional currencies, narrative systems, map technology, or engine requirements.

| Levels / neighborhood | Mechanics and introduction | Tutorial/difficulty progression | Final challenge | Approval/fallback |
|---|---|---|---|---|
| **13–18: Parcel Row** | New: one assigned pickup per van. Existing: static switches, matching, directed routes and crossings. | One van/one fork → downstream decision → two vans → ownership → pickup detour as spacing → two-van composition. No live taps. | **18, Neighborhood Round:** both pickup tours work together at one crossing; choosing who takes the longer tour establishes safe order. | Recommended first chapter only after a three-board pickup trial. |
| **19–24: Market Loop** | No new system. Combine pickups with existing live exits and holding loops. | One loaded van/one live exit → collection before sharing space → two-vans shared split → quiet static consolidation → repeatable loop → three-van finale. | **24, Saturday Deliveries:** two interacting tours and one simple independent delivery; one clearly cued live change. | Requires broad windows and accessible intervention support before release. |
| **25–30: Canal Streets** | No new motion rules. Explicitly teach existing one-way direction; introduce static closure presentation. | Read direction → separate entry/return → closed shortcut → choose detour owner → return beside the entry through a distinct junction → spatial finale. | **30, Canal Circuit:** two pickups on directed routes around a closed spur; both crossings clear by the planned route choices. | Omit closure signage if it would require a new disabled-edge model; existing barriers/absent links suffice. |
| **31–36: Signal Square** | Conditional new subsystem: automatic stop/go and exclusive crossing phases. | One automatic hold with a meaningful route choice → crossing alternation → select wait versus detour → add cargo → offset phase comparison → two-van finale. No manual signals or live-switch deadline. | **36, Green Wave:** choose pickup routes that work with two visible signal phases rather than race them. | If signals fail their gate, use the fallback curriculum below. |
| **37–42: Depot Junction** | Conditional: player release requests using the approved signal subsystem. | One release-order choice → request during clearance → cargo-first order → downstream consequence → quiet planning level → finale. | **42, Dispatch Desk:** two vans, separate holding bays and one signal group; release order plus one static route decision. | Requires scoring decision and deliberate-play accessibility. No automatic queues. |
| **43–48: Two-Parcel Gardens** | Conditional: two packages assigned to one van, either pickup order, same terminal house. | One van/two choices → show both orders → second van → collection tour changes traffic order → simple consolidation → two-vans finale. | **48, Garden Collection:** choose an order for the two-item tour that leaves the crossing free for the other van. | Trial before accepting six slots. If repetitive/cluttered, retain one package and make alternate tour choices matter through traffic. |
| **49–54: Old Town Routes** | No new required mechanics. Deliberate recombination, emphasizing which van takes the useful detour. | Return to two vans → shared configuration constraints → distinguish safe waiting from bad loops → separate live/static commitments → three vans with reduced input load → mastery board. | **54, Town Routes:** one dependency between each pair of vans, revealed in sequence rather than three simultaneous emergencies. | Multiple destinations, priority deadlines and speed classes remain optional side experiments; not prerequisites here. |
| **55–60: City Delivery Day** | No new rules. Integrate only systems retained after their trials. | Readable remix → alternative valid plans → dependency ordering → staggered three-van work → four-van rehearsal → final composition. | **60, TinyRoutes:** four readable deliveries arranged in two episodes; at most one active intervention to attend to at once. | If four cargo tours cannot fit cleanly, use three vans. Do not enlarge the board or add rules to justify a finale. |

### Later-level concepts and acceptance intent

Each row supplies an objective/decision, an intended solution pattern and a failure lesson. All also require the timing, feedback, accessibility and validation gates in Section 6. Exact geometry, timing, par and solution scripts await authoring and simulation.

| Level / working name | Objective and player decision | Intended pattern; failure lesson; visual payoff |
|---|---|---|
| 25 — Follow the Arrows | Learn that geographic proximity does not imply reverse access. Choose the pickup's valid approach. | Route around the directed block; the apparent reverse shortcut is absent, not secretly rejected. Preview explains direction; cargo attaches on the return side. |
| 26 — In and Out | Plan separate entry/exit paths around the same block. | Use distinct forks for entry and return; selecting a return into the holding loop leaves the route unfinished. Preview and loaded van confirm the tour. |
| 27 — Works Ahead | Avoid a visibly closed spur while still collecting. | Choose the remaining pickup approach, then the house branch; blocked branch reaches the existing barrier. Empty-to-loaded state rewards the detour. |
| 28 — Who Goes Around? | Choose which of two vans takes the longer directed route. | Give the delay to the van whose pickup tour otherwise reaches the crossing too early; the opposite assignment collides. Safe sequential crossings are the payoff. |
| 29 — Back to the Square | Return beside the entry without expecting a frozen switch to change by itself. | The winning return uses a distinct nearby junction and bypasses the entry switch. Revisiting that same graph node would repeat its fixed route forever; the wrong branch demonstrates this loop. Stop allows correction; the loaded return confirms the useful route. |
| 30 — Canal Circuit | Combine one-way approaches, a closed spur and two pickup routes. | Establish crossing order through whole-route choice; skipping pickup or taking the tempting short tour exposes the corresponding error. Two loaded vans complete the circuit. |
| 31 — Red Means Wait | Learn automatic stopping through a route choice, not a zero-input light demo. | Choose a pickup route passing a red stop line over an empty-house bypass; observe stop then automatic release. Missing cargo is the wrong-choice failure; waiting itself is safe. |
| 32 — Taking Turns | Recognize that opposing approaches alternate. Choose valid matching/pickup exits before Go. | Signal separates crossing admissions while routing still matters; wrong exit reaches wrong house or misses cargo. Two clearly separated releases explain the rule. |
| 33 — Wait or Wander | Choose between a short signal route and a long bypass. | The short route's wait gives correct downstream spacing; the tempting bypass conflicts later. Keep that later crossing plainly visible. The release creates the useful gap. |
| 34 — Pickup on Green Street | Combine cargo location with an automatic hold. | Choose the route with pickup before the signal, then safe crossing; bypassing pickup fails at home. Collection and a separate stop/go moment stay readable. |
| 35 — Offset Corners | Compare two alternative signal approaches, not two simultaneous taps. | Choose the pickup tour whose arrival fits the downstream crossing; a later cycle remains legal. Wrong route collides downstream, never because a light secretly expires. |
| 36 — Green Wave | Combine two familiar signal groups and two vans. | Planned tours establish a safe sequence through both; all lights remain automatic. Bad bypass choice creates one visible downstream conflict. Sequential arrivals are the finale. |
| 37 — Your Turn | Introduce manual release order and the physical presence of held vans. | Two vans start held on separate approaches. B's bay visibly intersects A's downstream road outside the protected junction. Release B to clear that obstruction, then A. Sending A all the way while B stays held collides there; another safely timed order is valid. Red holding is indefinite. |
| 38 — Clear the Crossing | Understand requested versus effective release. | Request the second group while the first van traverses; the engine waits for clearance. A separate route fork is the meaningful puzzle; rapid repeated requests gain nothing. Pending→go feedback explains safety. |
| 39 — Loaded First | Connect release order to pickup-route choice and a visible held obstacle. | Select the complete cargo tours, clear the blocking bay first, then release the longer tour. A premature release can hit the held van downstream; merely waiting longer before moving the blocked van does not remove that obstacle. No pickup-time delay is introduced. |
| 40 — Beyond the Light | See that a safe signal crossing does not make the whole route safe. | Choose a downstream detour and release order together; a shortcut collides beyond the controlled area. Highlight that area clearly on failure. |
| 41 — Quiet Dispatch | Consolidate through planning after several controlled runs. | Configure separate pickup tours; one initial release lets both use the same permitted approach group on distinct bays/paths with no queue. Wrong planning, not slow pressing, causes failure. Calm paired deliveries reset the pace. |
| 42 — Dispatch Desk | Solve one signal group plus a static routing dependency. | Choose the useful pickup detour and clear a visibly obstructing held van before admitting the blocked tour. Wrong route or premature admission explains the downstream conflict. Accept alternate safe sequences; two full cargo tours reward a composed plan. |
| 43 — A Pair of Parcels | Teach a two-item requirement at one final house. | Choose the tour visiting both rather than the one-item shortcut; no strict pickup order. Missing-item preview names the second package. HUD reaches 2/2. |
| 44 — Either Way Round | Establish that package order is flexible. | Two distinct tour configurations collect both and win; compare their spatial route, without demanding speed optimization. A bypass misses one. Both legal orders receive equal completion recognition. |
| 45 — One Collector, One Neighbor | Add one ordinary one-package van to the two-item tour. | Choose the collector's order that separates a crossing; the opposite order still collects both but collides. This proves order choice has traffic meaning. |
| 46 — The Useful Detour | Choose tour order based on a signal wait or, if absent, path length. | Visit the far pickup first to create the gap; the near-first version conflicts at the downstream crossing. A safe later phase remains legal. Cargo count and clearance agree. |
| 47 — All Accounted For | Quiet consolidation of cargo completeness. | Two pickups and distinct static forks; resist an early home branch. Missing item fails descriptively. No timing interaction; final unload confirms both items. |
| 48 — Garden Collection | Combine order choice and another van's route. | Two-item collector chooses far-first, other van takes its pickup route; one visible crossing clears. Alternate collector order teaches why completeness alone is insufficient. |
| 49 — The Short Way for Whom? | Choose which van receives the useful long route. | A longer cargo tour for one creates safe spacing for both; switching the detour owner collides. Paired deliveries validate the assignment. |
| 50 — Shared Choice | Recognize one frozen switch affects both approaching routes. | Select a common safe exit and use a distinct downstream bypass for one van; trying to assign different static exits cannot work. Preview exposes the shared selection. |
| 51 — Waiting Is Working | Distinguish a purposeful hold from an unproductive loop. | Use one live loop to wait for a crossing to clear, then release on any safe later lap. No tap leaves the run unfinished, not failed. Repeated release opportunity is explicit. |
| 52 — Commitments | Separate the van already on an edge from the van still approaching a live switch. | Change a broad-gap live exit for the later van; the earlier one keeps its committed road. Early change sends the first van wrong; no subsecond gap. Two divergence traces demonstrate commitment. |
| 53 — Three Addresses | Coordinate three vans with only two interacting at once. | Third van's simple pickup tour completes before the single live decision, or waits safely under approved signals. Wrong plan fails at the relevant pairwise crossing. Three deliveries build the payoff without three control demands. |
| 54 — Town Routes | Read a chain of dependencies. | Route A clears B's crossing, then B's route permits C; use length choices and at most one live control. A local shortcut breaks one named link. Each cleared crossing makes the next step understandable. |
| 55 — Familiar Streets | Start final chapter with a readable two-van remix. | Apply pickup-first and one known spacing choice; wrong route misses cargo or creates the single crossing conflict. Restore confidence before the finale ramp. |
| 56 — Two Good Plans | Discover more than one valid overall solution. | Either detour owner can work if its companion settings match; test both complete scripts. Mixed settings collide. Equal success feedback rewards reasoning rather than guessing the designer's favorite. |
| 57 — Set the Order | Coordinate one approved waiting mechanism with cargo tours. | Select routes, then establish release order using one signal group or one repeatable live loop. Wrong order has one clear downstream conflict. No new precedence objective or deadline. |
| 58 — Across the Neighborhood | Extend the dependency to three vans. | A short independent delivery finishes before the two-van interaction. Missing pickup and traffic errors remain separately identifiable. Three payoff moments are spaced around control needs. |
| 59 — Dress Rehearsal | Practice two episodes with up to four vans. | Resolve first pair through static routes; second pair uses the known waiting mechanism later. Wrong episode settings fail locally. No simultaneous controls; reduce to three vans if markers crowd. |
| 60 — TinyRoutes | Demonstrate mastery through a compact, explainable composition. | Two pickup tours establish clearance for the final pair, with at most one active intervention at once. Every wrong-choice test maps to an earlier lesson. End with readable sequential unloads and the existing all-delivered celebration. |

### Conditional chapter replacements

Do not hold a good campaign hostage to an unproven subsystem. Preserve each chapter's lesson density and six-slot shape, then re-author and verify its geometry under retained rules.

- **If signals are rejected:** 31 teaches a pickup detour that creates a gap; 32 an already-separated two-van crossing; 33 short-route collision versus long-route clearance; 34 pickup before a safe loop; 35 choose which directed approach arrives later; 36 combines two sequential crossings. For 37–42, substitute a single existing live holding loop: teach release order through a second van's visible crossing, repeatable opportunities, pickup-dependent route lengths, one downstream conflict, quiet static consolidation, then the loop finale. None requires a new stopped state. Accessibility remains a gate for live input.
- **If live input cannot be made accessible in the intended mode:** use static route-length/departure-order alternatives for 19–24 and the live rows later. Do not merely enlarge a timing window and claim equivalent VoiceOver operation.
- **If two-package play is rejected:** 43 chooses between two routes to one assigned package; 44 demonstrates both valid pickup tours; 45 makes that route choice affect a neighbor; 46 assigns the detour; 47 consolidates static routing; 48 combines the choice with a crossing. Do not display a second package that has no gameplay purpose.
- **49–60 depend only on accepted mechanics.** Signal/extra-cargo variants are optional. Their core decisions can use one assigned package per van, directed paths, detours, authored departure delays, and the existing live loop. No multiple-destination or speed subsystem is needed to reach Level 60.

## 8. Detailed concepts — Levels 13–24

These concepts specify the reasoning, not geometry or exact action timestamps. A successful route using only frozen switches cannot revisit the same graph node: it would repeat the same future route indefinitely, since cargo does not change exit selection. Use distinct entry/return junctions in static tours; a true repeated-node loop needs a live change to exit. All crossings/merges must be visually honest and checked against actual sampled paths.

### Level 13 — Pick Up First

- **Objective/new rule:** one Red circle van collects its assigned circle package before the existing circle house. One ordinary two-way fork, no other van.
- **Board/decision:** the short branch reaches the house empty; a visibly separate branch visits the pickup and reconnects downstream of the fork before home. Select cargo rather than the tempting direct route.
- **Solution:** set the fork to the pickup tour, press Go, watch pickup then delivery. No live input or loading delay.
- **Failure/teaching:** direct route preview says the package is missing; running anyway produces a missing-package result and points back to the pickup. The house does not count as delivered.
- **Difficulty/timing:** deliberately easier than 12. One route choice; unlimited planning. Hint: “Pick up the circle parcel before going home.”
- **Payoff/accessibility:** marker empties, roof cargo appears, chip changes to carrying, then unload. Route summary names both stops; collection announcement is once-only.
- **Acceptance:** pickup route wins; bypass fails for missing cargo; preview matches both; retry restores package and preserves fork; old package-free levels remain unchanged.

### Level 14 — Loaded and Homeward

- **Objective:** collecting cargo is necessary but does not replace routing to the matching house.
- **Board/decision:** first fork offers pickup versus empty bypass; a distinct downstream fork offers home versus barrier. Both decisions are visible before Go.
- **Solution:** select pickup, then home. Avoid returning through the first frozen fork with an expectation of a different exit.
- **Failure/teaching:** skipping pickup yields missing cargo; selecting the bad downstream exit reaches the barrier while visibly loaded. Feedback distinguishes the causes.
- **Difficulty/timing:** two static decisions, one van, no interaction deadline. Hint: “Plan the trip after the pickup, too.”
- **Payoff/accessibility:** carrying state remains visible between pickup and delivery; summary exposes remaining destination after collection.
- **Acceptance:** omit each correction separately and verify its intended failure; full tour wins with exactly one collection/delivery event; no preview ownership mutation.

### Level 15 — Two Parcel Routes

- **Objective:** apply the cargo rule independently to Red circle and Blue triangle.
- **Board/decision:** two spatially separated tours, each with a direct-to-house bypass and a pickup branch. No crossing and no shared switch yet.
- **Solution:** send each van through its own pickup. Route configuration, not speed, controls success.
- **Failure/teaching:** one van's collection never satisfies the other's requirement. An empty arrival names the van and missing symbol.
- **Difficulty/timing:** adds a second thing to track, not a new rule; at most two main decisions. No live input.
- **Payoff/accessibility:** stagger payoff through path length so each carrying transition can be perceived; two stable per-van cargo summaries.
- **Acceptance:** all four branch combinations; only both pickup routes complete. Verify no premature win after the first delivery and no cross-van cargo leakage.

### Level 16 — Know Your Parcel

- **Objective:** understand fixed ownership: passing the wrong pickup does not collect it.
- **Board/decision:** two separate fork areas offer the visually nearer other-symbol pickup route or the own-symbol pickup route, each leading toward the van's own house. Keep resulting roads collision-free so ownership is the sole lesson.
- **Solution:** choose circle pickup for Red and triangle pickup for Blue, regardless of which marker is nearer.
- **Failure/teaching:** a mismatched pickup stays in place; the van stays empty; home fails for missing cargo. No “wrong package” inventory is created. The planning preview makes that outcome inspectable.
- **Difficulty/timing:** low–medium recognition puzzle, no live taps or crossing timing. Hint: “Match the parcel symbol to the van.”
- **Payoff/accessibility:** matching symbols visibly connect van/pickup/house; labels include owner and state. Inspecting either route reveals whether collection occurs.
- **Acceptance:** wrong-van visits leave stock untouched; reversing van array order cannot change ownership; correct routes both win. Reject the layout if two pickups plus fork controls become visually ambiguous.

### Level 17 — The Useful Pickup

- **Objective:** discover that a required pickup detour can also solve a traffic conflict.
- **Board/decision:** Red's fork chooses direct empty homebound crossing or a pickup tour before that crossing. Blue has a simple assigned pickup tour. Blue's crossing time is deliberately close to Red's direct route and safely clear of Red's loaded route.
- **Solution:** take Red's pickup detour; Blue collects and crosses first, Red follows loaded.
- **Failure/teaching:** the direct route can collide at the marked crossing before the missing-cargo house failure. It is visibly missing cargo in planning, so the collision does not hide that requirement. A separate bypass negative test verifies missing-cargo handling elsewhere.
- **Difficulty/timing:** first cargo-plus-traffic composition; no live tap. Hint after failure: “The pickup trip also leaves room for Blue.”
- **Payoff/accessibility:** collection occurs before the safe staggered crossing. Route summary identifies the shared location without claiming the preview predicts collisions.
- **Acceptance:** pickup tour has robust geometric/time separation; shortcut reliably conflicts; collect/deliver sequence stays deterministic across frames. The crossing must look like shared space.

### Level 18 — Neighborhood Round

- **Objective:** compose two valid pickup tours whose traffic order works together.
- **Board/decision:** two vans, one pickup each, independent route-length forks after/around collection, and one geometric crossing. Do not use a frozen shared split requiring different exits. Arrange one complete route pairing with broad clearance and a plausible short pairing that conflicts.
- **Solution:** Red takes the longer complete pickup tour; Blue takes its shorter complete tour. Both collect before home; the selected pairing separates the crossing.
- **Failure/teaching:** both-short still has correct cargo but collides, demonstrating that cargo-valid previews do not guarantee traffic safety. Missing-pickup variants remain separately diagnosable.
- **Difficulty/timing:** medium chapter finale, two or three relevant static decisions, no new rule. No requirement to guess a precise delay.
- **Payoff/accessibility:** both vans become loaded and cross in a clear order; two delivery celebrations. Route summaries list collection completeness and the common crossing.
- **Acceptance:** enumerate the small static configuration space, record all valid plans, test collision and missing-cargo alternatives, and provisionally assign par only after verification. If one van's choices are irrelevant, redesign before expanding the pack.

### Level 19 — Leave Loaded

- **Objective:** reconnect cargo to familiar live switching using one van.
- **Board/decision:** one van collects on a directed loop that returns to a live fork. The fork begins set to hold; the player chooses when to send the now-loaded van home. No competing traffic.
- **Solution:** let the van collect, then select home while it is safely away from the fork. Missing the first unlocked opportunity permits another lap.
- **Failure/teaching:** an early home selection bypasses pickup and produces missing cargo; never tapping leaves a safe loop. Stop remains explicit. The preview labels the current loop as unfinished, not a guaranteed crash.
- **Difficulty/timing:** chapter reset, one live control with a long repeatable opportunity; authored loop length must satisfy the timing target. Hint: “Load up, then use the live exit.”
- **Payoff/accessibility:** carrying state is a durable cue for release. Deliberate-play mode allows inspection and a legal tap while paused away from the fork; it cannot unlock a nearby van.
- **Acceptance:** collect then release wins; early release misses cargo; later laps still win; duplicate pickup is impossible. Sweep the full intended legal release interval.

### Level 20 — Collect, Then Clear

- **Objective:** use the loaded loop from 19 to wait for another van's crossing.
- **Board/decision:** Red collects inside a repeatable loop; Blue's independent pickup route crosses Red's release road. One existing live exit decides Red's departure from the loop.
- **Solution:** let Blue clear the visible crossing, then release Red on a later safe pass. Set the fork while Red is away; do not aim for its exact arrival.
- **Failure/teaching:** releasing on the first pass can collide; a missed later opportunity remains recoverable. Failure names the crossing pair and preserves the plan.
- **Difficulty/timing:** two known ideas, one control, broad/repeatable release after clearance. No signal system.
- **Payoff/accessibility:** Red's cargo remains visible while waiting; Blue clearing gives the release cue. Stable status names “Blue has cleared [place]” can support the assist view without stealing focus.
- **Acceptance:** early-release crash, never-release unfinished run, multiple late-lap wins, correct package conservation, and engine-derived timing/clearance margins.

### Level 21 — Shared Exit, Separate Parcels

- **Objective:** route two loaded vans through opposite exits of one live switch.
- **Board/decision:** separate pickups feed a shared approach/split. Path lengths establish a generous Red-first/Blue-second gap; both need the same physical switch at different settings.
- **Solution:** set the live exit for Red, let it commit and move beyond the lock area, then change it for Blue. Pickup branches are chosen in planning.
- **Failure/teaching:** fixed Red exit sends Blue to the wrong house; early change misroutes Red. Correct cargo cannot compensate for the wrong destination.
- **Difficulty/timing:** medium; one live change, no second crossing or timed pickup. Target at least the Section 6 window; author alternate geometry if it is too tight.
- **Payoff/accessibility:** two loaded vans visibly diverge and keep their symbols. Expose committed versus approaching routes in the inspectable summary.
- **Acceptance:** no static switch setting completes both; missing/early/late/locked taps behave predictably; sweep a broad successful interval and compare frame partitions. Do not claim par counts the live tap history.

### Level 22 — The Quiet Route

- **Objective:** provide a planning consolidation and teach that more motion is not necessarily more complexity.
- **Board/decision:** two vans, separate ordinary forks, two possible pickup detours and one visible crossing. No live controls. One complete route pairing separates the crossing; another complete pairing conflicts.
- **Solution:** choose complementary pickup tours entirely before Go. Use the existing directed graph and measured path lengths.
- **Failure/teaching:** picking both attractive short routes collides; omitting pickup is separately flagged. The fix is a changed plan, not an in-run rescue.
- **Difficulty/timing:** lower execution demand after 21; still one traffic insight. No precision or extra system.
- **Payoff/accessibility:** uninterrupted pickup-and-delivery sequence; full plan can be inspected without moving time. Reduce Motion leaves collection and destination status clear.
- **Acceptance:** configuration enumeration proves the meaningful alternatives, correct routes win without live actions, and feedback does not suggest tapping a frozen control would help.

### Level 23 — Another Lap Is Fine

- **Objective:** make recoverable waiting explicit rather than increasing tap pressure.
- **Board/decision:** one loaded van loops before a crossing; a second van has the right of way through its existing route. Use one live release switch and one static entry decision.
- **Solution:** choose the pickup loop, observe the second van clear, and release on any later safe lap. The intended insight is permission to wait.
- **Failure/teaching:** immediate release conflicts; no release remains unfinished. A hint after an extra lap reassures that another opportunity is coming; there is no hidden timeout.
- **Difficulty/timing:** medium reasoning, forgiving execution. Keep ordinary completion near the duration target, but never fail a player for choosing another safe lap.
- **Payoff/accessibility:** already-collected marker remains empty; loaded van never collects again. A status summary makes clearance inspectable while paused.
- **Acceptance:** at least two later-lap winning intervals, no duplicated events/cargo, safe indefinite holding within a bounded test horizon, Stop recovery, and clear loop-limit preview semantics.

### Level 24 — Saturday Deliveries

- **Objective:** close the chapter by combining pickup completeness, spacing and one shared live exit.
- **Board/decision:** three vans; Yellow has a short independent pickup tour and finishes before the live decision. Red and Blue take separate pickup tours, one useful detour, then a shared live split with opposite matching exits.
- **Solution:** choose both interacting cargo tours and the spacing detour, set Red's exit, then change the split for Blue after Red clears. Yellow's route is a simple planning confirmation.
- **Failure/teaching:** omitted pickup, shortcut collision and mistimed split each reproduce a known lesson. No failure introduces a new exception.
- **Difficulty/timing:** medium–high chapter finale; one live interaction, not three simultaneous controls. Keep Yellow's celebration away from the live cue. Reduce to two vans if the third adds clutter without reward.
- **Payoff/accessibility:** three distinct loaded deliveries, one clearly readable split and the existing all-delivered celebration. The itinerary/status view groups the interacting pair and the completed independent van.
- **Acceptance:** winning complete script, relevant omitted-plan variants, missing/early/late/rejected live inputs, broad live window, safe clearances and no premature win. Human observation must show players can explain why the detour and live change are both needed.

## 9. Engineering dependencies and compatibility

### Architecture impact categories

| Category | Mechanics/features | Boundary to preserve |
|---|---|---|
| **Supported by current engine** | Directed roads; static barriers/absent connections; route-length spacing; authored departure delay; 2–4 exit switches; one shared active exit; live locks; safe loops; multiple vans; matching terminal houses. | New content still needs proof of solvability, readable geometry and human timing. |
| **Small engine extension** | Bounded speed multiplier; relative delivery precedence; two-package allowance after cargo exists; exact-tick event metadata; optional tick-pausing input mode. | Small movement/model scope can still have broad UI/validation consequences. Deliberate-play requires real usability work. |
| **Moderate subsystem addition** | Initial package lifecycle; automatic/manual signals with held collision state and clearance; dynamic closures; cargo-sensitive routing; coupled switches. | Add explicit state within Multi-Van rather than importing a global single-van state model. |
| **Major architectural change** | Intermediate/multiple destinations; shared-stock assignment/cargo transfers; realistic queues/lanes/overtaking; interacting junction reservations; physics/real-time nondeterministic traffic. | Outside the recommended core expansion. Require a separate design decision and dedicated small experiment. |

### Cross-system compatibility map

| System | Pickup impact | Signal impact | Recommended approach |
|---|---|---|---|
| Fixed-step simulation | Node-arrival lifecycle changes. | Tick phases, holding, clearance and command ordering. | Keep one simulation clock and value-snapshot tuning; add no gameplay timers in views. |
| Route graphs | Pickup metadata references nodes; movement graph stays unchanged. | Approach references edges; stop points use actual paths. | Keep topology/geometry stable during a run initially. Do not rebuild graphs for cargo or light changes. |
| Live switches | Cargo does not alter lock/exit selection. | Held vans remain road occupants and lock nearby switches. | One engine-authoritative legality check; never let a board infer a different lock. |
| Collisions | Same van body/radius. | Add held pairs and safe conflict clearance. | Preserve old-level threshold/precedence; verify new states explicitly. No free pass through a red-light queue. |
| Multiple vans | Fixed ownership by van ID. | Separate approaches/holds; shared group state. | Avoid one global package flag or per-view signal state. Explicit stable ordering for simultaneous events. |
| Level schema | Optional package/requirement data, legacy empty defaults. | Optional signal groups, approach/phase definitions. | Version feature-bearing levels; reject unsupported content. Keep ordered exits intact. Do not generate new JSON in this planning phase. |
| Validation | Ownership, cargo limits, pickup→house reachability, role clarity. | Stop positions, phase validity, clearance, no unintended queue. | Share only relevant pure checks; promote authoring checks to load-time validation before broad user-authored content, without a generic rules engine. |
| Solution scripts | Existing action types initially suffice. | Need typed signal requests and tick semantics. | Preserve legacy script decoding; add minimal versioned commands when needed. Test full state/events, not just final win. |
| UI/feedback | New markers/cargo/chips/outcome/events and preview cargo tracing. | New signal controls, stop/go/pending labels and held status. | Engine owns truth; shared semantic controls for both board styles. A native diorama is not a prerequisite. |
| Playtest logging | Exact pickup/delivery ticks and missing-cargo causes. | Hold/release/request/effective-phase/clearance ticks. | Extend local schema deliberately, preserve old-row reading/export. Keep event truncation visible. |
| Progress/promotion | Package chapters need main progression only if prototype is promoted. | Same, plus assist preference and scoring decisions. | Promotion, save compatibility and campaign navigation are a separate milestone. Do not couple pickup trial to economy or production migration. |

The browser miniature-world reference also contains its own small gameplay demonstration. Keep it a visual reference during these trials; do not turn it into a second authoritative implementation or require new mechanics to be duplicated in JavaScript. Native simulation and its solution runner remain the gameplay authority.

### Logging proposal

Existing JSONL already captures attempts, outcomes, planning time, switch result, chosen edge, fast-forward use, stars, final configuration and abandonment. It lacks tuning/build/content identity and exact semantic arrival times; event rows are capped at 1,024 and later events are counted as omitted.

For future trials, propose level content identity/version, build identity and the effective tuning snapshot once per attempt/session association. New semantic engine events should include simulation tick, package/van/signal IDs and reason, while real elapsed and dispatch-observed simulation time retain their current meanings. Record assistance mode and facilitator assistance separately; neither can be inferred reliably from success. Keep this local and anonymous under the current model.

Analyze whether players choose valid pickup tours, understand missed cargo, distinguish safe holding from being stuck, correct a failure, and watch the resulting run. Separate rejected taps from accepted-but-wrong timing. Do not infer enjoyment from completion alone or treat fast-forward as automatically negative; it may skip already-understood motion.

### Avoiding an engine rewrite

1. Add the package rule at the existing arrival boundary and expand preview tracing with local objective state.
2. Keep cargo lifecycle data separate from graph selection. Add only the fields needed by the first playable trial.
3. If signals pass their trial, extend movement permission around existing path progress and preserve held physical presence. A small concrete signal state is sufficient; no generic simulation scheduler, entity-component rewrite, traffic AI or plugin rules framework is justified.
4. Preserve the single input path and single event drain. Add semantic events where needed rather than separate simulation logic per board.
5. Extract shared logic only when a second real caller needs it. The existing graph, geometry, board-rule and control seams are already useful.
6. Keep the legacy single-vehicle engine, generator and production schemas isolated. Any later promotion must explicitly decide the runtime/schema boundary instead of making one engine impersonate the other.

## 10. Recommended implementation sequence

These are approval-stage phases and exit gates, not generated tickets or instructions to start implementation. Complexity includes engineering and authoring/verification, not just changed line count. Complete the small playable milestone before filling its chapter slots.

| Phase | Features and dependencies | Complexity / technical risks | Validation and playable milestone | Exit criteria before proceeding |
|---|---|---|---|---|
| **0 — Establish the foundation** | Current 1–12 real-device playtest; clarify live-switch comprehension, current scoring and intended accessible play. Requires installed current build and attributable logs/notes. | Low code scope; significant unknown player evidence. Risk: diagnosing timing confusion as a speed problem. No tuning change is presumed. | Observe original plan's five-person directional trial, including nonregular players; separately exercise VoiceOver/Reduce Motion/device targets. Current 12-level build is the milestone. | Owner accepts the foundation or specifies a separately approved correction; known timing/accessibility limitations and scoring discrepancy are explicit. Do not treat documentation of a passing engine as human acceptance. |
| **1 — Small cargo trial** | One package per van; assigned pickups, cargo requirement, preview, feedback/reset and cargo validation. Depends on approved contract in Section 4. | Moderate. Risks: false preview checkmarks, global ownership, stale resets, crowded markers. | Three boards based on 13, 14 and 15 only; old 1–12 regression plus package edge cases and frame replay. Test whether players infer pickup-first and independent ownership. | Each board is explainable unaided after the first tutorial; missing-cargo feedback leads to a useful correction; no old trace/behavior regressions; owner agrees the added choice is worthwhile. Do not author 13–24 wholesale yet. |
| **2 — Pickup depth and forgiving live play** | Author remaining 13–18, then trial 19/20/21; deliberate-play support and route/status accessibility before new live content release. Depends on cargo trial and approved assist/scoring treatment. | Moderate integration/content work. Risks: repeating “take parcel branch,” narrow windows, assistance allowing illegal lock bypass. | First six-level pickup chapter, plus three isolated live-cargo boards; exhaustive small static choices, interval sweeps, full deterministic state/events and device accessibility. | At least three distinct cargo decisions demonstrated: completeness, ownership and traffic spacing. Live boards meet timing target and work with the approved assist interaction. Otherwise keep new release static-only. |
| **3 — Establish a content vocabulary** | Finish 19–24 after its trials; trial 25/27/28 before completing 25–30. Existing one-way/static closure content, no dynamic roads. | Low engine scope, moderate level design. Risk: visual false connections or irrelevant forks. | A coherent 13–30 pack only after each group is validated. Measure failed-choice causes, pace and route explanations; inspect small-screen/Dynamic Type layouts. | Chapters have different insights, not just more switches; finales combine known rules. No proposal to increase board size merely to fit content. |
| **4 — Automatic signal experiment** | Single-approach automatic hold, then two exclusive approaches with clearance; held collision state, phase UI, script/log extensions. Depends on accepted pickup architecture and a documented tick contract. | Moderate, highest near-term movement risk: overshoot, held collision omission, unsafe clearance, state-order dependence. | Three boards based on 31/32/33 before authoring 31–36. Phase-boundary, held-state, occupancy, replay, reset and no-queue checks; accessible planning of automatic cycles. | Players understand that waiting is safe and green permits entry only; signal changes a route decision; no unsafe opposing admissions or unintended required queues; owner approves keeping the subsystem. Otherwise use fallback chapter. |
| **5 — Deliberate dispatch experiment** | Manual signal requests, requested/effective feedback, separate control command; approve long-term scoring before a scored chapter. Depends on signal safety and deliberate-play accessibility. | Moderate extension. Risks: frantic toggling, UI ambiguity, exploitative stars, universal one-at-a-time solution, demand for queue AI. | Three boards based on 37/38/39; no deadline, two holding bays, one group; then approve or reject 37–42. Validate same-tick commands, requests under occupancy, and both fully serialized orders. | Order choice is enjoyable without fast tapping; users can explain pending release and held obstacles; VoiceOver can inspect and activate; scoring contract is consistent and signed off. Reject if safe waiting only adds dead time or useful decisions require contrived obstruction. |
| **6 — Two-package experiment** | Two assigned pickups, either order, one final house; no transfer, weight, or intermediate stops. Depends on cargo stability; signals optional. | Small/moderate. Risks: memory/clutter, forced errand chains, two packages adding no route choice. | Trial 43/44/45 before accepting 43–48. Both-order, partial-completeness, collision and reset tests; route-summary/cargo-count device review. | Order choice meaningfully changes at least one traffic relationship and players track 0/1/2 cargo easily. Otherwise keep one-package replacement chapter. |
| **7 — Mastery pack and promotion decision** | Author 49–60 using retained mechanics; decide whether to promote Multi-Van into the main game. Depends on stable contracts, accepted chapters and evidence of sustained interest. | Moderate content effort; potentially major product migration if promoted. Risks: unreadable finale, old-save/progression conflicts, generator assumptions. | Trial 49/54/60 as difficulty anchors before filling gaps; full retained corpus scripts, static alternatives/live margins, accessible/device checks, progression/save migration review separately. | Every level has a purpose and validated solution; no finale exception rules; return players want more; owner explicitly approves runtime/progression promotion and migration scope. |

Optional work after these gates: a one-van two-destination tour, a two-speed comparison, or an optional relative-priority board. Each gets a separate tiny experiment and keep/drop decision. None blocks the roadmap above, and none is automatically added to a task file.

### Proposed trial evidence standard

Use the existing five-person prototype test as directional evidence, not a statistical guarantee. For a new mechanic, initially observe a small separate group, ideally five new-to-that-mechanic players including two who do not play games often. Proposed keep signal: at least four can explain its rule and complete the second teaching board without a hint, at least three want to continue, and no recurring “I understood it but could not operate it” pattern remains. These are proposed review criteria, not results or replacements for accessibility testing. A failed criterion triggers diagnosis/revision or rejection, not automatic global tuning changes.

## 11. Risks, open questions, and decisions for owner approval

### Principal risks and countermeasures

| Risk | Why it matters | Proposed response |
|---|---|---|
| Cargo becomes a compulsory toll | Every level repeats “use the longer branch.” | Require ownership, order, spacing or tradeoff insight; use quiet teaching sparingly. Drop weak concepts before filling quotas. |
| More symbols overwhelm a small board | Vans, packages, houses, signals and switches compete in 35 coordinate positions. | Separate roles in tutorials, limit simultaneous controls, keep optional systems optional, reduce van count before enlarging the board. |
| Preview promises more than it knows | Cargo-valid checkmarks may be read as guaranteed safe delivery. | Explicit route/objective validity language; preserve visible crossing failure lessons and mark future live-dependent routes as current-state traces. |
| Timing becomes the main challenge | Existing narrow live windows and 2× playback can punish understanding. | Broad new windows, repeatable loops, one interaction at once, deliberate-play mode and measured human operation. Do not alter 1–12 under this plan. |
| Signals imply realistic traffic | Players may expect queuing and automatic collision avoidance everywhere. | Teach a bounded stop/admission rule; no multiple arrivals per holding bay; clearly distinguish controlled area from ordinary road. Reject scope that requires lane AI. |
| Automatic waits become downtime | A light can add spectacle without a decision. | Test wait-versus-detour/ordering consequences; remove the light if the choice is unchanged. |
| Changed shared state breaks determinism | A global package flag or iteration-based release can let one van alter another unexpectedly. | Per-ID cargo, stable tick order, occupancy-safe admission, old-level regression and complete event/state comparisons. |
| Scoring rewards the wrong behavior | Current configuration score differs from the plan; signals add inputs outside it. | Keep first pickup trial stable; make future scoring an explicit product decision before scored manual signals. Log physical input counts separately. |
| “More destinations” erodes clarity | Delivery stops no longer mean parking; identity and victory become harder to read. | Separate experiment and visual language; do not smuggle continuing houses into the first cargo system. |
| More content masks weak systems | Forty-eight slots can create pressure to ship every proposal. | Approve three-board trials first; use fallback chapters and delete repetitive levels. Numbering is a target, not a quota. |
| Visual port doubles presentation work | A new mechanic may work only on one board. | Validate shared semantics on flat first; implement parity in the real diorama when it exists. Do not count the stand-in as a second renderer. |

### Decisions requiring approval before the relevant phase

1. **Direction:** make assigned pickup-before-house the first new mechanic, with package-free Levels 1–12 untouched.
2. **Cargo contract:** one fixed-owner package per participating van; automatic instantaneous collection; another van passes it without collecting; matching-house arrival without required cargo fails; no transfer or load-time delay.
3. **Scope:** one package/one terminal house remains the campaign baseline. Two packages are conditional; multiple destinations, speeds, deadlines, dynamic closures and special switch species are deferred experiments.
4. **Scoring:** retain current behavior for the initial pickup trial. Later choose configuration-based stars, input-based stars, or a distinct optimization metric. Any migration/rebalancing of old pars is separately reviewed; this document approves none.
5. **Accessibility:** approve an optional deliberate-play mode with no proposed star penalty, or choose an alternative that demonstrates equivalent usable access. It must preserve command legality and deterministic clock behavior.
6. **Signals:** accept safe automatic holding/exclusive admission as a moderate subsystem trial, with collision-active held vans, no queues, fixed reset phase and occupancy clearance. Manual release follows only after this proves useful.
7. **Content:** accept the eight-neighborhood direction and the detailed 13–24 concepts as authoring hypotheses, subject to geometry, simulation and human revision; not as guaranteed solvable boards or final pars.
8. **Promotion:** decide separately whether and when Multi-Van becomes the main game, including saves, navigation, production runtime/schema identity, generator/editor scope and onboarding order. Existing resources and product progression are not migrated by this roadmap.

### Questions to resolve through play rather than architecture speculation

- Do players enjoy seeing cargo collected, or do previews make the new rule feel like a trivial checklist? Compare 13/14 with the interacting 17/18 concepts.
- Does the current first live-switch exposure feel fair after players understand the hint? Observe existing Level 6 before deciding any future onboarding or tuning change.
- Can players explain route-valid versus traffic-safe without a full timeline preview? If not, trial a small inspectable crossing summary before building ghost-run simulation UI.
- Do manual lights create satisfying dispatch choices, or remove the useful stakes of route planning? Compare the three-board dispatch trial with a loop-based equivalent.
- Is either-order two-package collection meaningfully richer than choosing two routes to one package? Test both before adopting a capacity system.
- Can the final two-episode board fit visibly and nonvisually on the intended phone? Reduce to three vans if it cannot.

**Recommended first playable addition:** assigned package pickup before the current matching house, demonstrated on three small boards. It adds an understandable new route requirement, visible progress and natural interactions with the existing detours and multiple vans, while preserving fixed-step movement and avoiding a rewrite. The strongest long-term direction is deeper relationships among pickups, routes and safe arrival order, with traffic signals earned through a separate playable trial.
