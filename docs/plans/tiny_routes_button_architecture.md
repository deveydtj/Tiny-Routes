# Tiny Routes - Button Architecture Plan

## Purpose

Define the production approach for the main menu buttons shown in the Tiny Routes visual target:

- Blue `Play`
- Green `Daily Route`
- Purple `Shop`
- White `Settings`

These buttons should be generated in code rather than exported as static image assets.

The button artwork is a UI system: rounded rectangles, vertical gradients, highlights, shadows, glows, and press animation. Keeping those pieces in SwiftUI makes the buttons scalable, themeable, lightweight, and easier to animate across screen sizes.

---

## Recommendation

Build the menu buttons as reusable SwiftUI components first.

Use SpriteKit-generated nodes only if a future screen needs the same button treatment inside an active SpriteKit scene. The home, shop, settings, and level-select screens should stay in SwiftUI because they are interface-heavy and benefit from native accessibility, dynamic layout, and simple state handling.

Recommended target files:

```text
TinyRoutes/UI/Components/TRMenuButton.swift
TinyRoutes/UI/Components/TRMenuButtonStyle.swift
TinyRoutes/UI/Components/TRButtonTheme.swift
```

If the project keeps UI files flat, these can live directly under `TinyRoutes/UI/` instead. A `Components` folder is cleaner once the home screen adds cards, nav tabs, currency pills, and icon buttons.

---

## Visual Anatomy

Each button should be assembled from these code-generated layers:

1. Base rounded rectangle
2. Vertical gradient fill
3. Top highlight overlay
4. Subtle inner bottom shade
5. Outer drop shadow
6. Optional color glow
7. Icon and label foreground
8. Pressed-state scale, opacity, and shadow adjustment

The reference style is soft, saturated, and toy-like without requiring bitmap button backgrounds.

---

## Component API

Create one high-level component for primary menu actions:

```swift
struct TRMenuButton: View {
    let title: String
    let systemImage: String
    let variant: TRButtonVariant
    let size: TRButtonSize
    let action: () -> Void
}
```

Suggested variants:

```swift
enum TRButtonVariant {
    case play
    case dailyRoute
    case shop
    case settings
}
```

Each variant owns:

- Fill gradient colors
- Foreground color
- Shadow color
- Glow strength
- Icon symbol
- Text weight
- Border/highlight opacity

Use SF Symbols for initial icons:

| Button | Symbol | Notes |
|---|---|---|
| Play | `play.fill` | Large leading icon |
| Daily Route | `calendar.badge.star` | May need fallback if symbol availability is limited |
| Shop | `bag.fill` | White icon on purple |
| Settings | `gearshape.fill` | Blue-gray icon/text on white |

If a symbol is unavailable on the minimum iOS target, replace it with a supported SF Symbol or a small vector asset.

---

## Layout Rules

Menu buttons should have stable dimensions and avoid text-driven layout shifts.

Recommended sizing:

- Width: `min(414, availableWidth - 64)`
- Height: `74` for Play, `62` for secondary actions
- Corner radius: `18` to `20`
- Horizontal content padding: `28`
- Icon frame: fixed width, around `44`
- Label: centered visually within the full button, not only within remaining space

The `Play` button should be taller and more prominent than the others. `Daily Route`, `Shop`, and `Settings` can share the same component with smaller sizing.

---

## SwiftUI Styling Approach

Use a custom `ButtonStyle` so pressed states are consistent:

```swift
struct TRMenuButtonStyle: ButtonStyle {
    let variant: TRButtonVariant
    let size: TRButtonSize

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .opacity(configuration.isPressed ? 0.94 : 1.0)
            .animation(.spring(response: 0.22, dampingFraction: 0.72), value: configuration.isPressed)
    }
}
```

The background can be a separate view so it can be reused by non-button surfaces:

```swift
struct TRButtonBackground: View {
    let variant: TRButtonVariant
    let isPressed: Bool

    var body: some View {
        RoundedRectangle(cornerRadius: 20, style: .continuous)
            .fill(variant.gradient)
            .overlay(alignment: .top) {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .fill(.white.opacity(variant.highlightOpacity))
                    .frame(height: 24)
                    .blur(radius: 10)
                    .offset(y: -8)
            }
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(.white.opacity(variant.strokeOpacity), lineWidth: 1)
            }
            .shadow(
                color: variant.shadowColor.opacity(isPressed ? 0.18 : 0.32),
                radius: isPressed ? 6 : 12,
                x: 0,
                y: isPressed ? 3 : 8
            )
    }
}
```

Keep color values centralized in `TRButtonVariant` or a `TRButtonTheme` struct so seasonal themes and dark mode can alter the palette without changing call sites.

---

## File Responsibilities

The current project uses a flat `TinyRoutes/UI/` folder. Prefer a `TinyRoutes/UI/Components/` folder for the first implementation because the home screen is expected to grow into a real app shell with reusable controls. XcodeGen already includes the whole `TinyRoutes` source tree, so adding this folder does not require a manual project file edit as long as `project.yml` remains the source of truth.

Recommended files:

```text
TinyRoutes/UI/Components/TRMenuButton.swift
TinyRoutes/UI/Components/TRMenuButtonStyle.swift
TinyRoutes/UI/Components/TRButtonTheme.swift
```

Suggested ownership:

| File | Responsibility |
|---|---|
| `TRMenuButton.swift` | Public SwiftUI component, size enum, content layout, previews |
| `TRMenuButtonStyle.swift` | `ButtonStyle`, pressed state behavior, background composition |
| `TRButtonTheme.swift` | Variants, color tokens, gradients, foregrounds, shadows, accessibility labels |

If implementation is very small, combine these into one file initially:

```text
TinyRoutes/UI/Components/TRMenuButton.swift
```

Split the theme and style into separate files only when the single file becomes hard to scan. Avoid a broad UI kit layer until there are at least two or three reusable controls using the same tokens.

---

## Initial Color Tokens

Use these as starting values, then tune in Simulator against the reference art:

| Variant | Top | Bottom | Foreground | Shadow |
|---|---|---|---|---|
| Play | `#34B8FF` | `#0B7FEA` | White | `#0876D8` |
| Daily Route | `#42DEC4` | `#19B79D` | White | `#159A87` |
| Shop | `#8B67F4` | `#5B3BDE` | White | `#4B31C8` |
| Settings | `#FFFFFF` | `#EAF1FA` | `#34435C` | `#9CAFC5` |

Do not export separate PNGs for these backgrounds. Export only icons or decorative art that cannot be reasonably generated in SwiftUI.

---

## Icon Policy

The current resource folder includes large PNG icon-style assets for play, shop, and settings. For the menu buttons, prefer SF Symbols at first because they are crisp, tintable, accessible, and cheap to animate.

Use bundled PNGs only when the art direction needs a bespoke icon that SF Symbols cannot approximate. If PNG icons are used:

- Keep them as foreground icons only.
- Render them at a fixed frame size inside the same SwiftUI button layout.
- Do not bake labels, shadows, fills, or button states into the PNG.
- Prefer template-renderable assets for simple one-color icons.
- Add image accessibility through the containing button label, not separate image labels.

The missing daily icon should not block the button component. Start with `calendar.badge.star` or `calendar`, then replace with a custom asset later if needed.

---

## Current App Integration

The app currently has:

- `HomeScreen` with `onPlayTapped`, `onShopTapped`, and `onSettingsTapped`
- `ContentView` rendering the global background image behind all screens
- `AppCoordinator` routes for level select, shop, and settings
- No daily route state or callback yet

Therefore the first integration should keep `HomeScreen` simple and add the daily route entry point in one of two safe ways:

1. **Preferred for visual polish only:** render `Daily Route` disabled with a visually complete button and an accessibility hint such as `Coming soon`.
2. **Preferred when routing is added in the same story:** add `onDailyRouteTapped` to `HomeScreen`, add a coordinator method, and route to an explicit placeholder screen or state.

Do not make `Daily Route` secretly open normal level select unless product explicitly chooses that behavior. Daily route is a retention feature with different completion and streak semantics, so ambiguous routing will create cleanup work later.

---

## Home Screen Layout Blueprint

Keep the global background in `ContentView`; `HomeScreen` should only own its foreground menu layout.

Recommended structure:

```swift
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onDailyRouteTapped: (() -> Void)?
    let onShopTapped: () -> Void
    let onSettingsTapped: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Spacer(minLength: 40)

            titleStack

            VStack(spacing: 14) {
                TRMenuButton(title: "Play", systemImage: "play.fill", variant: .play, size: .primary, action: onPlayTapped)
                TRMenuButton(title: "Daily Route", systemImage: "calendar.badge.star", variant: .dailyRoute, size: .secondary, action: onDailyRouteTapped ?? {})
                    .disabled(onDailyRouteTapped == nil)
                TRMenuButton(title: "Shop", systemImage: "bag.fill", variant: .shop, size: .secondary, action: onShopTapped)
                TRMenuButton(title: "Settings", systemImage: "gearshape.fill", variant: .settings, size: .secondary, action: onSettingsTapped)
            }
            .frame(maxWidth: 414)

            Spacer(minLength: 32)
        }
        .padding(.horizontal, 32)
    }
}
```

Tune the actual title treatment against the background artwork. The button component should not assume anything about the title, coin counters, streak cards, or other home-screen modules.

---

## Detailed Component Design

Use two explicit sizes:

```swift
enum TRButtonSize {
    case primary
    case secondary

    var height: CGFloat {
        switch self {
        case .primary: return 74
        case .secondary: return 62
        }
    }

    var cornerRadius: CGFloat {
        switch self {
        case .primary: return 21
        case .secondary: return 18
        }
    }
}
```

Use a variant model that keeps visual tokens close together:

```swift
enum TRButtonVariant {
    case play
    case dailyRoute
    case shop
    case settings

    var gradientColors: [Color] { ... }
    var foregroundColor: Color { ... }
    var shadowColor: Color { ... }
    var highlightOpacity: Double { ... }
    var strokeOpacity: Double { ... }
    var glowOpacity: Double { ... }
}
```

The high-level button should compose a real `Button`, not a gesture on a custom view:

```swift
struct TRMenuButton: View {
    let title: String
    let systemImage: String
    let variant: TRButtonVariant
    let size: TRButtonSize
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.system(size: size == .primary ? 26 : 22, weight: .bold))
                    .frame(width: 44)

                Text(title)
                    .font(.system(size: size == .primary ? 25 : 21, weight: .heavy, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                Color.clear.frame(width: 44, height: 1)
            }
            .frame(maxWidth: .infinity)
            .frame(height: size.height)
            .padding(.horizontal, 20)
        }
        .buttonStyle(TRMenuButtonStyle(variant: variant, size: size))
        .accessibilityLabel(Text(title))
    }
}
```

The trailing clear spacer mirrors the icon width so the label remains visually centered within the full button. If a future button needs a right-side badge, replace the spacer with a fixed-width badge container instead of changing the core alignment behavior.

---

## Pressed, Disabled, and Motion States

Pressed behavior:

- Scale to `0.97` for regular motion.
- Reduce shadow radius and vertical offset.
- Slightly lower opacity for a tactile response.
- Keep the button frame stable so the stack does not jump.

Disabled behavior:

- Keep layout identical.
- Lower saturation or opacity enough to communicate disabled state.
- Preserve label contrast.
- Add an accessibility hint when the disabled state is product-driven, such as `Daily Route coming soon`.

Reduce Motion behavior:

- Use `@Environment(\.accessibilityReduceMotion)` in the style.
- Replace spring scale animation with a short opacity transition or no animation.
- Do not remove pressed feedback completely unless testing shows the opacity feedback is enough.

Dynamic Type:

- The home menu should remain stable at common accessibility sizes.
- Use `minimumScaleFactor` on button labels.
- Avoid multi-line primary button labels unless product copy changes beyond the current four titles.
- Re-test if localized copy is introduced.

---

## Layering Details

The button background should be rendered in this order:

1. Glow behind the rounded rectangle for color variants only.
2. Main vertical gradient rounded rectangle.
3. Top white highlight clipped to the rounded shape.
4. Bottom inner shade using a black-to-clear gradient with low opacity.
5. One-pixel white or tinted stroke.
6. Outer drop shadow.
7. Foreground content.

For the white settings button, use a cooler blue-gray shadow and a slightly stronger stroke so it remains visible against the home background.

Avoid heavy blur values on old devices. A subtle glow can be faked with one or two shadows instead of large blurred overlays if performance becomes a concern.

---

## Accessibility

Each button must support native accessibility:

- Use a real SwiftUI `Button`
- Provide clear labels: `Play`, `Daily Route`, `Shop`, `Settings`
- Keep hit targets at least `44x44`
- Respect Reduce Motion by replacing spring/scale animation with a shorter opacity change
- Maintain contrast in light mode
- Avoid relying on color alone for meaning

---

## Implementation Notes

Use `Color` helpers for hex tokens if the repo already has one. If not, avoid adding a global extension unless several screens need it. Local static colors in `TRButtonVariant` are enough for the first pass:

```swift
private static let playTop = Color(red: 0.20, green: 0.72, blue: 1.00)
```

If a hex initializer is added, keep it internal to the UI layer and test edge cases only if it becomes shared production infrastructure.

Use SwiftUI previews for visual iteration. Unit tests are not useful for gradients and shadows unless the component grows non-visual logic. The important verification is build coverage, previews, Simulator screenshots, and manual accessibility checks.

Because this project is managed by XcodeGen, regenerate the Xcode project only when the local workflow requires it. Source files under `TinyRoutes/` should be picked up by the existing `project.yml` source path.

---

## Rollout Plan

### Step 1 - Create Button Component ✅ Completed

Add `TRMenuButton`, `TRButtonVariant`, `TRButtonSize`, and `TRMenuButtonStyle`.

Status:

- [x] Added `TRMenuButton`
- [x] Added `TRButtonVariant`
- [x] Added `TRButtonSize`
- [x] Added `TRMenuButtonStyle`
- [x] Added generated background, highlight, stroke, and shadow layers
- [x] Added pressed and disabled visual states

Acceptance criteria:

- [x] Component renders all four variants in SwiftUI previews.
- [x] Button backgrounds are generated entirely in code.
- [x] Pressed state visibly scales and reduces shadow.
- [x] Disabled state is visually distinct without changing layout.

### Step 2 - Replace HomeScreen Buttons ✅ Completed

Update `HomeScreen` to use the new component:

- [x] `Play` triggers `onPlayTapped`
- [x] `Daily Route` is disabled until a callback or route exists
- [x] `Shop` triggers `onShopTapped`
- [x] `Settings` triggers `onSettingsTapped`

If the app does not yet have a daily route callback, render the button disabled. If the same story adds routing, add explicit app state support rather than sending daily traffic through normal level select.

Acceptance criteria:

- [x] Home screen no longer uses plain text buttons.
- [x] Vertical spacing matches the stacked menu look from the reference.
- [x] Buttons resize cleanly on compact iPhone widths.
- [x] Current `ContentView` routing for play, shop, and settings still works.

### Step 3 - Add Preview Coverage ◑ Partially Completed

Create previews for:

- [x] Individual button variants
- [x] Full button stack
- [x] Light mode
- [ ] Dark mode placeholder, even if final dark palette comes later
- [ ] Narrow-width layout
- [x] Disabled daily route state

Acceptance criteria:

- [x] Previews make it easy to tune gradients, shadows, and spacing without running gameplay.
- [x] Preview backgrounds include at least one plain color and one approximation of the home background brightness.

### Step 4 - Integrate Disabled Daily Route State ✅ Completed

Until the daily route feature exists, decide and encode the temporary behavior explicitly.

Recommended first-pass behavior:

- [x] Add `onDailyRouteTapped: (() -> Void)? = nil` to `HomeScreen`.
- [x] Render the daily button disabled when the callback is `nil`.
- [x] Add an accessibility hint: `Coming soon`.
- [x] Keep the visual button in the stack so the home screen matches the target composition.

Acceptance criteria:

- [x] The disabled daily button is visible but cannot trigger a wrong route.
- [x] `ContentView` can continue constructing `HomeScreen` without adding daily route app state.
- [x] The future daily route integration point is obvious from the `HomeScreen` initializer.

### Step 5 - Tune Against Background Art ◑ Partially Completed

Use the current `background.png` in Simulator when tuning button contrast.

Status:

- [x] Buttons were built and checked against the current home-screen background flow.
- [x] The white settings button uses stronger highlight/stroke treatment than colored buttons.
- [ ] Final visual tuning across multiple devices is still open.

Acceptance criteria:

- [x] White settings button remains distinct over the lightest background areas.
- [x] Colored buttons do not visually merge into the background.
- [x] Shadows read as depth, not muddy outlines.
- [x] Button stack is readable with `.padding()` from `ContentView`.

### Step 6 - Theme Extraction ◑ Partially Completed

Move hard-coded colors into a small theme layer once the first implementation looks correct.

Status:

- [x] Visual tokens are centralized in `TRButtonVariant`.
- [ ] Tokens have not been extracted into a separate `TRButtonTheme` file yet.

Acceptance criteria:

- [x] Variants expose semantic colors.
- [ ] Future dark mode or event skins can swap palettes from one place.

### Step 7 - Optional SpriteKit Bridge ☐ Not Started

Only add this if a SpriteKit scene needs interactive menu buttons.

Approach:

- Use SpriteKit nodes for in-scene buttons.
- Match SwiftUI tokens manually or through shared color constants.
- Keep SwiftUI as the source of truth for app menu screens.

Acceptance criteria:

- [ ] SpriteKit buttons visually match SwiftUI buttons.
- [ ] No bitmap background export is introduced.

---

## Story Mapping

This button work fits into the home-shell polish backlog:

- `STORY-029` / home screen shell: use the component for Play, Daily Route, Shop, and Settings.
- Future daily route stories: wire `onDailyRouteTapped` to real daily challenge state.
- Future shop/settings polish stories: reuse the same button style for prominent calls to action where appropriate.

Do not block the core gameplay loop on the full daily route system. The button component can ship with a disabled daily entry point while daily challenge services remain placeholders.

---

## QA Matrix

Verify the following combinations before treating the component as done:

| Area | Cases |
|---|---|
| Device sizes | iPhone SE, standard iPhone, large iPhone |
| Orientation | Portrait only |
| Appearance | Light mode, dark mode preview placeholder |
| Text | Default Dynamic Type, one large accessibility size |
| Interaction | Tap down, tap release, disabled daily route |
| Accessibility | VoiceOver labels, hit target size, Reduce Motion |
| Background | Current `background.png`, plain preview background |

Manual checks:

- [x] Tap each enabled button and confirm coordinator navigation still works.
- [x] Confirm disabled daily route does not announce as an enabled action.
- [x] Confirm pressing a button does not move neighboring buttons.
- [ ] Confirm the stack remains centered and readable on compact widths.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Buttons look too much like native controls | Use custom gradient, highlight, and shadow layers while preserving real `Button` semantics |
| Daily Route implies a feature that is not ready | Render disabled with explicit coming-soon accessibility hint or add a real placeholder route |
| White settings button disappears on bright background | Add cooler stroke, stronger shadow, or a subtle tinted fill |
| Large localized titles break the layout | Use fixed icon gutters, `minimumScaleFactor`, and preview long strings before localization |
| Visual tokens spread across files | Keep all variant values in `TRButtonVariant` or `TRButtonTheme` |
| SpriteKit and SwiftUI styles diverge later | Keep SwiftUI as the source of truth and only bridge tokens if an in-scene button becomes necessary |

---

## Non-Goals

- Do not create PNG button backgrounds.
- Do not create separate image assets for each button state.
- Do not hand-place text into images.
- Do not build dark mode in the first pass unless the surrounding screen already supports it.
- Do not add a broad design system before the concrete menu buttons exist.

---

## Definition of Done

The button architecture is complete when:

- [x] A reusable SwiftUI menu button component exists.
- [x] All four home actions use the component.
- [x] Button backgrounds, highlights, shadows, and pressed states are generated in code.
- [x] The daily route button has an explicit temporary behavior if daily route state is still absent.
- [ ] Previews cover variants and compact layout.
- [x] The app builds.
- [ ] Manual Simulator checks pass on at least one compact and one standard iPhone size.
- [x] VoiceOver labels are correct.
- [x] No static PNG button backgrounds are introduced.

Current verification note:

- `xcodebuild build -project TinyRoutes.xcodeproj -scheme TinyRoutes -destination 'generic/platform=iOS Simulator'` succeeded.
- `xcodebuild test -project TinyRoutes.xcodeproj -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5'` compiled the app and ran tests, but unrelated `LevelRepositoryTests` failures are still present in the repo.

---

## Testing Checklist

- Buttons render sharply on iPhone SE, standard iPhone, and large iPhone sizes.
- Labels do not truncate.
- Icons remain aligned when title length changes.
- Press animation feels responsive and does not shift surrounding layout.
- VoiceOver reads each button correctly.
- Settings white button remains visible on the home background.
- Gradients and shadows do not look muddy in Simulator screenshots.
- Reduce Motion does not leave the buttons feeling unresponsive.
- Disabled Daily Route behavior is clear and intentional.
- No button label is baked into an image asset.

---

## Final Recommendation

Implement the buttons now as a compact SwiftUI component under `TinyRoutes/UI/Components/`. Keep the first pass focused on the home menu. Use SF Symbols for foreground icons, generate every button background in code, and leave Daily Route disabled unless the same story adds a real route through `AppCoordinator`.

This approach gives the game the visual target's soft, polished menu style without adding image-state maintenance, accessibility regressions, or SpriteKit complexity to interface-heavy screens.
