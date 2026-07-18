# LEGACY DELETION GATES — QtWidgets removal criteria for Michi Music Player

## Gate 1 — Preservation documentation

- [ ] All 127 legacy `.py` files classified by category
- [ ] All 50+ functional domains identified
- [ ] All exclusive legacy logic documented
- [ ] All discard decisions justified
- [ ] All critical workflows described
- [ ] YAML inventory validated by `scripts/validate_legacy_preservation_docs.py`

## Gate 2 — Architecture

- [ ] **0** productive imports of `legacy_widgets`
- [ ] **0** productive imports of `PySide6.QtWidgets`
- [ ] **0** productive `QApplication()` for Qt Widgets
- [ ] **0** routes or code paths opening `MainWindow` legacy
- [ ] **0** automatic fallback to Qt Widgets
- **Current status as of audit:**
  - `michi/widgets_app.py` — already stubbed, not importable by default
  - `library/album_art.py:32` — `CoverFlowItem = _CoverFlowItemLegacy` (cross-import from non-existent module)
  - `legacy_widgets/ui/window.py` — references 12 deleted modules, dead code
  - 23 test files import from `legacy_widgets` (all marked `pytest.skip`)

## Gate 3 — Functional parity

Each function must be in one of these states before its legacy files can be deleted:

| Status | Allowed for deletion |
|--------|---------------------|
| `PARITY` | ✅ Yes |
| `SUPERSEDED` | ✅ Yes |
| `NOT_REQUIRED` | ✅ Yes |
| `DEPRECATED` (with justification) | ✅ Yes |
| `BLOCKED_BY_HARDWARE` (no Qt dep) | ✅ Yes |
| `NOT_STARTED` (critical/high) | ❌ No |
| `PARTIAL` (critical/high) | ❌ No |
| `NEEDS_MANUAL_VERIFICATION` | ❌ No |

### Critical functions requiring parity before deletion

| Function | Current status | Blocks deletion of |
|----------|---------------|-------------------|
| Metadata editor (advanced batch) | PARTIAL | `legacy_widgets/ui/audio_lab/services/tag_writer.py` |
| CD Ripper | PARTIAL | `legacy_widgets/ui/audio_lab/services/rip_job_manager.py`, `rip_worker.py` |
| ADC Recorder (full workflow) | PARTIAL | `legacy_widgets/ui/audio_lab/vinyl_lab_page.py` |
| Disc Lab | PARTIAL | `legacy_widgets/ui/audio_lab/services/disc_detection_service.py` |
| Device sync (full) | PARTIAL | `legacy_widgets/ui/services/*` (7 files) |
| Library import pipeline | NOT_STARTED | `legacy_widgets/ui/audio_lab/services/library_importer.py` |
| Playlist cover service | NOT_STARTED | `legacy_widgets/ui/services/playlist_cover_service.py` |
| External tools detection | NOT_STARTED | `legacy_widgets/ui/audio_lab/services/external_tools.py` |
| Library Doctor (legacy) | PARTIAL | `legacy_widgets/ui/audio_lab/services/library_doctor.py` |
| Smart tagging (legacy models) | PARTIAL | `legacy_widgets/ui/audio_lab/services/smart_tagging_service.py` |

## Gate 4 — Tests

Each function must have a test that validates:

- [ ] Startup completes without legacy imports
- [ ] Core operations succeed end-to-end
- [ ] Error states handled gracefully
- [ ] Cancellation works
- [ ] Persistence round-trips correctly

### Minimum test coverage required per domain

| Domain | Test type | Minimum cases |
|--------|-----------|--------------|
| Metadata | Unit + Integration | 10 |
| Equalizer | Unit + Integration | 8 |
| Search | Integration | 6 |
| Library | Integration | 10 |
| Playback | Integration | 8 |
| Queue | Unit | 6 |
| Smart Tagging | Integration | 8 |
| Library Doctor | Integration | 10 |
| Audio Conversion | Integration | 6 |
| CD Ripper | Integration (mocked) | 6 |
| ADC Recorder | Integration (mocked) | 6 |
| Devices | Integration (mocked) | 8 |
| Connections | Integration (mocked) | 6 |
| Sync | Unit + Integration | 8 |
| Radio | Integration | 6 |
| Playlists | Integration | 6 |
| Now Playing | Integration | 6 |
| Home Dashboard | Integration | 6 |
| Home Audio | Integration (mocked) | 6 |
| Settings | Integration | 6 |

## Gate 5 — Hardware dependencies

Functions that require physical hardware. These must NOT block deletion as long as they are protected by capability detection, not Qt Widgets fallback.

| Function | Hardware | Fallback without hardware |
|----------|----------|--------------------------|
| CD Ripper | Optical drive | Capability check → "No disponible" |
| Disc detection | Optical drive | Capability check → "No disponible" |
| ADC Recorder | USB audio interface | Capability check → "No disponible" |
| Vinyl digitization | USB turntable | Capability check → "No disponible" |
| Device sync (MTP) | USB MTP device | Capability check → "No disponible" |
| Device sync (MSC) | USB MSC device | Capability check → "No disponible" |
| DAC output | DAC USB | Capability check → "No disponible" |
| Michi Micro Server | Network | Graceful connection error |
| Snapcast | Network Snapcast server | Graceful connection error |
| Home Assistant | Network HA server | Graceful connection error |

## Gate 6 — Performance

Metrics to compare before and after legacy removal:

| Metric | Baseline (before) | Target (after) |
|--------|------------------|----------------|
| RAM at startup | Measure | ≤ Baseline |
| RAM at idle (post-scan) | Measure | ≤ Baseline |
| RAM during playback | Measure | ≤ Baseline |
| Startup time | Measure | ≤ Baseline |
| Thread count at idle | Measure | ≤ Baseline |
| CPU usage at idle | Measure | ≤ Baseline |
| Shutdown time | Measure | ≤ Baseline |
| QObject count at idle | Measure | ≤ Baseline |
| QObject leak after 10 nav cycles | Measure | ≤ Baseline |

## Gate 7 — Git reversibility

Before deleting any files:

- [ ] Branch `archive/qtwidgets-final` created and pushed
- [ ] Tag `archive-qtwidgets-pre-cleanup` created and pushed
- [ ] Exact commit hash documented: `e1809ed0`
- [ ] Recovery instructions included in this document

### Recovery instructions

```bash
# To restore Qt Widgets at any time:
git checkout archive/qtwidgets-final
# Or restore a single file from the archive branch:
git checkout archive/qtwidgets-final -- legacy_widgets/path/to/file.py
```

## Current gate status (as of this audit)

| Gate | Status |
|------|--------|
| Gate 1 — Documentation | ⬜ Not started (this document created, detailed per-function docs pending) |
| Gate 2 — Architecture | 🟡 Production imports: 0; `album_art.py` import of deleted module blocks clean removal |
| Gate 3 — Parity | 🔴 10 critical functions are PARTIAL or NOT_STARTED |
| Gate 4 — Tests | 🔴 Many domains lack dedicated tests |
| Gate 5 — Hardware | 🟢 Capability-based design is the norm |
| Gate 6 — Performance | 🔴 No baseline measurements taken |
| Gate 7 — Git | 🟢 Branch and tag created, commit hash documented |

## Verification commands

```bash
# Check for QtWidgets imports outside legacy_widgets
grep -rn "from PySide6.QtWidgets\|from PyQt5\|from PyQt6" --include="*.py" \
  --exclude-dir=legacy_widgets --exclude-dir=tests --exclude-dir=build \
  /home/cristian/music_player

# Check for legacy_widgets imports in producton code
grep -rn "from legacy_widgets\|import legacy_widgets" --include="*.py" \
  --exclude-dir=tests --exclude-dir=build \
  /home/cristian/music_player

# Check for QApplication in QML runtime path
grep -rn "QApplication(" --include="*.py" \
  --exclude-dir=legacy_widgets --exclude-dir=tests --exclude-dir=build \
  /home/cristian/music_player

# Validate preservation docs
python3 scripts/validate_legacy_preservation_docs.py
```
