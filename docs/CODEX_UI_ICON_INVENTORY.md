# Codex UI Icon Inventory

## Debt

- 49 baseline text/Unicode icon patterns were detected.
- Sidebar fallbacks use abbreviations such as `BL`, `MX`, `RP`, `HA`.
- Toast and playlist removal use `[X]`.
- Synced lyrics and expanded playback use Unicode/arrows as controls.
- SVG, PNG 32/64/128 and backup assets coexist with inconsistent names.

## Semantic mapping

| Name | Current asset/fallback | Status |
|---|---|---|
| play/pause/next/previous | `warm_*.svg` | Ready |
| queue | `sidebar_songs.svg` | Ready, shared metaphor |
| history | `sidebar_recent.svg` | Ready |
| library/album/artist/folder | sidebar/folder SVGs | Ready |
| playlist/radio/mix/settings | existing SVGs | Ready |
| devices/connections | sidebar SVGs | Ready |
| lyrics | `sidebar/metadata.svg` | Temporary metaphor |
| jobs | `sidebar_audio_lab.svg` | Temporary metaphor |
| refresh | `warm_repeat.svg` | Temporary metaphor |
| warning/error/search/more/close | `actions/missing-icon.svg` | Asset required |
| back | `nav_back.svg` | Ready |

`MichiIcon` resolves semantic names without bridges. Missing semantic assets deliberately use the shared missing-icon resource so new Unicode fallbacks cannot leak into foundations.

## Naming rule

New assets should use `icons/actions/<semantic-name>.svg`, monochrome fills suitable for tinting, a 24 px view box and no embedded hardcoded brand color. Do not replace production page icons until the corresponding adoption stage.
