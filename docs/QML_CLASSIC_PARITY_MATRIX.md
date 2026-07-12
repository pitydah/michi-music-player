# QML Classic Parity Matrix

**Legend:** ✅ Full parity · ⚠️ Partial · ❌ Missing · — Not applicable

## Core workflow parity

| Module | QtWidgets | QML | Backend | Error handling | Async | Cancel | Tests |
|---|---|---|---|---|---|---|---|
| Shell/Navigation | ✅ | ✅ | NavigationBridge | ✅ | — | — | 1 |
| Home | ✅ | ✅ | HomeBridge | ✅ | — | — | 3 |
| Library | ✅ | ✅ | LibraryQueryService | ✅ | ✅ | ✅ | 28 |
| Albums | ✅ | ✅ | AlbumListModel | ✅ | ✅ | ✅ | 5 |
| Artists | ✅ | ✅ | ArtistListModel | ✅ | ✅ | ✅ | 4 |
| Folders | ✅ | ✅ | FolderTreeModel | ✅ | ✅ | ✅ | 3 |
| Playback | ✅ | ✅ | PlaybackBridge | ✅ | — | — | 2 |
| Queue | ✅ | ✅ | QueueBridge | ✅ | — | — | 4 |
| History | ✅ | ✅ | HistoryBridge | ✅ | — | — | 4 |
| Search | ✅ | ✅ | QueryService | ✅ | ✅ | ✅ | 10 |

## Content workflow parity

| Module | QtWidgets | QML | Backend | Error handling | Async | Cancel | Tests |
|---|---|---|---|---|---|---|---|
| Playlists | ✅ | ✅ | PlaylistsBridge | ✅ | ✅ | ✅ | 4 |
| Radio | ✅ | ✅ | RadioBridge | ✅ | — | — | 2 |
| Lyrics | ✅ | ⚠️ | LyricsBridge | ✅ | ✅ | ✅ | 9 |
| Mix | ✅ | ✅ | MixBridge | ✅ | — | — | 2 |
| Metadata | ✅ | ✅ | MetadataBridge | ✅ | — | — | 2 |
| Smart Tagging | ✅ | ✅ | SmartTaggingBridge | ✅ | ✅ | ✅ | 4 |
| Global Search | ✅ | ✅ | GlobalSearchBridge | ✅ | — | — | 3 |
| Command Palette | ✅ | ✅ | CommandPaletteBridge | ✅ | — | — | 1 |

## System workflow parity

| Module | QtWidgets | QML | Backend | Error handling | Async | Cancel | Tests |
|---|---|---|---|---|---|---|---|
| Settings | ✅ | ⚠️ | SettingsBridge | ✅ | — | — | 2 |
| EQ | ✅ | ✅ | EqBridge | ✅ | — | — | 3 |
| Library Sources | ✅ | ✅ | LibrarySourcesBridge | ✅ | — | — | 8 |
| Jobs | ✅ | ✅ | JobBridge | ✅ | ✅ | ✅ | 4 |
| Library Doctor | ✅ | ⚠️ | LibraryDoctorBridge | ✅ | — | — | 1 |
| Diagnostics | ✅ | ✅ | DiagnosticsBridge | ✅ | — | — | 1 |
| Audio Lab | ✅ | ✅ | AudioLabBridge | ✅ | — | — | 2 |
| Disc Lab | ✅ | ✅ | DiscLabBridge | ✅ | — | — | 4 |
| Output Profiles | ❌ | ❌ | — | — | — | — | 0 |

## Ecosystem parity

| Module | QtWidgets | QML | Backend | Error handling | Async | Cancel | Tests |
|---|---|---|---|---|---|---|---|
| Devices | ✅ | ✅ | DevicesBridge | ✅ | — | — | 1 |
| Connections | ✅ | ✅ | ConnectionsBridge | ✅ | — | — | 3 |
| Home Audio | ✅ | ✅ | HomeAudioBridge | ✅ | — | — | 9 |
| Michi AI | ✅ | ✅ | MichiAIBridge | ✅ | — | — | 1 |

## Summary

| Metric | Count | % |
|---|---|---|
| Full parity (✅) | 24/27 | 89% |
| Partial (⚠️) | 3/27 | 11% |
| Missing (❌) | 1/27 | 4% |
| Total modules | 27 | 100% |

**QML default readiness:** ~70% (requires Output Profiles + Settings completeness)
