"""Tests for folder_index — caching, file listing, subfolder listing, classification."""

import os
import tempfile



class TestListAudioFiles:
    def test_empty_directory(self):
        from library.folder_index import list_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            files = list_audio_files(tmpdir)
            assert files == []

    def test_finds_audio_files(self):
        from library.folder_index import list_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("song.mp3", "track.flac", "album/cover.jpg"):
                p = os.path.join(tmpdir, name)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w").close()
            files = list_audio_files(tmpdir)
            paths = [os.path.basename(f) for f in files]
            assert "song.mp3" in paths
            assert "track.flac" in paths

    def test_ignores_hidden_files(self):
        from library.folder_index import list_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in (".hidden.mp3", "visible.mp3"):
                open(os.path.join(tmpdir, name), "w").close()
            files = list_audio_files(tmpdir)
            names = [os.path.basename(f) for f in files]
            assert ".hidden.mp3" not in names
            assert "visible.mp3" in names

    def test_ignores_non_audio(self):
        from library.folder_index import list_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("song.mp3", "doc.txt", "image.png"):
                open(os.path.join(tmpdir, name), "w").close()
            files = list_audio_files(tmpdir)
            assert len(files) == 1


class TestListSubfolders:
    def test_empty_directory(self):
        from library.folder_index import list_subfolders, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            assert list_subfolders(tmpdir) == []

    def test_finds_subfolders(self):
        from library.folder_index import list_subfolders, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("Music", "Podcasts", ".hidden"):
                os.makedirs(os.path.join(tmpdir, name), exist_ok=True)
            dirs = list_subfolders(tmpdir)
            names = [os.path.basename(d) for d in dirs]
            assert "Music" in names
            assert "Podcasts" in names
            assert ".hidden" not in names


class TestCache:
    def test_cache_hit(self):
        from library.folder_index import list_audio_files, clear_cache, _cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.mp3"), "w").close()
            list_audio_files(tmpdir)
            assert f"files:{tmpdir}" in _cache

    def test_clear_cache(self):
        from library.folder_index import list_audio_files, clear_cache, _cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.mp3"), "w").close()
            list_audio_files(tmpdir)
            clear_cache()
            assert f"files:{tmpdir}" not in _cache


class TestClassifyFile:
    def test_audio_supported(self):
        from library.folder_index import classify_file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            entry = classify_file(tmp)
            assert entry.kind == "audio"
            assert entry.is_supported_audio is True
            assert entry.format_label == "MP3"
        finally:
            os.unlink(tmp)

    def test_folder(self):
        from library.folder_index import classify_file
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = classify_file(tmpdir)
            assert entry.kind == "folder"

    def test_cover_file(self):
        from library.folder_index import classify_file
        for name in ("cover.jpg", "folder.png", "front.jpg", "portada.png"):
            with tempfile.TemporaryDirectory() as tmpdir:
                p = os.path.join(tmpdir, name)
                open(p, "w").close()
                entry = classify_file(p)
                assert entry.kind == "cover", f"Expected cover for {name}, got {entry.kind}"

    def test_playlist_file(self):
        from library.folder_index import classify_file
        for ext in (".m3u", ".m3u8", ".pls", ".xspf"):
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"data")
                tmp = f.name
            try:
                entry = classify_file(tmp)
                assert entry.kind == "playlist", f"Expected playlist for {ext}, got {entry.kind}"
            finally:
                os.unlink(tmp)

    def test_cue_file(self):
        from library.folder_index import classify_file
        with tempfile.NamedTemporaryFile(suffix=".cue", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            entry = classify_file(tmp)
            assert entry.kind == "cue"
        finally:
            os.unlink(tmp)

    def test_log_file(self):
        from library.folder_index import classify_file
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            entry = classify_file(tmp)
            assert entry.kind == "log"
        finally:
            os.unlink(tmp)

    def test_text_file(self):
        from library.folder_index import classify_file
        for ext in (".txt", ".nfo"):
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"data")
                tmp = f.name
            try:
                entry = classify_file(tmp)
                assert entry.kind == "text", f"Expected text for {ext}, got {entry.kind}"
            finally:
                os.unlink(tmp)

    def test_unknown(self):
        from library.folder_index import classify_file
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            entry = classify_file(tmp)
            assert entry.kind == "unknown"
        finally:
            os.unlink(tmp)

    def test_missing_path(self):
        from library.folder_index import classify_file
        entry = classify_file("/nonexistent/file.mp3")
        assert entry.kind == "error"


class TestIsCoverFile:
    def test_known_covers(self):
        from library.folder_index import is_cover_file
        assert is_cover_file("/music/cover.jpg") is True
        assert is_cover_file("/music/folder.png") is True
        assert is_cover_file("/music/portada.jpg") is True
        assert is_cover_file("/music/song.mp3") is False
        assert is_cover_file("/music/random.jpg") is False


class TestListFolderEntries:
    def test_empty_directory(self):
        from library.folder_index import list_folder_entries, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = list_folder_entries(tmpdir)
            assert entries == []

    def test_mixed_directory(self):
        from library.folder_index import list_folder_entries, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            for name in ("song.mp3", "cover.jpg", "playlist.m3u", "album.cue", "readme.txt"):
                open(os.path.join(tmpdir, name), "w").close()
            entries = list_folder_entries(tmpdir)
            kinds = {e.name: e.kind for e in entries}
            assert kinds.get("sub") == "folder"
            assert kinds.get("song.mp3") == "audio"
            assert kinds.get("cover.jpg") == "cover"
            assert kinds.get("playlist.m3u") == "playlist"
            assert kinds.get("album.cue") == "cue"
            assert kinds.get("readme.txt") == "text"


class TestWalkAudioFiles:
    def test_recursive(self):
        from library.folder_index import walk_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "a", "b"), exist_ok=True)
            for p in ("song.mp3", "a/track.flac", "a/b/deep.ogg"):
                fp = os.path.join(tmpdir, p)
                open(fp, "w").close()
            files = walk_audio_files(tmpdir)
            assert len(files) == 3
            assert any(f.endswith("song.mp3") for f in files)
            assert any(f.endswith("track.flac") for f in files)
            assert any(f.endswith("deep.ogg") for f in files)

    def test_max_depth(self):
        from library.folder_index import walk_audio_files, clear_cache
        clear_cache()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "a", "b"), exist_ok=True)
            for p in ("song.mp3", "a/track.flac", "a/b/deep.ogg"):
                fp = os.path.join(tmpdir, p)
                open(fp, "w").close()
            files = walk_audio_files(tmpdir, max_depth=1)
            assert len(files) == 2
            assert any(f.endswith("song.mp3") for f in files)
            assert any(f.endswith("track.flac") for f in files)
