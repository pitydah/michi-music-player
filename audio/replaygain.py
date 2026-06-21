"""ReplayGain — tag parsing, mode selection, preamp, headroom, anti-clipping."""
import contextlib
import math
from dataclasses import dataclass


@dataclass
class ReplayGainConfig:
    mode: str = "track"          # off | track | album | auto
    preamp_db: float = 0.0       # additional gain in dB
    headroom_db: float = 0.0     # headroom before clipping in dB
    anti_clip: bool = True       # prevent clipping
    peak_limit: float = 1.0      # max linear amplitude after gain

    @property
    def is_active(self) -> bool:
        return self.mode != "off"


def parse_gain_db(text: str) -> float | None:
    """Parse a ReplayGain value like '-5.2 dB' or '-5.2'."""
    if not text:
        return None
    with contextlib.suppress(ValueError):
        return float(str(text).replace(" dB", "").replace("dB", "").strip())
    return None


def db_to_linear(db: float) -> float:
    """Convert dB to linear gain factor."""
    return 10.0 ** (db / 20.0)


def linear_to_db(linear: float) -> float:
    """Convert linear gain to dB."""
    return 20.0 * math.log10(max(linear, 0.0001))


def select_gain(mode: str, track_gain: float | None,
                album_gain: float | None) -> float | None:
    """Select the ReplayGain value based on mode.

    Modes:
        off    → None (no gain)
        track  → track_gain
        album  → album_gain
        auto   → album_gain if available (album-level), else track_gain
    """
    if mode == "off":
        return None
    if mode == "track" and track_gain is not None:
        return track_gain
    if mode == "album" and album_gain is not None:
        return album_gain
    if mode == "auto":
        return album_gain if album_gain is not None else track_gain
    return track_gain if track_gain is not None else album_gain


def compute_safe_gain(gain_db: float | None, headroom_db: float,
                      track_peak: float | None = None,
                      album_peak: float | None = None,
                      anti_clip: bool = True) -> float:
    """Compute the safe linear gain, accounting for headroom and clipping.

    Args:
        gain_db: ReplayGain value in dB (negative = attenuate)
        headroom_db: Additional headroom in dB (positive = safer)
        track_peak: Peak amplitude from tag (0.0 to 1.0)
        album_peak: Peak amplitude from tag (0.0 to 1.0)
        anti_clip: If True, ensure output never exceeds 1.0

    Returns:
        Linear gain factor (1.0 = no change, <1.0 = attenuation)
    """
    if gain_db is None:
        return 1.0

    # Base gain from ReplayGain
    effective_db = gain_db - headroom_db
    gain = db_to_linear(effective_db)

    if not anti_clip:
        return gain

    # Check peak values
    peak = track_peak if track_peak is not None else album_peak
    if peak is None or peak <= 0.0 or peak >= 1.0:
        return gain

    # Prevent clipping: if peak * gain > peak_limit, reduce gain
    max_gain = 1.0 / max(peak, 0.0001)
    return min(gain, max_gain)


def apply_replaygain(profile, gain_db: float | None) -> tuple[bool, float]:
    """Check if ReplayGain should be applied for a profile.

    Returns (should_apply, linear_factor).
    """
    if gain_db is None or not profile.allows_replaygain:
        return False, 1.0
    return True, db_to_linear(gain_db)


def apply_full(config: ReplayGainConfig,
               track_gain: float | None,
               album_gain: float | None,
               track_peak: float | None = None,
               album_peak: float | None = None) -> tuple[float, str]:
    """Full ReplayGain application with preamp, headroom, anti-clip.

    Returns (linear_gain, label).
    """
    if not config.is_active:
        return 1.0, "ReplayGain off"

    selected = select_gain(config.mode, track_gain, album_gain)
    if selected is None:
        return 1.0, "No ReplayGain tags"

    # Apply preamp
    effective_db = selected + config.preamp_db

    # Compute safe gain
    gain = compute_safe_gain(
        effective_db, config.headroom_db,
        track_peak, album_peak, config.anti_clip)

    # Label
    mode_label = {"track": "Track", "album": "Album",
                  "auto": "Auto"}.get(config.mode, config.mode)
    db_str = f"{effective_db:+.1f}"
    return gain, f"{mode_label} {db_str} dB"
