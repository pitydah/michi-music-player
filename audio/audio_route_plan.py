# -*- coding: utf-8 -*-
"""Audio Route Plan — describes the playback path for a given format/profile/device."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AudioRoutePlan:
    profile: str = "standard"
    backend: str = "auto"
    device_string: str = ""
    use_playbin: bool = True
    use_manual_pipeline: bool = False
    use_volume: bool = True
    use_eq: bool = False
    use_replaygain: bool = False
    use_spectrum: bool = False
    use_transmit: bool = False
    use_audioconvert: bool = True
    use_audioresample: bool = True
    force_rate: int = 0
    force_format: str = ""
    dsd_mode: str = ""  # none, pcm, dop, native
    bitperfect_expected: bool = False
    warnings: list[str] = field(default_factory=list)
    fallback_suggestion: str = ""
