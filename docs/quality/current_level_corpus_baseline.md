# Current Production Level Corpus Baseline

Generated deterministically by `Tools/LevelGenerator/analyze_level_corpus.py`.

- Levels analyzed: 27
- Solutions passing with every tap at `0.0`: 24
- Solutions passing with taps compressed into `0.15` seconds: 24
- Levels reaching destination before package in a tested state: 3

| Level | Switches | Taps | Repeated taps | Route length | Original | At 0.0 | In 0.15s | Destination first |
| --- | ---: | ---: | --- | ---: | --- | --- | --- | --- |
| level_001 | 0 | 0 | — | 2.731 | pass | pass | pass | no |
| level_002 | 1 | 1 | — | 2.787 | pass | pass | pass | no |
| level_003 | 0 | 0 | — | 2.795 | pass | pass | pass | no |
| level_004 | 1 | 1 | — | 2.787 | pass | pass | pass | no |
| level_005 | 0 | 0 | — | 2.795 | pass | pass | pass | no |
| level_006 | 1 | 1 | — | 3.103 | pass | pass | pass | no |
| level_007 | 1 | 1 | — | 3.110 | pass | pass | pass | no |
| level_008 | 2 | 2 | — | 3.070 | pass | pass | pass | no |
| level_009 | 1 | 1 | — | 3.062 | pass | pass | pass | no |
| level_010 | 2 | 2 | — | 3.070 | pass | pass | pass | no |
| level_011 | 2 | 2 | — | 3.908 | pass | pass | pass | no |
| level_012 | 2 | 2 | — | 4.258 | pass | pass | pass | no |
| level_013 | 2 | 2 | — | 3.239 | pass | pass | pass | no |
| level_014 | 3 | 3 | — | 3.752 | pass | pass | pass | no |
| level_015 | 2 | 3 | upper_alpha_switch x2 | 9.268 | pass | fail (reached_destination_without_package) | fail (reached_destination_without_package) | yes |
| level_016 | 2 | 2 | — | 3.000 | pass | pass | pass | no |
| level_017 | 2 | 3 | alpha_switch x2 | 9.268 | pass | fail (reached_destination_without_package) | fail (reached_destination_without_package) | yes |
| level_018 | 2 | 2 | — | 3.070 | pass | pass | pass | no |
| level_019 | 2 | 3 | lower_alpha_switch x2 | 9.268 | pass | fail (reached_destination_without_package) | fail (reached_destination_without_package) | yes |
| level_020 | 2 | 2 | — | 3.070 | pass | pass | pass | no |
| level_021 | 3 | 3 | — | 5.153 | pass | pass | pass | no |
| level_022 | 3 | 3 | — | 4.268 | pass | pass | pass | no |
| level_023 | 3 | 3 | — | 4.508 | pass | pass | pass | no |
| level_024 | 3 | 3 | — | 3.546 | pass | pass | pass | no |
| level_025 | 3 | 3 | — | 4.050 | pass | pass | pass | no |
| level_026 | 3 | 3 | — | 3.053 | pass | pass | pass | no |
| level_027 | 3 | 3 | — | 3.410 | pass | pass | pass | no |
