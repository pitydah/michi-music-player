"""Conversion between graphic (31-band) and parametric EQ modes."""

import numpy as np
from audio.eq_presets import ISO_31_FREQS
from audio.eq_biquad import eval_response


def graphic_to_parametric(graphic_bands: list[float]) -> tuple[list[dict], float]:
    """Convert 31-band graphic EQ values to a 10-band parametric preset.
    
    Strategy: find peaks/valleys in the 31-band response and create
    Peak filters at those positions. Add shelf filters at extremes.
    """
    assert len(graphic_bands) == 31
    gains = np.array(graphic_bands, dtype=np.float64)

    bands = []

    # Low shelf at 60Hz (average of bands 1-5)
    low_avg = float(np.mean(gains[1:5]))
    if abs(low_avg) > 0.5:
        bands.append({"type": "LowShelf", "freq": 60, "gain": round(low_avg, 1), "Q": 0.7})

    # Find local peaks/valleys (bands 4-27, skipping extreme ends)
    peaks = []
    for i in range(3, 28):
        if abs(gains[i]) < 0.3:
            continue
        prev = gains[i-1] if i > 0 else 0
        nxt = gains[i+1] if i < 30 else 0
        if (gains[i] > prev and gains[i] > nxt) or (gains[i] < prev and gains[i] < nxt):
            peaks.append((ISO_31_FREQS[i], gains[i]))

    # Take top 6-7 peaks by absolute value
    peaks.sort(key=lambda x: abs(x[1]), reverse=True)
    for freq, gain in peaks[:7]:
        bands.append({"type": "Peak", "freq": freq, "gain": round(float(gain), 1), "Q": 1.4})

    # High shelf at 10kHz (average of last 3 bands)
    high_avg = float(np.mean(gains[28:31]))
    if abs(high_avg) > 0.5:
        bands.append({"type": "HighShelf", "freq": 10000, "gain": round(high_avg, 1), "Q": 0.7})

    # Sort by frequency
    bands.sort(key=lambda b: b["freq"])

    return (bands, 0.0)


def parametric_to_graphic(param_bands: list[dict], preamp_db: float = 0.0) -> list[float]:
    """Sample parametric EQ response at 31 ISO frequencies."""
    freqs = np.array(ISO_31_FREQS, dtype=np.float64)
    response = eval_response(param_bands, freqs, preamp_db)
    return [round(float(v), 1) for v in response]
