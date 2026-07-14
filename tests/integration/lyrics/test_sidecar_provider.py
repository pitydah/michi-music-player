import pytest
import tempfile
import os

from core.lyrics.models import TrackIdentity, LyricsDocument
from infrastructure.lyrics.sidecar_provider import FileSidecarProvider


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestFileSidecarProvider:
    def test_read_lrc(self, tmpdir):
        with open(os.path.join(tmpdir, "test.lrc"), "w") as f:
            f.write("[01:00.00]Hello World\n[02:00.00]Second line")
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="test", artist="", filepath="test.mp3")
        result = provider.read(tmpdir, identity)
        assert result.ok is True
        assert len(result.document.lines) == 2
        assert result.document.lines[0].text == "Hello World"

    def test_read_txt(self, tmpdir):
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("Plain text lyrics\nLine two")
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="test", filepath="test.mp3")
        result = provider.read(tmpdir, identity)
        assert result.ok is True
        assert result.document.plain_text == "Plain text lyrics\nLine two"

    def test_not_found(self, tmpdir):
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="nonexistent")
        result = provider.read(tmpdir, identity)
        assert result.ok is False

    def test_write_lrc(self, tmpdir):
        provider = FileSidecarProvider()
        doc = LyricsDocument(
            synced_text="[01:00.00]Test",
            identity=TrackIdentity(title="test", filepath="test.mp3"),
        )
        result = provider.write(tmpdir, doc)
        assert result.ok is True
        lrc_path = os.path.join(tmpdir, "test.lrc")
        assert os.path.exists(lrc_path)
        with open(lrc_path) as f:
            content = f.read()
        assert "Test" in content

    def test_atomic_write_no_temp_left(self, tmpdir):
        provider = FileSidecarProvider()
        doc = LyricsDocument(
            synced_text="[01:00.00]Atomic test",
            identity=TrackIdentity(title="atomic", filepath="atomic.mp3"),
        )
        provider.write(tmpdir, doc)
        temps = [f for f in os.listdir(tmpdir) if f.endswith(".tmp")]
        assert len(temps) == 0

    def test_write_and_read_back(self, tmpdir):
        provider = FileSidecarProvider()
        doc = LyricsDocument(
            synced_text="[01:00.00]Write and read",
            identity=TrackIdentity(title="wr", filepath="wr.mp3"),
        )
        provider.write(tmpdir, doc)
        result = provider.read(tmpdir, TrackIdentity(title="wr", filepath="wr.mp3"))
        assert result.ok is True
        assert result.document.lines[0].text == "Write and read"

    def test_path_traversal_rejected(self, tmpdir):
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="../etc/passwd", filepath="../etc/passwd.mp3")
        result = provider.read(tmpdir, identity)
        assert result.ok is False

    def test_invalid_directory(self, tmpdir):
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="test")
        result = provider.read(os.path.join(tmpdir, "nonexistent"), identity)
        assert result.ok is False

    def test_read_only_directory(self, tmpdir):
        provider = FileSidecarProvider()
        doc = LyricsDocument(
            plain_text="Test",
            identity=TrackIdentity(title="ro", filepath="ro.mp3"),
        )
        os.chmod(tmpdir, 0o444)
        result = provider.write(tmpdir, doc)
        os.chmod(tmpdir, 0o755)
        assert result.ok is False

    def test_delete(self, tmpdir):
        with open(os.path.join(tmpdir, "test.lrc"), "w") as f:
            f.write("[01:00.00]Delete me")
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="test", filepath="test.mp3")
        assert provider.delete(tmpdir, identity) is True
        assert os.path.exists(os.path.join(tmpdir, "test.lrc")) is False

    def test_unicode_filename(self, tmpdir):
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="Canción", artist="Artíst", filepath="cancion.mp3")
        doc = LyricsDocument(
            synced_text="[01:00.00]Unicode test",
            identity=identity,
        )
        result = provider.write(tmpdir, doc)
        assert result.ok is True
        result2 = provider.read(tmpdir, identity)
        assert result2.ok is True
