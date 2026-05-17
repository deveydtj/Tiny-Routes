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

**Sub-tasks (entry-level checklist):**

- [x] Open each target domain file and replace the placeholder comments with simple struct definitions that only use Swift/Foundation types.
- [x] Add `Codable` conformance to `LevelData`, `RouteNode`, and `RouteEdge` so these models can be read from JSON in a later story.
- [x] Add stable identity fields (`id`) to nodes and edges, and basic coordinate / connection fields needed to describe a route board.
- [x] Add `RouteGraph` fields for node and edge collections (dictionary or array-based), with no pathfinding logic yet.
- [x] Add a minimal initializer or helper on `RouteGraph` that can build an instance from node + edge collections for test setup.
- [x] Add `PlayerProfile` with beginner-safe progress properties (e.g., unlocked levels, best stars, coin total) using default values.
- [x] Add `CosmeticItem` with lightweight metadata fields (id, type, unlock status) only; no storefront logic.
- [x] Add doc comments above each model describing its purpose in one sentence.
- [x] Confirm there are no imports of UIKit, SwiftUI, or SpriteKit in these domain files.
- [x] Run the project tests/build and fix any compile issues caused by renamed or newly required fields.
- [x] Add/adjust unit tests that instantiate each model and verify basic graph wiring assumptions (node IDs referenced by edges exist).
- [x] Self-review the diff for scope: models only, no gameplay movement, rendering, or persistence behavior.

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

**Status:** ✅ Completed — replaced STORY-003 domain placeholders with Foundation-only model definitions for level, node, edge, graph, player profile, and cosmetic metadata, including Codable support for level loading models and graph construction helpers. Added focused unit tests that instantiate the models and verify graph edge references point to existing node IDs.

## STORY-004 — Add Level JSON Schema ✅ COMPLETED

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

**Status:** ✅ Completed — created `Resources/Levels/level_001.json` with the canonical level JSON schema, implemented `LevelRepository` with `loadLevel(id:)` that decodes bundled JSON into `LevelData` and surfaces readable `LevelRepositoryError` values for missing files or decoding failures. Added `LevelRepositoryTests` covering valid decoding, malformed JSON, missing required fields, and the file-not-found error path.

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

**Status:** ✅ Completed — added `loadAllLevels()` to `LevelRepository` that enumerates all bundled JSON files in `Resources/Levels/`, loads and decodes each, and surfaces `LevelRepositoryError.readFailed` or `.decodingFailed` on the first failure. Added an `allLevelURLs` injectable closure to the testing init to keep the new method fully unit-testable. Added four new tests covering the empty case, successful multi-level load, read I/O failure, and malformed-JSON failure.

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

**Status:** ✅ Completed — redesigned `Resources/Levels/level_001.json` into a playable starter route with explicit start/switch/package/destination nodes, a dead-end wrong path, connected edge topology, tuned timer budget, and `parTaps` metadata. Added tests that validate node/edge reference integrity, switch branching, wrong-path dead-end behavior, graph reachability from start→package→destination, and repository decoding against the bundled sample level.

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

**Status:** ✅ Completed — implemented static route-board rendering in `UI/GameplayScreen.swift` by loading level data, building a runtime graph via `RouteEngine`, drawing rounded route edges and circular nodes, visually distinguishing package and destination nodes, and fitting/centering the board responsively across device sizes.

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

**Status:** ✅ Completed — added `Gameplay/DeliveryDot.swift` with runtime node/edge/progress/package fields and position interpolation support, then integrated delivery-dot initialization into `RouteEngine` so each loaded level starts with the dot at an explicit `startNodeID` and exposes dot state via the engine.

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

**Status:** ✅ Completed — added frame-rate-independent single-edge dot traversal to `RouteEngine`, including start-on-active-edge behavior, interpolation by delta time, overshoot-safe snapping, and zero-length edge handling. `GameplayScreen` now renders the delivery dot as a simple circle and advances it across the board while respecting pause state, with focused tests covering start, interpolation, snap, and leaf-node behavior.

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

**Status:** ✅ Completed — upgraded `RouteEngine` movement updates to automatically continue across connected nodes by following each node’s active outgoing edge, including within a single frame update when enough movement distance remains. Added dead-end stop behavior when no outgoing edge exists, retained overshoot-safe interpolation and snapping, and expanded `RouteEngineTests` to cover multi-node traversal, continuation after node arrival, and dead-end termination.

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

**Status:** ✅ Completed — implemented switch-node tap rotation by adding runtime switch cycling logic (`NodeSwitchController` + `RouteEngine.rotateSwitchNode(nodeID:)`), wired node tap handling into `GameplayScreen`, and added `tapCount` increments only when a switch rotation occurs. Added `SwitchNodeView` so switch arrows visibly update immediately to the active outgoing direction, while non-switch nodes continue to ignore taps. Expanded `RouteEngineTests` with switch-rotation cycle and non-switch/unknown-node tap coverage.

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

**Status:** ✅ Completed — added one-time package pickup state in `RouteEngine` by tracking the level package node and marking `DeliveryDot.hasCollectedPackage` when the dot reaches that node (including start-on-package levels). Updated `GameplayScreen` rendering so the package node visual changes after pickup. Expanded `RouteEngineTests` with focused coverage for package pickup on arrival, persistence on revisits, and start-node package collection.

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

**Status:** ✅ Completed — implemented destination-based level resolution in the gameplay loop: reaching destination with package transitions to success, while reaching destination without package fails. Gameplay halts on terminal state and routes into the result flow.

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

**Status:** ✅ Completed — added core failure-state handling with explicit fail outcomes (including dead-end and invalid completion paths), terminal-state gameplay stop behavior, failure reason propagation, and failure result-screen integration.

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

**Status:** ✅ Completed — added restart actions from gameplay and result flows, wired through app navigation, with full in-level state reset behavior (dot progression, package/switch state, timer, and taps) so retries start cleanly without returning to level select.

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

**Status:** ✅ Completed — implemented level timer state in the gameplay loop and HUD presentation, including countdown progression, timeout-triggered failure integration, and final-time handoff to results for completed/failed runs.

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

**Status:** ✅ Completed — implemented switch-rotation tap tracking with HUD and result-screen reporting, ensuring tap count starts at zero, increments only on switch rotations, and resets correctly on restart/new attempt.

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

**Status:** ✅ Completed — implemented `ScoringService` star rules for 1/2/3-star outcomes based on completion, time limit, and par taps; implemented `ProgressService` persistence for best stars per level with upward-only updates; and updated `ResultScreen` to calculate/display awarded stars and persisted best stars on level completion. Added unit tests covering star thresholds and best-star persistence behavior.

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

**Status:** ✅ Completed — added a unified result screen flow for both success and failure states; success now displays stars, final time, taps, restart, next level, and menu actions; failure displays reason, restart, and menu actions; result actions are wired through app navigation.

---

# Next Recommended Stories After STORY-021

After the first playable loop works, continue with the remaining phase-aligned backlog:

## Remaining P1 MVP Stories

## STORY-022 — Add Player Save Profile

**Goal:**  
Persist the player profile locally so progress, economy state, cosmetic state, settings, and monetization flags survive app restarts.

**Files likely involved:**

- `TinyRoutes/Domain/PlayerProfile.swift`
- `TinyRoutes/Infrastructure/SaveDataRepository.swift`
- `TinyRoutes/Services/ProgressService.swift`
- `TinyRoutes/Services/EconomyService.swift`
- `TinyRoutes/Services/CosmeticService.swift`
- `TinyRoutes/App/AppCoordinator.swift`

**Implementation steps:**

1. Define the full save payload shape and make sure it contains version information.
2. Expand `PlayerProfile` so it can represent completed levels, best stars, coin balance, owned/equipped cosmetics, basic settings, streak placeholders, and ad-removal state.
3. Implement save/load behavior in `SaveDataRepository` using a local on-device format that can round-trip the profile cleanly.
4. Create a bootstrap path that loads an existing profile on app start or creates a new default profile when no save exists.
5. Add controlled fallback behavior for corrupt or unreadable save data so the app recovers without crashing.
6. Route profile mutations through the existing game-facing services instead of letting UI screens write save data directly.
7. Make sure save writes happen after meaningful profile changes and not on every frame of gameplay.

**Acceptance criteria:**

- Progress persists after app restart.
- Save data contains a version field suitable for future migrations.
- Missing save data creates a valid default profile automatically.
- Corrupt save data does not crash the app and falls back to a recoverable default path.
- UI and gameplay systems consume profile state through services/repositories instead of directly encoding JSON.

**Testing notes:**

- Save a populated profile, reload it, and confirm all persisted fields survive round-trip.
- Launch with no existing save and confirm a default profile is created.
- Simulate corrupt save payload data and confirm the app handles it safely.
- Verify star progress, coin balance, equipped cosmetics, and settings all persist across relaunch.

**Do not do / out of scope:**

- Do not add cloud sync or account login.
- Do not add world progression yet.
- Do not add purchase restoration flows beyond persisting the local flag.
- Do not add analytics migration events yet.

---

## STORY-023 — Add Level Unlocking

**Goal:**  
Unlock campaign levels sequentially while keeping previously completed levels replayable and clearly separating locked vs. playable content.

**Files likely involved:**

- `TinyRoutes/Services/ProgressService.swift`
- `TinyRoutes/Domain/PlayerProfile.swift`
- `TinyRoutes/UI/LevelSelectScreen.swift`
- `TinyRoutes/UI/ResultScreen.swift`
- `TinyRoutes/UI/HomeScreen.swift`
- `TinyRoutes/App/AppCoordinator.swift`

**Implementation steps:**

1. Define the unlocking rule for MVP campaign progression, including what counts as "completed" for unlocking the next level.
2. Add progress-service APIs that answer whether a level is locked, unlocked, completed, or replayable.
3. Update level-completion flow so finishing a level unlocks the next sequential level exactly once.
4. Ensure replaying an already completed level does not regress unlock progress.
5. Prevent locked levels from being launched through normal navigation.
6. Update home/level-select/result flows so the next recommended level is based on current unlock state.
7. Add a debug-only override path so locks can be bypassed for testing without exposing that control in the normal player flow.

**Acceptance criteria:**

- Completing a level unlocks the next level in sequence.
- Completed levels remain replayable.
- Locked levels are visibly locked and cannot be started through standard UI.
- Debug mode can override locks for testing.
- "Next level" navigation respects unlock state.
- Unlock data persists through the player save profile.

**Testing notes:**

- Complete the first playable level and confirm the next becomes available.
- Replay a completed level and confirm unlock progress is unchanged.
- Attempt to launch a locked level from level select and confirm it is blocked.
- Enable debug mode and confirm a locked level can be launched through the override path without changing production UI behavior.
- Relaunch the app and confirm unlocked state persists.

**Do not do / out of scope:**

- Do not add world-based unlock rules yet.
- Do not add coin-based unlock skips.
- Do not add difficulty recommendations or progression maps.
- Do not expose the debug unlock override in production UI.

---

## STORY-024 — Add Home Screen

**Goal:**  
Create the primary landing screen that gives the player a fast path into the next playable level and previews the main MVP navigation destinations.

**Files likely involved:**

- `TinyRoutes/UI/HomeScreen.swift`
- `TinyRoutes/App/ContentView.swift`
- `TinyRoutes/App/AppCoordinator.swift`
- `TinyRoutes/Services/ProgressService.swift`
- `TinyRoutes/Services/EconomyService.swift`
- `TinyRoutes/Services/StreakService.swift`
- `TinyRoutes/Services/DailyChallengeService.swift`

**Implementation steps:**

1. Replace the placeholder home screen with an MVP landing layout aligned to the product plan.
2. Add primary actions for Play, Daily Route, Shop, and Settings.
3. Show the current coin balance and a lightweight streak preview using available service data or placeholders when features are not yet implemented.
4. Surface the player's next recommended campaign level so gameplay can start quickly.
5. Add a simple route-preview graphic or board card that reinforces the game identity without embedding live gameplay logic in the home screen.
6. Wire all home-screen actions through `AppCoordinator`.
7. Make the layout resilient to partially implemented systems so missing daily/shop details do not break the screen.

**Acceptance criteria:**

- Player can start the next playable level quickly from home.
- Daily Route, Shop, and Settings entry points are visible.
- Coin balance is visible from the home screen.
- Streak preview area exists even if backed by placeholder data.
- Navigation from home feels simple and does not embed gameplay state management.

**Testing notes:**

- Launch the app and confirm home becomes the primary landing screen.
- Tap Play and confirm it opens the correct next campaign level.
- Tap Daily Route, Shop, and Settings and confirm routing works or reaches the intended placeholder destination.
- Verify the home screen still renders when streak/daily data is empty.

**Do not do / out of scope:**

- Do not build the final polished live preview or animated board.
- Do not add rewarded-ad placements on home.
- Do not add profile/social features.
- Do not implement the full daily challenge system yet.

---

## STORY-025 — Add Level Select Screen

**Goal:**  
Create a level select screen that shows campaign progression clearly, including unlocked levels, locked levels, and earned stars.

**Files likely involved:**

- `TinyRoutes/UI/LevelSelectScreen.swift`
- `TinyRoutes/App/AppCoordinator.swift`
- `TinyRoutes/Services/ProgressService.swift`
- `TinyRoutes/Infrastructure/LevelRepository.swift`
- `TinyRoutes/Domain/LevelData.swift`

**Implementation steps:**

1. Define the list/grid presentation for campaign levels using available level metadata.
2. Load enough level metadata to show level number, lock state, and earned stars without starting gameplay.
3. Display unlocked, completed, current, and locked states distinctly.
4. Allow completed levels to be replayed and unlocked levels to be started.
5. Prevent locked levels from entering gameplay.
6. Highlight the next recommended/current level based on progression state.
7. Add navigation back to home and into gameplay without duplicating unlock logic in the UI layer.

**Acceptance criteria:**

- Available levels are displayed.
- Locked levels are shown as locked.
- Completed levels show earned stars.
- The current recommended level is highlighted.
- Player can replay completed levels.

**Testing notes:**

- Open level select with a fresh profile and confirm only the expected starting levels are playable.
- Complete levels and confirm stars and unlock state appear correctly.
- Launch a replay from a completed level and confirm gameplay starts normally.
- Attempt to select a locked level and confirm it does not start.

**Do not do / out of scope:**

- Do not add world grouping yet.
- Do not add milestone reward UI.
- Do not add filtering, sorting, or search.
- Do not turn this into a map-navigation screen yet.

---

## STORY-026 — Add Coin Wallet

**Goal:**  
Create the MVP soft-currency wallet so the game can safely track earned and spent coins through a central service.

**Files likely involved:**

- `TinyRoutes/Services/EconomyService.swift`
- `TinyRoutes/Domain/PlayerProfile.swift`
- `TinyRoutes/Infrastructure/SaveDataRepository.swift`
- `TinyRoutes/UI/HomeScreen.swift`
- `TinyRoutes/UI/ResultScreen.swift`
- `TinyRoutes/UI/ShopScreen.swift`

**Implementation steps:**

1. Define the wallet API for reading balance, earning coins, and spending coins.
2. Store the authoritative coin balance in the player profile.
3. Enforce non-negative balance rules in the economy layer so UI cannot overspend.
4. Persist wallet changes through the save profile flow.
5. Expose balance updates to screens that need to display currency.
6. Return clear success/failure results for spend attempts so future shop flows can react predictably.
7. Keep reward-calculation policy separate so this story only owns wallet state and transactions.

**Acceptance criteria:**

- Coins can be earned through the wallet API.
- Coins can be spent through the wallet API.
- Coin balance persists through app restart.
- Negative balances are impossible.
- Balance reads come from a centralized economy path, not duplicated UI state.

**Testing notes:**

- Award coins and confirm the balance increases correctly.
- Spend coins within the available balance and confirm the balance decreases correctly.
- Attempt to overspend and confirm the operation fails without producing a negative balance.
- Relaunch the app and confirm the coin balance persists.

**Do not do / out of scope:**

- Do not add reward formulas yet.
- Do not add double-coins rewards yet.
- Do not add real-money currency packs.
- Do not implement the cosmetic shop purchase flow yet.

---

## STORY-027 — Add Reward Rules and Coin Rewards

**Goal:**  
Centralize reward logic so coin payouts are determined consistently from level outcomes and are ready to expand to future reward sources.

**Files likely involved:**

- `TinyRoutes/Services/EconomyService.swift`
- `TinyRoutes/Services/ScoringService.swift`
- `TinyRoutes/Services/ProgressService.swift`
- `TinyRoutes/UI/ResultScreen.swift`
- `TinyRoutes/Infrastructure/AnalyticsAdapter.swift`

**Implementation steps:**

1. Define the MVP reward rule set for campaign completion and star-based coin payouts.
2. Keep reward values configurable in one place so balance tuning does not require UI edits.
3. Add a game-facing reward calculation path that consumes completion context and returns a reward breakdown.
4. Wire successful level completion to award coins through the centralized reward path and wallet service.
5. Define replay behavior so repeat clears do not produce unintended economy exploits.
6. Surface the awarded coin result on the result screen.
7. Log reward grants through `AnalyticsAdapter` so awarded rewards are available for analytics reporting.
8. Leave extension points for future reward sources such as dailies, streaks, rewarded ads, and bonus chests.

**Acceptance criteria:**

- Coins are awarded after eligible level completion.
- Reward amount is based on the centralized rules rather than UI-specific logic.
- Reward rules can be tuned from a single configuration point.
- Coin awards are persisted through the wallet/profile flow.
- Replay rewards follow a defined and testable MVP rule.
- Reward grants are logged for analytics from the centralized reward path.

**Testing notes:**

- Complete levels with different star outcomes and confirm the expected coin awards are granted.
- Replay a completed level and confirm reward behavior matches the chosen economy rule.
- Verify the result screen displays the awarded coins from the centralized reward result.
- Confirm no reward is granted on failed runs unless explicitly configured.
- Confirm eligible reward grants emit the expected analytics event payload once per award.

**Do not do / out of scope:**

- Do not add rewarded ad multipliers yet.
- Do not add daily challenge rewards yet.
- Do not add bonus chests or milestone rewards yet.
- Do not add live economy tuning infrastructure yet.

---

## STORY-028 — Add Basic Cosmetic Inventory

**Goal:**  
Track owned and equipped cosmetics so the MVP can support default cosmetic availability plus future unlock/equip flows.

**Files likely involved:**

- `TinyRoutes/Domain/CosmeticItem.swift`
- `TinyRoutes/Domain/PlayerProfile.swift`
- `TinyRoutes/Services/CosmeticService.swift`
- `TinyRoutes/Infrastructure/SaveDataRepository.swift`
- `TinyRoutes/UI/ShopScreen.swift`

**Implementation steps:**

1. Finalize the cosmetic model fields needed for inventory management, including category, rarity, unlock state, and price metadata.
2. Seed the default always-available cosmetics required for MVP gameplay visuals.
3. Add service APIs to list owned items, list equippable items by category, unlock items, and equip items.
4. Enforce that only owned items can be equipped, while default items remain permanently available.
5. Persist owned/equipped cosmetic state through the save profile flow.
6. Expose inventory state in a UI-friendly form for future shop/equip screens, even if the first UI is minimal.
7. Keep purchase and reward acquisition logic outside this story so inventory remains the single ownership/equip source of truth.

**Acceptance criteria:**

- Cosmetics have stable metadata fields needed for MVP inventory behavior.
- Default cosmetics are always available.
- Owned cosmetics persist.
- Equipped cosmetics persist.
- Invalid equip attempts are rejected cleanly.

**Testing notes:**

- Load a fresh profile and confirm default cosmetics are available.
- Unlock a cosmetic and confirm it becomes owned.
- Equip an owned cosmetic and confirm the equipped state persists after reload.
- Attempt to equip an unowned cosmetic and confirm the service rejects it.

**Do not do / out of scope:**

- Do not build the full cosmetic shop yet.
- Do not add real-money cosmetic bundles.
- Do not add random cosmetic chest rewards yet.
- Do not implement every cosmetic category's final UI in this story.

---

## STORY-029 — Add Route Themes

**Goal:**  
Ship the first four MVP route themes and apply them to gameplay visuals without affecting gameplay behavior.

**Files likely involved:**

- `TinyRoutes/Services/CosmeticService.swift`
- `TinyRoutes/Domain/CosmeticItem.swift`
- `TinyRoutes/UI/GameplayScreen.swift`
- `TinyRoutes/UI/HomeScreen.swift`
- `TinyRoutes/UI/LevelSelectScreen.swift`

**Implementation steps:**

1. Define the first four theme variants: Classic, Ocean Drive, Sunset, and Neon.
2. Create a theme representation that captures route-line colors, node colors, destination/package accents, and background accents.
3. Connect the equipped theme state from the cosmetic system to the gameplay renderer.
4. Apply theme styling consistently to gameplay and any lightweight route previews used in navigation screens.
5. Ensure theme changes are purely visual and do not modify hit areas, routing rules, or gameplay readability.
6. Provide a preview-friendly way for future inventory/shop UI to render the theme options.
7. Verify default fallback styling exists when equipped-theme data is missing.

**Acceptance criteria:**

- Four MVP route themes exist.
- Theme selection changes route line colors, node colors, and background accents.
- Equipped theme is reflected in gameplay visuals.
- Theme changes do not alter gameplay behavior.
- Theme options can be previewed from inventory-facing UI.

**Testing notes:**

- Equip each theme and confirm gameplay visuals update correctly.
- Verify package, destination, switch arrows, and delivery dot remain readable across all themes.
- Confirm a missing or invalid equipped-theme value falls back safely to the default theme.
- Check lightweight preview surfaces for visual consistency with gameplay.

**Do not do / out of scope:**

- Do not add paid/premium theme bundles yet.
- Do not add world-specific theming rules yet.
- Do not add animated backgrounds.
- Do not change level difficulty or layout per theme.

---

## STORY-030 — Add Trail Effects

**Goal:**  
Add the first six MVP delivery-dot trail effects so equipped cosmetics visibly change movement presentation during gameplay.

**Files likely involved:**

- `TinyRoutes/UI/GameplayScreen.swift`
- `TinyRoutes/Gameplay/DeliveryDot.swift`
- `TinyRoutes/Services/CosmeticService.swift`
- `TinyRoutes/Domain/CosmeticItem.swift`

**Implementation steps:**

1. Define the first six trail options: Dots, Sparkles, Glow, Bubbles, Stars, and Leaves.
2. Choose a lightweight rendering approach that can follow the moving delivery dot without introducing heavy performance cost.
3. Bind the equipped trail selection from the cosmetic system to gameplay rendering.
4. Render trail output behind or around the delivery dot while preserving route readability.
5. Add safe fallback behavior for missing trail data so the default trail always works.
6. Ensure trail state resets cleanly on restart, success, failure, and level changes.
7. Keep the trail system extensible so more effects can be added later without rewriting gameplay movement.

**Acceptance criteria:**

- Six MVP trail options exist.
- Trail follows the moving delivery dot.
- Equipped trail is reflected during gameplay.
- Trail can be changed from cosmetic inventory/shop-facing state.
- Trail implementation does not introduce obvious performance issues on the MVP board.

**Testing notes:**

- Equip each trail and confirm it appears while the dot moves.
- Restart/fail/complete a level and confirm the trail resets cleanly.
- Verify trails do not obscure switches, package state, or destination readability.
- Confirm default trail behavior works when no custom trail is equipped.

**Do not do / out of scope:**

- Do not add heavy particle systems that require complex tuning.
- Do not add audio or haptic behavior tied to trails.
- Do not add premium-only trail unlock rules yet.
- Do not add trail-specific monetization or reward placements yet.

---

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
