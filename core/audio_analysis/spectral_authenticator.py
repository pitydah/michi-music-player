"""Spectral Authenticator — detect fake hi-res / upsampled audio via FFT analysis.

Uses numpy FFT to analyse the spectral content of a PCM audio file and
estimate whether the declared sample rate / bit depth is authentic.

Output: dict with keys:
  - verdict: HI_RES_COHERENT | LOSSLESS_COHERENT | POSSIBLE_LOSSY_SOURCE |
             SUSPICIOUS_UPSAMPLING | INCONCLUSIVE | ANALYSIS_ERROR
  - label: human-readable short label in Spanish
  - explanation: technical explanation
  - metrics: dict with spectral_rolloff_95, energy_16k, energy_18k, energy_20k,
             noise_floor, declared_sr, effective_sr
"""

from __future__ import annotations

import logging
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
    """Read a PCM chunk from a WAV file for spectral analysis."""
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
                dtype = np.uint8
            elif sampwidth == 2:
                dtype = np.int16
            elif sampwidth == 3:
                raw_bytes = np.frombuffer(raw, dtype=np.uint8)
                raw_bytes = raw_bytes.reshape(-1, 3)
                padded = np.zeros((len(raw_bytes), 4), dtype=np.uint8)
                padded[:, :3] = raw_bytes[:, :]
                samples = padded.view(np.int32).flatten()
                samples = samples / (2**31)
                if n_channels > 1:
                    samples = samples.reshape(-1, n_channels)
                    samples = samples[:, 0]
                return samples.astype(np.float64)
            elif sampwidth == 4:
                dtype = np.int32
            else:
                return None

            samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
            if n_channels > 1:
                samples = samples.reshape(-1, n_channels)
                samples = samples[:, 0]
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

    metrics = {
        "spectral_rolloff_95": float(np.median(rolloff_95_vals)) if rolloff_95_vals else 0.0,
        "spectral_rolloff_99": float(np.median(rolloff_99_vals)) if rolloff_99_vals else 0.0,
        "energy_above_16k": float(energy_16k / total_energy) if total_energy > 0 else 0.0,
        "energy_above_18k": float(energy_18k / total_energy) if total_energy > 0 else 0.0,
        "energy_above_20k": float(energy_20k / total_energy) if total_energy > 0 else 0.0,
        "segments_analysed": seg_count,
    }
    return metrics


def _verdict_from_metrics(metrics: dict[str, float],
                          declared_sr: int,
                          declared_bd: int) -> tuple[str, str, str]:
    """Produce a verdict from spectral metrics.

    Returns (verdict_key, label_es, explanation_es).
    """
    rolloff_99 = metrics.get("spectral_rolloff_99", 0)
    e_16k = metrics.get("energy_above_16k", 0)
    e_20k = metrics.get("energy_above_20k", 0)

    # Hi-Res coherence: declared >= 96kHz
    if declared_sr >= 96000:
        if rolloff_99 >= declared_sr * 0.45:
            return (
                "HI_RES_COHERENT",
                "Hi-Res coherente",
                "El contenido espectral alcanza frecuencias propias de "
                f"una grabación de {declared_sr // 1000} kHz.",
            )
        if rolloff_99 < declared_sr * 0.22:
            return (
                "SUSPICIOUS_UPSAMPLING",
                "Upsampling sospechoso",
                "El techo espectral efectivo ({:.0f} Hz) está muy por "
                "debajo de lo esperado para {} kHz. "
                "Posible upsampling desde una fuente de menor resolución."
                .format(rolloff_99, declared_sr // 1000),
            )
        if e_20k < 1e-6 and declared_sr >= 96000:
            return (
                "SUSPICIOUS_UPSAMPLING",
                "Upsampling sospechoso",
                "No se detecta energía significativa por encima de 20 kHz, "
                "lo que sugiere que el archivo fue upsampled "
                "desde una fuente de 44.1 o 48 kHz.",
            )
        return (
            "HI_RES_COHERENT",
            "Hi-Res coherente",
            "El análisis espectral es compatible con la resolución declarada.",
        )

    # Lossless (CD quality or lower)
    if declared_sr <= 48000:
        if e_16k > 0.005 and rolloff_99 > 18000:
            return (
                "LOSSLESS_COHERENT",
                "Lossless coherente",
                "El contenido espectral es compatible con una fuente "
                "sin pérdidas de {} kHz.".format(declared_sr // 1000),
            )
        if rolloff_99 < declared_sr * 0.40:
            return (
                "POSSIBLE_LOSSY_SOURCE",
                "Posible fuente con pérdida",
                "El techo espectral ({:.0f} Hz) es bajo para {} kHz. "
                "Podría tratarse de un archivo lossy (MP3/AAC) "
                "convertido a lossless."
                .format(rolloff_99, declared_sr // 1000),
            )
        if e_16k < 0.001 and declared_sr >= 44100:
            return (
                "POSSIBLE_LOSSY_SOURCE",
                "Posible fuente con pérdida",
                "Muy poca energía por encima de 16 kHz. "
                "Sugiere origen lossy.",
            )
        return (
            "LOSSLESS_COHERENT",
            "Lossless coherente",
            "El análisis espectral no encuentra anomalías.",
        )

    return ("INCONCLUSIVE", "No concluyente",
            "No se pudo determinar la coherencia espectral.")


def analyse_spectral(filepath: str,
                     declared_sample_rate: int = 44100,
                     declared_bit_depth: int = 16) -> dict[str, Any]:
    """Analyse a PCM audio file for spectral authenticity.

    Args:
        filepath: Path to a WAV file (other formats not supported yet).
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
        samples = _read_pcm_chunk(filepath, declared_sample_rate)
        if samples is None or len(samples) < FFT_SIZE:
            result["error"] = (
                "No se pudieron leer suficientes muestras de audio. "
                "Solo se admiten archivos WAV PCM."
            )
            return result

        metrics = _compute_spectral_analysis(samples, declared_sample_rate)
        if not metrics:
            result["error"] = "No se pudo completar el análisis espectral."
            return result

        metrics["declared_sample_rate"] = declared_sample_rate
        metrics["declared_bit_depth"] = declared_bit_depth
        result["metrics"] = metrics

        verdict_key, label, explanation = _verdict_from_metrics(
            metrics, declared_sample_rate, declared_bit_depth,
        )
        result["verdict"] = verdict_key
        result["label"] = label
        result["explanation"] = explanation

    except Exception as e:
        logger.exception("Spectral analysis failed for %s", filepath)
        result["error"] = str(e)

    return result


def can_analyse(filepath: str) -> bool:
    """Check if spectral analysis is possible for this file."""
    return filepath.lower().endswith(".wav")
