"""DiscLabService — optical disc detection, ripping, and encoding with subprocess."""
from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger("michi.disc_lab")

CDROM_PATHS = ["/dev/cdrom", "/dev/cdrw", "/dev/dvd", "/dev/sr0", "/dev/sr1"]

AUDIO_EXTS = frozenset({".flac", ".wav", ".mp3", ".ogg", ".opus",
                         ".m4a", ".wv", ".ape", ".dsf", ".dff", ".aiff"})


class DiscLabService:
    def __init__(self, db=None, worker_manager=None, process_controller=None):
        self._db = db
        self._worker_manager = worker_manager
        self._process = process_controller
        self._cancelled = False
        self._rip_process: subprocess.Popen | None = None
        self._tracks: list[dict] = []
        self._extraction_format = "flac"
        self._destination = ""
        self._progress = 0.0

    @property
    def available(self) -> bool:
        return self._detect_drive() is not None

    def _detect_drive(self) -> str | None:
        for path in CDROM_PATHS:
            if os.path.exists(path):
                return path
        try:
            out = subprocess.run(["cdparanoia", "-Q"], capture_output=True,
                                 text=True, timeout=5)
            if out.returncode == 0:
                return "/dev/cdrom"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def detect_disc(self) -> dict:
        drive = self._detect_drive()
        if not drive:
            return {"ok": False, "detected": False, "error": "NO_DRIVE"}
        try:
            out = subprocess.run(["cdparanoia", "-Q"], capture_output=True,
                                 text=True, timeout=10)
            if out.returncode != 0:
                return {"ok": False, "detected": False, "error": "NO_DISC"}
            lines = out.stdout.strip().split("\n")
            tracks = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].isdigit():
                    tracks.append({"number": int(parts[0]), "offset": parts[1] if len(parts) > 1 else ""})
            self._tracks = [
                {"number": t["number"], "title": f"Track {t['number']:02d}",
                 "artist": "", "duration": 0}
                for t in tracks
            ]
            return {"ok": True, "detected": True, "drive": drive,
                    "tracks": len(self._tracks), "track_list": self._tracks}
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"ok": False, "detected": False, "error": str(e)}

    def get_track_list(self) -> list:
        return self._tracks

    def rip_plan(self, fmt: str = "flac", quality: str = "lossless") -> dict:
        if not self._tracks:
            base = self.detect_disc()
            if not base.get("detected"):
                return {"ok": False, "error": "NO_DISC"}
        self._extraction_format = fmt
        est_mb = len(self._tracks) * (50 if fmt == "flac" else 35 if fmt == "wav" else 10)
        return {"ok": True, "format": fmt, "quality": quality,
                "estimated_size_mb": est_mb, "tracks": len(self._tracks),
                "track_list": self._tracks}

    def start_rip(self, plan: dict) -> dict:
        if self._rip_process is not None:
            return {"ok": False, "error": "ALREADY_RIPPING"}
        drive = self._detect_drive()
        if not drive:
            return {"ok": False, "error": "NO_DRIVE"}
        dst = self._destination or os.path.expanduser("~/Music/rips")
        os.makedirs(dst, exist_ok=True)
        self._cancelled = False
        self._progress = 0.0
        try:
            for i, track in enumerate(self._tracks):
                if self._cancelled:
                    break
                tnum = track["number"]
                outpath = os.path.join(dst, f"track_{tnum:02d}.wav")
                self._rip_process = subprocess.Popen(
                    ["cdparanoia", f"{tnum}", outpath],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self._rip_process.wait(timeout=300)
                self._progress = (i + 1) / len(self._tracks)
                if self._extraction_format == "flac" and os.path.exists(outpath):
                    flac_out = outpath.replace(".wav", ".flac")
                    subprocess.run(["flac", outpath, "-o", flac_out, "--best"],
                                   capture_output=True, timeout=120)
                    os.remove(outpath)
            self._rip_process = None
            return {"ok": True, "destination": dst, "tracks": len(self._tracks),
                    "progress": self._progress, "format": self._extraction_format}
        except Exception as e:
            self._rip_process = None
            return {"ok": False, "error": str(e)}

    def cancel(self):
        self._cancelled = True
        if self._rip_process:
            self._rip_process.terminate()
            self._rip_process = None

    def get_progress(self) -> float:
        return self._progress

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        self.cancel()
