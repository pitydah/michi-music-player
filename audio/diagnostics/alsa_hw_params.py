"""ALSA hw_params reader — inspects /proc/asound for real playback parameters.

On Linux, when a PCM device is active, ALSA exposes the actual hardware parameters
in /proc/asound. This module reads those files to verify bit-perfect output.
"""

import os
import re
from dataclasses import dataclass


_PROC_ASOUND = "/proc/asound"

_PCM_PATH_RE = re.compile(
    r"card(?P<card>\d+)/pcm(?P<pcm>\d+)p/sub(?P<sub>\d+)/hw_params"
)


@dataclass
class AlsaHwParams:
    card: int = 0
    device: int = 0
    sub: int = 0
    access: str = ""
    format: str = ""
    sample_rate: int = 0
    channels: int = 0
    period_size: int = 0
    buffer_size: int = 0
    raw_text: str = ""


SAMPLE_RATE_RE = re.compile(r"rate:\s*(\d+)")
FORMAT_RE = re.compile(r"format:\s*(\S+)")
CHANNELS_RE = re.compile(r"channels:\s*(\d+)")
ACCESS_RE = re.compile(r"access:\s*(\S+)")
PERIOD_SIZE_RE = re.compile(r"period_size:\s*(\d+)")
BUFFER_SIZE_RE = re.compile(r"buffer_size:\s*(\d+)")


def find_active_hw_params() -> list[AlsaHwParams]:
    """Find all active ALSA PCM playback substreams with hw_params.

    Returns list of AlsaHwParams for each active substream found.
    Empty list if none found or /proc not available.
    """
    if not os.path.isdir(_PROC_ASOUND):
        return []

    results: list[AlsaHwParams] = []
    for root, _dirs, files in os.walk(_PROC_ASOUND):
        if "hw_params" in files:
            hw_path = os.path.join(root, "hw_params")
            m = _PCM_PATH_RE.search(hw_path)
            if not m:
                continue
            try:
                with open(hw_path) as f:
                    text = f.read()
            except (OSError, PermissionError):
                continue

            if not text.strip():
                continue

            params = parse_hw_params(text)
            params.card = int(m.group("card"))
            params.device = int(m.group("pcm"))
            params.sub = int(m.group("sub"))
            params.raw_text = text
            results.append(params)

    return results


def parse_hw_params(text: str) -> AlsaHwParams:
    """Parse hw_params text content into an AlsaHwParams struct."""
    params = AlsaHwParams()

    m = SAMPLE_RATE_RE.search(text)
    if m:
        params.sample_rate = int(m.group(1))

    m = FORMAT_RE.search(text)
    if m:
        params.format = m.group(1).strip()

    m = CHANNELS_RE.search(text)
    if m:
        params.channels = int(m.group(1))

    m = ACCESS_RE.search(text)
    if m:
        params.access = m.group(1).strip()

    m = PERIOD_SIZE_RE.search(text)
    if m:
        params.period_size = int(m.group(1))

    m = BUFFER_SIZE_RE.search(text)
    if m:
        params.buffer_size = int(m.group(1))

    return params
