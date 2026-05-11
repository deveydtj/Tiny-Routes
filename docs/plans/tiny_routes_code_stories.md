# Tiny Routes Code Stories

This document breaks the **Tiny Routes** backlog into granular development stories. Each story is designed to be small enough for a developer or AI coding agent to implement independently, and the story order is aligned with `tiny_routes_game_concept.md` and `tiny_routes_epics_features_plan.md`.

---

## Story Template

Each story should follow this format:

- **Story ID**
- **Title**
- **Goal**
- **Files likely involved**
- **Implementation steps**
- **Acceptance criteria**
- **Testing notes**
- **Do not do / out of scope**

---

## Backlog Alignment

- **STORY-001 to STORY-019** cover the P0 prototype loop from project setup through timer and tap tracking.
- **STORY-020 onward** cover MVP systems such as stars, results, progression, monetization, cosmetics, analytics, onboarding, and settings.
- The first engineering milestone stops at a playable route loop with a result screen; stars, coins, ads, and cosmetics stay in the MVP backlog.

---

# Core Backlog Stories

---

## STORY-001 — Create Project Structure ✅ COMPLETED

**Goal:**  
Establish the initial project folder and module layout for Tiny Routes.

**Files likely involved:**

- `TinyRoutes/`
- `App/`
- `Domain/`
- `Gameplay/`
- `UI/`
- `Services/`
- `Infrastructure/`

**Implementation steps:**

1. Create the Tiny Routes project.
2. Set the app to portrait mode.
3. Create the base folder structure.
4. Add placeholder files for each layer.
5. Confirm the project builds and launches.

**Acceptance criteria:**

- App builds successfully.
- App launches on simulator.
- Folder structure matches the planned architecture.
- No gameplay logic exists yet.

**Testing notes:**

- Run the app in the iOS simulator.
- Confirm no startup crash.

**Do not do / out of scope:**

- Do not add gameplay.
- Do not add ads.
- Do not add IAP.
- Do not add cosmetics.

**Status:** ✅ Completed — folder and file skeleton created under `TinyRoutes/`, covering all planned architectural layers (App, Domain, Gameplay, UI, Services, Infrastructure) with placeholder Swift stubs. Portrait orientation configured in `Resources/Info.plist`. Note: an Xcode project file is not part of this story's scope; "App builds / launches" criteria will be fully verified once the Xcode project is wired up in a follow-on setup step.

---

## STORY-002 — Add App State Machine

**Goal:**  
Create a central app flow that can move cleanly between boot, menus, gameplay, pause, results, shop, and settings.

**Files likely involved:**

- `App/AppCoordinator.swift`
- `App/AppState.swift`
- `UI/HomeScreen.swift`
- `UI/LevelSelectScreen.swift`
- `UI/GameplayScreen.swift`
- `UI/ResultScreen.swift`
- `UI/SettingsScreen.swift`

**Implementation steps:**

1. Define the core app states.
2. Create a single coordinator or state container that owns transitions.
3. Add boot, main menu, level select, gameplay, pause, level complete, and level failed flows.
4. Add placeholder routing for shop and settings.
5. Keep gameplay logic out of menu screens.
6. Confirm restart, resume, and exit paths are represented in the app flow.

**Acceptance criteria:**

- Screens transition cleanly.
- Gameplay can be started, paused, resumed, restarted, and exited.
- Menu screens do not own gameplay logic.
- Shop and settings can be added without restructuring the app flow.

**Testing notes:**

- Launch the app and confirm it reaches the first interactive screen.
- Enter gameplay, pause, resume, restart, and exit.
- Complete or fail a level and confirm the result flow returns to the app shell cleanly.

**Do not do / out of scope:**

- Do not build the final shop UI yet.
- Do not implement persistence yet.
- Do not integrate ads or analytics yet.

---

**Status:** ✅ Completed — implemented a centralized `AppCoordinator` state machine with explicit transitions for boot, menu, level select, gameplay, pause, level complete/failed, plus placeholder shop/settings routes. `ContentView` now renders screen shells by state, and UI placeholders expose restart/resume/exit flow controls without embedding gameplay logic in menu screens.

## STORY-003 — Add Core Domain Models

**Goal:**  
Create the pure data models used by the game.

**Files likely involved:**

- `Domain/LevelData.swift`
- `Domain/RouteNode.swift`
- `Domain/RouteEdge.swift`
- `Domain/RouteGraph.swift`
- `Domain/PlayerProfile.swift`
- `Domain/CosmeticItem.swift`

**Implementation steps:**

1. Define `LevelData`.
2. Define `RouteNode`.
3. Define `RouteEdge`.
4. Define `RouteGraph`.
5. Define `PlayerProfile`.
6. Define `CosmeticItem`.
7. Keep all models free of UI or SpriteKit dependencies.

**Acceptance criteria:**

- Domain models compile.
- Models contain no UI references.
- A route graph can be created from nodes and edges.
- Player profile can store basic progress fields.

**Testing notes:**

- Create sample instances in unit tests.
- Verify route graph relationships.

**Do not do / out of scope:**

- Do not implement movement.
- Do not implement rendering.
- Do not implement persistence yet.

---

## STORY-004 — Add Level JSON Schema

**Goal:**  
Define the JSON format used to describe levels.

**Files likely involved:**

- `Resources/Levels/level_001.json`
- `Domain/LevelData.swift`
- `Infrastructure/LevelRepository.swift`

**Implementation steps:**

1. Define the JSON level structure.
2. Make `LevelData`, `RouteNode`, and `RouteEdge` decodable.
3. Add a sample JSON level.
4. Add parser logic to decode JSON into `LevelData`.
5. Add validation for required fields.

**Acceptance criteria:**

- A JSON level can be decoded into `LevelData`.
- Missing required fields produce readable errors.
- The sample level loads successfully.

**Testing notes:**

- Decode valid JSON.
- Try malformed JSON.
- Try JSON with missing nodes or edges.

**Do not do / out of scope:**

- Do not render the level yet.
- Do not create multiple levels yet.

---

## STORY-005 — Add Level Repository

**Goal:**  
Create a repository that loads levels from bundled JSON files.

**Files likely involved:**

- `Infrastructure/LevelRepository.swift`
- `Resources/Levels/*.json`

**Implementation steps:**

1. Create `LevelRepository`.
2. Add `loadLevel(id:)`.
3. Add `loadAllLevels()`.
4. Load JSON from the app bundle.
5. Return controlled errors for missing or invalid levels.

**Acceptance criteria:**

- Repository loads a level by ID.
- Repository can load all bundled levels.
- Invalid level IDs do not crash the app.

**Testing notes:**

- Load `level_001`.
- Request a nonexistent level.
- Confirm error handling works.

**Do not do / out of scope:**

- Do not fetch levels from a server.
- Do not build level select UI yet.

---

## STORY-006 — Add Sample Level 001

**Goal:**  
Create the first playable sample level.

**Files likely involved:**

- `Resources/Levels/level_001.json`

**Implementation steps:**

1. Create a small graph with a start node, switch node, package node, and destination node.
2. Add at least one wrong path.
3. Define coordinates for each node.
4. Define edges between nodes.
5. Set time limit and par taps.

**Acceptance criteria:**

- `level_001.json` exists.
- Level contains start, package, destination, switch, and edges.
- Level can be decoded through `LevelRepository`.
- Level is solvable.

**Testing notes:**

- Load the level from JSON.
- Verify all node IDs are valid.
- Verify all edge references exist.

**Do not do / out of scope:**

- Do not create all 30 levels.
- Do not add advanced mechanics.

---

## STORY-007 — Build RouteGraph From LevelData

**Goal:**  
Convert static level data into a runtime graph.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Domain/RouteGraph.swift`
- `Domain/LevelData.swift`

**Implementation steps:**

1. Create `RouteEngine`.
2. Add a method to build a runtime graph from `LevelData`.
3. Convert nodes into runtime nodes.
4. Convert edges into runtime edges.
5. Initialize switch directions.
6. Store the runtime graph in the engine.

**Acceptance criteria:**

- Runtime graph is created from `LevelData`.
- All nodes and edges are present.
- Switches initialize with their default direction.
- Invalid graph data fails safely.

**Testing notes:**

- Load `level_001`.
- Build the runtime graph.
- Confirm node and edge counts.

**Do not do / out of scope:**

- Do not move the dot yet.
- Do not render the graph yet.

---

## STORY-008 — Render Static Route Board

**Goal:**  
Display the level graph visually without movement or interactivity.

**Files likely involved:**

- `UI/GameplayScreen.swift`
- `Gameplay/RouteEngine.swift`

**Implementation steps:**

1. Create a gameplay screen.
2. Draw route edges as rounded lines.
3. Draw nodes as circles.
4. Show package and destination differently.
5. Center the board on screen.
6. Scale board to fit different iPhone sizes.

**Acceptance criteria:**

- Level graph appears on screen.
- Nodes and edges are readable.
- Package and destination are visually distinct.
- Board fits on small and large iPhones.

**Testing notes:**

- Test on iPhone SE simulator.
- Test on larger iPhone simulator.
- Verify safe-area spacing.

**Do not do / out of scope:**

- Do not add dot movement.
- Do not add switch tapping.

---

## STORY-009 — Add Delivery Dot Model

**Goal:**  
Create the runtime model for the moving delivery dot.

**Files likely involved:**

- `Gameplay/DeliveryDot.swift`
- `Gameplay/RouteEngine.swift`

**Implementation steps:**

1. Create `DeliveryDot`.
2. Track current node ID.
3. Track current edge ID.
4. Track progress along edge.
5. Track whether the package has been collected.
6. Initialize the dot at the level start node.

**Acceptance criteria:**

- Dot state exists in the route engine.
- Dot initializes at the start node.
- Dot tracks package state.
- Dot can expose its current runtime position.

**Testing notes:**

- Start `level_001`.
- Confirm dot starts at the correct node.

**Do not do / out of scope:**

- Do not render movement yet.
- Do not add collision or completion logic.

---

## STORY-010 — Move Dot Along One Edge

**Goal:**  
Move the delivery dot smoothly from one node to another.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Gameplay/DeliveryDot.swift`
- `UI/GameplayScreen.swift`

**Implementation steps:**

1. Add edge movement state.
2. Start movement from the start node to a target node.
3. Interpolate the dot position along the edge.
4. Advance movement using delta time.
5. Snap the dot to the target node when complete.
6. Render the dot as a simple circle.

**Acceptance criteria:**

- Dot moves smoothly along one edge.
- Movement is frame-rate independent.
- Dot snaps cleanly to the target node.
- Dot does not overshoot.

**Testing notes:**

- Run the level and watch dot movement.
- Test different movement speeds.

**Do not do / out of scope:**

- Do not traverse multiple nodes yet.
- Do not support switch decisions yet.

---

## STORY-011 — Move Dot Through Connected Nodes

**Goal:**  
Allow the dot to automatically continue through connected nodes.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Gameplay/DeliveryDot.swift`
- `UI/GameplayScreen.swift`

**Implementation steps:**

1. Detect when the dot arrives at a node.
2. Find the next outgoing edge.
3. Start movement along the next edge.
4. Continue until no edge is available.
5. Stop movement at dead ends.

**Acceptance criteria:**

- Dot can move through multiple connected nodes.
- Dot follows default switch directions.
- Dot stops at a dead end.
- Movement remains smooth.

**Testing notes:**

- Use `level_001`.
- Confirm dot can travel through several nodes.
- Confirm dead-end behavior does not crash.

**Do not do / out of scope:**

- Do not add player switch tapping yet.
- Do not show failure UI yet.

---

## STORY-012 — Add Switch Node Rotation

**Goal:**  
Allow players to tap switch nodes and rotate their active direction.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `UI/GameplayScreen.swift`
- `UI/SwitchNodeView.swift`

**Implementation steps:**

1. Detect taps on switch nodes.
2. Cycle the switch to the next valid outgoing edge.
3. Update the runtime switch state.
4. Update the visible arrow direction.
5. Increment tap count.

**Acceptance criteria:**

- Tapping a switch rotates its direction.
- Direction cycles through valid exits.
- Arrow display updates immediately.
- Tap count increments.
- Non-switch nodes ignore taps.

**Testing notes:**

- Tap a switch repeatedly.
- Confirm it cycles through all valid exits.
- Confirm tap count increments.

**Do not do / out of scope:**

- Do not add hints.
- Do not add scoring yet.

---

## STORY-013 — Route Dot Based On Active Switch Direction

**Goal:**  
Make the delivery dot follow the current active switch direction.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Gameplay/DeliveryDot.swift`
- `UI/GameplayScreen.swift`

**Implementation steps:**

1. When the dot reaches a switch node, read its active direction.
2. Select the matching outgoing edge.
3. Move the dot along that edge.
4. Allow the player to rotate switches before the dot arrives.
5. Keep behavior consistent if a switch is tapped exactly as the dot arrives.

**Acceptance criteria:**

- Dot follows the active switch direction.
- Switch changes affect the next visit to that node.
- Dot does not change course mid-edge.
- Wrong switch states can send the dot to the wrong path.

**Testing notes:**

- Tap switches before the dot arrives.
- Confirm the dot follows the selected route.
- Test timing near node arrival.

**Do not do / out of scope:**

- Do not add package logic yet.
- Do not add destination completion yet.

---

## STORY-014 — Add Package Pickup State

**Goal:**  
Let the delivery dot collect the package when it reaches the package node.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Gameplay/DeliveryDot.swift`
- `UI/GameplayScreen.swift`

**Implementation steps:**

1. Mark the package node in runtime state.
2. Detect when the dot reaches the package node.
3. Set `hasPackage` to true.
4. Mark the package as collected.
5. Hide or change the package icon.
6. Prevent duplicate package collection.

**Acceptance criteria:**

- Dot collects the package once.
- Package visual updates after pickup.
- `hasPackage` becomes true.
- Returning to the package node does not recollect it.

**Testing notes:**

- Guide dot to the package.
- Confirm pickup event only fires once.

**Do not do / out of scope:**

- Do not complete the level yet.
- Do not add rewards.

---

## STORY-015 — Add Destination Completion State

**Goal:**  
Complete the level when the dot reaches the destination with the package.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `Gameplay/DeliveryDot.swift`
- `UI/ResultScreen.swift`

**Implementation steps:**

1. Mark destination node in runtime state.
2. Detect when the dot reaches the destination.
3. Check whether `hasPackage` is true.
4. If true, transition to level complete.
5. If false, transition to failure.
6. Show a basic result screen.

**Acceptance criteria:**

- Level completes only with the package.
- Reaching destination without package fails.
- Gameplay stops after completion or failure.
- Result screen appears.

**Testing notes:**

- Complete the level correctly.
- Try reaching the destination without package.
- Confirm different outcomes.

**Do not do / out of scope:**

- Do not add final scoring yet.
- Do not add coins yet.

---

## STORY-016 — Add Failure State

**Goal:**  
Implement core fail conditions.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `UI/ResultScreen.swift`
- `UI/GameplayScreen.swift`

**Implementation steps:**

1. Define failure reasons.
2. Detect dead ends.
3. Detect time expiry.
4. Detect invalid destination arrival.
5. Pause gameplay on failure.
6. Show failure result screen.
7. Allow restart.

**Acceptance criteria:**

- Failure state triggers correctly.
- Failure reason is shown.
- Gameplay stops after failure.
- Restart is available.

**Testing notes:**

- Force a dead end.
- Force a timeout.
- Force wrong destination arrival.

**Do not do / out of scope:**

- Do not add rewinds.
- Do not add rewarded ads.

---

## STORY-017 — Add Instant Restart

**Goal:**  
Let players restart the current level immediately.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `UI/GameplayScreen.swift`
- `UI/ResultScreen.swift`

**Implementation steps:**

1. Add restart button to gameplay HUD.
2. Add restart button to result screen.
3. Implement `restartLevel()`.
4. Reset dot position.
5. Reset package state.
6. Reset switch directions.
7. Reset timer and tap count.

**Acceptance criteria:**

- Restart works from gameplay.
- Restart works from failure screen.
- Restart resets all level state.
- Restart does not return to level select.

**Testing notes:**

- Restart during movement.
- Restart after package pickup.
- Restart after failure.

**Do not do / out of scope:**

- Do not add confirmation dialog.
- Do not add ads.

---

## STORY-018 — Add Timer

**Goal:**  
Track and display level time.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `UI/GameplayScreen.swift`
- `UI/ResultScreen.swift`

**Implementation steps:**

1. Add timer state.
2. Initialize timer from level data.
3. Update timer each frame.
4. Display timer in HUD.
5. Trigger failure when time expires.
6. Show final time on result screen.

**Acceptance criteria:**

- Timer appears in gameplay.
- Timer counts accurately.
- Timer triggers failure at zero.
- Final time appears on result screen.

**Testing notes:**

- Test with a short time limit.
- Pause/resume behavior should not corrupt timer.

**Do not do / out of scope:**

- Do not add time bonuses.
- Do not tune scoring yet.

---

## STORY-019 — Add Tap Counter

**Goal:**  
Track switch taps during a level.

**Files likely involved:**

- `Gameplay/RouteEngine.swift`
- `UI/GameplayScreen.swift`
- `UI/ResultScreen.swift`

**Implementation steps:**

1. Add `tapCount` state.
2. Increment when a switch rotates.
3. Display tap count in HUD.
4. Show final tap count on result screen.
5. Reset tap count on restart.

**Acceptance criteria:**

- Tap count starts at zero.
- Switch rotations increment tap count.
- Tap count is visible.
- Tap count resets correctly.

**Testing notes:**

- Rotate switches repeatedly.
- Restart level.
- Confirm reset.

**Do not do / out of scope:**

- Do not count pause/restart/menu taps.
- Do not calculate stars yet.

---

## STORY-020 — Add Star Scoring

**Goal:**  
Award stars based on completion, time, and tap count.

**Files likely involved:**

- `Services/ScoringService.swift`
- `Gameplay/RouteEngine.swift`
- `UI/ResultScreen.swift`

**Implementation steps:**

1. Create `ScoringService`.
2. Add star calculation rules.
3. Award 1 star for completion.
4. Award 2 stars if under time limit.
5. Award 3 stars if under time limit and under par taps.
6. Save best star rating per level.
7. Display stars on result screen.

**Acceptance criteria:**

- Completing a level gives at least 1 star.
- Time goal gives 2 stars.
- Time plus par tap goal gives 3 stars.
- Best score persists.

**Testing notes:**

- Test 1-star, 2-star, and 3-star completions.
- Replay level and improve score.
- Confirm best score updates only upward.

**Do not do / out of scope:**

- Do not add coins yet.
- Do not add perfect route badges.

---

## STORY-021 — Add Result Screen

**Goal:**  
Create a clear result screen for success and failure.

**Files likely involved:**

- `UI/ResultScreen.swift`
- `UI/GameplayScreen.swift`
- `Services/ScoringService.swift`

**Implementation steps:**

1. Create result screen layout.
2. Show success or failure title.
3. Show stars if completed.
4. Show time.
5. Show tap count.
6. Add restart button.
7. Add next level button for success.
8. Add main menu button.
9. Save improved star score.

**Acceptance criteria:**

- Result screen appears after success.
- Result screen appears after failure.
- Success result shows stars, time, and taps.
- Failure result shows reason and restart.
- Buttons navigate correctly.

**Testing notes:**

- Complete a level.
- Fail a level.
- Use restart.
- Use next level.
- Return to main menu.

**Do not do / out of scope:**

- Do not add ads.
- Do not add coins.
- Do not add daily challenge data.

---

# Next Recommended Stories After STORY-021

After the first playable loop works, continue with the remaining phase-aligned backlog:

## Remaining P1 MVP Stories

## STORY-022 — Add Player Save Profile

Persist progress, stars, coins, cosmetics, settings, and ad-removal state.

## STORY-023 — Add Level Unlocking

Unlock levels sequentially while keeping completed levels replayable.

## STORY-024 — Add Home Screen

Create the main landing screen with Play, Daily Route, Shop, Settings, coins, and streak preview.

## STORY-025 — Add Level Select Screen

Display available levels, locks, and earned stars.

## STORY-026 — Add Coin Wallet

Create a soft-currency wallet that tracks earned and spent coins.

## STORY-027 — Add Reward Rules and Coin Rewards

Centralize reward logic and award coins from stars, level completion, and future systems.

## STORY-028 — Add Basic Cosmetic Inventory

Track owned and equipped cosmetics.

## STORY-029 — Add Route Themes

Ship the first 4 MVP route themes.

## STORY-030 — Add Trail Effects

Ship the first 6 MVP trail options.

## STORY-031 — Add Rewarded Ad Adapter

Abstract rewarded ads behind a game-facing service.

## STORY-032 — Add Rewarded Rewind Placement

Offer rewind after failure through the rewarded ad adapter.

## STORY-033 — Add Double Coins Placement

Offer a rewarded double-coins flow on successful level completion.

## STORY-034 — Add Remove Ads Purchase

Add the MVP remove-ads purchase and persist its unlock state.

## STORY-035 — Add Analytics Adapter

Create a centralized analytics wrapper for future SDK integration.

## STORY-036 — Add Level and Monetization Events

Track level starts, completions, failures, restarts, rewarded ads, and purchases.

## STORY-037 — Add First-Time Tutorial Flow

Use the first few levels to teach destination, switch tapping, failure, and package pickup.

## STORY-038 — Add Objective Labels and Hand Pointer

Add lightweight onboarding helpers without blocking gameplay.

## STORY-039 — Add Settings Screen

Add sound, music, haptics, restore purchases, privacy, terms, and credits.

## STORY-040 — Add Haptics

Add subtle feedback for taps, pickup, failure, completion, and rewards.

## STORY-041 — Build First 30 MVP Levels

Create the first 30 handcrafted levels with a smooth tutorial-to-MVP difficulty curve.

## P2 Launch and Later Stories

## STORY-042 — Add Daily Route Selector

Rotate one curated daily challenge without requiring a server.

## STORY-043 — Add Daily Result and Streak System

Track daily completion, streak growth, and daily rewards.

## STORY-044 — Add Hint System

Support hints as a convenience system tied to coins or rewarded ads.

## STORY-045 — Add Cosmetic Shop

Let players preview, buy, and equip cosmetics with coins.

## STORY-046 — Add World Structure and Milestone Rewards

Group levels into worlds and reward long-term progression.

## STORY-047 — Add Accessibility, Compliance, and Polish Pass

Finish accessibility basics, privacy/tracking compliance, audio, animation, and launch polish.

---

# First Engineering Milestone

The first major milestone is complete when:

> One JSON level loads, renders, the dot moves, switches rotate, the package is collected, the destination completes the level, and a result screen appears.
