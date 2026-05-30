# Switch Arrow Bug Fixture

This fixture preserves a level-028-style generated level where switch targets sit diagonally from the switch node but the road initially leaves on a cardinal axis.

## Reproduction Notes

- Fixture level: `level_028_style_switch_arrow_mismatch.json`
- Matching solution: `level_028_style_switch_arrow_mismatch.solution.json`
- Source case: production `level_028`, generated as a hard `multi_switch_chain_zigzag` level.

The legacy target-vector arrow resolver pointed each solution edge toward its target node. In this fixture that made several tapped switch choices look diagonal:

| Switch | Solution edge | Legacy displayed direction | Actual first travel direction |
|---|---|---|---|
| `multi_switch_chain_zigzag_switch_a` | `e_multi_switch_chain_zigzag_switch_a_package` | diagonal up/right toward `package` | up, from the first `verticalFirst` road segment |
| `multi_switch_chain_zigzag_switch_b` | `e_multi_switch_chain_zigzag_switch_b_multi_switch_chain_zigzag_switch_c` | diagonal up/right toward `switch_c` | up, from the first `verticalFirst` road segment |
| `multi_switch_chain_zigzag_switch_c` | `e_multi_switch_chain_zigzag_switch_c_multi_switch_chain_zigzag_switch_d` | diagonal down/right toward `switch_d` | down, from the first `verticalFirst` road segment |
| `multi_switch_chain_zigzag_switch_d` | `e_multi_switch_chain_zigzag_switch_d_destination` | diagonal up/right toward `destination` | up, from the first `verticalFirst` road segment |

The regression expectation is that switch arrows use the road path's start tangent. A target-node vector is only acceptable as a fallback when usable road geometry is missing.
