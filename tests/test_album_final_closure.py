"""Final closure test: end-to-end with mock library, real AlbumRepository."""
from __future__ import annotations

from unittest.mock import MagicMock


def _make_item(album="A", artist="X", albumartist="", filepath="/m/s.flac",
               title="Song", duration=200.0, year=2024, ext="flac",
               track_number=1, disc_number=1):
    t = MagicMock()
    t.album = album
    t.artist = artist
    t.albumartist = albumartist
    t.filepath = filepath
    t.title = title
    t.duration = duration
    t.year = year
    t.ext = ext
    t.track_number = track_number
    t.disc_number = disc_number
    t.sample_rate = 44100
    t.bit_depth = 16
    t.bitrate = 1411
    t.genre = "Rock"
    return t


class TestFinalClosure:
    def test_mock_library_grouping(self):
        """Full mock library: normal, multi-disc, compilation, remaster, deluxe."""
        from library.album_repository import AlbumRepository

        items = [
            # Normal album (2 tracks)
            _make_item(album="Normal", artist="Artist", filepath="/n/1.flac"),
            _make_item(album="Normal", artist="Artist", filepath="/n/2.flac"),
            # Multi-disc
            _make_item(album="Multi", artist="Band", disc_number=1, filepath="/m/d1/1.flac"),
            _make_item(album="Multi", artist="Band", disc_number=1, filepath="/m/d1/2.flac"),
            _make_item(album="Multi", artist="Band", disc_number=2, filepath="/m/d2/1.flac"),
            # Compilation via Various Artists
            _make_item(album="Comp VA", artist="A1", albumartist="Various Artists",
                       filepath="/c/va/1.flac"),
            _make_item(album="Comp VA", artist="A2", albumartist="Various Artists",
                       filepath="/c/va/2.flac"),
            # Compilation via tag — need compilation or albumartist for grouping
            _make_item(album="Comp VA2", artist="B1", albumartist="Various Artists",
                       filepath="/c/va2/1.flac"),
            _make_item(album="Comp VA2", artist="B2", albumartist="Various Artists",
                       filepath="/c/va2/2.flac"),
            # Remaster — same title different edition
            _make_item(album="Classic", artist="Legend", filepath="/orig/1.flac"),
            _make_item(album="Classic (Remastered)", artist="Legend", filepath="/rem/1.flac"),
            # Deluxe
            _make_item(album="Classic (Deluxe Edition)", artist="Legend", filepath="/dlx/1.flac"),
            # Same title different artist — separate
            _make_item(album="Greatest Hits", artist="Queen", filepath="/gh/q/1.flac"),
            _make_item(album="Greatest Hits", artist="ABBA", filepath="/gh/a/1.flac"),
        ]

        repo = AlbumRepository()
        repo.build(items)
        groups = repo.list_groups()

        # Normal album = 1 group
        normal = [g for g in groups if g.identity.display_title == "Normal"]
        assert len(normal) == 1

        # Multi-disc = 1 group with disc_count=2
        multi = [g for g in groups if g.identity.display_title == "Multi"]
        assert len(multi) == 1
        assert multi[0].identity.disc_count == 2

        # Compilations = 1 group each
        comp_va = [g for g in groups if g.identity.display_title == "Comp VA"]
        assert len(comp_va) == 1
        comp_va2 = [g for g in groups if g.identity.display_title == "Comp VA2"]
        assert len(comp_va2) == 1

        # Remaster and Deluxe = separate from Classic
        classic = [g for g in groups if g.identity.canonical_title == "classic"]
        remastered = [g for g in groups if "remastered" in (g.identity.canonical_title or "")]
        deluxe = [g for g in groups if "deluxe" in (g.identity.canonical_title or "")]
        assert len(classic) == 1
        assert len(remastered) == 1
        assert len(deluxe) == 1
        assert classic[0].identity.album_key != remastered[0].identity.album_key

        # Greatest Hits = 2 groups (Queen + ABBA)
        greatest = [g for g in groups if g.identity.canonical_title == "greatest hits"]
        assert len(greatest) == 2

        # Adapter preserves album_key (skip QPixmap — needs QApp)

    def test_health_detects_missing(self):
        from library.album_repository import AlbumHealthSummary
        h = AlbumHealthSummary()
        assert h.status == "warning"

        h2 = AlbumHealthSummary(track_count=5)
        assert h2.status == "ok"

        h3 = AlbumHealthSummary(track_count=5, missing_files=2)
        assert h3.status == "warning"

    def test_has_sequential_multi_disc(self):
        from library.album_identity import has_sequential_track_numbers

        def _t(tn, disc=1):
            m = MagicMock()
            m.track_number = tn
            m.disc_number = disc
            return m

        assert has_sequential_track_numbers([
            _t(1, 1), _t(2, 1), _t(3, 1),
        ]) is True

        assert has_sequential_track_numbers([
            _t(1, 1), _t(2, 1),
            _t(1, 2), _t(2, 2),
        ]) is True

        assert has_sequential_track_numbers([
            _t(1), _t(3),
        ]) is False

        assert has_sequential_track_numbers([
            _t(1, 1), _t(1, 2),
        ]) is True

        assert has_sequential_track_numbers([]) is False

    def test_should_group_real_vs_fake(self):
        from library.album_identity import should_group_as_compilation

        def _t(artist="A", albumart="", folder="/m/s.flac", tn=1, disc=1):
            m = MagicMock()
            m.artist = artist
            m.albumartist = albumart
            m.filepath = folder
            m.track_number = tn
            m.disc_number = disc
            return m

        # Real VA
        assert should_group_as_compilation([
            _t("A1", "Various Artists", "/comp/1.flac"),
            _t("A2", "Various Artists", "/comp/2.flac"),
        ]) is True

        # Fake: same title, different artists, different folders
        assert should_group_as_compilation([
            _t("Queen", "", "/m/q/1.flac"),
            _t("ABBA", "", "/m/a/1.flac"),
        ]) is False
