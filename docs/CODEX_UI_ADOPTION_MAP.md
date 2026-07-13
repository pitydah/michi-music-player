# Codex UI Adoption Map

| Page/area | Current pattern | Recommended components | Priority | Conflict risk | Functional prerequisite | Safe stage |
|---|---|---|---|---|---|---|
| Shell/Header | Fixed row/search | PageHeader, Toolbar, Responsive | P1 | Medium | Navigation contracts stable | SAFE_AFTER_WAVE_XII |
| Settings | Card index | Page, Section, ListRow | P2 | Low | Route list stable | SAFE_AFTER_WAVE_XII |
| Devices | Repeated device cards | Page, EmptyState, ResponsiveGrid | P2 | Medium | Device states stable | SAFE_AFTER_WAVE_XIII |
| Connections | Two-column cards | SplitView, ResponsiveGrid, UnavailableState | P2 | Medium | Discovery/pairing stable | SAFE_AFTER_WAVE_XIII |
| Home Audio | Mode panels | Page, SplitView, UnavailableState | P2 | Medium | Receiver contracts stable | SAFE_AFTER_WAVE_XIII |
| Library | Fixed toolbar/table/cards | Toolbar, TrackRow, AlbumTile, ArtistTile | P1 | High | Search/scanner/models frozen | SAFE_AFTER_WAVE_XIV |
| Playlists | Flow cards and custom rows | Toolbar, ListRow, TrackRow, ErrorState | P1 | High | Playlist mutation parity | SAFE_AFTER_WAVE_XIV |
| Playback | Fixed split and queue | SplitView, TrackRow, VisualState | P1 | High | Playback/queue parity | DEFER_UNTIL_FUNCTIONAL_PARITY |
| Smart Tagging | Custom status/form | Page, Loading/Error/Unavailable | P1 | High | Jobs and apply contract stable | DEFER_UNTIL_FUNCTIONAL_PARITY |
| Library Doctor | Custom scan states | Page, LoadingState, StatCard | P2 | High | Worker jobs stable | DEFER_UNTIL_FUNCTIONAL_PARITY |
| Radio | Fixed list/add form | Toolbar, ListRow, Empty/ErrorState | P2 | High | Station mutations stable | DEFER_UNTIL_FUNCTIONAL_PARITY |
| Lyrics | Custom loading/error | Loading, Empty, Error, Unavailable | P1 | Medium | Lyrics lifecycle stable | SAFE_AFTER_WAVE_XIV |
| Mix hub/detail | Fixed grid/list | ResponsiveGrid, TrackRow, EmptyState | P2 | High | Mix data parity | DEFER_UNTIL_FUNCTIONAL_PARITY |
| Metadata inspector | Fixed label widths | Page, MetadataLine, ErrorState | P2 | Medium | Tag-write workflow stable | SAFE_AFTER_WAVE_XIV |

No page adoption is performed in this branch. OpenCode can rebase/cherry-pick foundations after the listed wave without changing backend contracts.
