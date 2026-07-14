# Core Services Capability Matrix

| Capability | Service | Status | Depends On |
|------------|---------|--------|------------|
| `playback.control` | PlayerService | ✅ available | PlayerService |
| `queue.read` | PlayerService/QueueService | ✅ available | PlayerService |
| `queue.modify` | PlayerService/QueueService | ✅ available | PlayerService |
| `library.search` | LibraryDB | ✅ available | LibraryDB |
| `library.read` | LibraryDB | ✅ available | LibraryDB |
| `playlist.read` | LibraryDB | ✅ available | LibraryDB |
| `playlist.modify` | LibraryDB | ✅ available | LibraryDB |
| `settings.read` | SettingsService | ✅ available | SettingsService |
| `settings.modify` | SettingsService | ✅ available | SettingsService |
| `audio_lab.analyze` | AnalysisService | ✅ available | AnalysisService |
| `audio_lab.convert` | AnalysisService | 🔴 UNAVAILABLE | Not wired |
| `devices.read` | SyncManager | ⚠️ PARTIAL | SyncManager |
| `devices.sync` | SyncManager | 🔴 UNAVAILABLE | Not wired |
| `diagnostics.read` | DiagnosticsService | ✅ available | DiagnosticsService |
| `mix.generate` | MixService | 🔴 UNAVAILABLE | Not wired |
| `radio.read` | RadioService | 🔴 UNAVAILABLE | Not wired |
| `radio.control` | RadioService | 🔴 UNAVAILABLE | Not wired |
| `lyrics.read` | LyricsService | 🔴 UNAVAILABLE | Not wired |
| `lyrics.edit` | LyricsService | 🔴 UNAVAILABLE | Not wired |
| `metadata.read` | MetadataService | 🔴 UNAVAILABLE | Not wired |
| `metadata.modify` | MetadataService | 🔴 UNAVAILABLE | Not wired |
| `navigation.request` | NavigationBridge | ✅ stub | NavigationBridge |
| `library_doctor.scan` | LibraryDoctorService | 🔴 UNAVAILABLE | Not wired |

## Dynamic Capability Updates

Capabilities must be updated when:
1. Provider fails
2. Network changes
3. Service degrades
4. Filesystem becomes read-only
5. Shutdown begins

Current implementation: capabilities set at startup via `AssistantGateways`. Dynamic updates deferred.
