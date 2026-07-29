"""Test metadata round-trip: write tags, verify audio integrity."""

import struct
import tempfile
import shutil
from pathlib import Path
from hashlib import md5

import pytest

from metadata.tag_model import TrackTags


# ── Minimal audio file generators ──

_MINIMAL_MP3_HEADER = struct.pack(">I", 0xFFFB9000)
_MP3_FRAME_SIZE = 417


def _make_minimal_mp3(path: str, frames: int = 10):
    """Write a minimal MP3 with valid MPEG1 Layer III sync frames."""
    with open(path, "wb") as f:
        for _ in range(frames):
            f.write(_MINIMAL_MP3_HEADER)
            f.write(b"\x00" * (_MP3_FRAME_SIZE - 4))


def _make_minimal_flac(path: str):
    """Write a minimal FLAC with fLaC + STREAMINFO + VORBISCOMMENT."""
    streaminfo = struct.pack(">HH", 4096, 4096)
    streaminfo += b"\x00\x00\x00\x00\x00\x00"
    sr = 44100
    ch = 1
    bps = 15
    combined = int((sr << 44) | (ch << 41) | (bps << 36) | 0)
    streaminfo += struct.pack(">Q", combined)
    streaminfo += b"\x00" * 16

    si_header = struct.pack(">B", 0x00)
    si_header += struct.pack(">I", 34)[1:]

    vc_data = struct.pack(">I", 0) + struct.pack(">I", 0)
    vc_header = struct.pack(">B", 0x80 | 4)
    vc_header += struct.pack(">I", len(vc_data))[1:]

    with open(path, "wb") as f:
        f.write(b"fLaC")
        f.write(si_header)
        f.write(streaminfo)
        f.write(vc_header)
        f.write(vc_data)


# ── Fixtures ──


@pytest.fixture
def test_dir():
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def mp3_file(test_dir):
    path = str(test_dir / "test.mp3")
    _make_minimal_mp3(path)
    return path


@pytest.fixture
def flac_file(test_dir):
    path = str(test_dir / "test.flac")
    _make_minimal_flac(path)
    return path


# ── Round-trip tests ──


class TestMetadataRoundTrip:
    def test_mp3_write_and_readback(self, mp3_file):
        from metadata.tag_writer import write_tags

        original_hash = md5(open(mp3_file, "rb").read()).hexdigest()

        tags = TrackTags(filepath=mp3_file, artist="Test Artist", title="Roundtrip Title")
        tags.dirty = True
        ok = write_tags(tags)
        assert ok, "write_tags returned False"

        new_hash = md5(open(mp3_file, "rb").read()).hexdigest()
        assert new_hash != original_hash, "File should change after tag write"

        import mutagen

        audio = mutagen.File(mp3_file)
        assert audio is not None
        assert str(audio.get("TPE1", "")) == "Test Artist"

    def test_flac_write_and_readback(self, flac_file):
        from metadata.tag_writer import write_tags

        original_hash = md5(open(flac_file, "rb").read()).hexdigest()

        tags = TrackTags(filepath=flac_file, artist="FLAC Artist", album="FLAC Album")
        tags.dirty = True
        ok = write_tags(tags)
        assert ok, f"write_tags returned False: {tags.error}"

        new_hash = md5(open(flac_file, "rb").read()).hexdigest()
        assert new_hash != original_hash, "File should change after tag write"

        import mutagen

        audio = mutagen.File(flac_file)
        assert audio is not None
        assert str(audio.get("artist", [""])[0]) == "FLAC Artist"

    def test_file_still_openable_after_write(self, mp3_file, flac_file):
        from metadata.tag_writer import write_tags

        for path in (mp3_file, flac_file):
            tags = TrackTags(filepath=path, album="Still Openable")
            tags.dirty = True
            ok = write_tags(tags)
            assert ok

            import mutagen

            audio = mutagen.File(path)
            assert audio is not None

    def test_multiple_tag_writes_mp3(self, mp3_file):
        from metadata.tag_writer import write_tags

        tags = TrackTags(filepath=mp3_file, artist="Artist", title="Title", genre="Rock")
        tags.dirty = True
        ok = write_tags(tags)
        assert ok

        import mutagen

        audio = mutagen.File(mp3_file)
        assert audio is not None
        assert str(audio.get("TIT2", "")) == "Title"

        # Second write
        tags2 = TrackTags(filepath=mp3_file, artist="New Artist")
        tags2.dirty = True
        ok = write_tags(tags2)
        assert ok

        audio2 = mutagen.File(mp3_file)
        assert audio2 is not None
        assert str(audio2.get("TPE1", "")) == "New Artist"

    def test_verify_fails_restores_backup(self, test_dir):
        """Simulate verify failure by corrupting the temp after save."""
        from metadata.tag_writer import write_tags

        path = str(test_dir / "protect.flac")
        _make_minimal_flac(path)

        import mutagen

        original = mutagen.File(path)
        assert original is not None, "Minimal FLAC should be openable"

        original_hash = md5(open(path, "rb").read()).hexdigest()
        tags = TrackTags(filepath=path, artist="Should Restore")
        tags.dirty = True

        # Monkey-patch mutagen.File so the verify call fails
        _real_file = mutagen.File

        def _bad_verify(*a, **kw):
            return None

        mutagen.File = _bad_verify
        try:
            ok = write_tags(tags)
            assert not ok, "Should fail on VERIFY_FAILED"
        finally:
            mutagen.File = _real_file

        # Original file must be restored from backup
        import mutagen

        audio = mutagen.File(path)
        assert audio is not None, "File should be intact after restore"

    def test_missing_file_returns_false(self):
        from metadata.tag_writer import write_tags

        tags = TrackTags(filepath="/nonexistent/audio.mp3")
        ok = write_tags(tags)
        assert ok is False

    def test_nonexistent_mutagen_race(self, test_dir):
        """Path exists when checked but mutagen returns None."""
        from metadata.tag_writer import write_tags

        path = str(test_dir / "bogus.mp3")
        pathlib_path = Path(path)
        pathlib_path.write_text("not audio content")

        tags = TrackTags(filepath=path, artist="Ghost")
        tags.dirty = True
        ok = write_tags(tags)
        assert ok is False
