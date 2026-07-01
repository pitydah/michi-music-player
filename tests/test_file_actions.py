"""Tests: FileActions — open_containing_folder edge cases."""

from unittest.mock import patch

from core.file_actions import open_containing_folder


class TestFileActions:

    def test_empty_path_returns_false(self):
        assert open_containing_folder("") is False

    def test_nonexistent_path_returns_false(self):
        assert open_containing_folder("/nonexistent_dir_12345/song.flac") is False

    def test_no_path_returns_false(self):
        assert open_containing_folder(None) is False

    @patch("core.file_actions.subprocess.Popen")
    @patch("core.file_actions.os.path.isdir", return_value=True)
    def test_valid_path_returns_true(self, mock_isdir, mock_popen):
        result = open_containing_folder("/home/user/Music/song.flac")
        assert result is True
        mock_popen.assert_called_once_with(["xdg-open", "/home/user/Music"])

    @patch("core.file_actions.os.path.isdir", return_value=True)
    def test_subprocess_exception_returns_false(self, mock_isdir):
        with patch("core.file_actions.subprocess.Popen", side_effect=FileNotFoundError("no xdg-open")):
            result = open_containing_folder("/home/user/Music/song.flac")
            assert result is False
