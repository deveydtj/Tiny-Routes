# Multi-Van tutorials and teaching levels

Status: implemented · Last updated: 2026-11-05

Each level that adds a mechanic explains it once, in the level's own JSON. Two teaching levels sit before the two steepest steps in the original twelve.

## Level order (19 levels)

| # | Name | New idea | Teaching |
|---|---|---|---|
| 1 | Go! | Press Go, match the house | Start tip, rings the house |
| 2 | Pick a Lane | Tap a switch | Start tip, rings the switch |
| 3 | Two Turns | Switches in sequence; Stop | Start tip about Stop when a van circles |
| 4 | Roundabout | Three-way cycling | Start tip, rings the switch |
| 5 | Two Colours | Two vans, matching | Start tip, rings both switches |
| 6 | **Wait for It** (new) | ⚡ live switches | Start tip, rings the ⚡ switch. Window ≈2.1 s, Convoy's is ≈0.97 s |
| 7 | Convoy | Live split under tighter timing, staggered departure | Hint |
| 8 | Merge | Correct routes can still crash | Crash tip on the first crash (no start tip, so the crash stays a surprise); hint names the fix |
| 9 | **Take a Lap** (new) | Hold a van in a loop, release with ⚡ | Start tip, rings the loop switch and merge. No entry switch, window ≈4.7 s |
| 10 | Hold the Loop | Loop hold plus a planning switch | Hint |
| 11 | Split | Shared live switch | Hint |
| 12 | Three's Company | Three vans | Hint |
| 13 | Rush | Merge + live split | Hint |
| 14 | Big Delivery | Four vans | Hint |
| 15 | **Pick Up First** (Parcel Row) | Collect a parcel before home | Start tip, rings the fork; hint |
| 16 | Make Room for a Pickup | A pickup trip changes another van's road | Crash tip on the first crash; hint |
| 17 | Around the Block | A one-way street reached from its far end | Hint |
| 18 | Two Good Plans | A shared switch has one setting for both vans; two equal plans | Hint |
| 19 | Neighborhood Round | A parcel each, then one road choice at a crossing | Crash tip on the first crash; hint |

Levels 6–12 of the old set moved to 7, 8, 10–14. Save schema 4 moves stars, completions, unlocks, fastest times and claimed rewards to the new IDs, and unlocks each new level for anyone who finished the level before it (`PlayerProfile.schemaFourLevelIDs`). Moved levels keep their old diorama scenery through `scenerySeed`.

## Level JSON

```json
"tutorial": [
  {
    "trigger": "start",
    "title": "⚡ Live switches",
    "body": "Most switches lock when you press Go. …",
    "focusNodeIDs": ["switch"]
  }
]
```

- `trigger`: `start` opens a card over the bottom of the board when the level first opens; `crash` adds the tip to the failure card on the level's first crash.
- `focusNodeIDs` (optional): pieces ringed on both boards while the card is open and while the player plans, until Go.
- At most one tip per trigger. The level tests check that focus nodes exist and that title and body are filled in.
- `scenerySeed` (optional): seeds the diorama's lawn and scenery; defaults to the number in the level ID.

## Behaviour

- Each tip appears unprompted once per player (`multiVanTutorial.seenTips` in user defaults). Settings → Reset Progress clears it.
- The **?** button in the level card reopens the start tip while planning.
- From the second failed attempt on a level (per visit), the failure card shows the level's `hint`.
- Autoplay shows no tips.
- The playtest log records `tutorial_shown` (with `tutorialTrigger`) and `hint_shown` events.

## Playtests

The game now gives assistance on its own. When filling in the playtest kit, a level where `hint_shown` appears in the log counts as **assisted**. Start tips are part of the level and don't count as assistance. Level numbers in the playtest kit and the MV-46 assessment refer to the old twelve-level order.
