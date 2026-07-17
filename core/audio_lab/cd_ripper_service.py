"""Audio-CD extraction service.

Linux is the first productive backend and uses cdparanoia for secure PCM
extraction followed by FFmpeg encoding. Other platforms remain explicitly
unsupported until equivalent backends are implemented and tested.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CDRomDrive:
    device: str
    model: str
    is_audio_capable: bool
    backend: str = "unsupported"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CDTrack:
    track_number: int
    title: str
    artist: str
    duration: float
    start_sector: int
    end_sector: int


@dataclass(frozen=True)
class CDInfo:
    album_title: str
    album_artist: str
    year: int
    genre: str
    tracks: list[CDTrack]
    disc_id: str
    total_tracks: int
    metadata_source: str = "toc"


class CDRipperService:
    SUPPORTED_FORMATS = ("flac", "wav", "mp3", "opus", "aac")

    def __init__(self) -> None:
        self.default_format = "flac"
        self.default_quality = "lossless"
        self._lock = threading.RLock()
        self._active_process: subprocess.Popen[bytes] | None = None
        self._cancel_requested = threading.Event()

    @property
    def supported_formats(self) -> list[str]:
        return list(self.SUPPORTED_FORMATS)

    def capability(self) -> dict[str, Any]:
        platform_supported = sys.platform.startswith("linux")
        missing = [tool for tool in ("cdparanoia", "cd-discid", "ffmpeg") if not shutil.which(tool)]
        return {
            "available": platform_supported and not missing,
            "platform_supported": platform_supported,
            "backend": "cdparanoia" if platform_supported else "unsupported",
            "missing_tools": missing,
            "formats": list(self.SUPPORTED_FORMATS),
        }

    def detect_drives(self) -> list[CDRomDrive]:
        if not sys.platform.startswith("linux"):
            return []
        drives: list[CDRomDrive] = []
        candidates = sorted(Path("/dev").glob("sr*"))
        cdrom = Path("/dev/cdrom")
        if cdrom.exists():
            try:
                resolved = cdrom.resolve()
                if resolved not in candidates:
                    candidates.append(resolved)
            except OSError:
                pass

        for candidate in candidates:
            model = candidate.name
            if shutil.which("udevadm"):
                try:
                    result = subprocess.run(
                        ["udevadm", "info", "--query=property", f"--name={candidate}"],
                        capture_output=True,
                        text=True,
                        timeout=4,
                        check=False,
                    )
                    properties = dict(
                        line.split("=", 1)
                        for line in result.stdout.splitlines()
                        if "=" in line
                    )
                    model = (
                        properties.get("ID_MODEL_FROM_DATABASE")
                        or properties.get("ID_MODEL")
                        or model
                    ).replace("_", " ")
                except (OSError, subprocess.TimeoutExpired, ValueError):
                    pass
            drives.append(
                CDRomDrive(
                    device=str(candidate),
                    model=model,
                    is_audio_capable=shutil.which("cdparanoia") is not None,
                    backend="cdparanoia",
                )
            )
        return drives

    @staticmethod
    def _parse_cddb_toc(output: str) -> CDInfo | None:
        """Parse cd-discid's CDDB output into a truthful track list."""
        fields = output.strip().split()
        if len(fields) < 4:
            return None
        disc_id = fields[0]
        try:
            track_count = int(fields[1])
            offsets = [int(value) for value in fields[2 : 2 + track_count]]
            leadout_seconds = int(fields[2 + track_count])
        except (ValueError, IndexError):
            return None
        if track_count <= 0 or len(offsets) != track_count:
            return None

        leadout_sector = leadout_seconds * 75
        tracks: list[CDTrack] = []
        for index, start_sector in enumerate(offsets):
            end_sector = offsets[index + 1] if index + 1 < len(offsets) else leadout_sector
            duration = max(0.0, (end_sector - start_sector) / 75.0)
            tracks.append(
                CDTrack(
                    track_number=index + 1,
                    title=f"Track {index + 1:02d}",
                    artist="Unknown Artist",
                    duration=duration,
                    start_sector=start_sector,
                    end_sector=end_sector,
                )
            )
        return CDInfo(
            album_title="Unknown Album",
            album_artist="Unknown Artist",
            year=0,
            genre="Unknown",
            tracks=tracks,
            disc_id=disc_id,
            total_tracks=track_count,
            metadata_source="cddb_toc",
        )

    def get_cd_info(self, device: str) -> CDInfo | None:
        capability = self.capability()
        if not capability["platform_supported"] or "cd-discid" in capability["missing_tools"]:
            return None
        try:
            result = subprocess.run(
                ["cd-discid", device],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Could not read CD TOC from %s: %s", device, exc)
            return None
        if result.returncode != 0:
            logger.warning("cd-discid failed for %s: %s", device, result.stderr.strip())
            return None
        return self._parse_cddb_toc(result.stdout)

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value).strip(" .")
        return cleaned[:140] or "Unknown"

    @staticmethod
    def _encode_args(fmt: str, quality: str) -> list[str]:
        if fmt == "wav":
            return ["-c:a", "pcm_s16le"]
        if fmt == "flac":
            level = "8" if quality in ("lossless", "high") else "5"
            return ["-c:a", "flac", "-compression_level", level]
        if fmt == "mp3":
            bitrate = "320k" if quality in ("lossless", "high") else "192k"
            return ["-c:a", "libmp3lame", "-b:a", bitrate]
        if fmt == "opus":
            bitrate = "256k" if quality in ("lossless", "high") else "160k"
            return ["-c:a", "libopus", "-b:a", bitrate]
        if fmt == "aac":
            bitrate = "256k" if quality in ("lossless", "high") else "192k"
            return ["-c:a", "aac", "-b:a", bitrate]
        raise ValueError(f"UNSUPPORTED_FORMAT:{fmt}")

    def _run_process(self, command: list[str], timeout: float) -> tuple[bool, str]:
        with self._lock:
            if self._active_process and self._active_process.poll() is None:
                return False, "CD_RIP_ALREADY_ACTIVE"
            self._cancel_requested.clear()
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                return False, str(exc)
            self._active_process = process

        try:
            _, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
            return False, "CD_RIP_TIMEOUT"
        finally:
            with self._lock:
                if self._active_process is process:
                    self._active_process = None

        error = stderr.decode("utf-8", errors="replace").strip() if stderr else ""
        if self._cancel_requested.is_set():
            return False, "CD_RIP_CANCELLED"
        return process.returncode == 0, error

    def rip_track(
        self,
        device: str,
        track_number: int,
        output_path: str,
        format: str = "flac",
        quality: str = "lossless",
    ) -> dict[str, Any]:
        capability = self.capability()
        if not capability["available"]:
            return {
                "success": False,
                "error": "CD_RIPPING_UNAVAILABLE",
                "capability": capability,
                "output_file": output_path,
                "log": [],
            }
        fmt = format.casefold().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            return {"success": False, "error": f"UNSUPPORTED_FORMAT:{fmt}", "log": []}
        if track_number < 1:
            return {"success": False, "error": "INVALID_TRACK_NUMBER", "log": []}

        target = Path(output_path).expanduser()
        if target.suffix.casefold() != f".{fmt}":
            return {"success": False, "error": "OUTPUT_EXTENSION_MISMATCH", "log": []}
        if target.exists():
            return {"success": False, "error": "OUTPUT_EXISTS", "log": []}
        target.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="michi-cd-") as temp_dir:
            pcm_path = Path(temp_dir) / f"track-{track_number:02d}.wav"
            extract_command = [
                "cdparanoia",
                "-d",
                device,
                "-w",
                str(track_number),
                str(pcm_path),
            ]
            ok, error = self._run_process(extract_command, timeout=900)
            if not ok:
                return {
                    "success": False,
                    "error": error or "CD_EXTRACTION_FAILED",
                    "output_file": str(target),
                    "log": [],
                }

            if fmt == "wav":
                shutil.move(str(pcm_path), target)
            else:
                encode_command = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(pcm_path),
                    *self._encode_args(fmt, quality),
                    "-n",
                    str(target),
                ]
                ok, error = self._run_process(encode_command, timeout=900)
                if not ok:
                    return {
                        "success": False,
                        "error": error or "CD_ENCODING_FAILED",
                        "output_file": str(target),
                        "log": [],
                    }
        return {
            "success": True,
            "error": "",
            "output_file": str(target),
            "log": [f"Track {track_number} extracted with cdparanoia"],
        }

    def rip_full_cd(
        self,
        device: str,
        output_dir: str,
        format: str = "flac",
        quality: str = "lossless",
        include_log: bool = True,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        info = self.get_cd_info(device)
        if not info or info.total_tracks <= 0 or not info.tracks:
            return {
                "success": False,
                "tracks_completed": 0,
                "tracks_failed": 0,
                "errors": ["CD_TOC_UNAVAILABLE_OR_EMPTY"],
                "log_file": None,
            }

        fmt = format.casefold().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            return {
                "success": False,
                "tracks_completed": 0,
                "tracks_failed": info.total_tracks,
                "errors": [f"UNSUPPORTED_FORMAT:{fmt}"],
                "log_file": None,
            }

        album_dir = Path(output_dir).expanduser() / (
            f"{self._safe_name(info.album_artist)} - {self._safe_name(info.album_title)}"
        )
        album_dir.mkdir(parents=True, exist_ok=True)
        completed = 0
        failed = 0
        errors: list[str] = []
        log_entries: list[str] = []

        for track in info.tracks:
            if self._cancel_requested.is_set():
                errors.append("CD_RIP_CANCELLED")
                break
            filename = f"{track.track_number:02d}. {self._safe_name(track.title)}.{fmt}"
            track_result = self.rip_track(
                device,
                track.track_number,
                str(album_dir / filename),
                fmt,
                quality,
            )
            if track_result["success"]:
                completed += 1
                log_entries.extend(track_result.get("log", []))
            else:
                failed += 1
                errors.append(f"Track {track.track_number}: {track_result.get('error', 'UNKNOWN_ERROR')}")
            if progress_callback:
                progress_callback(completed + failed, info.total_tracks)

        log_file: str | None = None
        if include_log:
            log_path = album_dir / "ripping_log.txt"
            with log_path.open("w", encoding="utf-8") as handle:
                handle.write(f"Michi CD rip log\nDisc ID: {info.disc_id}\n")
                handle.write(f"Tracks: {info.total_tracks}\nMetadata source: {info.metadata_source}\n")
                for entry in log_entries:
                    handle.write(f"{entry}\n")
                for error in errors:
                    handle.write(f"ERROR: {error}\n")
            log_file = str(log_path)

        return {
            "success": completed == info.total_tracks and failed == 0 and not errors,
            "tracks_completed": completed,
            "tracks_failed": failed,
            "errors": errors,
            "log_file": log_file,
            "output_dir": str(album_dir),
        }

    def cancel(self) -> dict[str, Any]:
        self._cancel_requested.set()
        with self._lock:
            process = self._active_process
            if not process or process.poll() is not None:
                return {"success": False, "error": "NO_ACTIVE_CD_RIP"}
            process.terminate()
        return {"success": True}

    def shutdown(self) -> None:
        with self._lock:
            process = self._active_process
            if process and process.poll() is None:
                self._cancel_requested.set()
                process.terminate()
