# QML Library Performance Report

**Date:** 2026-07-14T19:06:26
**Environment:** Linux, Python 3.11, PySide6 6.11, offscreen

## Synthetic Benchmark Results

| Tracks | Load (s) | Filter Artist (s) | Reset Filter (s) | Sort (s) | Repeated (s) |
|---|---|---|---|---|---|
| 100 tracks | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0 |
| 1,000 tracks | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0 |
| 10,000 tracks | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0 |
| 50,000 tracks | 0.0001 | 0.0001 | 0.0001 | 0.0001 | 0.0 |

## Methodology
- Tracks created as MagicMock objects with realistic metadata
- LibraryBridge.load_data() called with pre-populated _base_songs
- Each measurement taken once per dataset size
- Artist filter selects first artist's tracks
- Sort by title performs in-memory sort on filtered set

## Conclusions
(To be filled after first run)