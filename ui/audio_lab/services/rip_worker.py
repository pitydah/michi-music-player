"""Rip worker — QProcess wrapper for cdparanoia CD ripping with progress signals."""

from __future__ import annotations

import logging
import os
import re

from PySide6.QtCore import QObject, Signal, QProcess

logger = logging.getLogger("michi.audio_lab.rip_worker")

_PROGRESS_RE = re.compile(
    r"(?:outputting|Ripping)\s+to\s+.+?:\s+\[?\s*(\d+):(\d+)\.(\d+)\s*\].*"
)
_PERCENT_RE = re.compile(r"(\d+)%")


class RipWorker(QObject):
    progress_changed = Signal(str, int, float, str)
    track_started = Signal(str, int, int)
    track_finished = Signal(str, int, str)
    finished = Signal(str, dict)
    error_occurred = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._job_id: str = ""
        self._current_track: int = 0
        self._total_tracks: int = 0
        self._track_outputs: dict[int, str] = {}
        self._process: QProcess | None = None
        self._buffer: str = ""

    def rip_track(self, job_id: str, drive: str, track_num: int,
                  output_path: str, start_sectors: int = 0,
                  end_sectors: int = 0):
        self._job_id = job_id
        self._current_track = track_num

        args = ["-d", drive, "--stderr-progress"]
        if start_sectors > 0 and end_sectors > start_sectors:
            args.append(f"{start_sectors}[00:00.00]-{end_sectors}[00:00.00]")
        else:
            args.append(str(track_num))
        args.append(output_path)

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.start("cdparanoia", args)

        self.track_started.emit(job_id, track_num, self._total_tracks)

    def rip_all_tracks(self, job_id: str, drive: str, track_list: list[dict],
                       output_dir: str, extraction_mode: str = "fast",
                       stop_on_error: bool = False):
        self._job_id = job_id
        self._total_tracks = len(track_list)
        self._track_outputs = {}
        self._extraction_mode = extraction_mode
        self._stop_on_error = stop_on_error
        self._error_count = 0

        for track in track_list:
            tnum = track.get("number", 0)
            fname = f"track_{tnum:02d}.wav"
            self._track_outputs[tnum] = os.path.join(output_dir, fname)

        self._rip_next(job_id, drive, track_list, output_dir, 0)

    def _rip_next(self, job_id: str, drive: str, track_list: list[dict],
                  output_dir: str, idx: int):
        if idx >= len(track_list):
            status = "completed_with_errors" if self._error_count > 0 else "completed"
            self.finished.emit(job_id, {"status": status, "tracks_ripped": len(track_list) - self._error_count, "errors": self._error_count})
            return

        track = track_list[idx]
        tnum = track.get("number", 0)
        out_path = self._track_outputs.get(tnum, os.path.join(output_dir, f"track_{tnum:02d}.wav"))

        self._current_track = tnum
        args = ["-d", drive, "--stderr-progress"]
        if self._extraction_mode == "safe":
            args.append("--never-skip=1")
        elif self._extraction_mode == "accurate":
            pass  # whipper not available yet
        args.extend([str(tnum), out_path])

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(
            lambda ec, es, j=job_id, tl=track_list, od=output_dir, n=idx, drv=drive:
            self._on_track_done(ec, es, j, tl, od, n, drv)
        )
        self._process.errorOccurred.connect(self._on_error)
        self._process.start("cdparanoia", args)

        self.track_started.emit(job_id, tnum, self._total_tracks)
        progress = 0.0
        if self._total_tracks > 0:
            progress = idx / self._total_tracks
        self.progress_changed.emit(job_id, tnum, progress, "running")

    def _on_track_done(self, exit_code: int, _exit_status,
                       job_id: str, track_list: list[dict],
                       output_dir: str, idx: int, drive: str):
        out_path = self._track_outputs.get(self._current_track, "")
        self.track_finished.emit(job_id, self._current_track, out_path)

        if exit_code != 0:
            self._error_count += 1
            p = (idx + 1) / self._total_tracks if self._total_tracks else 1.0
            self.progress_changed.emit(job_id, self._current_track, p, "error")
            if self._stop_on_error:
                status = "completed_with_errors" if self._error_count > 0 else "completed"
                self.finished.emit(job_id, {"status": status, "tracks_ripped": self._total_tracks - self._error_count, "errors": self._error_count})
                return

        status = "completed" if exit_code == 0 else "error"
        progress = 0.0
        if self._total_tracks > 0:
            progress = (idx + 1) / self._total_tracks
        self.progress_changed.emit(job_id, self._current_track, progress, status)

        self._rip_next(job_id, drive, track_list, output_dir, idx + 1)

    def cancel(self):
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            if not self._process.waitForFinished(2000):
                self._process.kill()

    def _on_output(self):
        if not self._process:
            return
        data = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
        self._buffer += data
        for line in self._buffer.split("\n"):
            line = line.strip()
            if not line:
                continue
            perc_match = _PERCENT_RE.search(line)
            if perc_match:
                pct = float(perc_match.group(1)) / 100.0
                if self._total_tracks > 1:
                    progress = (self._current_track - 1 + pct) / self._total_tracks
                else:
                    progress = pct
                self.progress_changed.emit(self._job_id, self._current_track, progress, "running")
        if self._buffer.endswith("\n"):
            self._buffer = ""

    def _on_finished(self, exit_code: int, _exit_status):
        if exit_code != 0 and self._process:
            err = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
            logger.warning("cdparanoia exit %d: %s", exit_code, err[:200] if err else "")
            self.progress_changed.emit(self._job_id, self._current_track, 1.0, "error")

    def _on_error(self, error):
        err_msg = "Unknown error"
        if error == QProcess.FailedToStart:
            err_msg = "cdparanoia no se pudo iniciar"
        elif error == QProcess.Crashed:
            err_msg = "cdparanoia termino inesperadamente"
        elif error == QProcess.Timedout:
            err_msg = "cdparanoia excedio el tiempo de espera"
        self.error_occurred.emit(self._job_id, err_msg)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning
