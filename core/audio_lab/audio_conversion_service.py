"""AudioConversionService — convert audio files between formats.

Flow: selection → profile → format → codec → quality → sample rate →
bit depth → channel policy → metadata → artwork → ReplayGain →
output folder → naming → collisions → space → preview → confirm →
job → progress → cancel → results → library integration.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager
from core.audio_lab.audio_lab_contracts import ConversionProfile

logger = logging.getLogger("michi.audio_lab.conversion")

AUDIO_ONLY_FORMATS = {"flac", "wav", "aiff", "mp3", "aac", "opus", "vorbis", "alac"}
FORMAT_NAME_MAP = {"flac": "FLAC", "wav": "WAV", "aiff": "AIFF", "mp3": "MP3",
                   "aac": "AAC", "opus": "Opus", "vorbis": "Vorbis", "alac": "ALAC"}


@dataclass
class ConversionJob:
    id: str = ""
    status: str = "pending"
    progress: float = 0.0
    source: str = ""
    target: str = ""
    format: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    process: subprocess.Popen | None = None
    cancelled: bool = False


class AudioConversionService(QObject):
    conversionStarted = Signal(str)
    conversionProgress = Signal(str, float)
    conversionCompleted = Signal(str, str)
    conversionFailed = Signal(str, str)

    def __init__(self, db=None, wm: WorkerManager | None = None,
                 profile_service=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._profile_service = profile_service
        self._active_jobs: dict[str, ConversionJob] = {}

    def _build_target_path(self, source: str, profile: ConversionProfile) -> Path:
        """Construye la ruta de destino de forma consistente entre preview y conversion."""
        fmt = profile.format.lower()
        src_path = Path(source)
        target_dir = Path(profile.output_dir) if profile.output_dir else src_path.parent
        if profile.filename_template and "{artist}" in profile.filename_template:
            target_name = profile.filename_template.format(
                artist="{artist}", title=src_path.stem, album="{album}"
            )
            target_name = target_name.replace("{artist}", "Unknown").replace("{album}", "Unknown")
        else:
            target_name = src_path.stem
        # Evitar sobrescribir el original si mismo formato
        if fmt == src_path.suffix.lower().lstrip("."):
            target_name = target_name + "_converted"
        return target_dir / f"{target_name}.{fmt}"

    def preview(self, source: str, profile: ConversionProfile) -> dict[str, Any]:
        if not source or not os.path.isfile(source):
            return {"ok": False, "error": "SOURCE_NOT_FOUND"}
        fmt = profile.format.lower().strip()
        if fmt not in AUDIO_ONLY_FORMATS:
            return {"ok": False, "error": f"UNSUPPORTED_FORMAT:{profile.format}"}
        src_path = Path(source)
        estimated_size = src_path.stat().st_size * self._size_ratio(profile.format)
        target_path = self._build_target_path(source, profile)
        space_ok = True
        if profile.output_dir:
            try:
                free = shutil.disk_usage(profile.output_dir).free
                space_ok = free > estimated_size * 2
            except Exception:
                space_ok = True
        return {
            "ok": True,
            "source": source,
            "target": str(target_path),
            "estimated_size": estimated_size,
            "space_ok": space_ok,
            "format": profile.format,
            "collision": target_path.exists(),
        }

    def convert(self, source: str, profile: ConversionProfile,
                on_progress: Callable | None = None,
                on_done: Callable | None = None) -> str:
        job_id = f"conv_{int(time.time())}_{id(source)}"
        job = ConversionJob(id=job_id, source=source, format=profile.format)
        self._active_jobs[job_id] = job
        self.conversionStarted.emit(job_id)

        if self._wm:
            task_id = f"audio_conv_{job_id}"

            def _run():
                result = self._do_convert(source, profile, job)
                return result

            def _completed(result):
                job.status = "completed" if result.get("ok") else "failed"
                job.finished_at = time.time()
                if result.get("ok"):
                    job.target = result.get("target", "")
                    self.conversionCompleted.emit(job_id, job.target)
                else:
                    job.error = result.get("error", "")
                    self.conversionFailed.emit(job_id, job.error)
                if on_done:
                    on_done(result)

            self._wm.run_task(task_id, _run, on_done=_completed,
                              cancellable=True, owner="audio_lab_conv")
        else:
            result = self._do_convert(source, profile, job)
            job.finished_at = time.time()
            if result.get("ok"):
                job.status = "completed"
                job.target = result.get("target", "")
                self.conversionCompleted.emit(job_id, job.target)
            else:
                job.status = "failed"
                job.error = result.get("error", "")
                self.conversionFailed.emit(job_id, job.error)
            if on_done:
                on_done(result)

        return job_id

    def _do_convert(self, source: str, profile: ConversionProfile,
                    job: ConversionJob) -> dict[str, Any]:
        try:
            target_path = str(self._build_target_path(source, profile))
            job.target = target_path

            import subprocess
            cmd = self._build_command(source, target_path, profile)
            if not cmd:
                job.status = "failed"
                job.error = "NO_COMMAND_AVAILABLE"
                return {"ok": False, "error": "NO_COMMAND_AVAILABLE"}

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            job.process = proc
            try:
                duration = None
                progress_re = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')
                for stderr_line in proc.stderr:
                    if job.cancelled:
                        proc.terminate()
                        proc.wait(timeout=5)
                        return {"ok": False, "error": "CANCELLED"}

                    # Parse duration for progress calculation
                    if duration is None:
                        dm = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', stderr_line)
                        if dm:
                            duration = int(dm.group(1)) * 3600 + int(dm.group(2)) * 60 \
                                       + int(dm.group(3)) + int(dm.group(4)) / 100

                    # Parse current time for progress
                    m = progress_re.search(stderr_line)
                    if m:
                        current = int(m.group(1)) * 3600 + int(m.group(2)) * 60 \
                                  + int(m.group(3)) + int(m.group(4)) / 100
                        if duration and duration > 0:
                            pct = min(current / duration * 100, 99.9)
                            if pct - job.progress >= 1.0:
                                job.progress = round(pct, 1)
                                self.conversionProgress.emit(job.id, job.progress)

                proc.wait()
                if proc.returncode != 0 and not job.cancelled:
                    return {"ok": False, "error": f"ffmpeg exited with code {proc.returncode}"}
                if job.cancelled:
                    return {"ok": False, "error": "CANCELLED"}
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return {"ok": False, "error": "TIMEOUT"}

            if not os.path.isfile(target_path):
                return {"ok": False, "error": "Output file not created", "error_code": "FILE_NOT_CREATED"}
            return {"ok": True, "target": target_path, "format": profile.format, "verified": True}
        except Exception as e:
            logger.exception("Conversion failed for %s", source)
            return {"ok": False, "error": str(e)}

    def _build_command(self, source: str, target: str, profile: ConversionProfile) -> list[str] | None:
        fmt = profile.format.lower()
        if fmt == "flac":
            cmd = ["ffmpeg", "-i", source, "-c:a", "flac"]
            if profile.bit_depth > 0:
                cmd += ["-sample_fmt", f"s{profile.bit_depth}"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd += ["-compression_level", "8", target]
            return cmd
        if fmt == "wav":
            cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s16le"]
            if profile.bit_depth == 24:
                cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s24le"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd.append(target)
            return cmd
        if fmt == "aiff":
            cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s16be"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd.append(target)
            return cmd
        if fmt == "mp3":
            cmd = ["ffmpeg", "-i", source, "-c:a", "libmp3lame"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd += ["-q:a", "2", target]
            return cmd
        if fmt in ("aac", "m4a"):
            cmd = ["ffmpeg", "-i", source, "-c:a", "aac"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd.append(target)
            return cmd
        if fmt == "opus":
            cmd = ["ffmpeg", "-i", source, "-c:a", "libopus"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd.append(target)
            return cmd
        if fmt in ("ogg", "vorbis"):
            cmd = ["ffmpeg", "-i", source, "-c:a", "libvorbis"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd += ["-q:a", "3", target]
            return cmd
        if fmt == "alac":
            cmd = ["ffmpeg", "-i", source, "-c:a", "alac", target]
            return cmd
        return None

    def cancel(self, job_id: str) -> bool:
        if job_id not in self._active_jobs:
            return False
        job = self._active_jobs[job_id]
        if job.status in ("completed", "failed", "cancelled"):
            return False
        job.cancelled = True
        if job.process and job.process.poll() is None:
            try:
                job.process.terminate()
                job.process.wait(timeout=5)
            except Exception:
                with suppress(Exception):
                    job.process.kill()
        job.status = "cancelled"
        return True

    def _size_ratio(self, fmt: str) -> float:
        return {"MP3": 0.1, "AAC": 0.1, "Opus": 0.08, "Vorbis": 0.12,
                "FLAC": 0.5, "ALAC": 0.5, "WAV": 1.0, "AIFF": 1.0}.get(fmt, 0.5)
