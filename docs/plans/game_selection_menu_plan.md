# Tiny Routes - Game Selection Menu Plan

## Purpose

Develop the player-facing game selection menu from the concept art.

The screen should present levels as a soft map path with large rounded level boxes connected by dashed route segments. The green, blue, and grey background boxes from the concept art should be replicated in code instead of exported as static tile images.

The first implementation should replace the current simple level list in `TinyRoutes/UI/LevelSelectScreen.swift` with a polished SwiftUI level map that can scale as more levels are added.

## Visual Target

The concept art has three important tile states:

| State | Meaning | Visual Treatment |
|---|---|---|
| Green | Completed level | Teal-green gradient box, white number, three yellow stars, white circular check badge |
| Blue | Current playable level | Bright blue gradient box, white number, earned stars, raised selection outline, optional map pin |
| Grey | Locked level | Pale grey/white box, blue-grey number, lock icon, muted connector |

The route background should feel like a map:

```text
Soft pale blue base
Very subtle street/map shapes
Green connector for completed path
Grey connector for locked path
Rounded route turns between rows
```

The route artwork should be generated with SwiftUI shapes first. Use image assets only for optional decorative map texture if the code-generated background is not rich enough.

## Level Order Pattern

Levels should render in a repeating serpentine pattern.

The first two rows are:

```text
1 ---- 2 ---- 3 ---- 4
8 ---- 7 ---- 6 ---- 5
```

Then the pattern repeats:

```text
9  ---- 10 ---- 11 ---- 12
16 ---- 15 ---- 14 ---- 13

17 ---- 18 ---- 19 ---- 20
24 ---- 23 ---- 22 ---- 21
```

Rules:

1. Display four levels per row.
2. Odd-numbered visual rows go left to right.
3. Even-numbered visual rows go right to left.
4. The connector should continue from the end of one row into the start of the next row with a curved vertical turn.
5. The data source remains sorted by level number; only the visual placement changes.

## Recommended Direction

Build the level selection menu in SwiftUI.

Recommended target files:

```text
TinyRoutes/UI/LevelSelectScreen.swift
TinyRoutes/UI/Components/TRLevelTile.swift
TinyRoutes/UI/Components/TRLevelPathView.swift
TinyRoutes/UI/Components/TRMapBackgroundView.swift
TinyRoutes/UI/Components/TRLevelSelectHeader.swift
```

Keep the implementation code-generated:

```text
Rounded tile backgrounds: SwiftUI RoundedRectangle layers
Gradients: SwiftUI LinearGradient
Check badge: Circle plus SF Symbol checkmark
Stars: SF Symbol star.fill or existing star asset if one is added
Locks: SF Symbol lock.fill or existing locked_pin.png if preferred
Connectors: custom Shape paths with dashed stroke
Map background: SwiftUI shapes and low-opacity route/street strokes
```

## Screen Layout

Recommended high-level layout:

```text
+------------------------------------------------+
| Back button                         Level title |
+------------------------------------------------+
|                                                |
|   1 ---- 2 ---- 3 ---- 4                      |
|                         )                      |
|   8 ---- 7 ---- 6 ---- 5                      |
|   (                                            |
|   9 ---- 10 --- 11 --- 12                     |
|                                                |
+------------------------------------------------+
```

Use a scroll view because the map will grow beyond a single screen.

```swift
ScrollView(.vertical, showsIndicators: false) {
    ZStack {
        TRMapBackgroundView()
        TRLevelPathView(layout: layout, progress: progress)
        levelTiles(layout: layout)
    }
    .padding(.horizontal, 24)
    .padding(.vertical, 28)
}
```

The first viewport should clearly show the level map, not an explanatory page.

## Tile Component

Create a reusable tile component:

```swift
struct TRLevelTile: View {
    let levelNumber: Int
    let state: TRLevelTileState
    let stars: Int
    let action: () -> Void
}
```

Suggested state enum:

```swift
enum TRLevelTileState {
    case completed
    case current
    case locked
}
```

Tile sizing:

```text
Width: 82 to 96 points depending on device width
Height: 96 to 108 points
Corner radius: 18 to 22
Border: white outer stroke plus subtle grey shadow
Number: large, bold, centered
Stars/lock: fixed bottom row area
Badge: fixed top trailing overlay, outside tile bounds by a few points
```

Do not let the number, stars, lock, or badge change the tile size.

## Tile Rendering Details

Completed tile:

```text
Background: teal-green vertical gradient
Top highlight: white opacity overlay near top
Border: thick white stroke plus soft blue-grey outer edge
Number: white, bold
Bottom: three yellow stars
Badge: green circle with white check, white ring
Shadow: medium soft shadow under tile
```

Current tile:

```text
Background: blue vertical gradient
Outer emphasis: thicker white outline and stronger blue glow
Number: white, bold
Bottom: earned yellow stars plus empty muted stars
Badge: optional blue map pin above tile
Tap target: enabled
```

Locked tile:

```text
Background: pale grey vertical gradient
Border: light grey stroke
Number: blue-grey
Bottom: small lock icon
Stars: hidden
Tap target: disabled or opens locked feedback
Connector after this tile: grey
```

## Connector Rendering

Implement connectors as a dedicated view behind the tiles.

The connector should support:

```text
Horizontal dashed segments between tiles in a row
Curved vertical turns between rows
Completed green stroke up to the current level
Locked grey stroke after the current level
Rounded stroke caps
Dashed center highlight
```

The concept art uses a thick route with small lighter dashes. This can be built with two strokes:

```swift
path.stroke(baseColor, style: StrokeStyle(lineWidth: 16, lineCap: .round, lineJoin: .round))
path.stroke(highlightColor, style: StrokeStyle(lineWidth: 3, lineCap: .round, dash: [8, 12]))
```

Split the path into completed and locked portions if needed. A simpler first version may draw each segment independently and color it based on whether both connected levels are unlocked or completed.

## Progress Rules

Use `ProgressService.bestStars(for:)` as the source of completed stars.

Initial rules:

```text
Level 1 is always unlocked.
A level is completed when bestStars > 0.
The current level is the first level with bestStars == 0 after the completed run.
Levels after the current level are locked.
If every level is completed, the last level can remain current/completed depending on product preference.
```

This keeps the menu deterministic without adding a separate unlock store.

Later, if unlock rules become more complex, add a dedicated progress model:

```text
LevelSelectProgress
LevelSelectTileModel
LevelUnlockPolicy
```

## Layout Algorithm

Create a small pure layout helper so the screen is easy to test.

Inputs:

```text
levels: [LevelData]
columns: 4
tileSize
horizontalSpacing
verticalSpacing
```

Output:

```text
Level number
Level ID
Visual row
Visual column
Center point
Tile state
Stars
```

Placement rule:

```swift
let row = index / 4
let positionInRow = index % 4
let visualColumn = row.isMultiple(of: 2) ? positionInRow : 3 - positionInRow
```

This keeps the data ordered while the rendered path snakes across the screen.

## Interaction

Completed and current tiles should be tappable.

Recommended behavior:

```text
Completed tile: starts that level for replay
Current tile: starts the newest unlocked level
Locked tile: disabled, or gives a small bounce/locked haptic later
Back button: returns to main menu
```

Use `Button` for accessible tap behavior. The tile should have an accessibility label such as:

```text
Level 6, current, 2 of 3 stars
Level 7, locked
Level 3, completed, 3 of 3 stars
```

## Implementation Phases

### Phase 1 - Static Visual System

1. Create `TRLevelTile`.
2. Create green, blue, and grey code-generated tile backgrounds.
3. Render mock states in a SwiftUI preview.
4. Match the concept art's rounded, glossy, soft-shadow style.

### Phase 2 - Serpentine Layout

1. Add a layout helper for four-column serpentine placement.
2. Replace the current vertical list in `LevelSelectScreen`.
3. Render real `levels` using the layout.
4. Keep the existing `onLevelSelected(level.id)` callback.

### Phase 3 - Progress States

1. Inject or pass progress information into `LevelSelectScreen`.
2. Map each level to completed/current/locked.
3. Show stars from `ProgressService`.
4. Disable locked level taps.

### Phase 4 - Connectors and Map Background

1. Add `TRLevelPathView`.
2. Draw green and grey route segments behind the tiles.
3. Add curved row transitions.
4. Add `TRMapBackgroundView` with subtle map shapes.

### Phase 5 - Polish and Verification

1. Add SwiftUI previews for 4, 8, 12, and 24 levels.
2. Verify small iPhone layout and larger iPhone layout.
3. Check that text never overlaps stars, locks, badges, or tile edges.
4. Add focused tests for the serpentine layout helper.

## Entry-Level Engineering Tasks

These tasks are intentionally scoped so entry-level engineers can complete them independently. Each task should be implemented in a small PR or commit, with screenshots or test output included when relevant.

### Task 1 - Create the Level Tile State Enum

- [x] Add `TRLevelTileState` with `completed`, `current`, and `locked` cases.
- [x] Place it near the level tile component, or in its own small file if the component becomes large.
- [x] Add simple computed properties for state-specific colors only if they keep the tile code easier to read.
- [x] Verify the project builds after adding the enum.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 2 - Build the Static Level Tile Component

- [x] Create `TRLevelTile`.
- [x] Add parameters for `levelNumber`, `state`, `stars`, and `action`.
- [x] Render a fixed-size rounded tile.
- [x] Show the level number in the center.
- [x] Add a SwiftUI preview with one completed tile, one current tile, and one locked tile.
- [x] Verify the preview renders without layout warnings.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 3 - Recreate the Green Completed Tile

- [x] Add the teal-green gradient background.
- [x] Add a white outer stroke.
- [x] Add a soft shadow.
- [x] Add three yellow stars at the bottom.
- [x] Add the circular check badge in the top-right corner.
- [x] Verify the completed preview resembles the concept art.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 4 - Recreate the Blue Current Tile

- [x] Add the bright blue gradient background.
- [x] Add a stronger white outline than the completed tile.
- [x] Add a subtle blue glow or shadow.
- [x] Show earned yellow stars and muted empty stars.
- [x] Add an optional map pin above the tile if it fits cleanly.
- [x] Verify the current tile is visually more prominent than completed and locked tiles.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 5 - Recreate the Grey Locked Tile

- [x] Add the pale grey/white gradient background.
- [x] Use a blue-grey level number.
- [x] Hide stars for locked levels.
- [x] Add a lock icon at the bottom.
- [x] Reduce the shadow strength compared with playable tiles.
- [x] Verify the locked tile clearly reads as unavailable.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 6 - Add the Serpentine Layout Helper

- [x] Create a pure layout helper for four-column placement.
- [x] Use the placement rule `visualColumn = row.isMultiple(of: 2) ? positionInRow : 3 - positionInRow`.
- [x] Return enough data to render each tile: level ID, level number, row, column, and center point.
- [x] Add tests or preview-only debug output proving levels 1 through 8 render as `1 2 3 4` then `8 7 6 5`.
- [x] Verify the helper also works for 12, 16, and 24 levels.

Expected files:

```text
TinyRoutes/UI/LevelSelectScreen.swift
TinyRoutesTests/
```

### Task 7 - Replace the Plain Level List

- [x] Replace the current vertical button list in `LevelSelectScreen`.
- [x] Render level tiles using the serpentine layout helper.
- [x] Keep the existing `onLevelSelected(level.id)` callback for playable levels.
- [x] Keep the existing `onBackTapped` callback.
- [x] Wrap the map in a vertical + horizontal `ScrollView`.
- [x] Verify selecting a playable level still starts gameplay.

Expected files:

```text
TinyRoutes/UI/LevelSelectScreen.swift
```

### Task 8 - Connect Progress to Tile States

- [ ] Read star counts from `ProgressService.bestStars(for:)`, or pass equivalent progress data into the screen.
- [ ] Mark completed levels when `bestStars > 0`.
- [ ] Mark the first incomplete level as current.
- [ ] Mark later levels as locked.
- [ ] Disable locked level taps.
- [ ] Verify level 1 is unlocked when no progress exists.

Expected files:

```text
TinyRoutes/UI/LevelSelectScreen.swift
TinyRoutes/App/ContentView.swift
TinyRoutes/Services/ProgressService.swift
```

### Task 9 - Draw Horizontal Route Connectors

- [ ] Create `TRLevelPathView`.
- [ ] Draw thick horizontal connector segments between tiles in the same row.
- [ ] Use green connectors for completed/unlocked route portions.
- [ ] Use grey connectors for locked route portions.
- [ ] Add a lighter dashed center stroke.
- [ ] Verify connectors sit behind tiles and do not overlap text or stars.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelPathView.swift
TinyRoutes/UI/LevelSelectScreen.swift
```

### Task 10 - Draw Curved Row Transitions

- [ ] Add curved connector turns between the end of one row and the start of the next row.
- [ ] Match the serpentine direction: row 1 turns down on the right, row 2 turns down on the left.
- [ ] Keep curve thickness and dash styling consistent with horizontal connectors.
- [ ] Verify levels 4 to 5 and 8 to 9 appear connected.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelPathView.swift
```

### Task 11 - Add the Map Background

- [ ] Create `TRMapBackgroundView`.
- [ ] Add a pale blue base color.
- [ ] Add very low-opacity street or block shapes behind the route.
- [ ] Keep the background subtle enough that level tiles remain the focus.
- [ ] Verify the screen no longer feels like a plain white list.

Expected files:

```text
TinyRoutes/UI/Components/TRMapBackgroundView.swift
TinyRoutes/UI/LevelSelectScreen.swift
```

### Task 12 - Add Accessibility Labels

- [ ] Add accessibility labels for completed, current, and locked tiles.
- [ ] Include the level number.
- [ ] Include the tile state.
- [ ] Include stars for completed/current tiles.
- [ ] Verify VoiceOver labels are meaningful and do not expose raw IDs like `level_001`.

Expected files:

```text
TinyRoutes/UI/Components/TRLevelTile.swift
TinyRoutes/UI/LevelSelectScreen.swift
```

### Task 13 - Add Preview Coverage

- [ ] Add a preview for 4 levels.
- [ ] Add a preview for 8 levels.
- [ ] Add a preview for 12 levels.
- [ ] Add a preview for 24 levels.
- [ ] Include at least one preview with no progress and one with several completed levels.
- [ ] Verify the preview layout fits small and large iPhone sizes.

Expected files:

```text
TinyRoutes/UI/LevelSelectScreen.swift
TinyRoutes/UI/Components/TRLevelTile.swift
```

### Task 14 - Add Layout Tests

- [ ] Add unit tests for the serpentine placement helper.
- [ ] Assert level 1 appears at row 0, column 0.
- [ ] Assert level 4 appears at row 0, column 3.
- [ ] Assert level 5 appears at row 1, column 3.
- [ ] Assert level 8 appears at row 1, column 0.
- [ ] Assert level 9 appears at row 2, column 0.
- [ ] Run the test target and include the result in the PR or commit notes.

Expected files:

```text
TinyRoutesTests/LevelSelectLayoutTests.swift
```

### Task 15 - Final Visual QA

- [ ] Run the app on a small iPhone simulator.
- [ ] Run the app on a larger iPhone simulator.
- [ ] Confirm level numbers do not overlap stars, locks, badges, or connectors.
- [ ] Confirm the first screen shows the map immediately.
- [ ] Confirm scrolling works when there are more levels than fit onscreen.
- [ ] Capture screenshots for review.

Expected files:

```text
No required code file. This is a verification task.
```

## Acceptance Criteria

The feature is ready when:

```text
The level select screen no longer appears as a plain list.
The green completed tile, blue current tile, and grey locked tile are recreated in code.
Levels display in the required 1-2-3-4 / 8-7-6-5 repeating pattern.
Route connectors visually follow that same serpentine pattern.
Completed, current, and locked states are clearly distinguishable.
Completed/current levels can be launched with the existing callback.
Locked levels cannot accidentally launch gameplay.
The layout works with more levels than fit on one screen.
The implementation has previews or tests covering the layout pattern.
```

## Open Decisions

Decide during implementation:

```text
Whether the current tile should show a map pin, glow only, or both.
Whether completed levels should always show a check badge.
Whether replaying completed levels should be allowed immediately.
Whether locked tile taps should do nothing or show a locked response.
Whether star icons should use SF Symbols or a custom small star asset.
```
