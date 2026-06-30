"""Tests: MediaItemTableModel — populate, data roles, sorting, tooltips."""

from library.media_item import MediaItem
from library.mediaitem_table_model import MediaItemTableModel


def _make_item(filepath="/music/a.flac", title="Song", artist="Artist",
               album="Album", genre="Rock", year=2000, duration=180.0,
               ext=".flac", sample_rate=44100, bit_depth=16, channels=2,
               bitrate=1411, bpm=120, fid=1):
    return MediaItem(
        id=fid, filepath=filepath, title=title, artist=artist,
        album=album, genre=genre, year=year, duration=duration,
        ext=ext, sample_rate=sample_rate, bit_depth=bit_depth,
        channels=channels, bitrate=bitrate, bpm=bpm,
        filename="a.flac", directory="/music", kind="audio", size=1000000,
        mtime=0.0, track_number=1, composer="", albumartist="",
        disc_number=0, disc_total=0, track_total=0, mb_track_id="",
        mb_album_id="", mb_albumartist_id="", isrc="", label="",
        conductor="", compilation=False, media_type="", encoder="",
        copyright="", originaldate="", remixer="", grouping="", mood="",
        replaygain_track=0.0, replaygain_album=0.0,
        replaygain_track_peak=0.0, play_count=0, last_played=0.0,
        rating=0, created_at=0.0, updated_at=0.0, last_scanned=0.0,
        track_uid="",
    )


class TestMediaItemTableModel:

    def test_row_count(self):
        model = MediaItemTableModel()
        model.populate([_make_item(), _make_item(fid=2)])
        assert model.rowCount() == 2

    def test_column_count_base(self):
        model = MediaItemTableModel()
        model.populate([])
        assert model.columnCount() == 11  # base columns

    def test_column_count_with_optional(self):
        model = MediaItemTableModel()
        model.set_optional_columns(["bitrate", "bpm"])
        model.populate([])
        assert model.columnCount() == 13  # 11 base + 2 optional

    def test_display_title(self):
        model = MediaItemTableModel()
        item = _make_item(title="My Song")
        model.populate([item])
        val = model.data(model.index(0, 2))
        assert val == "My Song"

    def test_display_artist(self):
        model = MediaItemTableModel()
        model.populate([_make_item(artist="My Artist")])
        val = model.data(model.index(0, 3))
        assert val == "My Artist"

    def test_display_duration(self):
        model = MediaItemTableModel()
        model.populate([_make_item(duration=185.0)])
        val = model.data(model.index(0, 7))
        assert val == "3:05"

    def test_display_format(self):
        model = MediaItemTableModel()
        model.populate([_make_item(ext=".flac")])
        val = model.data(model.index(0, 8))
        assert val == "FLAC"

    def test_tooltip_contains_tech(self):
        model = MediaItemTableModel()
        model.populate([_make_item(sample_rate=96000, bit_depth=24)])
        tip = model.data(model.index(0, 0), role=3)  # ToolTipRole
        assert tip is not None
        assert "96kHz" in tip

    def test_sort_by_title(self):
        model = MediaItemTableModel()
        model.populate([_make_item(title="Z"), _make_item(title="A", fid=2)])
        model.sort(2)  # title column, ascending
        assert model._items[0].title == "A"
        assert model._items[1].title == "Z"

    def test_sort_by_year_desc(self):
        model = MediaItemTableModel()
        model.populate([_make_item(year=2020), _make_item(year=1990, fid=2)])
        from PySide6.QtCore import Qt
        model.sort(5, Qt.DescendingOrder)
        assert model._items[0].year == 2020
        assert model._items[1].year == 1990

    def test_header_data(self):
        from PySide6.QtCore import Qt
        model = MediaItemTableModel()
        model.populate([])
        title = model.headerData(2, Qt.Horizontal)
        assert title == "Título"

    def test_item_at(self):
        model = MediaItemTableModel()
        a = _make_item(title="A", fid=1)
        model.populate([a, _make_item(title="B", fid=2)])
        assert model.item_at(0).title == "A"
        assert model.item_at(1).title == "B"
        assert model.item_at(99) is None

    def test_optional_display_bitrate(self):
        model = MediaItemTableModel()
        model.set_optional_columns(["bitrate"])
        model.populate([_make_item(bitrate=320000)])
        col = model.columnCount() - 1
        val = model.data(model.index(0, col))
        assert val == "320k"

    def test_optional_display_sample_rate(self):
        model = MediaItemTableModel()
        model.set_optional_columns(["sample_rate"])
        model.populate([_make_item(sample_rate=96000)])
        col = model.columnCount() - 1
        val = model.data(model.index(0, col))
        assert val == "96kHz"
