# Codex UI/UX Foundations Audit

Base: `6aa371f8d09deea5b12bd7919e5ef51a5d0c854f`.

Scope: static audit of `ui_qml/theme`, `components`, `materials`, `shell` and `pages`. No functional page was modified.

## Baseline

| Signal | Count | Risk |
|---|---:|---|
| `MouseArea` controls | 53 | Keyboard/focus behavior is inconsistent. |
| Direct colors outside theme | 35 | Visual drift and difficult contrast changes. |
| Rigid numeric dimensions | 224 | Breakage at 1280x720, compact windows and HiDPI. |
| `Accessible.*` declarations | 4 | Screen-reader coverage is effectively absent. |
| Text/Unicode icon patterns | 49 | Icon language is inconsistent. |

## Findings

| Priority | Finding | Affected area | Recommendation |
|---|---|---|---|
| P1 | Shell and toolbars assume generous width | Header, Library, Playback | Adopt responsive page/toolbar primitives after functional parity. |
| P1 | Custom controls lack keyboard and accessible names | Components, rows, cards | Adopt focus ring and canonical controls first. |
| P1 | Loading/empty/error/unavailable patterns differ by page | Library, Radio, Lyrics, workflows | Replace progressively with canonical states. |
| P1 | 1280x720 loses vertical space to fixed heroes and bars | Home, Audio Lab, Radio, Mix | Use compact margins, overflow and responsive split/grid. |
| P2 | Direct `Qt.rgba` values remain in materials/pages | Global | Move semantic values into `MichiColors`; no mass rewrite during migration. |
| P2 | Album and artist views use fixed cells | Library pages | Adopt responsive grid only after Wave XIV. |
| P2 | Unicode/text icons remain | Toast, playlists, synced lyrics, fallbacks | Replace via semantic `MichiIcon` mapping. |
| P2 | Optional animation ignores reduced motion | Sidebar, lyrics, progress | Use `MichiReducedMotion`. |

## State maturity

- Shell and playback are visually coherent but not fully accessible.
- Library is functionally dense and needs overflow at 1280x720.
- Metadata, tagging, radio and advanced tools need canonical states before visual polish.
- Existing smoked/glass materials are reusable; a redesign is unnecessary.

## Isolation decision

The foundation branch adds presentational primitives only. It does not change routes, functional pages, bridges, context properties, services or models.
