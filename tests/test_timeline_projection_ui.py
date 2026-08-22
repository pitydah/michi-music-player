"""Regression test for timeline view section labels and decade grouping."""

from pathlib import Path

from michi.domain.library import AlbumRef, build_timeline_projection, timeline_decade

QML = Path("src/michi/presentation/qml")


def test_timeline_decade_domain_projection() -> None:
    assert timeline_decade(1973) == "1970s"
    assert timeline_decade(2024) == "2020s"
    assert timeline_decade(1999) == "1990s"
    assert timeline_decade(0) == "Unknown era"
    assert timeline_decade(-1) == "Unknown era"


def test_timeline_albums_projection_sorting_and_decades() -> None:
    albums = [
        AlbumRef(
            key="k1",
            title="Album 70s",
            artist="Artist A",
            track_paths=("p1",),
            year=1975,
            track_count=1,
            duration_ms=1000,
        ),
        AlbumRef(
            key="k2",
            title="Album 90s",
            artist="Artist B",
            track_paths=("p2",),
            year=1994,
            track_count=1,
            duration_ms=1000,
        ),
        AlbumRef(
            key="k3",
            title="Album Unknown",
            artist="Artist C",
            track_paths=("p3",),
            year=0,
            track_count=1,
            duration_ms=1000,
        ),
    ]
    projections = build_timeline_projection(albums)
    assert len(projections) == 3
    # Sorted by -year, then album_key
    assert projections[0].year == 1994
    assert projections[0].decade == "1990s"
    assert projections[1].year == 1975
    assert projections[1].decade == "1970s"
    assert projections[2].year == 0
    assert projections[2].decade == "Unknown era"


def test_timeline_view_qml_does_not_break_decade_string_with_number_cast() -> None:
    timeline_src = (QML / "views" / "TimelineView.qml").read_text()
    # Ensure Number(section) > 0 with section + 's' bug is fixed
    assert "Number(section) > 0" not in timeline_src
    assert 'section === "Unknown era"' in timeline_src
