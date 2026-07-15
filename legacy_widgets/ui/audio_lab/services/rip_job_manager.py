"""Rip job manager — manages CD ripping jobs with real QProcess-based ripping."""

from __future__ import annotations

import logging
import os
import uuid

from PySide6.QtCore import QObject, Signal

from ui.audio_lab.models import RipJob
from ui.audio_lab.services.disc_detection_service import DiscDetectionService
from ui.audio_lab.services.rip_worker import RipWorker

logger = logging.getLogger("michi.audio_lab.rip_job_manager")


class RipJobManager(QObject):
    progress_changed = Signal(str, int, float, str)
    track_started = Signal(str, int, int)
    track_finished = Signal(str, int, str)
    job_finished = Signal(str, dict)
    error_occurred = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._jobs: dict[str, RipJob] = {}
        self._workers: dict[str, RipWorker] = {}
        self._detection = DiscDetectionService()

    def create_job(self, drive: str, profile: str, destination: str,
                   extraction_mode: str = "fast") -> RipJob:
        toc = self._detection.get_disc_toc(drive)
        job = RipJob(
            id=str(uuid.uuid4())[:12],
            drive=drive, profile=profile, destination=destination,
            extraction_mode=extraction_mode,
            status="created", progress=0.0,
            current_track=0,
            total_tracks=toc.get("tracks", 0),
        )
        self._jobs[job.id] = job
        return job

    def start_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if not job or job.status == "running":
            return

        toc = self._detection.get_disc_toc(job.drive)
        if not toc.get("tracks"):
            self.error_occurred.emit(job_id, "No se pudo leer la tabla de contenido del disco.")
            return

        os.makedirs(job.destination, exist_ok=True)

        worker = RipWorker(self)
        self._workers[job_id] = worker

        worker.track_started.connect(
            lambda jid, tnum, total, j=job_id:
            self._on_worker_track(j, tnum, total)
        )
        worker.track_finished.connect(
            lambda jid, tnum, path, j=job_id:
            self.track_finished.emit(j, tnum, path)
        )
        worker.progress_changed.connect(
            lambda jid, tnum, prog, st, j=job_id:
            self._on_worker_progress(j, tnum, prog, st)
        )
        worker.error_occurred.connect(
            lambda jid, msg, j=job_id:
            self.error_occurred.emit(j, msg)
        )

        job.status = "running"
        worker.rip_all_tracks(job_id, job.drive, toc["track_list"], job.destination,
                             extraction_mode=job.extraction_mode,
                             stop_on_error=(job.extraction_mode != "fast"))

    def cancel_job(self, job_id: str):
        worker = self._workers.get(job_id)
        if worker:
            worker.cancel()
        job = self._jobs.get(job_id)
        if job:
            job.status = "cancelled"

    def get_progress(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if job:
            return {
                "job_id": job.id, "status": job.status,
                "progress": job.progress, "current_track": job.current_track,
                "total_tracks": job.total_tracks,
            }
        return {}

    def get_job(self, job_id: str) -> RipJob | None:
        return self._jobs.get(job_id)

    def _on_worker_track(self, job_id: str, track_num: int, total: int):
        job = self._jobs.get(job_id)
        if job:
            job.current_track = track_num
            job.total_tracks = total
        self.track_started.emit(job_id, track_num, total)

    def _on_worker_progress(self, job_id: str, track_num: int,
                            progress: float, status: str):
        job = self._jobs.get(job_id)
        if job:
            job.progress = progress
            job.current_track = track_num
            if status == "completed":
                job.status = "completed"
        self.progress_changed.emit(job_id, track_num, progress, status)
        if status == "completed":
            self.job_finished.emit(job_id, {"status": "completed", "tracks_ripped": job.total_tracks if job else 0})
