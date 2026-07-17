# -*- coding: utf-8 -*-
"""Audio chain — DAC config, quality labels, and parametric EQ builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DacConfig:
    device: str = "default"          # ALSA device name
    mode: str = "standard"           # standard | bitperfect | dop
    profile: str = "standard"        # standard | hifi_pcm | bitperfect_pcm ...
    backend: str = "auto"            # auto | pipewire | pulseaudio | alsa | jack
    output_device_id: str = ""       # id from AudioDeviceInfo
    alsa_device: str = "default"     # e.g. hw:1,0
    target_rate: int = 0             # 0 = auto-match source
    target_format: str = "auto"      # auto | S16LE | S24_3LE | S32LE
    buffer_ms: int = 100
    period_count: int = 4
    allow_resample: bool = True
    resample_quality: str = "medium"
    dsd_mode: str = "pcm"            # pcm | dop | native
    dsd_pcm_rate: int = 0            # 0 = auto
    allow_fallback: bool = True

    @property
    def alsa_device_str(self) -> str:
        if self.mode == "bitperfect" and self.device == "default":
            return "hw:0,0"  # force hardware for bitperfect
        return self.device

    @classmethod
    def from_settings(cls, settings: Any) -> "DacConfig":
        return cls(
            device=settings.get("audio/device", "default"),
            mode=settings.get("audio/mode", "standard"),
            target_rate=settings.get("audio/target_rate", 0),
            target_format=settings.get("audio/target_format", "auto"),
            buffer_ms=settings.get("audio/buffer_ms", 100),
        )


def get_quality_label(filepath: str) -> tuple[str, str]:
    """Return (label, color_hex) for audio quality badge."""
    import os
    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".dsf", ".dff"):
        try:
            from audio.dff_parser import parse_dff
            header = parse_dff(filepath) if ext == ".dff" else None
            rate = header.sample_rate if header else 2822400
            dsd_speed = rate // 44100
            return (f"DSD{dsd_speed} · {rate/1e6:.1f}MHz", "#ffd54f")
        except Exception:
            return ("DSD", "#ffd54f")

    if ext == ".flac":
        return ("FLAC", "#4caf50")
    if ext == ".mp3":
        return ("MP3", "#ff9800")
    if ext == ".opus":
        return ("Opus", "#42a5f5")
    if ext == ".ogg":
        return ("OGG", "#42a5f5")
    if ext == ".wav":
        return ("WAV", "#4caf50")
    if ext in (".aiff", ".aif"):
        return ("AIFF", "#4caf50")
    if ext in (".m4a", ".aac"):
        return ("AAC", "#42a5f5")
    return ("", "")


def build_eq_parametric_chain(bands: list[dict], preamp_db: float) -> str:
    """Build parametric EQ chain with audioiirfilter biquads.

    Each band is a dict with type, frequency, q, gain. Biquad coefficients
    (b0/b1/b2, a0/a1/a2) are computed on-the-fly by eq_biquad.py.
    Pre-computed coefficients in the dict (a0/a1/a2/b0/b1/b2) take precedence.
    """
    if not bands:
        return ""
    from audio.eq_biquad import compute_biquad
    parts = []
    for i, band in enumerate(bands):
        if all(k in band for k in ("a0", "a1", "a2", "b0", "b1", "b2")):
            a0, a1, a2 = band["a0"], band["a1"], band["a2"]
            b0, b1, b2 = band["b0"], band["b1"], band["b2"]
        else:
            coefs = compute_biquad(
                band.get("type", "Peak"),
                band.get("freq", 1000.0),
                band.get("gain", 0.0),
                band.get("Q", 1.41),
                fs=band.get("fs", 44100.0))
            b0, b1, b2, a0, a1, a2 = coefs
        parts.append(
            f"audioiirfilter name=param_eq_{i} "
            f"a0={a0} a1={a1} a2={a2} "
            f"b0={b0} b1={b1} b2={b2}")
    chain = " ! ".join(parts)
    if preamp_db != 0.0:
        chain += f" ! volume name=eq_preamp volume={10.0 ** (preamp_db / 20.0):.4f}"
    return chain
