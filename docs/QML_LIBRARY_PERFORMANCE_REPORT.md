# QML Library Performance Report

**Date:** 2026-07-04T16:27:01
**Environment:** Linux, Python 3.11, PySide6 6.11, offscreen

## Synthetic Benchmark Results

| Tracks | Load (s) | Filter Artist (s) | Reset Filter (s) | Sort (s) | Repeated (s) |
|---|---|---|---|---|---|
| 100 tracks | 0.0326 | 0.0039 | 0.0036 | 0.0035 | 0.0062 |
| 1,000 tracks | 0.4039 | 0.0426 | 0.102 | 0.0425 | 0.0056 |
| 10,000 tracks | 4.7975 | 0.4321 | 0.4335 | 0.4287 | 0.0057 |
| 50,000 tracks | 24.0365 | 2.1628 | 2.1706 | 2.1437 | 0.006 |

## Methodology
- Tracks created as MagicMock objects with realistic metadata
- LibraryBridge.load_data() called with pre-populated _base_songs
- Each measurement taken once per dataset size
- Artist filter selects first artist's tracks
- Sort by title performs in-memory sort on filtered set

## Conclusions
(To be filled after first run)