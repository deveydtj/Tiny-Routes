# Miniature World Board: Port Plan

Status: proposal · Owner: Jake · Last updated: 2026-11-03

Visual reference: [prototypes/miniature-world/index.html](../../prototypes/miniature-world/index.html) (levels 5 and 10, playable in a browser)

## Goal

Add a tilt-shift diorama board to the multi-van game, next to today's flat board: a floating slab of lawn, toy vans, papercraft houses and Paper Mario-style cutout scenery. Neither board changes the rules.

- **3D diorama:** the new look.
- **2D map:** today's `MultiVanBoardView`, kept as a first-class option. It's used in Low Power Mode, and by anyone who prefers it.

The spike answers three questions:

1. Is the diorama still readable at a glance on a phone, with the blur and the tilted camera?
2. Does it hold 60 fps without heating up the oldest phone we support?
3. Given a choice, which board do playtesters keep?

## What makes the look

The HTML prototype shows the effect comes from the camera and light more than from models. In order of impact:

1. **Shallow focus.** The middle of the board is sharp; the near and far edges blur.
2. **Long lens, looking down at about 45°**, turned slightly off-axis.
3. **Hard, warm sun shadows** plus soft contact shadows under every object.
4. **Punchy grade:** saturation up about 30%, a light vignette.
5. **A die-cut slab** with soil layers on its sides, floating over a soft shadow.
6. **Toy pieces:** cutouts with a white die-cut border and a plain brown-paper back, chunky vans, papercraft houses.

Items 1–4 are camera and lighting settings, which is why the port is mostly plumbing.

## Two boards, one game

### Choosing the board

A new **Board Style** row goes in Settings → Gameplay:

| Setting | Options | Default |
|---|---|---|
| Board Style | 3D Diorama · 2D Map | 3D Diorama once MW-10 passes; 2D Map until then |
| Use 2D in Low Power Mode | On · Off (shown only when 3D Diorama is chosen) | On |

A pure function decides which board to show, so it can be unit tested without a device:

```swift
enum MultiVanBoardStyle { case diorama, flat }

static func resolve(preference: MultiVanBoardStyle, flatInLowPower: Bool,
                    isLowPowerMode: Bool) -> MultiVanBoardStyle
```

| Preference | Use 2D in Low Power Mode | Low Power Mode | Board |
|---|---|---|---|
| 2D Map | any | any | 2D |
| 3D Diorama | On | on | 2D |
| 3D Diorama | On | off | 3D |
| 3D Diorama | Off | any | 3D |

Reduce Motion does **not** switch boards. The diorama stays 3D but drops camera sway, chimney smoke, dial pulsing and confetti, like the flat board does today. "Reduce Animations" has the same effect.

### Switching while playing

- A small `MultiVanPowerMonitor` publishes `ProcessInfo.processInfo.isLowPowerModeEnabled` and updates on `.NSProcessInfoPowerStateDidChange`. That notification can arrive on any thread, so hop to the main actor before publishing.
- Both boards read the same engine, so swapping one for the other never loses state: switch settings, van positions and the run all carry over.
- **Changes the player makes** in Settings apply straight away. Gameplay isn't on screen while Settings is open.
- **Automatic changes** (Low Power Mode turning on or off) apply straight away in the plan phase or after a run ends. During a run, wait for the run to end, so the camera doesn't jump while the player is watching the vans.
- Crossfade the swap over 0.25 s, or with no animation when motion is reduced.
- When the 2D board is showing, tear the `SCNView` down. That frees its GPU memory and stops rendering completely, which is the point of the low-power path.
- Optional, decide after MW-10: treat `ProcessInfo.thermalState` `.serious` or `.critical` like Low Power Mode, using the same mid-run rule.

### Keeping the two boards in step

Every new board feature now has to ship twice, so move what both boards need into shared code first (MW-01):

- **Switch buttons.** The 44 pt `Button` with its accessibility label, value and hint, the `engine.tapSwitch` / `onSwitchTapped` call and the rejection feedback. The flat board places it at the layout point; the diorama places it at the projected 3D point.
- **Board rules.** `switchNodes`, `isDelivered`, `barrierNodes` and `barrierHeading` are static functions on `MultiVanBoardView` today. Move them to a shared `MultiVanBoardRules` enum and point the existing tests at it.
- **Preview endpoints.** Which ✓ / ✗ goes where, and how markers stack when two routes end at the same place.

A parity test builds both boards' switch lists for all 12 levels and checks they match: same switch IDs, same accessibility labels, same tap results.

## Renderer choice for the diorama

Checked against the installed iOS 27.1 SDK and our iOS 17.0 deployment target:

| Option | Works on iOS 17 | Shallow focus | Grade |
|---|---|---|---|
| **SceneKit** (`SCNView`) | Yes | Built in: `SCNCamera.wantsDepthOfField`, `focusDistance`, `fStop` (iOS 11) | Built in: `saturation`, `contrast`, `vignettingIntensity`, `bloomIntensity`, `colorGrading` (iOS 10) |
| RealityKit `RealityView` | No, needs iOS 18; custom post-processing (`PostProcessEffect`) needs iOS 26 | Write our own Metal blur | Write our own |
| RealityKit `ARView(cameraMode: .nonAR)` | Yes | Write our own blur in `renderCallbacks.postProcess` | Write our own |

**Recommendation: SceneKit for the spike.** It gets the whole look from properties, with no shaders, and the scene is small (about 150–300 nodes).

The catch is that Apple announced at WWDC 2025 that SceneKit will get no new features and that RealityKit is the way forward. The 27.1 SDK headers don't mark it deprecated yet. So keep the renderer behind one view. If we keep the look and later raise the minimum iOS to 26, swap in `RealityView` plus a `PostProcessEffect`: a port of the prototype's tilt-shift shader, about 150 lines of Metal. The engine, feedback models, shared board code and the 2D board stay the same.

If raising the minimum to iOS 26 now is acceptable, skip SceneKit and go straight to `RealityView`. Everything below still applies; only MW-03 changes.

## How it fits the current code

`MultiVanGameplayScreen` already keeps rendering separate from rules:

- `MultiVanEngine` is the model. `MultiVanFrameDriver` advances it from a `TimelineView`.
- Engine events feed four feedback models: `MultiVanCelebration`, `MultiVanPersonality`, `MultiVanCrashEffects` and `MultiVanSwitchFeedback`.
- `MultiVanBoardView` only reads the engine and those models.

So the diorama is a **second board view with the same inputs**. A small switcher picks one of the two at the single place a board is created today (`MultiVanGameplayScreen.gameplayContent`):

```
MultiVanBoardSwitcher               picks a board from the resolved style; crossfades
├─ MultiVanBoardView                2D map (today's board, using the shared pieces)
└─ MultiVanDioramaBoardView         3D diorama, same parameters as MultiVanBoardView
   ├─ MultiVanDioramaSceneView      UIViewRepresentable around SCNView
   │    └─ MultiVanDioramaScene     builds nodes on level load, syncs them on update
   └─ shared switch buttons         placed at projected switch points
```

Key decisions for the diorama:

- **Sync on the main actor, never from SceneKit's render delegate.** Like the flat board, read the observable values (`vans`, `previewRoutes`, `runtimeGraph`, `phase`, the feedback tokens) in `body`, then push them into the scene from `updateUIView`. The engine is never touched from SceneKit's render thread. Ambient motion (tree sway, chimney smoke, dial pulse) runs as `SCNAction`s inside SceneKit, so it needs no per-frame Swift.
- **Taps and accessibility stay in SwiftUI**, using the shared switch buttons. SwiftUI owns the camera, so it projects each switch's world point with the renderer-free `MultiVanDioramaCamera.viewPoint` (tested against SceneKit's own matrices; `SCNView.projectPoint` lags a camera move until the next render) and re-projects as the camera moves. Don't hit-test in SceneKit. Houses, vans and roadblocks get invisible VoiceOver elements at their projected points with the flat board's words, so VoiceOver behaves the same on both boards.
- **Close switches share their targets.** On level 12 two diorama switches project 36 pt apart, and two flat-board switches 41 pt apart on a small phone, so 44 pt squares overlap. Each button's hit region is its square, clipped to the board, less any part a nearer switch's square covers (`MultiVanSwitchPlacement`).
- **Reuse the road geometry.** Van position and heading come from `RoadPath.point` / `tangent` and `MultiVanVanView.heading`, the same calls the flat board uses. No new path maths.
- **One coordinate mapping.** Grid (x 0…4, y 0…6, y up) maps to world `(x − 2, 0, 3 − y)` in grid units. Put it in one function and test it.
- **Screen-space effects can stay 2D at first.** The "+1 ×2" delivery popup and the failure ring can be SwiftUI overlays placed by projection until their 3D versions land (MW-09). MW-09 moved the failure ring onto the lawn but kept the "+1 ×2" label in SwiftUI, placed over the house by projection: text in the scene would blur with the back row. The flat board's 2D shake and 2D confetti now apply only to the flat board; the diorama shakes its lens and throws paper confetti.
- **Feedback plays from tokens.** The diorama reads the same feedback models' tokens (`MultiVanDioramaCues`) and plays each new one once as `SCNAction`s or a keyframe animation (`MultiVanDioramaEffects`). Tokens a board finds on its first sync, or that arrive with motion off, are treated as already played, so switching boards or turning motion back on never replays them.

## Numbers to carry over

These come from the HTML prototype's final tuning:

| Thing | Value |
|---|---|
| Camera | 30° vertical field of view; yaw −0.24 rad, pitch 0.80 rad around (0, −0.15, 0.1); drag range yaw ±0.85, pitch 0.45–1.30 |
| Framing | Binary-search the camera distance so the slab fits between the HUD and the buttons, then re-centre it (`frame()` in the prototype) |
| Sun | Warm white `#fff0d6`, from (−5.2, 8.2, 3.6), casts shadows; 2048 px shadow map |
| Fill | Sky/ground light `#e6f4ff` / `#a3b98a`, low intensity |
| Grade | Saturation ×1.3, light vignette, filmic tone mapping |
| Slab | 6.6 × 8.6 units, corner radius 0.42; grass 0.16 deep, soil 0.44, deep soil 0.36, each stepped in slightly |
| Roads | Curb 0.47 wide `#efe6d2`, white edge line 0.335, asphalt 0.30 `#626779`; switch plazas r 0.34 |
| House | 0.62 × 0.50 footprint, walls 0.34, roof rise 0.27, scaled ×1.28; centre 0.54 past the house node; front faces the incoming road; colour and shape plaque over the door |
| Van | 0.27 × 0.44 body, scaled ×1.15; roof decal carries the colour's shape symbol |
| Switch dial | Radius 0.27, scaled ×1.12; arrow springs to the active exit; small dots mark the other exits |
| Scenery | Seeded per level; trees in groves; nothing within road and house clearances; nothing tall in front of a road (tree height × 0.95 of clear lawn behind it) |

## Tasks

Same conventions as [multi_van_tasks.md](multi_van_tasks.md): one PR each, run `xcodegen generate` after adding files, and keep changes inside `TinyRoutes/Prototype/` and `TinyRoutesTests/Prototype/` unless a task says otherwise.

**MW-01 · Shared board pieces.** Move the switch button (with its accessibility and rejection feedback), the board rules and the preview-endpoint logic out of `MultiVanBoardView` into shared files. The flat board uses them, with no visible change. Update the tests that call `MultiVanBoardView.switchNodes` and friends.
*Done when:* the flat board looks and behaves the same, all tests pass, and the shared switch button has no knowledge of how its position was worked out.

**MW-02 · Board Style setting and switcher.** *Reasoning: High*: settings migration and mid-run timing.
- Add `boardStyle` and `usesFlatBoardInLowPowerMode` to `UserSettings`, plus setters on `UserSettingsService`. Today `UserSettings` uses the synthesised decoder, so a new non-optional property would make settings saved by older builds fail to decode. Add a custom `init(from:)` that uses `decodeIfPresent` with the defaults, plus a test that decodes a payload from the current build. This touches `TinyRoutes/Domain/` and `TinyRoutes/Services/`.
- Add the two rows to Settings → Gameplay in `TinyRoutes/UI/SettingsScreen.swift`. Wrap them in `#if MULTIVAN_INTERNAL` until MW-10 passes.
- Add `MultiVanBoardStyle.resolve`, `MultiVanPowerMonitor` and `MultiVanBoardSwitcher` with the mid-run rule. Until MW-03 lands, the diorama slot can show the flat board with a "3D" badge.
*Done when:* the resolver's table is covered by unit tests. Turning Low Power Mode on in the plan phase swaps to 2D straight away. Turning it on mid-run swaps when the run ends. Switch settings survive every swap.

**MW-03 · Scene shell.** `SCNView` representable, slab, sun and fill lights, camera with depth of field and grade, and framing between the HUD bars. *Reasoning: High*: depth-of-field tuning decides whether the board stays readable.
*Done when:* an empty table matches the prototype's look on a device, the start row and houses of level 12 are readable, and the view releases its scene when the switcher removes it.

**MW-04 · Lawn and road texture.** Paint the lawn texture once per level with `UIGraphicsImageRenderer`, stroking each edge's `RoadPath` in three passes (curb, white edge, asphalt) so overlapping roads merge cleanly. Add depot bays, switch plazas, driveways and barrier hatching.
*Done when:* all 12 levels' roads line up with the flat board when both are drawn at the same scale.

**MW-05 · Board pieces.** Houses, vans, switch dials and roadblocks as node builders, with materials from the table above.
*Done when:* every colour and symbol is distinguishable in a grayscale screenshot.

**MW-06 · Sync from the engine.** Van position, heading and status (waiting rumble, driving, parked, crashed, stuck); dial angle and locked or live tint; preview dots and ✓ / ✗ markers that follow `previewRoutes`, trimmed as vans drive.
*Done when:* levels 1–12 play the same on both boards. The existing solution tests are the reference.

**MW-07 · Input and accessibility.** Place the shared switch buttons at projected points and re-project them when the camera moves. A drag gesture orbits the camera, and double-tap straightens it. Add the board parity test.
*Done when:* VoiceOver reads and activates every switch on both boards, taps never miss within 44 pt, and the parity test passes for all 12 levels.

**MW-08 · Scenery.** Seeded groves, bushes, flower beds and one pond per level, following the keep-out and sightline rules. Cutout art goes in the asset catalog as PNGs with alpha; the prototype's canvas art can be exported as a starting set.
*Done when:* the same level always gets the same scenery, and a unit test confirms no scenery point overlaps a road or sits in front of one.

**MW-09 · Feedback in 3D.** Parcel toss and house squash on delivery, paper confetti on win, cotton-wool puff and camera shake on a crash, chimney smoke. All of it is driven by the existing feedback models and respects Reduce Motion and "Reduce Animations".
*Done when:* every event the flat board reacts to has a diorama response, or an explicit no-op when motion is reduced.

**MW-10 · Device and playtest pass.**
- Profile both boards on the oldest iOS 17 phone we support. Flatten static scenery into one node, and cap the diorama's frame rate in the plan phase if needed.
- Compare battery drain and thermals over a 10-minute session on each board. Decide whether thermal state should also trigger the 2D fallback.
- Playtest with players starting on each board and free to switch.
*Done when:* the diorama holds 60 fps in the run phase, and the 2D board uses clearly less power than the 3D board. Playtests show no slower time to the first Go on the diorama, and we have a default to ship. Then remove the `MULTIVAN_INTERNAL` gate from the Board Style rows.

*Progress (2026-11-03):* the tooling is in; the measurements and playtests aren't.
- **Playtest log, schema 2.** Each attempt records the board it started on, Go and `board_changed` events record the board on screen, and quit rows record the board the player left on. The log screen shows a per-board summary: attempts, wins, and the median time to first Go over levels whose first attempt reached Go without a board change. Schema 1 rows still decode and are left out of the board summary.
- **Signposts.** `MultiVanBoardSignposts` marks a `Board` interval such as "diorama run" (subsystem `com.tinyroutes.app`, category `MultiVanBoard`), so a trace of a free play session splits by board and phase.
- **Autoplay.** Internal builds launched with `-MultiVanAutoplay '<json>'` open one level on one board and win it on a loop with the solution script's taps, for identical workloads on both boards. Unit tests check every level wins at par at 60 and 30 fps. Its attempts go to a separate log in the temporary folder. It reads the process arguments directly, because the `UserDefaults` argument domain drops a JSON value.
- **`scripts/profile_multivan_boards.py`** builds `MultiVanInternal`, installs it and records each template for each board, for example `--template "Game Performance" --template "Power Profiler"`. Instruments needs a cabled device: a device that only `devicectl` reaches over the network shows as offline to `xctrace` ("Timed out waiting for device to boot"). A locked device fails the same way, so set Auto-Lock to Never for the run.
- **In-app meter, over Wi-Fi.** `MultiVanPerformanceMeter` runs with autoplay and writes frame times (main-thread display link, and SceneKit's render callback), thermal state, battery, app state and autoplay's presses to `Documents/multi_van_performance.jsonl`. `scripts/profile_multivan_boards.py --meter` launches each board with `devicectl`, copies the file back and summarises it, so no cable or Instruments is needed. A remotely launched app stays in an inactive SwiftUI scene, so autoplay also plays there.
- **First numbers, iPhone 14 (iOS 27.0.1), level 12, 2 min per board, 8 won runs each, on the charger:**

  | Board · phase | SceneKit fps (dropped frames) | Main-thread fps (late frames) |
  |---|---|---|
  | Diorama · run | 60.0 (0 in 65 s) | 58.6 (37) |
  | Diorama · plan | 60.0 (0 in 29 s) | 55.5 (59) |
  | Flat · run | — | 58.4 (38) |
  | Flat · plan | — | 54.2 (61) |

  The diorama holds 60 fps in the run phase on this phone, and it adds no main-thread load: both boards show the same late frames. That points to shared code, roughly one late frame per switch tap while planning and a few per run. Worth a look, but it doesn't block MW-10. Thermals stayed nominal. No frame-rate cap or scenery flattening is needed on this phone.
- Still open: the iPhone 14 is faster than the oldest supported phone, so its pass is a lower bound. The 10-minute unplugged battery comparison (`--meter --seconds 600`) and the playtests haven't run, so the default board and the gate stay as they are.

Dependencies:
- MW-01 and MW-03 can start straight away.
- MW-02 needs MW-01. MW-04 and MW-05 need MW-03.
- MW-06 needs MW-05. MW-07 needs MW-01 and MW-05. MW-08 needs MW-04. MW-09 needs MW-06.
- MW-10 needs everything else.

## Risks and open questions

- **Two boards to maintain.** Every future board feature, such as a new switch type, needs both a 2D and a 3D version. The shared pieces and the parity test keep that cost down. The decision point is MW-10: if almost nobody picks one board, consider dropping it.
- **Blur against readability.** Real depth of field blurs whatever is far from the focus distance, including the top row of houses on tall levels. Tune `fStop` per device size. Players who find it hard to read now have the 2D map.
- **Cutout shadows.** Checked in MW-05 with the roadblock cutout: SceneKit's shadow pass follows the texture's alpha on a blended material (`transparencyMode = .aOne`), but a `discard` in a shader modifier still casts the whole rectangle. MW-08's cutouts should use `MultiVanDioramaPieces.standee`, which is blended. If many blended cutouts sort badly, the fallback is contact shadows baked into the lawn texture, which the prototype already does and which look good. MW-08 uses both: up to 34 trees, 18 bushes and a few residents as blended standees, plus baked contact shadows. In simulator renders of levels 5, 10 and 12 they sort cleanly, with no halos through the depth of field. Check again on a device in MW-10.
- **Battery.** Continuous rendering with depth of field costs more than a static Canvas. The Low Power Mode fallback covers the worst case; MW-10 measures the normal case.
- **Renderer lifetime.** The SceneKit risk above. Keeping everything SceneKit-specific behind `MultiVanDioramaSceneView` and `MultiVanDioramaScene` is what makes a later swap cheap.
