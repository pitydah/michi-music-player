# Core Services Source Manifest

## Metadata

| Field | Value |
|-------|-------|
| Date | 2026-07-14 |
| Convergence branch | `integration/core-services-convergence-v1` |
| QML baseline | `origin/qml-wave9-functional-core-services` |
| QML baseline SHA | `8eccd4c5aee8b0e705edd1efdc95374a1228af86` |

## Source References

| Service | Ref | SHA | Status |
|---------|-----|-----|--------|
| Radio Core V2 | `feature/radio-core-v2` | `c73c76a87` (same as main) | Not yet implemented — at base commit |
| Lyrics Core V2 | `feature/lyrics-core-v2` | `2b2f2bc4a2` | Published |
| Metadata Core V2 | `integration/metadata-core-v2` | `c73c76a87` (same as main) | Not yet implemented — at base commit |
| Michi AI Core V2 | `feature/michi-ai-core-v2` | `0f2a095d3e` | Published |
| Michi AI QML Integration | `integration/michi-ai-core-v2` | `033d9cbc28` | Published (builds on QML wave9) |

## Status Notes

- `feature/radio-core-v2` and `integration/metadata-core-v2` are at the SAME commit as main — no actual implementation was committed to those branches.
- The implementation of ALL cores exists partially in the `michi_ai/v2/` directory and will be built progressively.
