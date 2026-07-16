"""Disc detection service — real optical drive + ISO image support via udisksctl."""

from __future__ import annotations

import logging
import os
import re
import subprocess

logger = logging.getLogger("michi.audio_lab.disc_detection")

_TOC_TRACK_RE = re.compile(
    r"^\s*(\d+)\.\s+(\d+)\s+\[(\d+):(\d+)\.(\d+)\]\s+\d+\s+\[(\d+):(\d+)\.(\d+)\]"
)
_CDROM_PATHS = [
    "/dev/sr0", "/dev/sr1", "/dev/sr2",
    "/dev/cdrom", "/dev/cdrw", "/dev/cdrecorder",
]
_LOOP_LINE_RE = re.compile(r"Mapped file .+ as (/dev/loop\d+)\.")


class DiscDetectionService:
    def __init__(self):
        self._drives: list[str] = []
        self._current_drive: str = ""
        self._toc: dict = {"tracks": 0, "duration_seconds": 0, "track_list": []}
        self._loop_device: str = ""
        self._iso_path: str = ""
        self._is_iso_mode: bool = False

    def detect_drives(self) -> list[str]:
        self._drives = [p for p in _CDROM_PATHS if os.path.exists(p)]
        if not self._drives:
            self._drives = self._scan_sr_devices()
        return list(self._drives)

    @staticmethod
    def _scan_sr_devices() -> list[str]:
        drives = []
        for i in range(10):
            path = f"/dev/sr{i}"
            if os.path.exists(path):
                drives.append(path)
        return drives

    def detect_audio_cd(self, drive: str = "") -> bool:
        if not drive:
            drive = self.get_default_drive()
        if not drive or not os.path.exists(drive):
            return False
        return self._try_read_toc(drive)

    def get_default_drive(self) -> str:
        if self._drives:
            return self._drives[0]
        for p in _CDROM_PATHS:
            if os.path.exists(p):
                return p
        return ""

    def get_disc_toc(self, drive: str = "") -> dict:
        if not drive:
            drive = self.get_default_drive()
        if not drive:
            return self._toc
        self._try_read_toc(drive)
        return self._toc

    def get_track_count(self, drive: str = "") -> int:
        self.get_disc_toc(drive)
        return self._toc.get("tracks", 0)

    def get_track_durations(self, drive: str = "") -> list[float]:
        self.get_disc_toc(drive)
        return [t.get("duration", 0.0) for t in self._toc.get("track_list", [])]

    def _try_read_toc(self, drive: str) -> bool:
        import subprocess
        try:
            result = subprocess.run(
                ["cdparanoia", "-d", drive, "-Q"],
                capture_output=True, text=True, timeout=15,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            if not output:
                return False
            if "No medium found" in output or "Unable to open" in output:
                return False
            return self._parse_toc(output)
        except FileNotFoundError:
            logger.debug("cdparanoia not installed — TOC reading unavailable")
            return False
        except subprocess.TimeoutExpired:
            logger.debug("cdparanoia TOC read timed out")
            return False
        except Exception as e:
            logger.debug("cdparanoia TOC read failed: %s", e)
            return False

    def _parse_toc(self, output: str) -> bool:
        tracks = []
        total_seconds = 0
        for line in output.split("\n"):
            m = _TOC_TRACK_RE.search(line)
            if m:
                track_num = int(m.group(1))
                length_sectors = int(m.group(2))
                dur_m = int(m.group(3))
                dur_s = int(m.group(4))
                dur_f = int(m.group(5))
                duration = dur_m * 60 + dur_s + dur_f / 75.0
                tracks.append({
                    "number": track_num,
                    "duration": round(duration, 2),
                    "length_sectors": length_sectors,
                    "start_m": int(m.group(6)),
                    "start_s": int(m.group(7)),
                    "start_f": int(m.group(8)),
                })
                total_seconds += duration

        if tracks:
            self._toc = {
                "tracks": len(tracks),
                "duration_seconds": round(total_seconds, 1),
                "track_list": tracks,
            }
            return True
        return False

    # ── ISO image support ──

    def mount_iso(self, filepath: str) -> str:
        self.unmount_iso()
        if not os.path.isfile(filepath):
            return ""
        try:
            result = subprocess.run(
                ["udisksctl", "loop-setup", "-f", filepath],
                capture_output=True, text=True, timeout=20,
            )
            output = result.stdout.strip()
            m = _LOOP_LINE_RE.search(output)
            if m:
                self._loop_device = m.group(1)
                self._iso_path = filepath
                self._is_iso_mode = True
                self._current_drive = self._loop_device
                return self._loop_device
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.warning("ISO mount failed: %s", e)
        return ""

    def unmount_iso(self):
        if self._loop_device and os.path.exists(self._loop_device):
            try:
                subprocess.run(
                    ["udisksctl", "loop-delete", "-b", self._loop_device],
                    capture_output=True, timeout=10,
                )
            except Exception as e:
                logger.debug("ISO unmount failed: %s", e)
        self._loop_device = ""
        self._iso_path = ""
        self._is_iso_mode = False
        self._current_drive = ""

    @property
    def is_iso_mode(self) -> bool:
        return self._is_iso_mode

    @property
    def current_source_name(self) -> str:
        if self._is_iso_mode:
            return os.path.basename(self._iso_path)
        return self._current_drive
