# Tiny Routes — Epics & Features Plan

## Purpose

This document defines the product and engineering backlog for **Tiny Routes**, a minimalist one-thumb iPhone route-puzzle game.

The goal is to organize the app into clear epics, features, priorities, and acceptance criteria so development can proceed in clean, testable slices.

---

## Phase Definitions

| Phase | Purpose |
|---|---|
| **P0 Prototype** | Prove the core mechanic is fun. |
| **P1 MVP** | Build a playable, monetizable first version. |
| **P2 Launch** | Add retention, polish, analytics, and App Store readiness. |
| **P3 Growth** | Add live events, deeper cosmetics, leaderboards, and economy expansion. |

---

# EPIC 01 — App Foundation & Architecture

## Goal

Create a clean, maintainable iPhone app structure that supports gameplay, UI screens, persistence, ads, IAP, analytics, and future expansion.

---

## FEAT-01.01 — Project Setup

**Phase:** P0 Prototype  
**Priority:** Critical

Set up the iOS project with the chosen engine/framework.

Recommended options:

- **SpriteKit** if building native iOS.
- **Godot** if prioritizing cross-platform.
- **SwiftUI + SpriteKit overlay** if using native Apple UI with a custom game scene.

### Acceptance Criteria

- App launches on iPhone simulator.
- Supports portrait orientation.
- Has a basic boot flow.
- Has separate modules/folders for gameplay, UI, data, services, and infrastructure.

---

## FEAT-01.02 — App State Machine

**Phase:** P0 Prototype  
**Priority:** Critical

Create a central app state flow.

### Required States

- Boot
- Main Menu
- Level Select
- Gameplay
- Pause
- Level Complete
- Level Failed
- Shop
- Settings

### Acceptance Criteria

- Screens transition cleanly.
- Gameplay can be started, paused, resumed, restarted, and exited.
- No gameplay logic is embedded directly in menu screens.

---

## FEAT-01.03 — Dependency Structure

**Phase:** P1 MVP  
**Priority:** High

Create clear boundaries between systems.

### Suggested Architecture

```text
TinyRoutes/
  App/
    AppCoordinator
    AppState

  Domain/
    LevelData
    RouteGraph
    RouteNode
    RouteEdge
    PlayerProfile
    CosmeticItem
    ScoreResult

  Gameplay/
    RouteEngine
    DotMovementController
    NodeSwitchController
    CollisionResolver
    LevelRuntimeState

  UI/
    HomeScreen
    GameplayScreen
    LevelSelectScreen
    ShopScreen
    SettingsScreen
    ResultScreen

  Services/
    ProgressService
    EconomyService
    CosmeticService
    DailyChallengeService
    StreakService
    ScoringService

  Infrastructure/
    LevelRepository
    SaveDataRepository
    AnalyticsAdapter
    AdsAdapter
    PurchaseAdapter
```

### Acceptance Criteria

- Domain models do not depend on UI.
- Gameplay engine can be tested without rendering.
- Save/load logic is not mixed into UI.
- Ads and IAP are abstracted behind adapters.

---

# EPIC 02 — Core Route Gameplay Engine

## Goal

Build the core game mechanic: a delivery dot moves along route lines, and the player taps switch nodes to redirect it.

---

## FEAT-02.01 — Level Data Model

**Phase:** P0 Prototype  
**Priority:** Critical

Create the data structure for a level.

### Minimum Fields

- Level ID
- World ID
- Level number
- Time limit
- Par taps
- Start node
- Package node
- Destination node
- Nodes
- Edges
- Initial switch directions

### Acceptance Criteria

- A level can be loaded from local JSON.
- Invalid level data fails gracefully.
- Nodes and edges can be inspected in debug mode.

---

## FEAT-02.02 — Route Graph Engine

**Phase:** P0 Prototype  
**Priority:** Critical

Implement route graph traversal.

### Acceptance Criteria

- Dot can move from node to node.
- Edges define valid connections.
- Current node determines next edge.
- Missing or invalid path causes failure.
- Engine can run independently from visual rendering.

---

## FEAT-02.03 — Delivery Dot Movement

**Phase:** P0 Prototype  
**Priority:** Critical

Create smooth movement along route edges.

### Acceptance Criteria

- Dot moves automatically after level start.
- Dot follows connected route lines.
- Movement speed is configurable per level/world.
- Dot reaches node centers accurately.
- Movement feels smooth at 60 FPS.

---

## FEAT-02.04 — Tap-Rotatable Switch Nodes

**Phase:** P0 Prototype  
**Priority:** Critical

Allow the player to tap nodes to rotate route direction.

### Acceptance Criteria

- Tapping a switch rotates its arrow.
- Direction cycles through valid exits.
- Tap count increments.
- Switch cannot rotate if locked or disabled.
- Visual arrow updates immediately.

---

## FEAT-02.05 — Package Pickup

**Phase:** P0 Prototype  
**Priority:** Critical

Add the required package pickup objective.

### Acceptance Criteria

- Dot collects package when reaching package node.
- Package visually disappears or changes state.
- Destination remains locked until package is collected.
- Reaching destination without package causes failure or redirect, depending on design.

---

## FEAT-02.06 — Destination Completion

**Phase:** P0 Prototype  
**Priority:** Critical

Complete the level when the dot reaches the destination after collecting the package.

### Acceptance Criteria

- Level completes only after package has been collected.
- Completion freezes gameplay.
- Result screen receives time, taps, stars, and reward data.
- Completion animation triggers.

---

## FEAT-02.07 — Failure Conditions

**Phase:** P0 Prototype  
**Priority:** High

Implement basic fail states.

### Failure Types

- Time expired
- Dot reaches dead end
- Dot reaches wrong endpoint
- Dot leaves valid route
- Destination reached without package, if treated as fail

### Acceptance Criteria

- Failure state is clearly shown.
- Player can restart instantly.
- Failure reason can be logged for analytics.

---

# EPIC 03 — Level Content Pipeline

## Goal

Make levels easy to create, test, validate, and expand without hardcoding.

---

## FEAT-03.01 — JSON Level Loader

**Phase:** P0 Prototype  
**Priority:** Critical

Load level files from bundled app content.

### Acceptance Criteria

- App loads levels from local JSON.
- Level files can be grouped by world.
- Bad level files show useful debug errors.
- Game can load at least 30 MVP levels.

---

## FEAT-03.02 — Level Validation Tool

**Phase:** P1 MVP  
**Priority:** High

Create validation rules to catch bad level data.

### Validation Rules

- Start node exists.
- Package node exists.
- Destination node exists.
- All edges reference valid nodes.
- Switch directions map to valid edges.
- Level has at least one possible solution.
- Par taps and time limit are present.

### Acceptance Criteria

- Validation runs during development.
- Invalid levels are reported with readable errors.
- App does not crash from malformed level files.

---

## FEAT-03.03 — Debug Level Viewer

**Phase:** P1 MVP  
**Priority:** Medium

Add a development-only screen for testing levels.

### Acceptance Criteria

- Developer can jump to any level.
- Shows node IDs and edge lines.
- Shows current dot state.
- Shows active switch directions.
- Can restart instantly.

---

## FEAT-03.04 — First 30 MVP Levels

**Phase:** P1 MVP  
**Priority:** Critical

Create the first playable level pack.

### Acceptance Criteria

- 30 handcrafted levels exist.
- Levels introduce mechanics gradually.
- First 10 levels function as tutorial progression.
- Difficulty curve is smooth.
- Every level can be completed with 3 stars.

---

# EPIC 04 — Scoring, Stars & Rewards

## Goal

Give players immediate feedback and reasons to replay levels.

---

## FEAT-04.01 — Timer System

**Phase:** P0 Prototype  
**Priority:** Critical

Add a visible countdown or target-time timer.

### Acceptance Criteria

- Timer starts when level begins.
- Timer pauses with pause menu.
- Timer stops on success/failure.
- Timer affects star rating.

---

## FEAT-04.02 — Tap Count System

**Phase:** P0 Prototype  
**Priority:** Critical

Track player taps during a level.

### Acceptance Criteria

- Each switch tap increments count.
- Taps are shown during gameplay or results.
- Tap count affects star rating.
- Restart resets tap count.

---

## FEAT-04.03 — Star Rating System

**Phase:** P1 MVP  
**Priority:** Critical

Award up to three stars per level.

### Recommended Star Rule

```text
1 star = completed
2 stars = completed under target time
3 stars = completed under target time and under par taps
```

### Acceptance Criteria

- Stars are calculated consistently.
- Best star result is saved.
- Level select shows earned stars.
- Replaying a level can improve stars.

---

## FEAT-04.04 — Coin Reward System

**Phase:** P1 MVP  
**Priority:** High

Award coins based on level performance.

### Acceptance Criteria

- Coins are awarded after completion.
- Reward amount is based on star result.
- Coins are saved to player profile.
- Replaying only grants meaningful rewards according to economy rules.

---

## FEAT-04.05 — Perfect Route Badge

**Phase:** P2 Launch  
**Priority:** Medium

Reward optimal play.

### Perfect Route Requirements

- No hints
- No rewinds
- Under par taps
- Under target time

### Acceptance Criteria

- Perfect completion is detected.
- Badge is shown on result screen.
- Badge appears in level select.
- Perfect completions can feed achievements.

---

# EPIC 05 — Gameplay UI & UX

## Goal

Make the game readable, satisfying, and playable with one thumb.

---

## FEAT-05.01 — Gameplay HUD

**Phase:** P0 Prototype  
**Priority:** Critical

Display core gameplay info.

### HUD Elements

- Level number
- Timer
- Tap count
- Pause button
- Restart button
- Hint button placeholder
- Objective label

### Acceptance Criteria

- HUD does not block gameplay.
- Important information is readable on small iPhones.
- Buttons are thumb-friendly.
- Timer state is obvious.

---

## FEAT-05.02 — Route Board Renderer

**Phase:** P0 Prototype  
**Priority:** Critical

Render the playable route map.

### Acceptance Criteria

- Nodes render clearly.
- Edges render clearly.
- Switch arrows are visible.
- Package and destination are visually distinct.
- Active route state is understandable.

---

## FEAT-05.03 — Success Feedback

**Phase:** P1 MVP  
**Priority:** High

Add cheap but satisfying polish.

### Effects

- Haptic tap feedback
- Completion chime
- Dot glow
- Confetti burst
- Star pop animation
- Coin count animation

### Acceptance Criteria

- Level completion feels rewarding.
- Effects do not require complex art.
- Effects can be disabled or reduced if needed.

---

## FEAT-05.04 — Failure Feedback

**Phase:** P1 MVP  
**Priority:** High

Make failure understandable, not frustrating.

### Acceptance Criteria

- Failure reason is obvious.
- Restart is one tap.
- Rewarded rewind can be offered when available.
- Failure animation is quick.

---

# EPIC 06 — Main Menu & Navigation

## Goal

Create a simple, polished app shell that encourages play, daily challenge participation, and cosmetic engagement.

---

## FEAT-06.01 — Home Screen

**Phase:** P1 MVP  
**Priority:** Critical

Create the primary landing screen.

### Home Screen Elements

- Tiny Routes title
- Play button
- Daily Route button
- Shop button
- Settings button
- Coin counter
- Streak preview
- Small route preview graphic

### Acceptance Criteria

- Player can start the next level quickly.
- Daily Route is visible.
- Coin balance is visible.
- Navigation feels simple.

---

## FEAT-06.02 — Level Select Screen

**Phase:** P1 MVP  
**Priority:** High

Show campaign progression.

### Acceptance Criteria

- Displays available levels.
- Locked levels are shown.
- Completed levels show stars.
- Current level is highlighted.
- Player can replay completed levels.

---

## FEAT-06.03 — Result Screen

**Phase:** P1 MVP  
**Priority:** Critical

Show performance after success/failure.

### Success Result Includes

- Stars
- Time
- Taps
- Coins earned
- Double coins offer
- Next level button
- Replay button

### Failure Result Includes

- Failure reason
- Restart button
- Rewind offer when eligible
- Exit button

### Acceptance Criteria

- Player always has a clear next action.
- Rewarded ad offers are optional.
- Restart and next level are fast.

---

# EPIC 07 — Progression System

## Goal

Give players a reason to continue beyond individual levels.

---

## FEAT-07.01 — Player Save Profile

**Phase:** P1 MVP  
**Priority:** Critical

Persist player progress locally.

### Saved Data

- Completed levels
- Best stars per level
- Coin balance
- Equipped cosmetics
- Owned cosmetics
- Daily streak
- Settings
- Ad removal purchase state

### Acceptance Criteria

- Progress persists after app restart.
- Save data can be versioned.
- Missing save data creates a new profile.
- Corrupt save data does not crash the app.

---

## FEAT-07.02 — Level Unlocking

**Phase:** P1 MVP  
**Priority:** High

Unlock levels sequentially.

### Acceptance Criteria

- Completing a level unlocks the next.
- Previously completed levels remain replayable.
- Locked levels cannot be started.
- Debug mode can override locks.

---

## FEAT-07.03 — World Unlocking

**Phase:** P2 Launch  
**Priority:** Medium

Organize levels into worlds.

### Suggested Worlds

- Suburbs
- Downtown
- Train Lines
- Night Shift
- Circuit City

### Acceptance Criteria

- Worlds can be locked/unlocked.
- Each world has a theme.
- Level select supports grouped levels.

---

## FEAT-07.04 — Milestone Rewards

**Phase:** P2 Launch  
**Priority:** Medium

Reward player progress.

### Example Milestones

- Complete 10 levels
- Complete 25 levels
- Complete 50 levels
- Earn 100 stars
- Perfect 10 levels

### Acceptance Criteria

- Milestones are tracked.
- Rewards can grant coins or cosmetics.
- Claimed rewards are saved.

---

# EPIC 08 — Daily Route & Streaks

## Goal

Create daily retention and a reason to reopen the app.

---

## FEAT-08.01 — Daily Route Generator/Selector

**Phase:** P2 Launch  
**Priority:** High

Provide one daily challenge per day.

### MVP Implementation

Select a daily level from a curated pool using date-based rotation.

### Acceptance Criteria

- Same daily route appears for all players on the same date.
- Daily route changes once per day.
- Player can see whether today's daily has been completed.
- Daily route does not depend on a server for MVP.

---

## FEAT-08.02 — Daily Route Result

**Phase:** P2 Launch  
**Priority:** High

Show daily-specific performance.

### Tracked Stats

- Completion time
- Tap count
- Hints used
- Rewinds used
- Stars
- Reward earned

### Acceptance Criteria

- Daily result is separate from campaign result.
- Result can update streak.
- Result can grant daily reward.

---

## FEAT-08.03 — Streak System

**Phase:** P2 Launch  
**Priority:** High

Track consecutive daily completions.

### Acceptance Criteria

- Completing daily route increments streak.
- Missing a day resets streak or freezes it if a future streak-freeze feature exists.
- Streak rewards trigger at milestones.
- Streak is visible on home screen.

---

## FEAT-08.04 — Shareable Daily Result Card

**Phase:** P3 Growth  
**Priority:** Low

Generate a share card for social sharing.

### Acceptance Criteria

- Card shows date, result, stars, taps, and time.
- No solution is spoiled.
- Uses clean Tiny Routes branding.

---

# EPIC 09 — Hints, Rewinds & Convenience Systems

## Goal

Support monetization and reduce frustration without making the game pay-to-win.

---

## FEAT-09.01 — Hint System

**Phase:** P2 Launch  
**Priority:** High

Reveal helpful information when the player is stuck.

### Hint Options

- Highlight the next correct switch.
- Show the first route segment.
- Temporarily preview the intended path.

### Acceptance Criteria

- Hint can be triggered from gameplay.
- Hint usage is tracked.
- Hint affects perfect-route status.
- Hint can be granted through coins or rewarded ad.

---

## FEAT-09.02 — Rewind Revive

**Phase:** P1 MVP  
**Priority:** High

After failure, allow player to rewind a few seconds.

### Acceptance Criteria

- Rewind restores dot position to recent valid state.
- Switch states are restored.
- Timer is restored or partially penalized.
- Rewind can be offered through rewarded ad.
- Rewind usage is tracked.

---

## FEAT-09.03 — Instant Restart

**Phase:** P0 Prototype  
**Priority:** Critical

Let players retry immediately.

### Acceptance Criteria

- Restart resets level state.
- Restart has minimal loading delay.
- Restart does not return to menu.
- Restart is available from pause, failure, and gameplay HUD.

---

# EPIC 10 — Cosmetic System

## Goal

Create a low-art-cost monetization and progression system.

---

## FEAT-10.01 — Cosmetic Inventory Model

**Phase:** P1 MVP  
**Priority:** High

Support unlockable cosmetic items.

### Categories

- Route themes
- Delivery dots
- Trails
- Destinations
- Confetti effects

### Acceptance Criteria

- Cosmetics have ID, name, category, rarity, unlock state, and price.
- Owned cosmetics are saved.
- Equipped cosmetics affect gameplay visuals.
- Default cosmetics are always available.

---

## FEAT-10.02 — Route Themes

**Phase:** P1 MVP  
**Priority:** High

Allow route board color/style changes.

### MVP Themes

- Classic
- Ocean Drive
- Sunset
- Neon

### Acceptance Criteria

- Theme changes route line colors, node colors, and background accents.
- Theme does not affect gameplay.
- Theme can be previewed.

---

## FEAT-10.03 — Delivery Dot Skins

**Phase:** P2 Launch  
**Priority:** Medium

Change the player marker.

### Examples

- Blue dot
- Gold dot
- Paper airplane
- Tiny truck
- UFO
- Bubble

### Acceptance Criteria

- Equipped skin appears during gameplay.
- Skin works with existing movement logic.
- Skin does not require unique animation logic.

---

## FEAT-10.04 — Trail Effects

**Phase:** P1 MVP  
**Priority:** Medium

Add simple trail visuals.

### Examples

- Dots
- Sparkles
- Glow
- Bubbles
- Stars
- Leaves

### Acceptance Criteria

- Trail follows dot.
- Trail can be changed from inventory/shop.
- Trail does not cause performance issues.

---

## FEAT-10.05 — Cosmetic Shop Screen

**Phase:** P2 Launch  
**Priority:** High

Let players browse, buy, preview, and equip cosmetics.

### Acceptance Criteria

- Shows owned and locked cosmetics.
- Player can buy with coins.
- Player can equip owned cosmetics.
- Featured items can be highlighted.
- Purchase state persists.

---

# EPIC 11 — Economy

## Goal

Create a simple, controlled economy around coins, rewards, and cosmetics.

---

## FEAT-11.01 — Coin Wallet

**Phase:** P1 MVP  
**Priority:** Critical

Track soft currency.

### Acceptance Criteria

- Coins can be earned.
- Coins can be spent.
- Coin balance persists.
- Negative balances are impossible.

---

## FEAT-11.02 — Reward Rules

**Phase:** P1 MVP  
**Priority:** High

Centralize reward logic.

### Reward Sources

- Level completion
- Star performance
- Perfect route
- Daily challenge
- Streak milestones
- Rewarded ads
- Bonus chests

### Acceptance Criteria

- Reward logic is not duplicated across UI.
- Rewards are logged for analytics.
- Rewards can be tuned through config.

---

## FEAT-11.03 — Bonus Chest

**Phase:** P3 Growth  
**Priority:** Medium

Occasionally offer a bonus reward.

### Acceptance Criteria

- Chest can grant coins or cosmetics.
- Chest can be opened through gameplay progress or rewarded ad.
- Chest odds are configurable.
- Duplicate cosmetic handling exists.

---

# EPIC 12 — Ads

## Goal

Add monetization without damaging retention.

---

## FEAT-12.01 — Rewarded Ad Adapter

**Phase:** P1 MVP  
**Priority:** Critical

Abstract rewarded ads behind a service.

### Rewarded Placements

- Rewind after fail
- Double coins
- Hint
- Daily retry
- Bonus chest

### Acceptance Criteria

- Game logic does not directly depend on ad SDK.
- Reward is granted only after successful ad completion.
- Cancelled ads do not grant rewards.
- Ad unavailable state is handled gracefully.

---

## FEAT-12.02 — Rewarded Rewind Placement

**Phase:** P1 MVP  
**Priority:** High

Offer rewind after failure.

### Acceptance Criteria

- Player can choose restart or watch ad to rewind.
- Offer is not shown when ad is unavailable.
- Rewind reward applies correctly.
- Analytics track offer, start, complete, and cancel.

---

## FEAT-12.03 — Double Coins Placement

**Phase:** P1 MVP  
**Priority:** High

Offer double coins after level completion.

### Acceptance Criteria

- Player sees base reward first.
- Watching ad doubles eligible coins.
- Reward is granted once.
- Offer does not block normal progression.

---

## FEAT-12.04 — Interstitial Ad Rules

**Phase:** P2 Launch  
**Priority:** Medium

Add carefully controlled forced ads.

### Rules

- No interstitial before level 6 or 8.
- No ad after every level.
- No ad during tutorial.
- No ad after very short failure.
- No ad immediately after rewarded ad.
- No ad on daily result screen.

### Acceptance Criteria

- Frequency rules are centralized.
- Interstitials respect cooldown.
- Remove Ads disables forced interstitials.
- Interstitial events are tracked.

---

# EPIC 13 — In-App Purchases

## Goal

Support small purchases without overcomplicating the MVP.

---

## FEAT-13.01 — Purchase Adapter

**Phase:** P1 MVP  
**Priority:** Critical

Abstract StoreKit purchases.

### Acceptance Criteria

- Product loading is centralized.
- Purchases can be restored.
- Purchase results are handled safely.
- App does not crash when store is unavailable.

---

## FEAT-13.02 — Remove Ads Purchase

**Phase:** P1 MVP  
**Priority:** Critical

Sell forced-ad removal.

### Acceptance Criteria

- Purchase disables interstitial ads.
- Rewarded ads remain optional.
- Purchase state persists.
- Restore purchases works.

---

## FEAT-13.03 — Starter Pack

**Phase:** P2 Launch  
**Priority:** Medium

Offer a small-value first purchase.

### Potential Contents

- Coin bundle
- Exclusive dot
- Exclusive trail
- Exclusive route theme
- Optional ad-free benefit

### Acceptance Criteria

- Starter pack can be purchased once.
- Contents are granted correctly.
- Owned items are not duplicated incorrectly.

---

## FEAT-13.04 — Coin Packs

**Phase:** P3 Growth  
**Priority:** Low

Sell optional coin bundles.

### Acceptance Criteria

- Coin products are available.
- Coins are granted after purchase.
- Purchases are logged.
- Refund/failed purchase states are handled.

---

# EPIC 14 — Analytics & Telemetry

## Goal

Track whether the game is fun, understandable, replayable, and monetizable.

---

## FEAT-14.01 — Analytics Adapter

**Phase:** P1 MVP  
**Priority:** Critical

Create a wrapper around analytics SDK.

### Acceptance Criteria

- Events can be logged from all systems.
- Analytics SDK is not directly referenced everywhere.
- Debug logging can be enabled.
- Missing analytics SDK does not break gameplay.

---

## FEAT-14.02 — Onboarding Events

**Phase:** P1 MVP  
**Priority:** High

Track tutorial funnel.

### Events

```text
tutorial_started
tutorial_completed
tutorial_failed
tutorial_skipped
```

### Acceptance Criteria

- Events include level ID where relevant.
- Events include session number if available.

---

## FEAT-14.03 — Level Events

**Phase:** P1 MVP  
**Priority:** High

Track gameplay performance.

### Events

```text
level_started
level_completed
level_failed
level_restarted
level_quit
level_hint_used
level_rewind_used
```

### Useful Parameters

- Level ID
- Attempt number
- Time elapsed
- Tap count
- Stars
- Failure reason

### Acceptance Criteria

- Every level attempt has start and end tracking.
- Failure reasons are consistent.
- Replay behavior can be measured.

---

## FEAT-14.04 — Monetization Events

**Phase:** P1 MVP  
**Priority:** High

Track ads and purchases.

### Events

```text
rewarded_ad_offered
rewarded_ad_started
rewarded_ad_completed
rewarded_ad_cancelled
interstitial_shown
purchase_started
purchase_completed
purchase_failed
remove_ads_purchased
```

### Acceptance Criteria

- Every ad placement includes placement ID.
- Purchase events include product ID.
- Reward grant is traceable.

---

## FEAT-14.05 — Retention Events

**Phase:** P2 Launch  
**Priority:** High

Track daily systems.

### Events

```text
daily_route_started
daily_route_completed
daily_route_failed
streak_incremented
streak_lost
daily_reward_claimed
```

### Acceptance Criteria

- Daily participation can be measured.
- Streak retention can be measured.
- Daily reward engagement can be measured.

---

# EPIC 15 — Tutorial & Onboarding

## Goal

Teach the route-switching mechanic in under 30 seconds.

---

## FEAT-15.01 — First-Time Tutorial Flow

**Phase:** P1 MVP  
**Priority:** Critical

Use the first few levels as tutorial.

### Acceptance Criteria

- Level 1 teaches destination.
- Level 2 teaches switch tapping.
- Level 3 teaches wrong route/failure.
- Level 4 teaches package pickup.
- Tutorial text is minimal.
- Player can understand without reading long instructions.

---

## FEAT-15.02 — Contextual Hand Pointer

**Phase:** P1 MVP  
**Priority:** Medium

Show simple tap guidance.

### Acceptance Criteria

- Hand pointer appears only when needed.
- It highlights the correct switch.
- It disappears after player interaction.
- It does not appear in later levels unless help is needed.

---

## FEAT-15.03 — Objective Labels

**Phase:** P1 MVP  
**Priority:** Medium

Show simple objectives.

### Example Labels

```text
Deliver the package
Pick up the package first
Tap the switch before the dot arrives
Reach the house
```

### Acceptance Criteria

- Objective updates by level mechanic.
- Text is short and readable.
- Objective does not block gameplay.

---

# EPIC 16 — Settings, Accessibility & Compliance

## Goal

Make the app usable, safe, and App Store-ready.

---

## FEAT-16.01 — Settings Screen

**Phase:** P1 MVP  
**Priority:** Medium

Create a basic settings screen.

### Settings

- Sound on/off
- Music on/off
- Haptics on/off
- Restore purchases
- Privacy policy
- Terms
- Credits

### Acceptance Criteria

- Settings persist.
- Restore purchases is accessible.
- Legal links are available before launch.

---

## FEAT-16.02 — Accessibility Basics

**Phase:** P2 Launch  
**Priority:** Medium

Support readable and accessible gameplay.

### Acceptance Criteria

- Important UI has readable contrast.
- Buttons have large tap targets.
- Game does not rely only on color.
- Colorblind-friendly route themes are considered.
- Haptics and sound can be disabled.

---

## FEAT-16.03 — Privacy & Tracking Compliance

**Phase:** P2 Launch  
**Priority:** Critical

Prepare for App Store review.

### Acceptance Criteria

- Privacy policy exists.
- Analytics and ad SDK usage is documented.
- App Tracking Transparency flow is implemented if needed.
- Purchases comply with StoreKit rules.

---

# EPIC 17 — Polish & Game Feel

## Goal

Make a simple game feel premium without increasing art burden.

---

## FEAT-17.01 — Haptics

**Phase:** P1 MVP  
**Priority:** High

Use subtle haptics for key moments.

### Haptic Moments

- Switch tap
- Package pickup
- Failure
- Level complete
- Star reward

### Acceptance Criteria

- Haptics feel responsive.
- Haptics respect settings.
- Haptics do not fire excessively.

---

## FEAT-17.02 — Audio Feedback

**Phase:** P2 Launch  
**Priority:** Medium

Add lightweight sound effects.

### Sounds

- Tap
- Switch rotate
- Package pickup
- Destination unlock
- Completion chime
- Failure sound
- Coin reward

### Acceptance Criteria

- Sounds are short and soft.
- Audio respects settings.
- No sound is annoying when repeated.

---

## FEAT-17.03 — Motion & Animation Pass

**Phase:** P2 Launch  
**Priority:** High

Add small animations.

### Animations

- Button press bounce
- Dot glow pulse
- Package pickup pop
- Destination glow
- Star reveal
- Coin count increase
- Confetti burst

### Acceptance Criteria

- Animations improve feel without slowing the game.
- No complex sprite sheets are required.
- Animations run smoothly on older iPhones.

---

# Recommended MVP Backlog

The first real build should focus only on proving the core experience and enabling light monetization.

```text
P0 Prototype
- Project setup
- App state machine
- Level data model
- Route graph engine
- Dot movement
- Switch nodes
- Package pickup
- Destination completion
- Failure conditions
- Gameplay HUD
- Instant restart
- 10 test levels

P1 MVP
- 30 handcrafted levels
- JSON level loader
- Level validation
- Home screen
- Level select
- Result screen
- Timer
- Tap count
- Star rating
- Coin wallet
- Local save profile
- Cosmetic inventory basics
- 4 route themes
- 6 trails
- Rewarded rewind ad
- Double coins ad
- Remove Ads IAP
- Analytics adapter
- Tutorial flow
- Settings screen
```

---

# Recommended Launch Backlog

Version 1.0 should include the systems that make the game retain users and feel complete.

```text
P2 Launch
- 100 levels
- Daily Route
- Streak system
- Cosmetic shop
- Starter Pack
- Hint system
- Interstitial ad rules
- Milestone rewards
- World structure
- Better onboarding
- Audio pass
- Animation polish
- Accessibility basics
- Privacy/compliance setup
- App Store screenshots
```

---

# Suggested GitHub Labels

```text
epic:architecture
epic:gameplay-engine
epic:level-content
epic:scoring
epic:ui-ux
epic:progression
epic:daily-route
epic:economy
epic:cosmetics
epic:ads
epic:iap
epic:analytics
epic:onboarding
epic:polish
epic:compliance

phase:p0-prototype
phase:p1-mvp
phase:p2-launch
phase:p3-growth

priority:critical
priority:high
priority:medium
priority:low
```

---

# Highest-Risk Features

These are the features that should be validated first because they determine whether the game is worth building.

1. **Route switching feel**  
   Tapping must feel instant and readable.

2. **Level readability**  
   Players must understand why the dot went where it went.

3. **Failure/retry loop**  
   Failing should feel like “one more try,” not frustration.

4. **Level variety**  
   The game cannot feel like the same puzzle repeated.

5. **Daily Route retention**  
   This is likely the strongest long-term hook.

6. **Cosmetic value**  
   Cosmetics need to feel visible enough to care about.

---

# Technical Recommendation

Build the core engine so that gameplay can run from pure data.

```text
LevelData -> RouteGraph -> RuntimeState -> Renderer
```

Do **not** hardcode levels directly into the scene.

This gives the project:

- Easier level creation
- Easier testing
- Easier daily challenge rotation
- Easier future procedural generation
- Cleaner agent/vibe-coding workflow
- Better ability to validate content before shipping

---

# First Engineering Milestone

The first major engineering milestone should be:

> Load one JSON level, render the route graph, move the dot, tap a switch, collect a package, reach the house, and show a result screen.

This proves the essential game loop before building monetization, progression, cosmetics, or daily challenges.

---

# Suggested Issue Creation Order

Use this order to create early GitHub issues.

1. `FEAT-01.01 — Project Setup`
2. `FEAT-01.02 — App State Machine`
3. `FEAT-02.01 — Level Data Model`
4. `FEAT-03.01 — JSON Level Loader`
5. `FEAT-02.02 — Route Graph Engine`
6. `FEAT-05.02 — Route Board Renderer`
7. `FEAT-02.03 — Delivery Dot Movement`
8. `FEAT-02.04 — Tap-Rotatable Switch Nodes`
9. `FEAT-02.05 — Package Pickup`
10. `FEAT-02.06 — Destination Completion`
11. `FEAT-02.07 — Failure Conditions`
12. `FEAT-09.03 — Instant Restart`
13. `FEAT-04.01 — Timer System`
14. `FEAT-04.02 — Tap Count System`
15. `FEAT-04.03 — Star Rating System`
16. `FEAT-06.03 — Result Screen`
17. `FEAT-03.04 — First 30 MVP Levels`

---

# MVP Definition of Done

The MVP is done when the following are true:

- A new player can open the app and understand the game within the first few levels.
- At least 30 levels are playable.
- The route-switching mechanic feels responsive.
- The dot movement is smooth and readable.
- Package pickup and destination completion work consistently.
- The player can fail, restart, and replay quickly.
- Stars, taps, timer, and coins are tracked.
- Player progress saves locally.
- Cosmetics have a working foundation.
- Rewarded rewind and double-coins ad hooks exist.
- Remove Ads purchase exists.
- Basic analytics events are implemented.
- The game is stable enough for small playtesting.

