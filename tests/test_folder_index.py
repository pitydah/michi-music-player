"""Tests for folder_index — file listing and edge cases."""

import pytest

from library.folder_index import list_audio_files, list_subfolders, get_audio_tree


@pytest.fixture
def audio_tree(tmp_path):
    """Create a temp directory structure with audio files and subfolders."""
    # Files
    (tmp_path / "song.mp3").touch()
    (tmp_path / "track.flac").touch()
    (tmp_path / "image.jpg").touch()          # non-audio
    (tmp_path / ".hidden.mp3").touch()         # hidden
    (tmp_path / "notes.txt").touch()           # non-audio

    # Subfolders
    sub = tmp_path / "album"
    sub.mkdir()
    (sub / "track01.ogg").touch()
    (sub / "track02.wav").touch()

    hidden_sub = tmp_path / ".secret"
    hidden_sub.mkdir()
    (hidden_sub / "ghost.mp3").touch()

    return tmp_path


def test_list_audio_files(audio_tree):
    files = list_audio_files(str(audio_tree))
    assert len(files) == 2  # song.mp3, track.flac (not .jpg, .txt, .hidden)
    assert any("song.mp3" in f for f in files)
    assert any("track.flac" in f for f in files)


def test_list_subfolders(audio_tree):
    dirs = list_subfolders(str(audio_tree))
    assert len(dirs) == 1  # album (not .secret)
    assert any("album" in d for d in dirs)


def test_list_audio_hidden_ignored(audio_tree):
    files = list_audio_files(str(audio_tree))
    for f in files:
        assert ".hidden" not in f
        assert ".secret" not in f


def test_list_nonexistent():
    assert list_audio_files("/nonexistent/path") == []
    assert list_subfolders("/nonexistent/path") == []


def test_get_audio_tree(audio_tree):
    tree = get_audio_tree(str(audio_tree), max_depth=2)
    assert len(tree["files"]) == 2
    assert "album" in tree["folders"]
    assert len(tree["folders"]["album"]["files"]) == 2
