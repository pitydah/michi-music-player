"""Vinyl recording export helpers.

The splitter streams PCM chunks instead of loading an entire side into memory.
Encoding remains delegated to the system FLAC/FFmpeg tools.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
import wave
from typing import Any

logger = logging.getLogger("michi.vinyl.exporter")


def _safe_title(title: str, fallback: str) -> str:
    cleaned = "".join(c for c in title if c.isalnum() or c in " _-.").strip()
    return cleaned or fallback


def split_wav(
    input_path: str,
    output_dir: str,
    split_points: list[float],
    tracks: list[dict],
) -> list[str]:
    """Split a PCM WAV file without reading the complete recording into RAM."""

    os.makedirs(output_dir, exist_ok=True)
    points = sorted({max(0.0, float(point)) for point in split_points})
    if len(points) < 2:
        return []

    created: list[str] = []
    try:
        with wave.open(input_path, "rb") as source:
            sample_rate = source.getframerate()
            sample_width = source.getsampwidth()
            channels = source.getnchannels()
            total_frames = source.getnframes()

            for index in range(len(points) - 1):
                start_frame = min(total_frames, int(points[index] * sample_rate))
                end_frame = min(total_frames, int(points[index + 1] * sample_rate))
                if start_frame >= end_frame:
                    continue

                track = tracks[index] if index < len(tracks) else {}
                track_number = int(track.get("track_number", index + 1))
                title = str(track.get("title", f"Track {track_number}"))
                safe_title = _safe_title(title, f"Track_{track_number}")
                output_path = os.path.join(
                    output_dir, f"{track_number:02d} - {safe_title}.wav"
                )

                source.setpos(start_frame)
                remaining = end_frame - start_frame
                with wave.open(output_path, "wb") as destination:
                    destination.setnchannels(channels)
                    destination.setsampwidth(sample_width)
                    destination.setframerate(sample_rate)
                    while remaining > 0:
                        count = min(remaining, sample_rate * 10)
                        chunk = source.readframes(count)
                        if not chunk:
                            break
                        destination.writeframes(chunk)
                        remaining -= count
                created.append(output_path)
    except Exception:
        logger.exception("Failed to split WAV: %s", input_path)
    return created


def split_by_markers(
    input_path: str,
    output_dir: str,
    markers: list[dict[str, Any]],
    total_duration: float,
) -> dict[str, Any]:
    """Convert recorder markers to track boundaries and split the WAV."""

    result: dict[str, Any] = {"success": False, "tracks": [], "errors": []}
    if not os.path.exists(input_path):
        result["errors"].append(f"No existe el archivo de entrada: {input_path}")
        return result

    ordered = sorted(
        (
            {
                "timestamp": max(0.0, float(marker.get("timestamp", 0.0))),
                "label": str(marker.get("label") or ""),
            }
            for marker in markers
        ),
        key=lambda marker: marker["timestamp"],
    )
    if not ordered:
        result["errors"].append("No hay marcadores para dividir")
        return result

    duration = max(0.0, float(total_duration))
    try:
        with wave.open(input_path, "rb") as source:
            duration = max(duration, source.getnframes() / source.getframerate())
    except Exception as exc:
        result["errors"].append(f"No se pudo leer el WAV: {exc}")
        return result

    boundaries = [0.0]
    labels = ["Pista 1"]
    for marker in ordered:
        timestamp = min(duration, marker["timestamp"])
        if timestamp <= 0.001:
            labels[0] = marker["label"] or labels[0]
            continue
        if timestamp >= duration or timestamp == boundaries[-1]:
            continue
        boundaries.append(timestamp)
        labels.append(marker["label"] or f"Pista {len(labels) + 1}")
    boundaries.append(duration)

    tracks = [
        {"track_number": index + 1, "title": labels[index]}
        for index in range(len(boundaries) - 1)
    ]
    files = split_wav(input_path, output_dir, boundaries, tracks)
    for index, filepath in enumerate(files):
        start = boundaries[index]
        end = boundaries[index + 1]
        result["tracks"].append(
            {
                "index": index + 1,
                "label": tracks[index]["title"],
                "start": start,
                "duration": max(0.0, end - start),
                "file": filepath,
            }
        )
    result["success"] = len(files) == len(tracks)
    if not result["success"]:
        result["errors"].append("No se pudieron generar todas las pistas")
    return result


def encode_to_flac(
    wav_path: str, output_dir: str, tags: dict | None = None
) -> str | None:
    """Encode a WAV file to FLAC, preferring the native ``flac`` CLI."""

    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(wav_path))[0]
    flac_path = os.path.join(output_dir, f"{base}.flac")

    try:
        if shutil.which("flac"):
            tag_args: list[str] = []
            for key, value in (tags or {}).items():
                if value not in (None, ""):
                    tag_args.extend(["-T", f"{key}={value}"])
            result = subprocess.run(
                ["flac", "--best", *tag_args, "-f", "-o", flac_path, wav_path],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode == 0 and os.path.exists(flac_path):
                return flac_path
            logger.warning("FLAC CLI failed for %s: %s", wav_path, result.stderr[-300:])

        if not shutil.which("ffmpeg"):
            return None
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                wav_path,
                "-c:a",
                "flac",
                "-compression_level",
                "12",
                flac_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0 and os.path.exists(flac_path):
            return flac_path
        logger.warning("FFmpeg FLAC encoding failed: %s", result.stderr[-300:])
    except Exception:
        logger.exception("FLAC encoding failed: %s", wav_path)
    return None


def encode_wav(
    wav_path: str,
    output_dir: str,
    output_format: str = "flac",
    tags: dict | None = None,
) -> str | None:
    fmt = output_format.lower()
    if fmt == "flac":
        return encode_to_flac(wav_path, output_dir, tags)
    if fmt == "wav":
        os.makedirs(output_dir, exist_ok=True)
        destination = os.path.join(output_dir, os.path.basename(wav_path))
        if os.path.abspath(wav_path) != os.path.abspath(destination):
            shutil.copy2(wav_path, destination)
        return destination
    logger.warning("Unsupported output format: %s", output_format)
    return None


def export_side(
    input_path: str,
    export_dir: str,
    split_points: list,
    tracks: list,
    fmt: str = "flac",
) -> dict:
    result: dict[str, list] = {"exported": [], "errors": []}
    split_files = split_wav(input_path, export_dir, split_points, tracks)
    if not split_files:
        result["errors"].append("No se generaron pistas")
        return result

    for index, wav_path in enumerate(split_files):
        try:
            tags = tracks[index] if index < len(tracks) else None
            output = encode_wav(wav_path, export_dir, fmt, tags)
            if output:
                result["exported"].append(output)
            else:
                result["errors"].append(f"No se pudo exportar {wav_path}")
            if fmt.lower() != "wav":
                with contextlib.suppress(OSError):
                    os.remove(wav_path)
        except Exception as exc:
            result["errors"].append(f"{wav_path}: {exc}")
    return result
