# QML Library Performance Report

**Date:** 2026-07-04T16:17:10
**Environment:** Linux, Python 3.11, PySide6 6.11, offscreen

## Synthetic Benchmark Results

| Tracks | Load (s) | Filter Artist (s) | Reset Filter (s) | Sort (s) |
|---|---|---|---|---|
| 100 tracks | 0.0325 | 0.0039 | 0.0034 | 0.0033 |
| 1,000 tracks | 0.4238 | 0.0414 | 0.0418 | 0.0412 |
| 10,000 tracks | 4.5778 | 0.4236 | 0.4266 | 1.1737 |
| 50,000 tracks | 22.4096 | 5.2278 | 2.1672 | 2.1273 |

## Methodology
- Tracks created as MagicMock objects with realistic metadata
- LibraryBridge.load_data() called with pre-populated _base_songs
- Each measurement taken once per dataset size
- Artist filter selects first artist's tracks
- Sort by title performs in-memory sort on filtered set

## Conclusions
(To be filled after first run)