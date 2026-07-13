# Codex UI Component Inventory

| Current component | Role | Duplicate/debt | Foundation action |
|---|---|---|---|
| `MichiButton` | Text action | Direct colors, weak tooltip contract | Extended with theme colors and accessibility. |
| `MichiIconButton` | Icon action | Rectangle/MouseArea implementation | Extended as keyboard-capable Qt button. |
| `SearchField` | Search input | Mixed programmatic/user signals | Exposed as `MichiSearchField` alias with presentational signals. |
| `IconSlot` | Text placeholder | Text used as icon | Exposed as semantic `MichiIcon`. |
| `MichiSlider` | Value control | Direct colors | Extended with role, name and theme tokens. |
| `MichiProgressBar` | Progress | Infinite motion always active | Added reduced-motion and accessibility contract. |
| `EmptyState` | Legacy empty state | Page-specific variants remain | New canonical state family can be adopted progressively. |
| `GlassCard`/`GlassPanel` | Smoked surfaces | Repeated row/tile patterns | Keep; new content primitives define semantics. |
| `PageHeader`/`SectionHeader` | Headings | Fixed layouts | New responsive header/section are adoption targets. |
| `SongRow` | Functional library row | Coupled to filepath | Do not reuse as foundation; `MichiTrackRow` uses public identity only. |
| `SongContextMenu` | Track menu | Domain-specific and mouse-led | Defer generic context menu until functional parity. |

## New components

| Group | Components | Purpose |
|---|---|---|
| Foundations | Responsive, FocusRing, ReducedMotion, VisualState | Shared visual behavior without backend knowledge. |
| States | Loading, Empty, Error, Unavailable, Skeleton | Consistent asynchronous and unavailable feedback. |
| Layout | Page, PageHeader, Toolbar, Section, ResponsiveGrid, SplitView | Compact/regular/wide composition. |
| Content | ListRow, TrackRow, AlbumTile, ArtistTile, MetadataLine, StatCard | Reusable music-domain presentation with public properties. |

`MichiMenuButton`, `MichiSegmentedControl`, `MichiSwitch` and a generic context menu remain deferred to avoid duplicating active functional controls and exceeding the branch limit.
