# First four level references

Original user-supplied images are retained here for future level design:

- [Level 1](level-01.jpg): outer route joins the inner loop at its right side; the house is reached along the bottom road. Timer: 60 seconds.
- [Level 2](level-02.jpg): upper and lower loops share a horizontal road, with the package on the left and house on the right. Timer: 90 seconds.
- [Level 3](level-03.jpg): outer route reaches the house directly; the inner loop connects only to the bottom road. Timer: 75 seconds.
- [Level 4](level-04.jpg): the inner loop connects to the outer route at the top, right, and bottom. Timer: 75 seconds.

The road layouts, start positions, package positions, and houses are traced into `TinyRoutes/Resources/Levels/level_001.json` through `level_004.json`. Both objectives remain visible from the beginning.

Some reference arrows point toward nonexistent exits. Following the user's request to choose the best beginner experience, Level 2's left junction points left toward the package. Level 4's inner arrows follow the clockwise loop (top points right, left points up, bottom points left). Every arrow therefore points along an available road; no extra roads are added.

Each attempt waits for the player to tap one of the dotted roads leaving the blue start. The dots disappear together after selection, and the timer begins. Restart restores the choice. Choosing a starting direction does not count as rotating a switch.
