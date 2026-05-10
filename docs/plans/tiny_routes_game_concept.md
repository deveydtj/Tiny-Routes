# Tiny Routes — iPhone Game Concept & Product Plan

## Executive Summary

**Tiny Routes** is a minimalist one-thumb route puzzle game for iPhone. Players guide a tiny delivery dot through compact route-map puzzles by tapping intersections, rotating direction arrows, collecting packages, and reaching the destination before time runs out.

The game is designed to be simple enough for a solo developer or vibe-coded prototype while still having enough progression, replayability, and monetization structure to support ad revenue and small in-app purchases.

The core design goal is:

> Simple gameplay, minimal art burden, strong retention hooks, and clean hybrid monetization.

---

## Final Recommended Name

# Tiny Routes

### Subtitle

**One-tap delivery puzzles**

### Why Tiny Routes is stronger than Route Rush

**Tiny Routes** is the better name for this concept because it feels more ownable, cozy, and puzzle-oriented.

It communicates:

- Bite-sized puzzle levels
- Route-based gameplay
- A clean minimalist art direction
- Daily challenge potential
- A broader casual audience

**Route Rush** is still usable, but it sounds more generic and arcade-heavy. It implies speed, pressure, and endless-runner style gameplay. That is not wrong, but it does not fit the broader casual-puzzle positioning as well as Tiny Routes.

Use **Tiny Routes** unless the game pivots heavily toward timed arcade play.

---

## One-Sentence Pitch

**Tiny Routes is a one-thumb minimalist puzzle game where players redirect a moving delivery dot through tiny map-like mazes before time runs out.**

---

## Core Concept

Each level is a small abstract city-map puzzle.

A glowing delivery dot automatically moves along connected route lines. The player taps intersections to rotate arrows, switches, or gates so the dot reaches the correct destination.

The player does not directly move the dot.  
The player controls the route.

---

## Core Gameplay Rule

1. A delivery dot starts moving automatically.
2. The map contains route lines and tap-controlled intersections.
3. The player taps switch nodes to rotate or change their direction.
4. The dot follows the direction of the active node when it reaches that point.
5. The player must collect the package and reach the destination.
6. The level is completed when the delivery reaches the house.
7. Performance is rated based on time, taps, hints, and mistakes.

---

## Why This Concept Works

Most low-effort mobile games fall into heavily saturated categories:

- Endless runners
- Stackers
- Merge games
- Idle clickers
- Generic block puzzles
- Obstacle-avoidance games

**Tiny Routes** has a clearer visual identity and gameplay hook:

> Can you fix the route before the delivery dot gets there?

This creates light pressure, fast retries, and satisfying puzzle-solving without requiring complex art, animation, or characters.

---

## Target Genre

**Hybrid-casual puzzle game**

This is not a pure hypercasual game. The goal is to combine:

- Simple controls
- Short sessions
- Fast retries
- Daily challenges
- Progression
- Cosmetic unlocks
- Rewarded ads
- Light in-app purchases

This gives the game better long-term monetization potential than a disposable hypercasual tap game.

---

## Target Audience

Primary audience:

- Casual puzzle players
- People who like short mobile sessions
- Players who enjoy daily challenge games
- Players who like clean, relaxing UI
- Players who enjoy progression and cosmetic unlocks

Secondary audience:

- Completionists
- Streak-driven players
- Players who like timing puzzles
- Players who enjoy simple logic games

---

## Visual Direction

The art should be intentionally minimal.

The game should be built using simple vector-style elements:

- Rounded route lines
- Circular nodes
- Arrow icons
- Package icons
- House icons
- Coin icons
- Soft gradient backgrounds
- Rounded UI cards
- Simple particle trails
- Confetti bursts
- Map-inspired backgrounds

No characters are required.

No frame-by-frame animation is required.

No detailed environments are required.

No complex sprite sheets are required.

---

## Visual Style Keywords

- Minimalist
- Clean
- Soft
- Friendly
- Rounded
- App Store-ready
- Pastel blue and teal
- Light city-map aesthetic
- Calm but satisfying
- Low-art-production vector style

---

## Suggested Color Palette

### Primary Colors

- Bright blue for active UI and player dot
- Deep navy for title text and important labels
- Teal/green for positive actions and daily route elements
- Soft white for cards and buttons
- Pale blue for backgrounds

### Accent Colors

- Warm yellow/orange for coins, packages, destinations, streaks, and rewards
- Purple for premium/shop accents
- Light gray for locked or inactive states

---

## Core Screen Concepts

The generated concept images should be treated as reference only. The final UI can be simpler.

### 1. Home / Main Menu

Purpose:

- Introduce the brand
- Show the core route mechanic visually
- Push the player toward Play or Daily Route

Elements:

- Title: **Tiny Routes**
- Subtitle: **One-tap delivery puzzles**
- Coin counter
- Small settings button
- Central gameplay preview
- Streak card
- Daily challenge card
- Main buttons:
  - Play
  - Daily Route
  - Shop
  - Settings
- Bottom navigation:
  - Home
  - Levels
  - Shop
  - Profile

### 2. Gameplay Screen

Purpose:

- Let the player focus on solving a single route puzzle

Elements:

- Level number
- Star rating preview
- Objective label: **Deliver the package**
- Timer
- Route puzzle board
- Moving blue delivery dot
- Package pickup
- Destination house
- Tap-rotatable arrow switches
- Hint button
- Pause button
- Restart button
- Optional skip button

### 3. Levels / Daily Route Screen

Purpose:

- Show progression and encourage daily retention

Elements:

- Daily Route feature card
- Countdown to next daily challenge
- Streak progress
- Level map/grid
- Completed levels with checkmarks
- Star ratings
- Locked future levels
- Current highlighted level
- Milestone rewards
- Achievement progress card

### 4. Shop / Customization Screen

Purpose:

- Monetize through cosmetics and convenience purchases

Elements:

- Featured purchase cards
- Starter Pack
- Remove Ads
- Cosmetic category tabs:
  - Route Themes
  - Delivery Dots
  - Trails
  - Confetti
  - Destinations
- Cosmetic preview panel
- Unlockable theme grid
- Coin and premium currency options
- Daily bonus claim

---

## Gameplay Mechanics

Start with only a few mechanics. Add complexity gradually.

### Basic Mechanics

#### Rotating Arrow Node

The player taps a node to rotate the arrow direction.

Example directions:

- Up
- Right
- Down
- Left

#### One-Way Path

Some routes only allow travel in one direction.

#### Package Pickup

The delivery dot must collect a package before the destination opens.

#### Destination

The house is the goal. It should glow once the package has been collected.

#### Timer

Each level has a target time. Finishing faster gives better rewards.

#### Tap Count

The game tracks how many times the player taps switches. Fewer taps can improve the score.

#### Stars

Each level can award up to three stars.

Potential criteria:

- Complete the level
- Finish under target time
- Use fewer than the par number of taps

---

## Mechanics to Add Later

### Locked Gates

A route is blocked until the player collects a key or package.

### Timed Gates

A gate opens and closes on a repeating timer.

### Split Routes

The delivery dot can choose between branching paths.

### Color Routes

The dot can only travel through matching colored paths after collecting a color token.

### Fog Preview

The player sees the full route briefly, then part of it fades.

### Multi-Package Levels

The player must collect two or more packages before reaching the destination.

### Rewind Revive

After failure, the player can rewind a few seconds and continue.

This is useful for rewarded ads.

---

## Mechanics to Avoid Early

Avoid these for the MVP:

- Physics
- Real-time enemies
- Complex character animation
- Multiplayer
- 3D rendering
- User-generated levels
- Advanced pathfinding AI
- Large animated environments
- Complicated economy systems

These add development cost without proving the game is fun.

---

## Core Game Loop

### 10-Second Loop

1. Start level.
2. Watch the delivery dot move.
3. Tap intersections to redirect it.
4. Deliver successfully or fail.
5. Retry instantly.

### 2-Minute Loop

1. Complete several levels.
2. Earn coins.
3. Unlock or preview cosmetics.
4. Watch rewarded ad for bonus coins, hint, or revive.
5. Continue to next level.

### Daily Loop

1. Open Daily Route.
2. Complete the shared daily puzzle.
3. Maintain streak.
4. Earn coins or cosmetic progress.
5. Return tomorrow.

### Long-Term Loop

1. Unlock new worlds.
2. Complete level packs.
3. Collect route themes, dot skins, trails, and destination icons.
4. Perfect old levels.
5. Build streaks.
6. Complete milestone rewards.

---

## Game Modes

### Main Levels

The standard campaign mode.

- Handcrafted levels
- Gradual difficulty curve
- New mechanics introduced over time
- Stars and milestone rewards

### Daily Route

One shared challenge per day.

Scoring can be based on:

- Completion time
- Number of taps
- Number of hints used
- Number of rewinds used

Daily Route should be one of the most important retention features.

### Chill Mode

Optional no-pressure version.

- No hard timer
- Lower rewards
- Good for casual players

### Rush Mode

Timer-focused version.

- Higher rewards
- Better leaderboard score
- Better ad engagement opportunities

---

## World Structure

Each world introduces one new mechanic or visual theme.

### World 1: Suburbs

Purpose:

- Teach basic arrow switches
- Introduce package and destination
- Low pressure

### World 2: Downtown

Purpose:

- Faster routes
- More intersections
- Package pickup before delivery

### World 3: Train Lines

Purpose:

- One-way paths
- Switch tracks

### World 4: Night Shift

Purpose:

- Partial route visibility
- Memory and planning

### World 5: Circuit City

Purpose:

- Timed gates
- Red/green blockers
- More advanced routing

---

## Monetization Strategy

Use hybrid monetization:

1. Rewarded ads
2. Light interstitial ads
3. Cosmetic purchases
4. No-ads purchase
5. Starter pack

The monetization should feel optional, not punishing.

---

## Rewarded Ads

Rewarded ads should be the main ad format.

Good rewarded ad placements:

### Revive / Rewind

After failing:

> Watch an ad to rewind 3 seconds and keep going.

This fits the game naturally because failure often happens from one wrong tap.

### Double Coins

After completing a level pack:

> Watch an ad to double your coins.

### Hint

During a level:

> Watch an ad to reveal the first correct switch.

### Daily Challenge Retry

After failing or getting a poor score:

> Watch an ad for one extra Daily Route attempt.

### Bonus Chest

After several completed levels:

> Watch an ad to open a bonus cosmetic chest.

---

## Interstitial Ads

Use interstitial ads carefully.

Suggested rules:

- Do not show interstitials before level 6 or 8.
- Do not show one after every level.
- Show one every 3 to 5 completed or failed levels.
- Never show one immediately after a very short failed attempt.
- Never interrupt the Daily Route result screen.
- Never interrupt streak claim moments.
- Never interrupt the tutorial.

Bad ad timing will hurt retention.

---

## In-App Purchases

### Remove Ads

Suggested price:

- $3.99 or $4.99

Removes forced interstitial ads.

Rewarded ads remain optional.

### Starter Pack

Suggested price:

- $1.99 or $2.99

Includes:

- Remove forced ads or temporary ad-free period
- Coin bundle
- Exclusive delivery dot
- Exclusive trail
- Exclusive route theme

### Coin Packs

Coins should only be used for cosmetics and convenience.

Suggested packs:

- $0.99 small coin pack
- $2.99 medium coin pack
- $6.99 large coin pack

### Premium Currency

Optional. Avoid adding this unless the game has traction.

If used, premium currency should unlock:

- Premium themes
- Special trails
- Limited-time cosmetics
- Event items

### Season Pass

Do not build this for the MVP.

Add only if the game has proven retention.

Potential contents:

- 30-day cosmetic route pass
- Exclusive themes
- Exclusive trails
- Daily challenge bonuses
- Bonus reward track

---

## Cosmetic System

Cosmetics should be cheap to create and easy to expand.

### Cosmetic Categories

#### Route Themes

Changes the color and style of route lines and nodes.

Examples:

- Classic
- Ocean Drive
- Forest Path
- Sunset Boulevard
- Neon Nights
- Candy Lane
- Blueprint
- Circuit Board
- Snow Day
- Cozy Autumn

#### Delivery Dots

Changes the moving player marker.

Examples:

- Blue dot
- Gold dot
- Paper airplane
- Tiny truck
- UFO
- Ladybug
- Bubble
- Spark

#### Trails

Changes the motion trail behind the delivery dot.

Examples:

- Dots
- Sparkles
- Neon glow
- Bubbles
- Stars
- Leaves
- Snowflakes
- Confetti

#### Destinations

Changes the goal icon.

Examples:

- House
- Cabin
- Pizza shop
- Mailbox
- Castle
- Treehouse
- Space station
- Beach hut

#### Confetti Effects

Changes the success animation.

Examples:

- Stars
- Coins
- Paper confetti
- Sparkles
- Mini packages
- Fireworks burst

---

## Retention Hooks

### Daily Route

A shared daily challenge gives players a reason to return.

Daily Route should include:

- Countdown timer
- Streak tracking
- Daily reward
- Optional leaderboard
- Shareable result card

### Streaks

Reward streaks at:

- 3 days
- 7 days
- 14 days
- 30 days

Rewards:

- Coins
- Cosmetic chest
- Trail unlock
- Route theme unlock

### Perfect Route Badge

A level is perfected when the player completes it with:

- No hints
- No rewinds
- Under par taps
- Under target time

This gives completionists a reason to replay.

### Milestone Rewards

Examples:

- Complete 10 levels: coin reward
- Complete 25 levels: cosmetic chest
- Complete 50 levels: premium cosmetic
- Complete 75 levels: rare theme

### Achievement Cards

Examples:

- Star Collector
- Perfect Planner
- No Hint Hero
- Daily Driver
- Route Master

---

## MVP Scope

The MVP should prove whether the core game is fun and whether users replay levels.

### Version 0.1

Build:

- 30 handcrafted levels
- Basic route map
- Rotating arrow nodes
- Package pickup
- Destination house
- Timer
- Tap count
- Three-star rating
- Coin reward
- Basic home screen
- Basic gameplay screen
- Basic level select screen
- One rewarded ad placement: revive
- One rewarded ad placement: double coins
- One IAP: remove ads
- 4 route themes
- 6 trails

Do not build:

- Season pass
- Leaderboards
- Complex shop
- Multiplayer
- Procedural level generation
- User accounts
- Premium currency

### Version 0.2

Add:

- Daily Route system
- Streak rewards
- Cosmetic shop
- More levels
- More themes
- Better tutorial
- Analytics events
- Hint system
- Better success animations

### Version 1.0

Launch target:

- 100 levels
- Daily Route
- Streaks
- Rewarded ads
- Tuned interstitial ads
- Remove Ads IAP
- Starter Pack IAP
- Cosmetic shop
- Level milestones
- Polished onboarding
- App Store screenshots
- Analytics dashboard

---

## Suggested File/Code Architecture

This can vary by engine, but the game should be structured around simple systems.

### Suggested Systems

```text
Game/
  Core/
    LevelData
    RouteGraph
    RouteNode
    RouteEdge
    DeliveryDot
    LevelState
    ScoringSystem

  UI/
    HomeScreen
    GameplayScreen
    LevelSelectScreen
    ShopScreen
    ProfileScreen
    SettingsScreen

  Economy/
    CoinWallet
    RewardSystem
    CosmeticInventory
    PurchaseManager

  Ads/
    RewardedAdManager
    InterstitialAdManager
    AdPlacementRules

  Daily/
    DailyChallengeManager
    StreakManager
    DailyScore

  Content/
    LevelPacks
    Themes
    Cosmetics
```

---

## Suggested Level Data Format

Levels can be stored as JSON.

Example:

```json
{
  "id": "world1_level001",
  "world": 1,
  "levelNumber": 1,
  "timeLimitSeconds": 45,
  "parTaps": 6,
  "startNodeId": "A",
  "packageNodeId": "C",
  "destinationNodeId": "F",
  "nodes": [
    {
      "id": "A",
      "x": 0.1,
      "y": 0.6,
      "type": "start"
    },
    {
      "id": "B",
      "x": 0.4,
      "y": 0.6,
      "type": "switch",
      "directions": ["up", "right", "down"],
      "initialDirection": "right"
    },
    {
      "id": "C",
      "x": 0.2,
      "y": 0.3,
      "type": "package"
    },
    {
      "id": "F",
      "x": 0.8,
      "y": 0.6,
      "type": "destination"
    }
  ],
  "edges": [
    {
      "from": "A",
      "to": "B"
    },
    {
      "from": "B",
      "to": "C"
    },
    {
      "from": "B",
      "to": "F"
    }
  ]
}
```

---

## Scoring System

A simple scoring system is enough.

### Star Rules

Award stars based on:

1. Completed level
2. Finished under target time
3. Finished under par taps

Example:

```text
1 star = delivery completed
2 stars = completed under time limit
3 stars = completed under time limit and under par taps
```

### Coin Rewards

Example:

```text
Base completion: 10 coins
2-star completion: 15 coins
3-star completion: 25 coins
Perfect route: 35 coins
Daily Route completion: 50 coins
Daily streak bonus: variable
```

---

## Ad Placement Rules

Create clear rules so ads do not ruin retention.

```text
Rewarded ad placements:
- revive_after_fail
- double_coins_after_level
- hint_during_level
- daily_retry
- bonus_chest

Interstitial placements:
- after_level_complete
- after_multiple_failures
- after_level_pack_complete

Interstitial restrictions:
- never during tutorial
- never before level 6
- never immediately after a failure under 10 seconds
- never after a rewarded ad
- never on daily result screen
- never during streak reward claim
```

---

## Analytics Events

Track these from day one.

### Onboarding

```text
tutorial_started
tutorial_completed
tutorial_failed
tutorial_skipped
```

### Level Events

```text
level_started
level_completed
level_failed
level_restarted
level_quit
level_hint_used
level_rewind_used
```

### Economy Events

```text
coins_earned
coins_spent
cosmetic_unlocked
daily_reward_claimed
streak_reward_claimed
```

### Ad Events

```text
rewarded_ad_offered
rewarded_ad_started
rewarded_ad_completed
rewarded_ad_cancelled
interstitial_shown
interstitial_closed
```

### Purchase Events

```text
purchase_started
purchase_completed
purchase_failed
remove_ads_purchased
starter_pack_purchased
```

### Retention Events

```text
daily_route_started
daily_route_completed
daily_route_failed
streak_incremented
streak_lost
```

---

## App Store Positioning

### App Name

**Tiny Routes**

### Subtitle

**One-tap delivery puzzles**

### Short Description

Guide tiny deliveries through clever route puzzles. Tap switches, fix paths, beat the clock, and keep your daily streak alive.

### Longer Description Draft

Tiny Routes is a cozy one-tap puzzle game about guiding tiny deliveries through clever little route maps.

Tap intersections, rotate switches, collect packages, and guide your delivery dot safely to its destination. Play quick levels, perfect your routes, unlock colorful themes, and come back every day for a new Daily Route challenge.

Features:

- Simple one-thumb gameplay
- Fast bite-sized puzzle levels
- Daily Route challenges
- Streak rewards
- Unlockable route themes
- Cosmetic trails and delivery dots
- Relaxed and timed play styles
- Clean minimalist design

Can you find the perfect route?

---

## App Store Keywords

Potential keywords:

```text
puzzle
route
delivery
tap
casual
brain
maze
daily
logic
relaxing
map
path
switch
one tap
```

---

## Prototype Priorities

The first prototype should answer only three questions:

1. Is redirecting the moving dot fun?
2. Do players understand the route-switch mechanic quickly?
3. Do players want to replay levels to get a better score?

Do not overbuild the shop, cosmetics, or world map until the core route puzzle is fun.

---

## Development Priorities

### Priority 1: Core Feel

- Smooth dot movement
- Responsive tapping
- Clear route direction
- Obvious failure state
- Satisfying success moment

### Priority 2: Readability

- Nodes must be easy to tap
- Arrows must be obvious
- Route direction must be clear
- Player should understand why they failed

### Priority 3: Replayability

- Instant restart
- Stars
- Tap count
- Timer
- Perfect route target

### Priority 4: Monetization

- Rewarded revive
- Rewarded double coins
- Remove ads purchase

### Priority 5: Retention

- Daily Route
- Streaks
- Milestone rewards

---

## First 10 Levels Design Plan

### Level 1

Teach movement and destination.

- No switch required
- Dot travels to house
- Player learns objective

### Level 2

Teach one switch.

- One tap changes route toward destination

### Level 3

Teach wrong route.

- If switch is wrong, dot misses destination

### Level 4

Introduce package pickup.

- Destination only works after package collected

### Level 5

Introduce timer.

- Easy timer, low pressure

### Level 6

Introduce star goals.

- Complete under par taps

### Level 7

Introduce two switches.

- Player must plan ahead

### Level 8

Introduce one-way route.

- Wrong path cannot be reversed

### Level 9

Introduce restart and hint.

- Level is slightly tricky

### Level 10

First mini-challenge.

- Combines package, two switches, timer, and stars

---

## Success Criteria for MVP

The concept is worth continuing if:

- Players understand the mechanic in under 30 seconds
- Tutorial completion is high
- Players voluntarily replay levels
- Daily challenge participation is strong
- Rewarded ad acceptance is decent
- Day 1 retention is promising
- Players care about unlocking themes/trails

The concept is weak if:

- Players are confused by routing
- Levels feel too similar
- Players do not retry after failure
- Cosmetics do not feel meaningful
- Ads are the only reason the game has revenue

---

## Key Design Principle

The art can be simple, but the game cannot feel lifeless.

Use polish in places that are cheap:

- Haptics
- Dot glow
- Smooth easing
- Button bounce
- Confetti burst
- Soft sound effects
- Success chime
- Timer pulse
- Route highlight
- Star animation

These make a simple game feel premium without requiring complex assets.

---

## Final Product Direction

Build **Tiny Routes** as a minimalist hybrid-casual iPhone puzzle game.

The final game should feel like:

> A clean daily route puzzle where players guide tiny deliveries through clever maps, perfect their paths, maintain streaks, and unlock cosmetic themes.

The strongest version is not an aggressive ad game. It is a polished, simple, satisfying daily puzzle game with optional ads and light purchases.
