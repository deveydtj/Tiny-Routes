# Current Production Level Corpus Baseline

Generated deterministically by `Tools/LevelGenerator/analyze_level_corpus.py`.

- Levels analyzed: 27
- Solutions passing with every tap at `0.0`: 1
- Solutions passing with taps compressed into `0.15` seconds: 1
- Levels reaching destination before package in a tested state: 0

| Level | Switches | Taps | Repeated taps | Route length | Original | At 0.0 | In 0.15s | Destination first |
| --- | ---: | ---: | --- | ---: | --- | --- | --- | --- |
| level_001 | 0 | 0 | — | 2.731 | pass | pass | pass | no |
| level_002 | 1 | 1 | — | 5.118 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_003 | 2 | 2 | — | 7.800 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_004 | 1 | 1 | — | 3.753 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_005 | 2 | 2 | — | 2.745 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_006 | 1 | 1 | — | 4.068 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_007 | 1 | 1 | — | 4.075 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_008 | 2 | 2 | — | 3.070 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_009 | 1 | 1 | — | 4.027 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_010 | 2 | 2 | — | 3.070 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_011 | 2 | 2 | — | 3.908 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_012 | 2 | 2 | — | 4.258 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_013 | 2 | 2 | — | 3.239 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_014 | 3 | 3 | — | 3.752 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_015 | 2 | 3 | upper_alpha_switch x2 | 9.268 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_016 | 2 | 2 | — | 3.000 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_017 | 2 | 3 | alpha_switch x2 | 9.268 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_018 | 2 | 2 | — | 3.070 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_019 | 2 | 3 | lower_alpha_switch x2 | 9.268 | pass | fail (tap_before_activation_window) | fail (tap_before_activation_window) | no |
| level_020 | 2 | 2 | — | 3.070 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_021 | 3 | 3 | — | 5.153 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_022 | 3 | 3 | — | 4.268 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_023 | 3 | 3 | — | 4.508 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_024 | 2 | 3 | ring_b x2 | 7.250 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_025 | 3 | 3 | — | 4.050 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_026 | 3 | 3 | — | 4.546 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
| level_027 | 3 | 3 | — | 3.410 | pass | fail (tap_noneligible_switch) | fail (tap_noneligible_switch) | no |
