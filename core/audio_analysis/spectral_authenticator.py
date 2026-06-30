"""Spectral Authenticator — evaluate spectral coherence of PCM audio via FFT.

Uses numpy FFT to analyse the spectral content of a WAV PCM file and
estimate whether the declared sample rate / bit depth is authentic.

This is an experimental, probabilistic analysis. It is NOT a definitive
proof of authenticity, upsampling, or lossy transcoding.

Output: dict with keys:
  - verdict: HI_RES_COHERENT | LOSSLESS_COHERENT | POSSIBLE_LOSSY_SOURCE |
             SUSPICIOUS_UPSAMPLING | INCONCLUSIVE | ANALYSIS_ERROR
  - label: human-readable short label in Spanish
  - explanation: technical explanation
  - confidence: float 0..1
  - metrics: dict with spectral_rolloff_95/99, energy_16k/18k/20k,
             effective_ceiling_hz, cutoff_detected, segments_analysed,
             nyquist_hz, declared_sample_rate, declared_bit_depth
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np

logger = logging.getLogger("michi.audio_analysis.spectral")

FFT_SIZE = 8192
WINDOW_TYPE = "hann"
OVERSAMPLE_FACTOR = 4


def _hann_window(n: int) -> np.ndarray:
    return 0.5 * (1 - np.cos(2 * np.pi * np.arange(n) / (n - 1)))


def _read_pcm_chunk(filepath: str, sample_rate: int,
                    duration_sec: float = 10.0) -> np.ndarray | None:
    """Read a PCM chunk from a WAV file for spectral analysis.

    Handles 8-bit (unsigned), 16-bit (signed), 24-bit (signed LE with sign extension),
    and 32-bit (signed) PCM. Stereo/multichannel is averaged to mono.
    Normalises output to approximate [-1.0, 1.0] range.
    """
    try:
        import wave
        with wave.open(filepath, "rb") as wf:
            frames = wf.getnframes()
            sr = wf.getframerate()
            sampwidth = wf.getsampwidth()
            n_channels = wf.getnchannels()
            if sr <= 0:
                return None

            n_frames = min(int(sr * duration_sec), frames)
            raw = wf.readframes(n_frames)

            if sampwidth == 1:
                # Unsigned 8-bit
                samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
                samples = (samples - 128.0) / 128.0
            elif sampwidth == 2:
                # Signed 16-bit LE
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
                samples = samples / 32768.0
            elif sampwidth == 3:
                # Signed 24-bit LE — proper sign extension
                raw_bytes = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                padded = np.zeros((len(raw_bytes), 4), dtype=np.int32)
                # Copy 3 bytes into lower 24 bits
                padded[:, 0] = raw_bytes[:, 0].astype(np.int32)
                padded[:, 1] = raw_bytes[:, 1].astype(np.int32) << 8
                padded[:, 2] = raw_bytes[:, 2].astype(np.int32) << 16
                # Sign-extend bit 23 to bits 24-31
                sign_mask = np.int32(0x80 << 16)  # bit 23
                is_negative = (padded[:, 2] & sign_mask) != 0
                samples = (padded[:, 0] | padded[:, 1] | padded[:, 2]).astype(np.float64)
                samples[is_negative] -= 16777216.0  # 2^24
                samples = samples / 8388608.0  # 2^23
            elif sampwidth == 4:
                # Signed 32-bit LE
                samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
                samples = samples / 2147483648.0
            else:
                return None

            # Average channels to mono
            if n_channels > 1:
                import contextlib
                with contextlib.suppress(ValueError):
                    samples = samples.reshape(-1, n_channels).mean(axis=1)

            return samples
    except Exception as e:
        logger.debug("Could not read WAV for spectral analysis: %s", e)
        return None


def _compute_spectral_analysis(samples: np.ndarray,
                                sample_rate: int) -> dict[str, float]:
    """Compute spectral metrics from PCM samples.

    Returns dict with: spectral_rolloff_95, spectral_rolloff_99,
    energy_above_16k, energy_above_18k, energy_above_20k, noise_floor.
    """
    if len(samples) < FFT_SIZE:
        return {}

    window = _hann_window(FFT_SIZE)
    n_segments = max(1, len(samples) // (FFT_SIZE // OVERSAMPLE_FACTOR) - 1)

    rolloff_95_vals = []
    rolloff_99_vals = []
    energy_16k = 0.0
    energy_18k = 0.0
    energy_20k = 0.0
    total_energy = 0.0
    seg_count = 0

    for i in range(n_segments):
        start = i * (FFT_SIZE // OVERSAMPLE_FACTOR)
        segment = samples[start:start + FFT_SIZE]
        if len(segment) < FFT_SIZE:
            break

        segment = segment * window
        fft = np.fft.rfft(segment)
        mag = np.abs(fft)
        freqs = np.fft.rfftfreq(FFT_SIZE, d=1.0 / sample_rate)

        cumsum = np.cumsum(mag)
        total = cumsum[-1]
        if total == 0:
            continue

        # Spectral rolloff 95% and 99%
        rolloff_95_idx = np.searchsorted(cumsum, 0.95 * total)
        rolloff_99_idx = np.searchsorted(cumsum, 0.99 * total)
        rolloff_95_vals.append(freqs[rolloff_95_idx] if rolloff_95_idx < len(freqs) else 0)
        rolloff_99_vals.append(freqs[rolloff_99_idx] if rolloff_99_idx < len(freqs) else 0)

        # Energy above frequency thresholds
        for freq_thresh in (16000, 18000, 20000):
            idx = np.searchsorted(freqs, freq_thresh)
            if idx < len(mag):
                e = np.sum(mag[idx:] ** 2)
                if freq_thresh == 16000:
                    energy_16k += e
                elif freq_thresh == 18000:
                    energy_18k += e
                elif freq_thresh == 20000:
                    energy_20k += e
        total_energy += np.sum(mag ** 2)
        seg_count += 1

    if seg_count == 0:
        return {}

    rolloff_95_val = float(np.median(rolloff_95_vals)) if rolloff_95_vals else 0.0
    rolloff_99_val = float(np.median(rolloff_99_vals)) if rolloff_99_vals else 0.0
    e_16k_val = float(energy_16k / total_energy) if total_energy > 0 else 0.0
    e_18k_val = float(energy_18k / total_energy) if total_energy > 0 else 0.0
    e_20k_val = float(energy_20k / total_energy) if total_energy > 0 else 0.0

    # effective_ceiling_hz: frequency below which most energy is concentrated
    effective_ceiling = max(rolloff_95_val, rolloff_99_val * 0.95) if rolloff_99_val > 0 else 0.0

    # cutoff_detected: sharp drop in energy above effective ceiling
    nyquist = sample_rate / 2.0
    cutoff_detected = False
    if nyquist > 0 and effective_ceiling > 0 and effective_ceiling < nyquist * 0.6 and e_20k_val < 1e-6:
        cutoff_detected = True

    metrics = {
        "spectral_rolloff_95": rolloff_95_val,
        "spectral_rolloff_99": rolloff_99_val,
        "effective_ceiling_hz": round(effective_ceiling, 1),
        "cutoff_detected": cutoff_detected,
        "energy_above_16k": e_16k_val,
        "energy_above_18k": e_18k_val,
        "energy_above_20k": e_20k_val,
        "segments_analysed": seg_count,
        "nyquist_hz": nyquist,
    }
    return metrics


def _verdict_from_metrics(metrics: dict[str, float],
                          declared_sr: int,
                          declared_bd: int) -> tuple[str, str, str, float]:
    """Produce a verdict from spectral metrics.

    Returns (verdict_key, label_es, explanation_es, confidence).
    confidence: 0.0 (low) to 1.0 (high).
    """
    rolloff_99 = metrics.get("spectral_rolloff_99", 0)
    e_16k = metrics.get("energy_above_16k", 0)
    e_20k = metrics.get("energy_above_20k", 0)
    segs = metrics.get("segments_analysed", 0)

    # Base confidence from segment count (more segments = more reliable)
    if segs < 3:
        return ("INCONCLUSIVE", "No concluyente",
                "Muy pocos segmentos analizados para una evaluación "
                "significativa. El archivo puede ser demasiado corto.", 0.05)
    base_conf = min(1.0, segs / 20.0) if segs else 0.1

    # Hi-Res coherence: declared >= 96kHz
    if declared_sr >= 96000:
        if rolloff_99 >= declared_sr * 0.45:
            conf = min(1.0, base_conf + 0.3)
            return (
                "HI_RES_COHERENT",
                "Hi-Res coherente",
                "El contenido espectral alcanza frecuencias propias de "
                f"una grabación de {declared_sr // 1000} kHz.",
                round(conf, 2),
            )
        if rolloff_99 < declared_sr * 0.22:
            conf = min(1.0, base_conf + 0.25)
            return (
                "SUSPICIOUS_UPSAMPLING",
                "Upsampling sospechoso",
                "El techo espectral efectivo ({:.0f} Hz) está muy por "
                "debajo de lo esperado para {} kHz. "
                "Posible upsampling desde una fuente de menor resolución."
                .format(rolloff_99, declared_sr // 1000),
                round(conf, 2),
            )
        if e_20k < 1e-6 and declared_sr >= 96000:
            conf = min(1.0, base_conf + 0.20)
            return (
                "SUSPICIOUS_UPSAMPLING",
                "Upsampling sospechoso",
                "No se detecta energía significativa por encima de 20 kHz, "
                "lo que sugiere que el archivo fue upsampled "
                "desde una fuente de 44.1 o 48 kHz.",
                round(conf, 2),
            )
        # Hi-Res but inconclusive
        conf = round(base_conf * 0.6, 2)
        return (
            "INCONCLUSIVE",
            "No concluyente",
            "El archivo declara {} kHz pero los indicios espectrales "
            "no son concluyentes.".format(declared_sr // 1000),
            conf,
        )

    # Lossless (CD quality or lower)
    if declared_sr <= 48000:
        if e_16k > 0.005 and rolloff_99 > 18000:
            conf = min(1.0, base_conf + 0.25)
            return (
                "LOSSLESS_COHERENT",
                "Lossless coherente",
                "El contenido espectral es compatible con una fuente "
                "sin pérdidas de {} kHz.".format(declared_sr // 1000),
                round(conf, 2),
            )
        if rolloff_99 < declared_sr * 0.40:
            conf = min(1.0, base_conf + 0.20)
            return (
                "POSSIBLE_LOSSY_SOURCE",
                "Posible fuente con pérdida",
                "El techo espectral ({:.0f} Hz) es bajo para {} kHz. "
                "Podría tratarse de un archivo lossy (MP3/AAC) "
                "convertido a lossless."
                .format(rolloff_99, declared_sr // 1000),
                round(conf, 2),
            )
        if e_16k < 0.001 and declared_sr >= 44100:
            conf = min(1.0, base_conf + 0.15)
            return (
                "POSSIBLE_LOSSY_SOURCE",
                "Posible fuente con pérdida",
                "Muy poca energía por encima de 16 kHz. "
                "Sugiere origen lossy.",
                round(conf, 2),
            )
        conf = round(base_conf * 0.7, 2)
        return (
            "LOSSLESS_COHERENT",
            "Lossless coherente",
            "El análisis espectral no encuentra anomalías.",
            conf,
        )

    return ("INCONCLUSIVE", "No concluyente",
            "No se pudo determinar la coherencia espectral.", 0.1)


def _decode_flac_to_wav(filepath: str) -> str | None:
    """Decode a FLAC file to a temporary WAV file using ffmpeg.

    Returns the path to the temp WAV, or None on failure.
    """
    import subprocess
    import tempfile
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="flac_spec_")
        os.close(fd)
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", filepath, "-c:a", "pcm_s16le",
             "-ar", "44100", "-ac", "1", tmp_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and os.path.isfile(tmp_path):
            return tmp_path
        os.unlink(tmp_path)
        return None
    except Exception as e:
        logger.debug("FLAC decode failed for %s: %s", filepath, e)
        return None


def analyse_spectral(filepath: str,
                     declared_sample_rate: int = 44100,
                     declared_bit_depth: int = 16) -> dict[str, Any]:
    """Analyse a PCM audio file for spectral authenticity.

    Supports WAV PCM directly and FLAC via temporary decode.

    Args:
        filepath: Path to audio file.
        declared_sample_rate: The sample rate declared in metadata.
        declared_bit_depth: The bit depth declared in metadata.

    Returns:
        dict with keys: verdict, label, explanation, metrics, error (if any).
    """
    result: dict[str, Any] = {
        "verdict": "ANALYSIS_ERROR",
        "label": "Error de análisis",
        "explanation": "",
        "metrics": {},
        "error": "",
    }

    try:
        tmp_wav = None
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".flac":
            tmp_wav = _decode_flac_to_wav(filepath)
            if tmp_wav is None:
                result["error"] = (
                    "No se pudo decodificar FLAC a WAM. "
                    "Asegúrate de tener ffmpeg instalado."
                )
                return result
            analyse_path = tmp_wav
        else:
            analyse_path = filepath

        samples = _read_pcm_chunk(analyse_path, declared_sample_rate)
        if tmp_wav:
            import contextlib
            with contextlib.suppress(Exception):
                os.unlink(tmp_wav)

        if samples is None or len(samples) < FFT_SIZE:
            result["error"] = (
                "No se pudieron leer suficientes muestras de audio. "
                "Solo se admiten archivos WAV PCM y FLAC."
            )
            return result

        metrics = _compute_spectral_analysis(samples, declared_sample_rate)
        if not metrics:
            result["error"] = "No se pudo completar el análisis espectral."
            return result

        metrics["declared_sample_rate"] = declared_sample_rate
        metrics["declared_bit_depth"] = declared_bit_depth
        result["metrics"] = metrics

        verdict_key, label, explanation, confidence = _verdict_from_metrics(
            metrics, declared_sample_rate, declared_bit_depth,
        )
        result["verdict"] = verdict_key
        result["label"] = label
        result["explanation"] = explanation
        result["confidence"] = confidence

    except Exception as e:
        logger.exception("Spectral analysis failed for %s", filepath)
        result["error"] = str(e)

    return result


def can_analyse(filepath: str) -> bool:
    """Check if spectral analysis is possible for this file.

    Supports WAV PCM (direct) and FLAC (decoded to temporary WAV via ffmpeg).
    Non-existent files return True based on extension (analyse_spectral will error later).
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".wav":
        if not os.path.isfile(filepath):
            return True
        try:
            with open(filepath, "rb") as f:
                header = f.read(12)
            return header[:4] == b"RIFF" and header[8:12] == b"WAVE"
        except OSError:
            return False
    if ext == ".flac":
        if not os.path.isfile(filepath):
            return False
        import shutil
        return shutil.which("ffmpeg") is not None
    return False
