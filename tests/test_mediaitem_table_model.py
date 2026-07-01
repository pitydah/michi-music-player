"""Tests: MediaItemTableModel — populate, data roles, sorting, optional columns, encapsulation."""

from library.media_item import MediaItem
from library.mediaitem_table_model import (
    MediaItemTableModel, STATUS_ROLE, QUALITY_ROLE,
    FAVORITE_ROLE, FILEPATH_ROLE,
)
from PySide6.QtCore import Qt


def _make_item(fid=1, filepath="/m/a.flac", title="A", artist="Art",
               album="Alb", genre="Rock", ext=".flac",
               sample_rate=44100, bit_depth=16, duration=180.0,
               bitrate=1411000, replaygain_track=0.0,
               replaygain_album=0.0, year=2000):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist=artist,
        album=album, genre=genre, ext=ext,
        sample_rate=sample_rate, bit_depth=bit_depth,
        duration=duration, bitrate=bitrate,
        replaygain_track=replaygain_track,
        replaygain_album=replaygain_album,
        year=year,
        filename="a.flac", directory="/m",
        kind="audio", size=0, mtime=0.0, track_number=1,
        composer="", albumartist="", disc_number=0, disc_total=0,
        track_total=0, mb_track_id="", mb_album_id="",
        mb_albumartist_id="", bpm=0, isrc="", label="",
        conductor="", compilation=False, media_type="", encoder="",
        copyright="", originaldate="", remixer="", grouping="",
        mood="", replaygain_track_peak=0.0, play_count=0,
        last_played=0.0, rating=0, created_at=0.0, updated_at=0.0,
        last_scanned=0.0, track_uid="",
    )


class TestMediaItemTableModel:

    def test_populate_and_row_count(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=1), _make_item(fid=2)])
        assert model.rowCount() == 2

    def test_column_count_base(self):
        model = MediaItemTableModel()
        model.populate([])
        assert model.columnCount() == 11

    def test_column_count_with_optional(self):
        model = MediaItemTableModel()
        model.set_optional_columns(["bitrate", "bpm"])
        model.populate([])
        assert model.columnCount() == 13

    def test_data_title(self):
        model = MediaItemTableModel()
        model.populate([_make_item(title="My Song")])
        val = model.data(model.index(0, 2))
        assert val == "My Song"

    def test_data_artist(self):
        model = MediaItemTableModel()
        model.populate([_make_item(artist="My Artist")])
        val = model.data(model.index(0, 3))
        assert val == "My Artist"

    def test_data_format(self):
        model = MediaItemTableModel()
        model.populate([_make_item(ext=".flac")])
        val = model.data(model.index(0, 8))
        assert val == "FLAC"

    def test_favorite_star(self):
        model = MediaItemTableModel()
        model.populate([_make_item(filepath="/m/x.flac")],
                       fav_set={"/m/x.flac"})
        val = model.data(model.index(0, 0))
        assert val == "★"

    def test_non_favorite_no_star(self):
        model = MediaItemTableModel()
        model.populate([_make_item(filepath="/m/x.flac")], fav_set=set())
        val = model.data(model.index(0, 0))
        assert val == ""

    def test_status_role(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=42)],
                       status_cache={42: {"quality_label": "Lossless"}})
        val = model.data(model.index(0, 0), STATUS_ROLE)
        assert val == {"quality_label": "Lossless"}

    def test_quality_role(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=42)],
                       status_cache={42: {"quality_category": "hires"}})
        val = model.data(model.index(0, 0), QUALITY_ROLE)
        assert val == "hires"

    def test_favorite_role(self):
        model = MediaItemTableModel()
        model.populate([_make_item(filepath="/m/x.flac")],
                       fav_set={"/m/x.flac"})
        val = model.data(model.index(0, 0), FAVORITE_ROLE)
        assert val is True

    def test_filepath_role(self):
        model = MediaItemTableModel()
        model.populate([_make_item(filepath="/m/song.flac")])
        val = model.data(model.index(0, 0), FILEPATH_ROLE)
        assert val == "/m/song.flac"

    def test_status_for_item(self):
        model = MediaItemTableModel()
        item = _make_item(fid=42)
        model.populate([item],
                       status_cache={42: {"quality_label": "Lossless"}})
        st = model.status_for_item(item)
        assert st == {"quality_label": "Lossless"}

    def test_favorite_set(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=1)], fav_set={"/m/a.flac"})
        assert model.favorite_set() == {"/m/a.flac"}

    def test_status_cache(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=42)],
                       status_cache={42: {"quality_label": "Lossless"}})
        assert model.status_cache() == {42: {"quality_label": "Lossless"}}

    def test_sort_by_title(self):
        model = MediaItemTableModel()
        items = [_make_item(fid=1, title="Z"), _make_item(fid=2, title="A")]
        model.populate(items)
        model.sort(2)
        assert model._items[0].title == "A"

    def test_sort_by_year_desc(self):
        model = MediaItemTableModel()
        items = [_make_item(fid=1, year=2020), _make_item(fid=2, year=1990)]
        model.populate(items)
        model.sort(5, Qt.DescendingOrder)
        assert model._items[0].year == 2020

    def test_refresh_status_empty_safe(self):
        model = MediaItemTableModel()
        model.refresh_status(status_cache={})  # should not crash

    def test_refresh_status_with_data(self):
        model = MediaItemTableModel()
        model.populate([_make_item(fid=42)])
        model.refresh_status(status_cache={42: {"quality_label": "Lossless"}})
        assert model._status_cache[42]["quality_label"] == "Lossless"

    def test_optional_replaygain_columns(self):
        model = MediaItemTableModel()
        model.set_optional_columns(["replaygain_track", "replaygain_album"])
        model.populate([_make_item(fid=1, replaygain_track=-6.5, replaygain_album=-8.0)])
        # replaygain_track col
        col_track = model.columnCount() - 2
        val = model.data(model.index(0, col_track))
        assert "-6.50 dB" in str(val)
        # replaygain_album col
        col_album = model.columnCount() - 1
        val = model.data(model.index(0, col_album))
        assert "-8.00 dB" in str(val)
