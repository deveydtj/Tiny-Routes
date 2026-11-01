# Multi-Van Prototype: Task Breakdown

Status: proposal · Source: [multi_van_prototype_plan.md](multi_van_prototype_plan.md) · Last updated: 2026-10-31

This splits the prototype plan into small tasks. Each one should be a single PR of a few hours to about a day. Read the plan first: it is the source of truth for rules, numbers and visuals. When this doc and the plan disagree, the plan wins. Fix this doc too.

## How to use this doc

- **Level** tells you who should pick a task up.
  - **Entry:** clear inputs and outputs, mostly one file, with an obvious way to test it. Good for your first weeks on the codebase.
  - **Junior+:** needs some design judgement, touches shared code, or has timing or geometry subtleties. Each of these tasks has a **Guidance** section. An entry-level engineer can still take one if they pair with someone or follow the guidance closely.
- **Reasoning: High** marks tasks that need extra care and more thinking time. If you use an AI coding assistant, set its reasoning effort to high for these tasks. Seven tasks have it: MV-05, MV-08, MV-15, MV-20, MV-21, MV-29 and MV-42.
- **Depends on** lists the tasks that must be merged first. Tasks with no shared dependency can run at the same time.
- **Done when** is the acceptance check. Your reviewer will use it.
- Keep every change inside `TinyRoutes/Prototype/`, `TinyRoutes/Resources/PrototypeLevels/` and `TinyRoutesTests/Prototype/` unless the task says otherwise. The prototype must not change how the current game plays.

### Everyday commands

After adding or removing any Swift or resource file:

```bash
xcodegen generate
```

Commit the regenerated `TinyRoutes.xcodeproj/project.pbxproj` in the same PR.

Run the full Swift test suite (the same one CI uses):

```bash
python3 scripts/run_swift_tests.py
```

### Shared rule constants

Put every tuning number in one place, `MultiVanTuning` (created in MV-02), so nobody hard-codes them:

| Constant | Value | From the plan |
|---|---|---|
| `vanSpeed` | 1.5 grid units/s | Run phase |
| `stepDuration` | 1/120 s | Engine notes |
| `crashDistance` | 0.35 units | Fail: crash |
| `liveSwitchLockRadius` | 0.4 units | Live switches |
| `previewEdgeLimit` | 40 roads | Preview lines |
| `failFreezeDuration` | 0.6 s | Screen flow: Fail |
| `fastForwardMultiplier` | 2 | Screen flow: Run |
| `gridColumns` / `gridRows` | 5 / 7 | Portrait grid |

## Rule decisions

The plan left these open. They're now settled and also recorded in the plan's rules table.

1. **Vans waiting to depart don't crash.** Only driving vans are checked for crashes. A van that hasn't departed yet, or has already parked, is skipped. This lets level 6's vans share a start node. (MV-20)
2. **Rejected taps don't count as changes.** Only accepted taps add to `changeCount`. (MV-07, MV-21)
3. **Lock radius: default, revisit at playtest.** Nobody has a strong view, so use the simplest rule: the straight-line distance from each **driving** van's position to the switch node's grid point. Waiting and parked vans don't lock a switch, which matches decision 1. Keep the radius in `MultiVanTuning` and on the tuning panel (MV-45) so it's easy to change if players find it unfair. (MV-21)
4. **No stars on a failed run.** Stars only appear on the win card. (MV-27, MV-39)

---

## Milestone M1: Skeleton

*Exit: levels 1–4 are playable start to finish.*

### MV-01 · Create the prototype folders and empty files

**Level:** Entry · **Depends on:** none

Create the folders and empty Swift files listed under "Technical approach" in the plan, each with just an `import` and a placeholder type, so later PRs have a home and don't fight over `project.pbxproj`.

- `TinyRoutes/Prototype/` with the seven files from the plan.
- `TinyRoutes/Resources/PrototypeLevels/` (add a `.gitkeep`).
- `TinyRoutesTests/Prototype/MultiVanEngineTests.swift` with one passing placeholder test.
- Run `xcodegen generate`.

**Done when:** the app builds, the placeholder test runs in CI, and the new files appear in Xcode in the right groups.

---

### MV-02 · Level data model

**Level:** Entry · **Depends on:** MV-01

In `MultiVanLevel.swift`, add `Decodable` types that match the "Level JSON" example in the plan:

- `MultiVanLevel`: `id`, `name`, `graph: RouteGraph`, `vans`, `houses`, `initialSwitchEdges: [String: String]`, `parChanges`, `liveSwitchNodeIDs` (default `[]`), `hint` (optional).
- `VanColor` enum: `red`, `blue`, `yellow`, `green`. Give it a `symbol` property (● ▲ ■ ★) and a `displayName`.
- `MultiVanVan`: `id`, `color`, `startNodeID`, `departDelay` (default `0`).
- `MultiVanHouse`: `nodeID`, `color`.
- `MultiVanTuning` enum holding the constants table above.

Reuse the existing `RouteGraph` type (`TinyRoutes/Domain/RouteGraph.swift`). Don't create a new graph type.

**Done when:** a unit test decodes a small hand-written JSON string into `MultiVanLevel` and checks every field, including the defaults when `departDelay`, `liveSwitchNodeIDs` and `hint` are left out.

---

### MV-03 · Load prototype levels, and keep them out of the main game

**Level:** Entry · **Depends on:** MV-02

In `MultiVanLevelRepository.swift`, load every `proto_*.json` from the bundle's `PrototypeLevels` subdirectory, sorted by ID.

Watch out: `LevelRepository.resolveAllLevelURLs` (`TinyRoutes/Infrastructure/LevelRepository.swift:106`) loads `.json` files from the `Levels` subdirectory **and the bundle root**. Prototype levels must stay in their own subdirectory.

- Use `Bundle.urls(forResourcesWithExtension: "json", subdirectory: "PrototypeLevels")`.
- Add a test that loads the production level list and asserts no level ID starts with `proto_`.
- Add a test that the prototype repository returns at least one level (this will pass once MV-04 lands; mark it as expected to grow).

**Done when:** both tests pass and the production level count is unchanged.

---

### MV-04 · Author levels 1 and 2

**Level:** Entry · **Depends on:** MV-02

Write `proto_01.json` ("Go!") and `proto_02.json` ("Pick a Lane") from the level table in the plan.

Tips:
- Use whole-number grid points with `x` in 0–4 and `y` in 0–6.
- Every node's `outgoingEdgeIDs` must list exactly the edges whose `fromNodeID` is that node. `RouteNode.validateOutgoingEdges(against:)` will check this in MV-17.
- A dead end is any node with no outgoing edges that isn't a house.
- For level 2, set `initialSwitchEdges` so the switch starts pointing at the barrier.
- Draw the level on grid paper first. Use the level 7 sketch in the plan as a model.

**Done when:** both files decode through `MultiVanLevelRepository` in a test.

---

### MV-05 · Share the runtime graph builder with `RouteEngine`

**Level:** Junior+ · **Depends on:** MV-01

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because it refactors the existing production game engine, so any mistake is a regression in the current game.

Pull the code that turns `RouteGraph` nodes and edges into a `RuntimeRouteGraph` out of `RouteEngine` (around `TinyRoutes/Gameplay/RouteEngine.swift:210–242`) into a small shared helper, for example `RuntimeRouteGraph.make(from: RouteGraph, availabilityRule:)`. Both engines then call it.

**Guidance:**
- This touches the production engine. It must be a pure refactor: same inputs, same output, no behaviour change. Keep the PR to just this.
- Only move the node and edge construction (the two `for` loops that build `nodesByID` and `edgesByID`, including `RoadPath.make`). Leave the objective and validation road-state logic that follows in `RouteEngine`, because the prototype doesn't use objectives.
- `RouteEngine` passes `levelData.effectiveAvailabilityRule(for: edge)` for each edge. Let the helper take a closure for this, so `RouteEngine` keeps its behaviour and the prototype can pass `{ $0.availabilityRule }` or `.always`.
- Keep throwing the same `RouteEngineError.edgeReferencesUnknownNode` error, or map to it, so existing tests keep their expectations.
- Run `RouteEngineTests` and `RuntimeParityFixtureTests` before and after. They must pass unchanged. If you had to edit a test to make it pass, stop and ask.

**Done when:** the full test suite passes with no test changes, and `RouteEngine` calls the new helper.

---

### MV-06 · Share road drawing with `GameplayScreen`

**Level:** Entry · **Depends on:** MV-01

`RouteBoardView.roadPath(for:layout:)` is `private` in `TinyRoutes/UI/GameplayScreen.swift` (around line 890). Move both overloads into a shared helper, for example `enum RoadPathRenderer { static func path(for: RoadPath, layout: BoardLayout) -> Path }`, in a new file under `TinyRoutes/UI/Components/`. Then make `RouteBoardView` call it.

- Move the code as it is. Don't change the drawing.
- Search the file for other private callers before you delete the old methods.

**Done when:** the app builds, the current game's roads look identical (compare a before and after screenshot of level 5 in the PR), and all tests pass.

---

### MV-07 · Engine skeleton: phases, switches, change counter

**Level:** Entry · **Depends on:** MV-02, MV-05

In `MultiVanEngine.swift`, create a `final class MultiVanEngine` (or `struct`, ask your reviewer) that:

- Builds its `RuntimeRouteGraph` from a `MultiVanLevel` with the MV-05 helper, then applies `initialSwitchEdges` to each node's `activeOutgoingEdgeID`. Nodes not listed default to their first outgoing edge.
- Has `enum Phase { case plan, run, finished }`, starting in `.plan`.
- Has `tapSwitch(nodeID:) -> SwitchTapResult`, which during `.plan` moves the node to the next exit in `outgoingEdgeIDs` order, wrapping around, and adds 1 to `changeCount`. Nodes with fewer than 2 exits return a rejected result. Rejected taps never add to `changeCount`.
- Has `resetSwitches()`, which restores `initialSwitchEdges`. Ask whether this should reset `changeCount` (proposed: no).
- Define a new prototype result enum such as `MultiVanTapResult { case accepted, rejectedFrozen, rejectedLocked, notASwitch }`. Don't reuse the production `SwitchTapResult`, which has different meanings.

**Done when:** tests cover cycling a 2-way switch, a 3-way switch wrapping round to the start, change counting, rejecting taps on non-switches, and `resetSwitches`.

---

### MV-08 · Fixed-step movement for one van

**Level:** Junior+ · **Depends on:** MV-07

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because fixed-step simulation, carrying movement remainders between roads, and deterministic timing are easy to get subtly wrong.

Add van state and movement to the engine:

- `MultiVanVanState`: `id`, `color`, `currentEdgeID?`, `distanceAlongEdge`, `status` (`waiting`, `driving`, `parked`, `crashed`, `stuck`), and a computed `position: RoadPoint`.
- `go()`: moves from `.plan` to `.run` and sends each van onto its start node's active edge.
- `advance(by realTime: TimeInterval)`: runs as many fixed 1/120 s steps as fit, moving each driving van `vanSpeed * stepDuration` along its edge.
- On arrival at a node: a house parks the van; a node with no exits makes it `stuck`; anything else moves it onto that node's **current** active edge.

**Guidance:**
- Use an accumulator. Add `realTime` to a stored remainder, run `while remainder >= stepDuration { step(); remainder -= stepDuration }`, and keep what's left for next frame. Never step by the frame's `dt` directly, or replays won't match.
- Clamp the time passed in (for example to 0.25 s) so a paused app or debugger break doesn't run thousands of steps at once.
- When a van reaches the end of an edge part-way through a step, carry the leftover distance onto the next edge. Otherwise vans slow down slightly at every node, and the timing puzzles in levels 7–9 drift.
- Use `RoadPath.totalLength` and `RoadPath.point(atDistance:)` (`TinyRoutes/Domain/RouteEdge.swift`) for positions. Don't recompute geometry.
- Read the switch state when the van **arrives** at a node, not when it enters the edge before. Live switches (MV-21) depend on this.
- Keep the engine free of SwiftUI and timers. The screen calls `advance(by:)` (MV-15), so tests can drive time exactly.

**Done when:** tests show a van on a 3-unit straight road arrives in 2.0 s (±1 step), follows the active edge at a switch, parks at a house, and gets stuck at a dead end. Calling `advance(by: 1.0)` once and `advance(by: 0.1)` ten times must give identical results.

---

### MV-09 · Outcomes: win, wrong house, stuck

**Level:** Entry · **Depends on:** MV-08

Add `outcome: Outcome?` with `win`, `failWrongHouse(vanID:, houseNodeID:)` and `failStuck(vanID:, nodeID:)` (leave room for `failCrash` in MV-20). Set phase to `.finished` as soon as an outcome is decided.

- Win: every van is `parked` at a house of its own colour.
- Wrong house: a van parks at a house of another colour. Fail straight away; don't wait for other vans.
- Stuck: a van reaches a dead end.

**Done when:** there's a test for each outcome, and `advance(by:)` does nothing once the phase is `.finished`.

---

### MV-10 · Stop and Retry keep the plan

**Level:** Entry · **Depends on:** MV-09

- `stop()`: from `.run`, returns to `.plan` with every van back at its start and **switch settings kept as they are now**, including live-switch changes made during the run.
- `retry()`: from `.finished`, does the same and clears `outcome`. Store the last fail position (`lastFailPoint: RoadPoint?`) so the UI can highlight it. Clear it on the next `go()`.
- Neither resets `changeCount`.

**Done when:** tests show settings survive both `stop()` and `retry()`, vans return to their starts, and `lastFailPoint` is set after a stuck fail.

---

### MV-11 · Route preview tracer

**Level:** Entry · **Depends on:** MV-07

In `MultiVanRoutePreview.swift`, write a pure function:

```swift
static func trace(van: MultiVanVan, graph: RuntimeRouteGraph, houses: [MultiVanHouse]) -> MultiVanPreviewRoute
```

It starts at the van's start node and follows `activeOutgoingEdgeID` from node to node. It stops at a house, at a dead end, or after `previewEdgeLimit` (40) edges. Return the edge IDs in order and an `ending`: `.matchingHouse`, `.wrongHouse`, `.deadEnd` or `.loopLimit`. Only `.matchingHouse` gets a ✓ in the UI.

Expose `previewRoutes` on the engine. Recompute it after every accepted tap.

**Done when:** tests cover all four endings, and a test taps a switch and checks the preview changes.

---

### MV-12 · Fit-to-screen board layout

**Level:** Junior+ · **Depends on:** MV-02

Given a level and the available `CGRect` between the HUD and the Go button, produce screen points for grid points so the whole level fits with no scrolling.

**Guidance:**
- Look at `BoardLayout` (`TinyRoutes/UI/GameplayScreen.swift:1409`) first. MV-06's road drawing takes a `BoardLayout`, so producing one keeps road drawing shared. Check whether its plain `init(pointsByNodeID:coordinateScale:minX:maxY:originX:originY:)` is enough on its own, without the camera plan and extents.
- If it is, write a `MultiVanBoardLayout.make(level:in rect:) -> BoardLayout` factory. If it needs the camera plan, ask your reviewer before writing a separate type.
- Use one scale for x and y (`min(width / columns, height / rows)`) so squares stay square, then centre the board in the rect.
- Grid y points **up** (see the plan's sketch); screen y points down. Flip it once, here.
- Leave padding of about half a grid unit so houses and vans at the edge aren't clipped.

**Done when:** unit tests check that the corners of a 5×7 grid map inside the rect on an iPhone SE size and a Pro Max size, and that y = 6 is above y = 0 on screen.

---

### MV-13 · Board view, plain version

**Level:** Junior+ · **Depends on:** MV-06, MV-08, MV-11, MV-12

In `MultiVanBoardView.swift`, draw the board with plain shapes. Nicer art comes later in M2 and M3.

- Roads: one pale neutral colour, drawn with the shared road path helper from MV-06.
- Houses: a coloured square at the node.
- Dead ends: a short grey bar.
- Vans: a coloured circle at `van.position`.
- Previews: a dashed line in each van's colour along `previewRoutes`.

**Guidance:**
- Draw with a `Canvas` or a `ZStack` of `Path`s. A `Canvas` is faster with many vans and simpler for dashed lines.
- The view should only **read** engine state. It must never decide game rules, such as whether a switch is locked. If you need a fact, add it to the engine.
- Build the preview line by joining each edge's `RoadPath` from MV-06 into one `Path`, then stroke it with `StrokeStyle(dash:)`.

**Done when:** a SwiftUI preview shows levels 1 and 2 with every element visible.

---

### MV-14 · Switch views and taps

**Level:** Junior+ · **Depends on:** MV-13

Show a tappable switch on every node with 2–4 exits, with an arrow toward the active exit and faint stubs toward the others. Tapping calls `engine.tapSwitch(nodeID:)`.

**Guidance:**
- Reuse `SwitchNodeView` (`TinyRoutes/UI/SwitchNodeView.swift`) and `SwitchArrowDirectionResolver` (`GameplayScreen.swift:1168`). They already take a `RuntimeRouteGraph`, so they should work as is. Read `SwitchNodeViewTests` to see how they're used.
- Make the hit area at least 44×44 pt, even when the board is scaled down.
- After a tap, the arrow and the preview line must both update in the same frame. If they don't, the engine probably isn't publishing changes. Mark it `@Observable` (iOS 17) or use `ObservableObject`.

**Done when:** on level 2 you can tap the switch, watch the arrow and the preview move, and see the ✗ change to ✓.

---

### MV-15 · Gameplay screen and game loop

**Level:** Junior+ · **Depends on:** MV-10, MV-14

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because it ties together SwiftUI rendering, the game loop and app lifecycle (frames, backgrounding, pausing).

In `MultiVanGameplayScreen.swift`, build the screen flow from the plan:

- Top HUD: level name, van chips (colour symbol → 🏠), "Changes N · Par P", and the level `hint` if it has one.
- Middle: the board.
- Bottom in plan phase: big **GO** and small "Reset switches".
- Bottom in run phase: **Stop**.
- After a fail: a simple text card with **Try again**. After a win: a simple card with **Next** and **Replay**. Polished versions come in MV-26 and MV-37.

**Guidance:**
- Drive the engine with `TimelineView(.animation)`. In its closure, work out `dt` from the previous frame's date and call `engine.advance(by: dt)`. Store the previous date in a reference type, not `@State`, so updating it doesn't trigger another render.
- Only call `advance` during `.run`. Pause it when the app goes to the background (`scenePhase`).
- Keep all game rules in the engine. The screen only maps buttons to `go()`, `stop()`, `retry()` and `resetSwitches()`.

**Done when:** levels 1 and 2 can be played from Go to the win card, and a deliberate fail on level 2 shows Try again, which keeps the switch setting.

---

### MV-16 · Prototype entry from the home screen

**Level:** Entry · **Depends on:** MV-03, MV-15

- Add a **Prototype** button to `HomeScreen` (`TinyRoutes/UI/HomeScreen.swift`) inside `#if DEBUG`.
- It opens a simple list of prototype levels. Tapping one opens `MultiVanGameplayScreen`. **Next** on the win card opens the next level.
- Present it with `.fullScreenCover` from the home screen. Don't add cases to `AppState` or `AppCoordinator`, so the prototype stays separate from production navigation.
- Keep progress (which levels are beaten, best stars) in memory, or in a separate `UserDefaults` key such as `multiVanPrototype.progress`. **Don't** touch `ProgressService`, `SaveDataRepository` or the economy.

**Done when:** in a Debug build you can open the list, play level 1, press Next, and play level 2. A Release build shows no Prototype button.

---

### MV-17 · Level validation tests

**Level:** Entry · **Depends on:** MV-03

In `TinyRoutesTests/Prototype/MultiVanLevelTests.swift`, loop over every prototype level and check:

- It decodes.
- Every node's `outgoingEdgeIDs` matches its edges (use `RouteNode.validateOutgoingEdges(against:)`).
- Every switch has 2–4 exits.
- Every node has whole-number `x` in 0–4 and `y` in 0–6.
- Every van colour has exactly one house of that colour, and every house node has no outgoing edges.
- Every `initialSwitchEdges` and `liveSwitchNodeIDs` entry points at a real switch.
- Each road is at least 1 grid unit long.

Write failure messages that name the level and node, for example `"proto_04: node s1 has 5 exits"`.

**Done when:** the tests pass for levels 1–2, and each check fails with a clear message when you break a copy of a level on purpose (show this in the PR description; don't commit the broken file).

---

### MV-18 · Solution scripts and the par check

**Level:** Junior+ · **Depends on:** MV-09, MV-17

Every level needs a recorded solution that wins with `changeCount == parChanges`.

**Guidance:**
- Define a small format in `TinyRoutesTests/Resources/PrototypeSolutions/proto_NN.solution.json`, for example:
  ```json
  { "planTaps": ["s1", "s1"], "liveTaps": [{ "atTime": 3.25, "nodeID": "s3" }] }
  ```
- The runner: apply `planTaps`, call `go()`, then advance in fixed steps, applying each live tap when the run clock passes `atTime`. Stop at an outcome or after 120 s of run time.
- Assert the outcome is `.win` and `changeCount == parChanges`. Also assert that **not** applying the plan taps doesn't win. If it does, the level has no puzzle.
- Look at `TinyRoutesTests/Support/LevelSolutionScript.swift` for how the current game does this. Copy the ideas, not the types, because the rules differ.
- Live taps will only work after MV-21. Until then, reject scripts with `liveTaps` with a clear "not supported yet" failure.

**Done when:** levels 1–2 have solutions that pass, and a deliberately wrong solution fails with a readable message.

---

### MV-19 · Author levels 3 and 4

**Level:** Entry · **Depends on:** MV-04, MV-18

Write `proto_03.json` ("Two Turns") and `proto_04.json` ("Roundabout"), plus their solution scripts, from the level table.

- Level 3: one wrong exit should loop back harmlessly. Check its preview ends in `.loopLimit` or returns to a switch, not in a crash or barrier.
- Level 4: the correct exit is two taps away from the starting exit.

**Done when:** MV-17 and MV-18 pass for all four levels, and you've played them on a device or simulator. **This is the M1 exit check.**

---

## Milestone M2: Many vans

*Exit: the level 7 crash, and its fix, read clearly.*

### MV-20 · Several vans, departure delays and crashes

**Level:** Junior+ · **Depends on:** MV-09

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because vans move at the same time, so collision checks and departure timing must not depend on update order.

Make the engine run all vans together, with each one waiting `departDelay` seconds after Go. Add crash detection and `Outcome.failCrash(vanIDs:, point:)`.

**Guidance:**
- Track a run clock (`runTime`), increased by `stepDuration` each step. A van's status goes from `waiting` to `driving` when `runTime >= departDelay`.
- In each step, move **every** van first, then check collisions. Checking during the move makes the result depend on van order.
- Check every pair: `distance(a.position, b.position) < crashDistance`. With at most 4 vans that's 6 checks, so no optimisation is needed.
- Only check pairs where both vans are `driving` (rule decision 1). Add a test where two vans share a start node with different `departDelay`s and don't crash.
- If two vans arrive at wrong houses or dead ends in the same step, pick the first one by van order in the level file, so results are deterministic.
- Set `lastFailPoint` to the midpoint of the two vans.

**Done when:** tests cover a crash at a merge, no crash when one van leaves 1.0 s later, `departDelay` being respected, and two vans both delivering for a win.

---

### MV-21 · Live switches and the lock radius

**Level:** Junior+ · **Depends on:** MV-20

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because live switching, locking and time-sensitive taps all interact with van positions every step.

- During `.run`, taps on normal switches return `.rejectedFrozen`.
- Switches in `liveSwitchNodeIDs` accept taps during the run, unless a van is within `liveSwitchLockRadius` of the node, in which case they return `.rejectedLocked`. An accepted live tap counts as a change.
- Expose `lockedSwitchNodeIDs: Set<String>` (normal switches during the run, plus live switches currently inside the radius) so the UI can draw locks without re-deriving the rules.
- Extend the MV-18 runner to apply `liveTaps`.

**Guidance:**
- Rejected taps never change `changeCount` (rule decision 2). Only `driving` vans lock a live switch, measured as straight-line distance to the node's grid point (rule decision 3). Read the radius from `MultiVanTuning` so the tuning panel can change it.
- Work out `lockedSwitchNodeIDs` at the end of each step, after collisions, so it always matches what a tap would do.
- Edge case worth a test: a van sitting exactly on a live switch node (distance 0) must lock it.
- Because vans read the switch on arrival (MV-08), a live tap applies to the next van to arrive, which is what levels 8 and 9 need.

**Done when:** tests cover a frozen normal switch during the run, a live switch accepting a tap when vans are far away, rejecting it within 0.4, counting accepted live taps, and a live tap changing the route of the second van but not the first.

---

### MV-22 · Retry highlights the fail point

**Level:** Entry · **Depends on:** MV-15, MV-20

On the board, draw a soft pulsing red ring at `engine.lastFailPoint` during the plan phase after a retry. Hide it when the player presses Go.

**Done when:** after a crash and Try again, the ring shows where the crash was, and it disappears on Go.

---

### MV-23 · Multi-van preview lines

**Level:** Junior+ · **Depends on:** MV-13, MV-20

Draw one preview per van. Where two routes share a road, shift their lines sideways so both show. End each line with a small ✓ or ✗.

**Guidance:**
- First, count how many previews use each edge, and give each van a lane index on that edge (0, 1, 2…).
- Offset a line by moving each point along the road's normal. `RoadPath.tangent(atDistance:)` gives the direction; rotate it 90° for the normal. Space the lanes about 4 pt apart on screen, centred on the road.
- Simplest working approach: sample each edge every few points along its length, offset each sample, and join them with `addLine`. This handles the curves too.
- Keep the lane order the same on every edge (for example by van order in the file), so lines don't swap sides at a node.

**Done when:** on a test level where red and blue share two roads, both dashed lines stay visible along the whole shared stretch.

---

### MV-24 · Toy van view

**Level:** Entry · **Depends on:** MV-13

In a new `MultiVanVanView.swift`, draw a top-down delivery van as a SwiftUI shape: a rounded rectangle body in the van's colour, a white rim, the colour's symbol on the roof, and two small headlight "eyes" at the front. Rotate it to face the direction of travel (`RoadPath.tangent(atDistance:)`).

- It must read clearly at about 28 pt long.
- Add `#Preview`s for all four colours, at 28 pt and at 56 pt.
- Motion (wiggle, hop, spin) comes later in MV-35.

**Done when:** the board uses this view instead of circles, and vans face the way they drive, including around turns.

---

### MV-25 · House and barrier views

**Level:** Entry · **Depends on:** MV-13

- House: a large marker with a coloured roof and the matching symbol on the door. A delivered house shows a checkmark.
- Dead end: a striped barrier cap (diagonal stripes, like a road barrier).
- Add `#Preview`s for each colour and both house states.

**Done when:** the board uses these views, and you can tell before pressing Go that a road leads to a barrier.

---

### MV-26 · Fail card

**Level:** Entry · **Depends on:** MV-15, MV-20

Replace the plain fail text with a non-blocking card that appears after `failFreezeDuration` (0.6 s):

- Crash: "Crash at the merge!" (or "Crash!" if you can't name the place).
- Wrong house: "Red went to the blue house!"
- Stuck: "Red hit a dead end!"
- A **Try again** button that calls `retry()`.

"Non-blocking" means the board stays visible behind the card. Use the existing card style (`TRGlassCardBackground`) so it matches the app.

**Done when:** each of the three fail types shows its own message after a short pause.

---

### MV-27 · Star rating

**Level:** Entry · **Depends on:** MV-09

Write a pure function `MultiVanStars.rating(changes: Int, par: Int) -> Int` for a won level. Failed runs get no stars (rule decision 4), so only the win card calls it.

- 3 stars if `changes <= par`
- 2 stars if `changes <= par + 2`
- otherwise 1 star

Show the result on the win card.

**Done when:** a parameterised test covers par 0, par 3, exactly par, par + 1, par + 2 and par + 3.

---

### MV-28 · Author levels 5 and 6

**Level:** Entry · **Depends on:** MV-19, MV-20

Write `proto_05.json` ("Two Colours") and `proto_06.json` ("Convoy") with solution scripts.

- Level 5: the starting settings send red to the blue house and blue to the red house.
- Level 6: blue leaves 1.5 s after red on the same road. Check that's enough to clear the crash distance at `vanSpeed` (1.5 s × 1.5 units/s = 2.25 units, so it is).

**Done when:** MV-17 and MV-18 pass for both.

---

### MV-29 · Author levels 7, 8 and 9

**Level:** Junior+ · **Depends on:** MV-21, MV-28

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because designing timing puzzles that are solvable with reliable margins needs careful length and timing maths.

Write "Merge", "Hold the Loop" and "Split" with solution scripts. These are the timing levels, so they need careful numbers.

**Guidance:**
- Start from the level 7 sketch in the plan. Work out each route's length to the merge by adding up `RoadPath.totalLength` for its edges, then divide by `vanSpeed` to get arrival times.
- For a crash, arrival times at the merge must differ by less than `crashDistance / vanSpeed` (about 0.23 s). For the safe route, aim for at least 1 s apart so a slightly different speed during tuning doesn't break it.
- Write a quick test helper that prints each van's arrival time at each node during a scripted run. It makes tuning far easier than guessing.
- Quarter-turn corners make roads slightly shorter than their grid distance. Use the computed length, not grid counting.
- Level 7: the starting settings must show ✓ on both previews and still crash. That's the "aha" the plan describes.
- Level 8: the loop switch is the first live switch, with the hint "⚡ switches work while vans drive." The solution's `liveTaps` time must fall in a window where no van is within 0.4 of the switch.
- Level 9: red and blue pass the same live switch, red first. Leave a comfortable gap (≥ 1 s) between them to flip it.
- Play each one yourself on a device. If you can't make the live tap on the first or second try, widen the window.

**Done when:** MV-17 and MV-18 pass for all three, and a reviewer agrees the level 7 crash reads clearly on a device. **This is the M2 exit check.**

---

### MV-30 · Deterministic replay test

**Level:** Entry · **Depends on:** MV-21

Add a test that runs the same level and taps twice, once with `advance(by: 1/60)` frames and once with uneven frames (for example alternating 0.004 s and 0.03 s), and checks that both runs end with the same outcome, the same `runTime` and the same van positions.

**Done when:** the test passes for levels 7 and 9.

---

## Milestone M3: Feel

*Exit: the Go moment feels good with the sound on.*

### MV-31 · Feedback events from the engine

**Level:** Junior+ · **Depends on:** MV-21

Make the engine report moments the UI should react to, without the engine knowing about haptics or sound.

**Guidance:**
- In `MultiVanFeedback.swift`, define `enum MultiVanEvent { case switchTapped, tapRejected(nodeID:), go, delivered(vanID:, comboIndex:), allDelivered, crashed(point:), wrongHouse(vanID:) }`.
- The engine appends events to a `pendingEvents` array as they happen. The screen reads and clears it once per frame (`drainEvents()`). This is simpler and easier to test than callbacks or Combine.
- `comboIndex` counts deliveries in this run (1, 2, 3…). The chime pitch and "×2" text use it.
- Test that each action produces the right events in the right order.

**Done when:** tests cover every event type, and the screen drains events each frame (even if nothing reacts to them yet).

---

### MV-32 · Haptics

**Level:** Entry · **Depends on:** MV-31

Map each event to the haptic in the plan's "Feel" table using SwiftUI `.sensoryFeedback(_:trigger:)` (iOS 17).

- Respect the existing `UserSettings.areHapticsEnabled` setting (`TinyRoutes/Domain/UserSettings.swift`). Don't add a new setting.
- Haptics only work on a real device. Test there and note in the PR which device you used.

**Done when:** every row of the table has the right haptic on a device, and turning haptics off in Settings silences them.

---

### MV-33 · Sound effects

**Level:** Entry · **Depends on:** MV-31

- Add a handful of short `.caf` files to `TinyRoutes/Resources/PrototypeSounds/`: click, dull tick, vroom, chime, fanfare, bonk, nope horn. Use only sounds with a licence that allows this (CC0 or made yourself). Record the source and licence of each in a `README.md` in that folder.
- Write a small `MultiVanSoundPlayer` that preloads one `AVAudioPlayer` per sound and plays it on the matching event.
- The delivery chime rises one step per `comboIndex`. The easiest way is a separate file per step (chime_1 … chime_4).
- Respect `UserSettings.areSoundEffectsEnabled` and `soundEffectsVolume`. These already exist and serve as the mute toggle.
- Set the audio session category to `.ambient` so the game doesn't stop the player's music.

**Done when:** every event plays its sound, and sound effects off in Settings silences them.

---

### MV-34 · Delivery payoff

**Level:** Entry · **Depends on:** MV-25, MV-31

On `delivered`: the house does a short bounce, a "+1" pops up and fades, and from the second delivery on a combo label ("×2", "×3") appears. On `allDelivered`: show confetti with the existing `TRConfettiScene`.

- Use `withAnimation(.spring)` and keep each effect under about 0.6 s.
- Skip the bounce and pop if `UserSettings.reducesExtraAnimations` is on.

**Done when:** a 3-van win shows +1, ×2, ×3 and then confetti.

---

### MV-35 · Van personality

**Level:** Entry · **Depends on:** MV-24, MV-31

Add the motion-only reactions from the plan:

- Idle wiggle (a small rotation back and forth) while waiting or parked.
- A happy hop (a quick scale up and down) on delivery.
- A lean forward on Go.
- A dizzy spin on a crash.

Keep it subtle, and skip the idle wiggle if `reducesExtraAnimations` is on.

**Done when:** each reaction is visible in a screen recording attached to the PR.

---

### MV-36 · Crash effects

**Level:** Entry · **Depends on:** MV-31, MV-35

On `crashed`: shake the board (a few quick horizontal offsets), show a puff (a few expanding, fading circles) at the crash point, and spin both vans. Then hold for the 0.6 s freeze before the fail card.

**Done when:** the crash on level 7 looks funny rather than harsh. Get a second opinion in the PR.

---

### MV-37 · Switch states during the run

**Level:** Entry · **Depends on:** MV-14, MV-21

- During the run, normal switches drop to 50% opacity and show a tiny lock.
- Live switches have an amber ring and a lightning badge at all times, and pulse gently while they can be tapped (not in `lockedSwitchNodeIDs`).
- On `tapRejected`, the switch gives a small shake and its lock icon flashes.

Read lock state only from `engine.lockedSwitchNodeIDs`.

**Done when:** in level 8 you can see the live switch stop pulsing as a van nears it, and tapping a frozen switch shakes it.

---

### MV-38 · Fast-forward

**Level:** Entry · **Depends on:** MV-15

Add a hold-to-fast-forward button in the run phase. While held, pass `dt * fastForwardMultiplier` to `engine.advance(by:)`. Because the engine uses fixed steps, results don't change; it just runs twice as many steps per frame.

Count how often it's used per level for the playtest log (MV-43).

**Done when:** holding the button doubles speed, and a test shows the outcome of a level is the same with and without it.

---

### MV-39 · Win card

**Level:** Entry · **Depends on:** MV-27, MV-34

Replace the plain win card: stars animate in one at a time, then **Next** (primary, default) and **Replay**. Look at `TRResultStarRatingView` and `TRResultActionButton` in `TinyRoutes/UI/Components/` before building new ones.

**Done when:** winning shows animated stars and Next goes to the next level. On level 12, Next goes back to the level list.

---

### MV-40 · Background and board card

**Level:** Entry · **Depends on:** MV-13

Show the existing street-map art (`SpriteImage("background")`, or `TRMapBackgroundView`) dimmed to about 40%, with a soft rounded card behind the board so roads stand out.

**Done when:** roads, vans and previews are easy to read in bright light. Check outside or at full brightness.

---

### MV-41 · Accessibility basics

**Level:** Entry · **Depends on:** MV-14, MV-24

Give switches, vans, houses and buttons VoiceOver labels, for example "Switch, pointing up, 2 exits" or "Red van, parked at red house". The plan only asks for basic labels, so don't go further than that.

**Done when:** with VoiceOver on, every interactive element reads something sensible.

---

## Milestone M4: Content and playtest

### MV-42 · Author levels 10, 11 and 12

**Level:** Junior+ · **Depends on:** MV-29

**Reasoning:** High. Use high reasoning effort for this task (for example, when working with an AI coding assistant), because these levels combine several complex mechanics (timing, shared live switches, four vans) at once.

Write "Three's Company", "Rush" and "Big Delivery" with solution scripts.

**Guidance:**
- Follow the MV-29 guidance on timing. Level 11 combines the level 7 and level 9 ideas, so reuse those layouts as a starting point.
- Level 12 has 4 vans, 5 switches (at most 1 live), one loop and one merge. Check it fits the 5×7 grid before writing JSON; sketch it first.
- Par should be the true minimum. Try to beat your own par. If you can, the par is wrong.
- For a 4-van level, preview lines may overlap heavily. Check MV-23's lane offsets still read clearly; if not, raise it with your reviewer.

**Done when:** MV-17 and MV-18 pass for all three, and two other people have played them.

---

### MV-43 · Local playtest log

**Level:** Junior+ · **Depends on:** MV-31, MV-38

The plan says to log through `AnalyticsAdapter`, but `TinyRoutes/Infrastructure/AnalyticsAdapter.swift` is an empty placeholder. Build the smallest thing that works.

**Guidance:**
- Write a `MultiVanPlaytestLog` that appends one record per attempt to a JSON Lines file in the app's Documents folder: level ID, attempt number, outcome and fail reason, time in plan phase, changes vs par, fast-forward use, and a timestamp.
- Record "quit at level" when the player leaves the prototype list or the app goes to the background mid-level.
- Keep it inside `TinyRoutes/Prototype/`. If you want to route through `AnalyticsAdapter`, add one simple `log(event:properties:)` method there and get it reviewed, since that's a production file.
- Don't collect names or device IDs. Use a random session ID created when the prototype opens.
- Write to the file off the main thread, or batch writes, so logging never causes a dropped frame.

**Done when:** after playing three levels, the file holds one record per attempt with all fields filled in.

---

### MV-44 · View and share the playtest log

**Level:** Entry · **Depends on:** MV-43

Add a "Playtest log" row to the prototype level list (Debug only) that shows a per-level summary (attempts, most common fail reason, average changes vs par) and has a `ShareLink` to send the raw file.

**Done when:** you can AirDrop the log from a device to a Mac.

---

### MV-45 · Tuning panel

**Level:** Entry · **Depends on:** MV-15

Add a small Debug-only panel (for example a gear button on the prototype list) to change `vanSpeed`, `crashDistance` and `liveSwitchLockRadius` live, so the team can tune during M4 without rebuilding. Store overrides in `UserDefaults` under a `multiVanPrototype.` prefix, with a "Reset to defaults" button.

**Done when:** changing speed in the panel changes how fast vans drive on the next Go.

---

### MV-46 · Tuning pass

**Level:** Junior+ · **Depends on:** MV-42, MV-45

Play all 12 levels in order with fresh eyes and adjust speed, delays and layouts until each level teaches its one idea.

**Guidance:**
- Change one thing at a time and replay the levels around it. A speed change shifts every timing level.
- After any speed change, rerun the solution tests (MV-18). They'll tell you which timing windows broke.
- Note every change and why in the PR. The playtest results will be compared against this baseline.

**Done when:** all solution tests pass, and the team agrees each level's idea comes across.

---

### MV-47 · Playtest kit

**Level:** Entry · **Depends on:** none (can start any time)

Write `docs/prototype/playtest_kit.md` from the plan's "Playtest plan": a checklist for the session host (charge the phone, clear the log, start in level 1, say nothing during levels 1–3), the three questions to ask afterwards, and a results table matching the success criteria and "signs to change direction".

**Done when:** someone who hasn't read the plan could run a session from the kit alone.

---

### MV-48 · TestFlight build

**Level:** Junior+ · **Depends on:** MV-46

**Guidance:**
- The Prototype button is behind `#if DEBUG`, so a normal Release archive won't show it. Agree with Jake on one of these before you start: add a hidden settings toggle (the plan allows "behind a settings toggle"), or archive a Debug-configuration build for internal testers only.
- You'll need App Store Connect access and the signing team. Ask Jake. Don't create new certificates or identifiers yourself.
- Check the build on a real device from TestFlight, not only from Xcode, before inviting playtesters.

**Done when:** at least one person outside the team installs the build from TestFlight and reaches level 1.

---

## Dependency overview

```
M1  MV-01 ─┬─ MV-02 ─┬─ MV-03 ─┬─ MV-17 ─ MV-18 ─ MV-19 (M1 exit)
           │         │         └─ MV-16
           │         ├─ MV-04
           │         └─ MV-12
           ├─ MV-05 ─ MV-07 ─┬─ MV-08 ─ MV-09 ─ MV-10
           │                 └─ MV-11
           └─ MV-06
           MV-13 (06, 08, 11, 12) ─ MV-14 ─ MV-15 ─ MV-16

M2  MV-09 ─ MV-20 ─ MV-21 ─┬─ MV-29 (M2 exit) ─ MV-42
                           ├─ MV-30
                           └─ MV-31 (M3 events)
    MV-22, MV-23, MV-24, MV-25, MV-26, MV-27, MV-28 can run in parallel once their inputs land.

M3  MV-31 ─┬─ MV-32, MV-33, MV-34, MV-35 ─ MV-36
           └─ MV-43 ─ MV-44
    MV-37, MV-38, MV-39, MV-40, MV-41 can run in parallel.

M4  MV-42 ─ MV-46 ─ MV-48;  MV-45 any time after MV-15;  MV-47 any time.
```

### Good first tasks

If you're new to the codebase, start with one of these: **MV-01**, **MV-02**, **MV-04**, **MV-06**, **MV-11**, **MV-27** or **MV-47**.
