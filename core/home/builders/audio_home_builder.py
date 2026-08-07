"""AudioHomeBuilder — maps the canonical ContextService audio section.

The section is produced by ``AudioSectionProvider`` (which follows the
AGENTS.md home rules: bit-perfect is never ``verified`` — at most
``intended`` — and ``dac_active`` derives from device name keywords, never
from the profile name alone). This adapter only reshapes the section into
``AudioHomeStatus``; it never re-implements those heuristics.
"""

from __future__ import annotations


from core.home.home_status import AudioHomeStatus


def build_audio_status_from_section(section: dict) -> AudioHomeStatus:
    if not isinstance(section, dict):
        return AudioHomeStatus()
    if not section.get("available"):
        return AudioHomeStatus(
            output_profile=str(section.get("output_profile", "") or ""),
        )
    return AudioHomeStatus(
        output_device=str(section.get("output_device", "") or ""),
        output_profile=str(section.get("output_profile", "") or ""),
        dac_active=bool(section.get("dac_active", False)),
        replaygain_enabled=bool(section.get("replaygain_enabled", False)),
        eq_enabled=bool(section.get("eq_enabled", False)),
        dsp_active=bool(section.get("dsp_active", False)),
        bitperfect_state=str(section.get("bitperfect_state", "not_available") or "not_available"),
        bitperfect_intended=bool(section.get("bitperfect_intended", False)),
        format_label=str(section.get("format_label", "") or ""),
        sample_rate=int(section.get("sample_rate", 0) or 0),
        bit_depth=int(section.get("bit_depth", 0) or 0),
        warnings=list(section.get("warnings", []) or [])[:5],
    )
