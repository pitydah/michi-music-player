#!/usr/bin/env python3
"""QML Library Bridge Performance Benchmark.

Measures LibraryBridge load times with synthetic track data.
Output: docs/QML_LIBRARY_PERFORMANCE_REPORT.md
"""
import time
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _make_track(tid: int, title: str, artist: str, album: str) -> MagicMock:
    t = MagicMock()
    t.id = tid
    t.filepath = f"/music/{artist}/{album}/{tid:04d}.flac"
    t.title = title
    t.artist = artist
    t.album = album
    t.duration = 200.0 + (tid % 60)
    t.genre = "Rock"
    t.year = 2000 + (tid % 25)
    t.play_count = tid % 100
    t.last_played = time.time() - (tid * 3600)
    t.track_number = (tid % 12) + 1
    t.bitrate = 1411
    t.format = "FLAC"
    t.created_at = time.time() - (tid * 86400)
    return t


def _make_db_mock(count: int):
    db = MagicMock()
    tracks = [_make_track(i, f"Track {i}", f"Artist {i % 50}", f"Album {i % 20}") for i in range(count)]
    db.fetch_all.return_value = tracks
    db.get_all.return_value = tracks
    db.get_favorites.return_value = [t.filepath for t in tracks[:count // 10]]
    return db, tracks


def benchmark(count: int, label: str) -> dict:
    from ui_qml_bridge.library_bridge import LibraryBridge
    db, tracks = _make_db_mock(count)

    bridge = LibraryBridge(db=db, search_engine=None, playback_ctrl=None)

    # Measure load
    t0 = time.perf_counter()
    bridge._base_songs = tracks
    bridge.refresh()
    t_load = time.perf_counter() - t0

    # Measure filter by artist
    t0 = time.perf_counter()
    bridge.setArtistFilter(tracks[0].artist)
    bridge.refresh()
    t_filter_artist = time.perf_counter() - t0

    # Measure filter reset
    t0 = time.perf_counter()
    bridge.setArtistFilter("")
    bridge.refresh()
    t_filter_reset = time.perf_counter() - t0

    # Measure sort by title
    t0 = time.perf_counter()
    bridge.sortBy("title")
    bridge.refresh()
    t_sort = time.perf_counter() - t0

    # Measure repeated property access (QML reads visibleCount + songs after filter)
    t0 = time.perf_counter()
    for _ in range(10):
        _ = bridge.visibleCount
        _ = bridge.songs
    t_repeated = (time.perf_counter() - t0) / 10

    # Count memory
    import sys as _sys
    mem_songs = _sys.getsizeof(bridge._base_songs)
    mem_filtered = _sys.getsizeof(bridge._cached_view) if hasattr(bridge, '_cached_view') and bridge._cached_view else 0

    return {
        "count": count,
        "label": label,
        "load_seconds": round(t_load, 4),
        "filter_artist_seconds": round(t_filter_artist, 4),
        "filter_reset_seconds": round(t_filter_reset, 4),
        "sort_seconds": round(t_sort, 4),
        "repeated_access_seconds": round(t_repeated, 4),
        "memory_songs_bytes": mem_songs,
        "memory_filtered_bytes": mem_filtered,
    }


def main():
    print("# QML Library Bridge Performance Benchmark")
    print(f"\n**Date:** {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    print("**Environment:** Linux, Python 3.11, PySide6 6.11, offscreen")
    print("\n## Results\n")
    print("| Tracks | Load (s) | Filter Artist (s) | Reset Filter (s) | Sort (s) | Repeated (s) |")
    print("|---|---|---|---|---|---|")

    results = []
    for count, label in [(100, "100 tracks"), (1000, "1,000 tracks"),
                          (10000, "10,000 tracks"), (50000, "50,000 tracks")]:
        r = benchmark(count, label)
        results.append(r)
        print(f"| {r['label']} | {r['load_seconds']} | {r['filter_artist_seconds']} | "
              f"{r['filter_reset_seconds']} | {r['sort_seconds']} | {r.get('repeated_access_seconds', '-')} |")

    # Save JSON
    outpath = Path("/tmp/michi_qml_library_benchmark.json")
    outpath.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nDetailed results written to {outpath}")
    print("\n## Analysis")
    max_load = max(r['load_seconds'] for r in results)
    if max_load < 0.1:
        print("- All loads complete in under 100ms — excellent performance.")
    elif max_load < 0.5:
        print("- All loads under 500ms — good performance.")
    elif max_load < 2.0:
        print("- Load times above 500ms may need optimization for 50k+ libraries.")
    else:
        print("- Load times critical — LibraryBridge needs caching optimization.")

    # Write doc
    doc_path = REPO / "docs" / "QML_LIBRARY_PERFORMANCE_REPORT.md"
    doc_lines = [
        "# QML Library Performance Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%dT%H:%M:%S')}",
        "**Environment:** Linux, Python 3.11, PySide6 6.11, offscreen",
        "",
        "## Synthetic Benchmark Results",
        "",
        "| Tracks | Load (s) | Filter Artist (s) | Reset Filter (s) | Sort (s) | Repeated (s) |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
            doc_lines.append(f"| {r['label']} | {r['load_seconds']} | {r['filter_artist_seconds']} | "
                         f"{r['filter_reset_seconds']} | {r['sort_seconds']} | {r.get('repeated_access_seconds', '-')} |")
    doc_lines.extend([
        "",
        "## Methodology",
        "- Tracks created as MagicMock objects with realistic metadata",
        "- LibraryBridge.load_data() called with pre-populated _base_songs",
        "- Each measurement taken once per dataset size",
        "- Artist filter selects first artist's tracks",
        "- Sort by title performs in-memory sort on filtered set",
        "",
        "## Conclusions",
        "(To be filled after first run)",
    ])
    doc_path.write_text("\n".join(doc_lines))
    print(f"\nReport written to {doc_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
