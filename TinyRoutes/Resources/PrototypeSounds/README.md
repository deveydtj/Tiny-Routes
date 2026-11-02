# Prototype sounds

All ten assets are original mathematical synthesis created for Tiny Routes (MV-33).
No recordings, samples, downloads, or external dependencies were used. Dedicated to
the public domain under CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/.
This dedication applies to every CAF listed below.

| File | Original generation method | Duration |
| --- | --- | --- |
| click.caf | 1,250 Hz sine with quiet 2,100 Hz overtone, fast decay | 65 ms |
| dull_tick.caf | 380 Hz sine with quiet octave, fast decay | 85 ms |
| vroom.caf | Rising 95–234 Hz sine chirp, quiet harmonic and 90 Hz body | 480 ms |
| chime_1.caf | C5 (523.251 Hz), quiet second/third harmonics | 460 ms |
| chime_2.caf | E5 (659.255 Hz), quiet second/third harmonics | 460 ms |
| chime_3.caf | G5 (783.991 Hz), quiet second/third harmonics | 460 ms |
| chime_4.caf | C6 (1,046.502 Hz), quiet second/third harmonics | 460 ms |
| fanfare.caf | Overlapping C5/E5/G5/C6 notes at 120 ms intervals | 840 ms |
| bonk.caf | Descending 320–147 Hz sine chirp, quiet 460 Hz overtone | 240 ms |
| nope_horn.caf | Descending 260/325 Hz two-note horn | 360 ms |

Generated with Python standard-library math/wave/struct, then Apple's `afconvert
-f caff -d LEI16`. Files contain mono 22,050 Hz, signed 16-bit PCM in CAF containers.
Every voice has an 8 ms attack, 25 ms release and exponential decay; peaks are
limited to 0.36 full scale (about −8.9 dBFS) before the user's volume is applied.
Chimes use a consonant rising arpeggio; the fanfare shares that tuning. No random
noise, sharp square waves, compression or loops are used.

The folder is copied intact to `PrototypeSounds/` inside the app bundle.
