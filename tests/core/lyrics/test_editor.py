import pytest
from core.lyrics.editor import LyricsEditorService
from core.lyrics.models import LyricsDocument, LyricsLine


@pytest.fixture
def editor():
    return LyricsEditorService()


@pytest.fixture
def doc():
    d = LyricsDocument()
    d.lines = [
        LyricsLine(line_id="0", start_ms=1000, end_ms=2000, text="Line A"),
        LyricsLine(line_id="1", start_ms=2000, end_ms=3000, text="Line B"),
        LyricsLine(line_id="2", start_ms=3000, end_ms=4000, text="Line C"),
    ]
    return d


class TestLyricsEditorService:
    def test_load_initial_state(self, editor, doc):
        editor.load(doc)
        assert editor.current is not None
        assert not editor.is_dirty

    def test_replace_plain_text(self, editor, doc):
        editor.load(doc)
        editor.replace_plain_text("New text")
        assert editor.current.plain_text == "New text"
        assert editor.is_dirty

    def test_replace_synced_text(self, editor, doc):
        editor.load(doc)
        editor.replace_synced_text("[01:00.00]New line")
        assert editor.is_dirty
        assert len(editor.current.lines) == 1
        assert editor.current.lines[0].text == "New line"

    def test_shift_all_positive(self, editor, doc):
        editor.load(doc)
        editor.shift_all(500)
        assert editor.current.lines[0].start_ms == 1500
        assert editor.current.lines[1].start_ms == 2500

    def test_shift_all_negative(self, editor, doc):
        editor.load(doc)
        editor.shift_all(-500)
        assert editor.current.lines[0].start_ms == 500
        assert editor.current.lines[1].start_ms == 1500

    def test_shift_all_no_negative(self, editor, doc):
        editor.load(doc)
        editor.shift_all(-5000)
        assert editor.current.lines[0].start_ms >= 0

    def test_insert_line(self, editor, doc):
        editor.load(doc)
        editor.insert_line(after_idx=0, text="New Line", start_ms=1500)
        assert len(editor.current.lines) == 4
        assert editor.current.lines[1].text == "New Line"

    def test_delete_line(self, editor, doc):
        editor.load(doc)
        editor.delete_line("1")
        assert len(editor.current.lines) == 2
        assert "B" not in [ln.text for ln in editor.current.lines]

    def test_undo(self, editor, doc):
        editor.load(doc)
        editor.replace_plain_text("Changed")
        assert editor.current.plain_text == "Changed"
        editor.undo()
        assert editor.current.plain_text == ""

    def test_undo_redo(self, editor, doc):
        editor.load(doc)
        editor.replace_plain_text("V1")
        editor.replace_plain_text("V2")
        editor.undo()
        assert editor.current.plain_text == "V1"
        editor.redo()
        assert editor.current.plain_text == "V2"

    def test_undo_empty_stack(self, editor):
        result = editor.undo()
        assert result.ok is False

    def test_redo_empty_stack(self, editor):
        result = editor.redo()
        assert result.ok is False

    def test_clear_timestamps(self, editor, doc):
        editor.load(doc)
        editor.clear_timestamps()
        for line in editor.current.lines:
            assert line.start_ms == 0.0
            assert line.end_ms == 0.0

    def test_normalize_timestamps(self, editor, doc):
        editor.load(doc)
        editor.current.lines[0].end_ms = 0
        editor.normalize_timestamps()
        assert editor.current.lines[0].end_ms == 2000

    def test_set_line_timestamp(self, editor, doc):
        editor.load(doc)
        editor.set_line_timestamp("0", 5000, 6000)
        assert editor.current.lines[0].start_ms == 5000
        assert editor.current.lines[0].end_ms == 6000

    def test_set_line_timestamp_no_negative(self, editor, doc):
        editor.load(doc)
        result = editor.set_line_timestamp("0", -1, -1)
        assert result.ok is False

    def test_split_line(self, editor, doc):
        editor.load(doc)
        editor.split_line("1", 3)
        assert len(editor.current.lines) == 4

    def test_merge_lines(self, editor, doc):
        editor.load(doc)
        editor.merge_lines("0", "1")
        assert len(editor.current.lines) == 2
        assert "Line A Line B" in editor.current.lines[0].text

    def test_validate_no_issues(self, editor, doc):
        editor.load(doc)
        assert editor.validate() == []

    def test_validate_negative_timestamp(self, editor, doc):
        editor.load(doc)
        editor.current.lines[0].start_ms = -100
        assert len(editor.validate()) >= 1

    def test_validate_unsorted(self, editor, doc):
        editor.load(doc)
        editor.current.lines[2].start_ms = 500
        warnings = editor.validate()
        assert len(warnings) >= 1

    def test_is_dirty_after_change(self, editor, doc):
        editor.load(doc)
        assert not editor.is_dirty
        editor.replace_plain_text("Changed")
        assert editor.is_dirty
