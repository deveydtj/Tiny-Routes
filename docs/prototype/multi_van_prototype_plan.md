# Multi-Van Prototype Plan

Status: proposal · Owner: Jake · Last updated: 2026-10-31

Implementation tasks: [multi_van_tasks.md](multi_van_tasks.md)

## Goal

Find out, with a small playable build, whether this loop is fun:

> **Set the switches, press Go, and watch every van reach its matching house.**

The prototype answers one question: *do people who have never seen the game understand it in seconds, enjoy the "Go" moment, and want the next level?* It is not a production feature. It lives beside the current game and leaves `RouteEngine`, the V3 generator contract, and the production levels untouched.

## Why this direction

An analysis of the current build found:

- **No planning.** Only the next switch can be tapped, inside a 2-second window, and later objectives stay hidden. Each decision is a guess.
- **Mostly waiting.** In levels 12–27 the last tap lands at about 20 s, but the level runs 43–87 s. That leaves 50–78% of play time with nothing to do.
- **No stakes.** The time limit is 360 s and stars depend only on taps. Wrong branches loop back, so mistakes cost nothing.
- **No feel.** There are no haptics or sounds anywhere in the app.
- **Hard-to-read boards.** Generated maps are 4–7 phone widths wide on a portrait screen, with knotted detours.

Successful casual puzzle games are readable at a glance, calm while you think, give a payoff when the plan plays out, and let you retry instantly after your own mistake. The prototype is built around those four traits.

## Core rules

| Rule | Prototype behaviour |
|---|---|
| Vans | 1–4 per level. Each has a colour (red, blue, yellow, green) and a start node. |
| Houses | Terminal nodes, one per colour. Each van must reach its own house. |
| Roads | One-way roads, the same as today's directed edges. |
| Switches | Any node with 2–4 outgoing roads. Each tap moves it to the next exit in order, so a 3-way switch can take 2 taps. |
| **Plan phase** | Nothing moves and there is no timer. Every switch is tappable. Each van shows a coloured preview line along its current route. |
| **Go** | All vans start together. Each van leaves after its own `departDelay` (seconds), so starts can be staggered. |
| Run phase | Vans move at a fixed speed (start at 1.5 grid units/s and tune it). Normal switches are frozen. A **Stop** button returns to the plan phase straight away with the settings kept. |
| Live switches | A separate kind of switch, introduced in level 8, with its own look (amber ring and lightning badge). Only these can be tapped mid-run, and only when no driving van is within 0.4 units (straight-line distance to the switch's grid point; tunable, revisit at playtest). A live tap counts as a change. Listed per level in `liveSwitchNodeIDs`. |
| Win | Every van is parked at its matching house. |
| Fail: crash | Two driving vans come within 0.35 units of each other, for example at a merge. Vans still waiting to depart, or already parked, never crash. |
| Fail: wrong house | A van parks at a house of a different colour. |
| Fail: stuck | A van reaches a dead end, marked with a barrier. |
| Retry | **Keeps your switch settings.** One tap goes back to the plan phase with the crash spot still highlighted, so you can fix the plan instead of rebuilding it. |
| Stars | ★ all delivered · ★★ changes ≤ par + 2 · ★★★ changes ≤ par. "Changes" counts every accepted switch tap, in planning and during the run. Rejected taps don't count. Failed runs get no stars. |

### Design principle: difficulty comes from vans interacting

Preview lines show exactly where each van will end up, so hidden information can't be the challenge. Difficulty has to come from the vans affecting each other:

1. **Shared switches.** Red needs the left exit and blue needs the right one at the same switch. You either find another road or, on a live switch, flip it between them during the run.
2. **Timing.** Two routes merge. If both vans arrive together, they crash. You fix it by sending one van the long way or holding it in a loop.
3. **Departure order.** A van that leaves later can use a switch after the first van has passed it.

Previews do **not** show timing. Spotting the crash before pressing Go is the "aha". The first crash a player sees should happen with every preview showing ✓. That surprise is how they learn that timing matters.

## Board and visual rules

- **Portrait grid.** Nodes sit on whole-number grid points, at most 5 columns × 7 rows. Scale the whole level to fit between the HUD and the Go button. No camera following and no scrolling.
- **Roads.** Use straight lines or single 90° turns, with at least 1 grid unit per segment. Roads that run side by side never overlap.
- **Calm roads, colourful vans.** Draw roads in one pale neutral colour. Colour comes only from vans, houses, and preview lines.
- **Preview lines.** For each van, draw a dashed line in its colour from its start along the current switch settings. Stop at a house, a dead end, or after 40 roads if the route loops. When two routes share a road, shift their lines slightly sideways so both stay visible. End each line with a small ✓ if it reaches the matching house, otherwise ✗.
- **Switches.** A white disc with an arrow toward the active exit and faint stubs toward the others. During planning, all switches are bright. During the run, normal switches drop to 50% opacity and show a tiny lock. Live switches stay bright with an amber ring and lightning badge, and pulse when they can be tapped.
- **Colour plus shape.** Each colour always comes with a symbol: red ●, blue ▲, yellow ■, green ★. The symbol appears on the van's roof, the house's door and the van chips. Matching then still works for colour-blind players and on dim screens.
- **Houses.** A large marker with a coloured roof and the matching symbol. A delivered house gets a checkmark and a short bounce.
- **Vans.** Chunky, toy-like, top-down delivery vans with rounded corners, a white rim and two headlight "eyes" facing the way they drive. They must still read clearly at about 28 pt. They react: idle wiggle while parked, a happy hop and honk on delivery, dizzy spin on a crash. No faces, speech or story. The personality comes from motion only.
- **Dead ends.** A striped barrier cap, so you can tell before pressing Go that a road leads nowhere.
- **Background.** The existing street-map art, dimmed to about 40% behind a soft board card, so roads don't compete with it.
- **One marker style everywhere.** Don't repeat the levels 1–4 reference-style split.

## Feel (juice) checklist

iOS 17 is the minimum, so use SwiftUI `.sensoryFeedback` for haptics.

| Moment | Haptic | Sound | Visual |
|---|---|---|---|
| Switch tap | `.selection` | soft click | Arrow springs to the new exit; preview line redraws |
| Rejected tap (frozen or locked switch) | `.impact(weight: .light)` | dull tick | Small shake; lock icon flashes |
| Go | `.impact(weight: .medium)` | engine "vroom" | Button presses in; vans lean forward |
| Van delivered | `.success` | Chime, one step higher for each van in the run | House bounce, "+1" pop, combo text "×2", "×3" |
| All delivered | `.success` | Short fanfare | Reuse `TRConfettiScene`; stars animate in |
| Crash | `.error` | Comic bonk | Screen shake, puff at the crash point, both vans spin |
| Wrong house | `.warning` | "Nope" horn | Van bounces off the house; ✗ over it |

Prototype sounds can be a handful of short bundled `.caf` files played through `AVAudioPlayer`. Add a mute toggle using the existing `UserSettings`.

## Screen flow

1. **Plan.** At the top: level name, van chips (● → 🏠 for each colour), and the change counter "Changes 0 · Par 2". The board in the middle. At the bottom: a big **GO** button and a small "Reset switches" button.
2. **Run.** At the bottom: **Stop** (back to the plan, settings kept) and hold-to-fast-forward (2×). Only live switches can be tapped.
3. **Fail.** Freeze for 0.6 s at the crash, then a non-blocking card ("Crash at the merge!") with **Try again**, which keeps the plan.
4. **Win.** Stars, then **Next** (default) and Replay.

Entry: add a **Prototype** button to `HomeScreen`, shown only in Debug builds or behind a settings toggle. It opens a simple list of prototype levels.

## Level set (12 hand-made levels)

Each level teaches one idea or combines two ideas players already know. Par is the minimum number of changes. Every level must have a recorded solution script in its tests.

| # | Name | Vans | Idea | Layout sketch | Par |
|---|---|---|---|---|---|
| 1 | Go! | 1 | Press Go | Van bottom-left, one bend, red house top-right. No switches. | 0 |
| 2 | Pick a Lane | 1 | Tap a switch | One 2-way switch. It starts pointing at a barrier; the other exit goes to the house. | 1 |
| 3 | Two Turns | 1 | Switches in sequence | Two switches. One wrong exit loops back harmlessly; the other hits a barrier. | 2 |
| 4 | Roundabout | 1 | 3-way cycling | One 3-way switch. The correct exit is two taps away. | 2 |
| 5 | Two Colours | 2 | Matching | Red and blue, each with its own switch. The starting settings swap their houses. | 2 |
| 6 | Convoy | 2 | Payoff: chained deliveries | Blue leaves 1.5 s after red on the same road. One shared switch that both need set the same way. | 1 |
| 7 | Merge | 2 | Collisions | Two roads merge into one before the houses. The short route makes red crash into blue; switch red to the longer road. | 1 |
| 8 | Hold the Loop | 2 | Live switches | The loop exit is the first live switch. Red circles until blue clears the merge, then you tap to let red out. Short tutorial line: "⚡ switches work while vans drive." | 2 |
| 9 | Split | 2 | Shared live switch, opposite exits | Red, then blue, pass one live switch. Red needs left and blue needs right, so flip it after red passes. | 2 |
| 10 | Three's Company | 3 | Scale up | Three vans, three switches, two wrong-house traps. No timing tricks. | 3 |
| 11 | Rush | 3 | Merge + shared live switch | Combines levels 7 and 9. One live switch. | 3 |
| 12 | Big Delivery | 4 | Final | 4 vans, 5 switches (at most 1 live), one loop, one merge. | 5 |

Example sketch for level 7 ("Merge"). Grid coordinates have y pointing up; S is a switch, M is a merge (a pass-through node with two incoming roads).

```
y6   [R-house]   [B-house]
          ^          ^
y5        +----S2----+          S2: route to the correct house
               ^
y4             M                merge: both vans pass here
             ^   ^
y3   +-------+   +------B       blue starts at x4, departDelay 0
     |       |
y2   |       S1                 S1 short way: up to M, arrives with blue -> crash
     |       |                  S1 long way: left loop, arrives 1.3 s later -> safe
y1   +-------+
             ^
y0           R                  red starts at x2, departDelay 0
```

Stretch levels, only if levels 1–12 test well: one-shot bridges that close after one van crosses (`usageLimit` already exists on `EdgeAvailabilityRule`), and a level where two roads cross without connecting.

## Technical approach

Build it as a standalone module. Reuse geometry and rendering, not the engine.

```
TinyRoutes/Prototype/
  MultiVanLevel.swift        // Decodable level: wraps RouteGraph + vans + houses + par + flags
  MultiVanEngine.swift       // Fixed-step simulation: phases, vans, switching, collisions, outcome
  MultiVanRoutePreview.swift // Traces each van's route along the current switch settings
  MultiVanGameplayScreen.swift
  MultiVanBoardView.swift    // Roads, switches, houses, vans, previews
  MultiVanFeedback.swift     // Haptic + sound events
  MultiVanLevelRepository.swift
TinyRoutes/Resources/PrototypeLevels/proto_01.json … proto_12.json
TinyRoutesTests/Prototype/MultiVanEngineTests.swift
```

### Level JSON

The graph uses the existing `RouteGraph` shape (nodes with `x`/`y`, edges with `roadShape`), so `RoadPath` geometry and road drawing carry over unchanged.

```json
{
  "id": "proto_07",
  "name": "Merge",
  "graph": { "nodes": [ ... ], "edges": [ ... ] },
  "vans": [
    { "id": "red",  "color": "red",  "startNodeID": "red_start",  "departDelay": 0 },
    { "id": "blue", "color": "blue", "startNodeID": "blue_start", "departDelay": 0 }
  ],
  "houses": [
    { "nodeID": "red_house",  "color": "red" },
    { "nodeID": "blue_house", "color": "blue" }
  ],
  "initialSwitchEdges": { "s1": "s1_short", "s2": "s2_left" },
  "parChanges": 1,
  "liveSwitchNodeIDs": [],
  "hint": "Two vans can't share the merge at the same time."
}
```

### Engine notes

- Build `RuntimeRouteGraph` the same way `RouteEngine.buildGraph` does (around `RouteEngine.swift:245`). Pull that construction into a small shared helper rather than copying it.
- Each van keeps its own state (current edge, progress, transition, delivered/crashed). Switch state is shared by all vans: it's the active outgoing edge on `RuntimeRouteNode`.
- Advance in fixed 1/120 s steps for determinism. Check collisions after each step using pairwise distance between van positions.
- When a van arrives at a node: a house → park it, or fail if the colour is wrong; a dead end → stuck; otherwise take the active outgoing edge.
- Expose `phase`, `vans`, `changeCount`, `outcome`, `lockedSwitchNodeIDs`, and `previewRoutes` so the UI never re-derives game rules.

### Reuse from the current code

- `RoadPath` geometry, `BoardLayout`, `SwitchArrowDirectionResolver`, and the visuals in `SwitchNodeView`.
- Road drawing: `RouteBoardView.roadPath(for:layout:)` is private in `GameplayScreen.swift`. Move it into a shared helper so both boards can use it.
- `TRConfettiScene`, the `TRGameplayStyle` colours, and `SpriteImage("background")`.

### Gotchas

- `project.pbxproj` is committed and generated by XcodeGen. After adding files, run `xcodegen generate` and commit the result.
- `LevelRepository.resolveAllLevelURLs` also picks up any `.json` at the bundle root. Keep prototype levels in their own subdirectory and make sure they don't end up in the production level list. Add a test that checks this.
- Don't wire the prototype into `ProgressService` or the economy. Keep its progress in memory, or in a separate `UserDefaults` key.

## Tests

- **Engine:** delivery, wrong house, dead end, crash at a merge, no crash when spaced apart, `departDelay`, live-switch lock radius, change counting, stars, deterministic replay.
- **Preview:** routes stop at houses, dead ends, and the loop limit, and update after each tap.
- **Levels:** every `proto_*.json` decodes, every switch has 2–4 exits, all nodes lie on the 5×7 grid, and each level's solution script finishes with changes equal to its par.

## Milestones

1. **M1 Skeleton.** Engine with one van, plan and run phases, levels 1–4, plain rendering. *Exit: levels 1–4 are playable start to finish.*
2. **M2 Many vans.** Several vans, colours, houses, collisions, preview lines, retry that keeps the plan, levels 5–9. *Exit: the level 7 crash, and its fix, read clearly.*
3. **M3 Feel.** Haptics, sounds, delivery combo, crash shake, fast-forward, stars, win and fail cards. *Exit: the Go moment feels good with the sound on.*
4. **M4 Content and playtest.** Levels 10–12, tuning pass, TestFlight build.

## Playtest plan

- **Who:** at least 5 people who haven't seen the game, ideally including 2 who don't play games often.
- **How:** hand them the phone and say nothing. Watch levels 1–3 silently, then let them play on freely.
- **Log locally** through `AnalyticsAdapter`, per level: attempts, fail reasons, time in the plan phase, changes compared with par, fast-forward use, and the level where they quit.
- **Ask afterwards:** "What were you trying to do?", "Which level was best, and which was worst?", "Would you play more?"

### Success criteria

- At least 4 of 5 players press Go without help by level 2.
- Levels 7–12 average 1–3 attempts. Fewer means too easy; more means too hard.
- At least 3 of 5 finish all 12 levels or ask for more.
- Players watch most runs instead of fast-forwarding every time.

### Signs to change direction

- Players don't spot crashes before pressing Go, even by level 9: show timing more clearly, for example with a "ghost run" preview.
- Players feel trapped watching a run they know will fail, and don't find Stop: make Stop bigger, or pulse it when a crash is coming.
- Players use live switches to skip planning in levels 9–12: limit levels to at most one live switch, or lock it once any van has passed it.
- The run phase feels boring even when short: raise speed, shorten roads, add more vans.

## Out of scope for the prototype

The level generator, production validation gates, the shop, cosmetics, the economy, ads and IAP, daily challenges, progression saved to the player profile, accessibility polish beyond basic labels, and iPad layouts.

## Design decisions

These replace the earlier open questions. Each one is a hypothesis for the playtest to confirm or overturn.

### 1. Live switching: only on special live switches, introduced at level 8

**Decision:** normal switches freeze when you press Go. A separate, clearly marked *live switch* (amber ring, ⚡) can be tapped mid-run, and appears only in levels built around it. A **Stop** button returns to the plan phase at any time with the settings kept.

**Why:**
- **People take the low-effort path.** If every switch works mid-run, most players skip planning and fix things as they happen. That removes the "aha" and the pride of watching *your* plan work, which is the hook of the whole design.
- **Being unable to act on a crash you can see is the worst frustration in this design.** Freezing switches without any way out would cause it. Stop gives that control back without turning the game into a reflex test.
- **One rule per thing that looks different.** When every live switch looks different from normal switches, players can always tell what they can tap. Switches that work sometimes and not at other times break people's sense of the rules.
- **Variety in small doses.** A timed tap is a fun change of pace when it's rare and announced. Used everywhere, it pushes away the relaxed players this game is aimed at.

### 2. Preview ✓/✗: keep it for all 12 levels; never preview collisions

**Decision:** the ✓/✗ at the end of each route stays throughout. Collisions and timing are never previewed. Every colour also gets a matching symbol (● ▲ ■ ★).

**Why:**
- **Hiding the ✓ creates busywork, not challenge.** The route line already shows where a van ends up, so removing the ✓ just makes players trace lines. Good difficulty comes from the puzzle's real tension, which here is vans interacting.
- **It sets up the best learning moment.** When all ✓s show, pressing Go and crashing anyway is a memorable surprise that teaches timing with no tutorial text.
- **Never rely on colour alone.** About 1 in 12 men has some colour-vision deficiency, and phones are played outside in glare. A symbol next to each colour costs nothing and removes a hidden reason people quit.

### 3. Theme: toy-like vans on a clean board

**Decision:** keep vans, styled as chunky, rounded, toy-like vehicles with headlight "eyes" and motion-based reactions (hop, honk, dizzy spin). Keep the board itself minimal.

**Why:**
- **A familiar picture means nothing to explain.** "Vans deliver to the matching house" needs no explanation; "dots go to nodes" does.
- **Rounded, slightly cute shapes make people care.** Players root for a little van and wince when it crashes, but feel nothing for a dot. That caring is what makes the delivery satisfying.
- **Crashes become funny instead of punishing.** A dizzy van that went bonk reads as comedy, which makes failure light and keeps people retrying. Two dots overlapping just reads as an error.
- **Abstract minimalism appeals to a smaller audience.** It suits players who like design for its own sake. For broad appeal, keep the cute objects and the clean board.

### 4. If the prototype passes, multi-van replaces the current mode

**Decision:** don't ship two modes. If the playtest meets its success criteria, multi-van *is* Tiny Routes. Parts of the current mode carry over:
- Single-van levels become the tutorial (levels 1–4 already are).
- The reflex idea survives as the live switch.
- The V3 generator's ability to prove levels solvable becomes the plan for generating multi-van levels later.

**Why:**
- **One mental model and one hook.** New players decide in seconds what a game *is*. Two modes at the start means more choice at the moment of least commitment, and an unclear store page and ad message.
- **Avoid the sunk-cost trap.** The current mode's loop isn't fun yet, and keeping it because of the work already put in would dilute the game that is. What carries forward is the infrastructure (graph, geometry, validation), not the mode.
- **Add a second mode later.** Once the core game keeps players, a remix mode (daily puzzle, time attack) can bring lapsed players back. That's when it helps rather than confuses.
