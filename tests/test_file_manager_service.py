"""Tests for FileManagerService — desktop detection, open/reveal commands."""

import os
import tempfile
from unittest.mock import patch

from core.file_manager_service import FileManagerService


class TestDesktopDetection:
    def test_detect_kde(self):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=True):
            assert "KDE" in FileManagerService.detect_desktop()

    def test_detect_gnome(self):
        with patch.dict(os.environ, {"DESKTOP_SESSION": "gnome"}, clear=True):
            assert "gnome" in FileManagerService.detect_desktop()

    def test_detect_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            assert FileManagerService.detect_desktop() == ""


class TestPreferredFileManager:
    def test_prefers_dolphin_on_kde(self):
        with patch.object(FileManagerService, 'available_file_managers',
                          return_value=[("Dolphin", "dolphin"),
                                        ("Nautilus", "nautilus")]):
            with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=True):
                pref = FileManagerService.preferred_file_manager()
                assert pref == ("Dolphin", "dolphin")

    def test_prefers_nautilus_on_gnome(self):
        with patch.object(FileManagerService, 'available_file_managers',
                          return_value=[("Dolphin", "dolphin"),
                                        ("Nautilus", "nautilus")]):
            with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=True):
                pref = FileManagerService.preferred_file_manager()
                assert pref == ("Nautilus", "nautilus")

    def test_fallback_to_first_available(self):
        with patch.object(FileManagerService, 'available_file_managers',
                          return_value=[("Thunar", "thunar")]):
            pref = FileManagerService.preferred_file_manager()
            assert pref == ("Thunar", "thunar")

    def test_no_managers(self):
        with patch.object(FileManagerService, 'available_file_managers',
                          return_value=[]):
            assert FileManagerService.preferred_file_manager() is None


class TestOpenFolder:
    def test_invalid_path(self):
        assert FileManagerService.open_folder("") is False
        assert FileManagerService.open_folder("/nonexistent_path") is False

    def test_build_open_command_with_preferred(self):
        with patch.object(FileManagerService, 'preferred_file_manager',
                          return_value=("Dolphin", "dolphin")):
            cmd = FileManagerService.build_open_command("/tmp")
            assert cmd == ["dolphin", "/tmp"]

    def test_build_open_command_fallback(self):
        with patch.object(FileManagerService, 'preferred_file_manager',
                          return_value=None):
            cmd = FileManagerService.build_open_command("/tmp")
            assert cmd == ["xdg-open", "/tmp"]

    @patch("subprocess.Popen")
    def test_open_folder_calls_popen(self, mock_popen):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(FileManagerService, 'preferred_file_manager',
                              return_value=("Dolphin", "dolphin")):
                assert FileManagerService.open_folder(tmpdir) is True
                mock_popen.assert_called_once_with(
                    ["dolphin", tmpdir], start_new_session=True)


class TestRevealFile:
    def test_reveal_nonexistent(self):
        assert FileManagerService.reveal_file("/nonexistent.mp3") is False

    @patch("subprocess.Popen")
    def test_reveal_with_dolphin(self, mock_popen):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            with patch.object(FileManagerService, 'preferred_file_manager',
                              return_value=("Dolphin", "dolphin")):
                assert FileManagerService.reveal_file(tmp) is True
                mock_popen.assert_called_once_with(
                    ["dolphin", "--select", tmp], start_new_session=True)
        finally:
            os.unlink(tmp)

    @patch("subprocess.Popen")
    def test_reveal_with_nautilus(self, mock_popen):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            with patch.object(FileManagerService, 'preferred_file_manager',
                              return_value=("Nautilus", "nautilus")):
                assert FileManagerService.reveal_file(tmp) is True
                mock_popen.assert_called_once_with(
                    ["nautilus", "--select", tmp], start_new_session=True)
        finally:
            os.unlink(tmp)

    @patch("subprocess.Popen")
    def test_reveal_with_thunar(self, mock_popen):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            with patch.object(FileManagerService, 'preferred_file_manager',
                              return_value=("Thunar", "thunar")):
                assert FileManagerService.reveal_file(tmp) is True
                mock_popen.assert_called_once_with(
                    ["thunar", tmp], start_new_session=True)
        finally:
            os.unlink(tmp)


class TestOpenTerminal:
    def test_invalid_path(self):
        assert FileManagerService.open_terminal_here("") is False

    @patch("shutil.which")
    @patch("subprocess.Popen")
    def test_konsole_preferred(self, mock_popen, mock_which):
        def which_side(binary):
            return {"konsole": "/usr/bin/konsole",
                    "gnome-terminal": "/usr/bin/gnome-terminal"}.get(binary)
        mock_which.side_effect = which_side
        with tempfile.TemporaryDirectory() as tmpdir:
            assert FileManagerService.open_terminal_here(tmpdir) is True
            mock_popen.assert_called_once_with(
                ["konsole", "--workdir", tmpdir], start_new_session=True)

    @patch("shutil.which")
    @patch("subprocess.Popen")
    def test_gnome_terminal_fallback(self, mock_popen, mock_which):
        def which_side(binary):
            return {"gnome-terminal": "/usr/bin/gnome-terminal"}.get(binary)
        mock_which.side_effect = which_side
        with tempfile.TemporaryDirectory() as tmpdir:
            assert FileManagerService.open_terminal_here(tmpdir) is True
            mock_popen.assert_called_once_with(
                ["gnome-terminal", f"--working-directory={tmpdir}"],
                start_new_session=True)

    @patch("shutil.which")
    def test_no_terminal_available(self, mock_which):
        mock_which.return_value = None
        with tempfile.TemporaryDirectory() as tmpdir:
            assert FileManagerService.open_terminal_here(tmpdir) is False

    def test_build_open_command_for_file(self):
        with patch.object(FileManagerService, 'preferred_file_manager',
                          return_value=("Dolphin", "dolphin")):
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(b"data")
                tmp = f.name
            try:
                cmd = FileManagerService.build_open_command(tmp)
                assert cmd == ["dolphin", os.path.dirname(tmp)]
            finally:
                os.unlink(tmp)


class TestAvailableFileManagers:
    @patch("shutil.which")
    def test_available(self, mock_which):
        def which_side(binary):
            available = {"dolphin": "/usr/bin/dolphin",
                         "nautilus": "/usr/bin/nautilus"}
            return available.get(binary)
        mock_which.side_effect = which_side
        fms = FileManagerService.available_file_managers()
        names = {n for n, _ in fms}
        assert "Dolphin" in names
        assert "Nautilus" in names
        assert "Nemo" not in names

    @patch("shutil.which")
    def test_all_unavailable(self, mock_which):
        mock_which.return_value = None
        assert FileManagerService.available_file_managers() == []


class TestPreferredName:
    def test_with_preferred(self):
        with patch.object(FileManagerService, 'preferred_file_manager',
                          return_value=("Dolphin", "dolphin")):
            assert FileManagerService.preferred_file_manager_name() == "Dolphin"

    def test_without_preferred(self):
        with patch.object(FileManagerService, 'preferred_file_manager',
                          return_value=None):
            assert FileManagerService.preferred_file_manager_name() == "Gestor de archivos"
