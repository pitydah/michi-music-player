"""Equalizer presets — graphic (31-band) and parametric modes."""

import os
import json

SETTINGS_DIR = os.path.expanduser("~/.local/share/michi-music-player")
PRESETS_PATH = os.path.join(SETTINGS_DIR, "eq_presets.json")

# ── 31-band ISO frequencies ──

ISO_31_FREQS = [
    20, 25, 31, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000,
]

ISO_31_LABELS = [
    "20", "25", "31", "40", "50", "63", "80", "100", "125", "160",
    "200", "250", "315", "400", "500", "630", "800", "1k", "1.3k", "1.6k",
    "2k", "2.5k", "3.2k", "4k", "5k", "6.3k", "8k", "10k", "13k", "16k", "20k",
]

# ── Graphic EQ presets (31 floats, ±12 dB) ──

GRAPHIC_PRESETS = {
    "Flat": [0.0] * 31,
    "Rock": [
        5.0, 4.5, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -2.5,
        -2.0, -1.0, 0.0, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5,
        5.0, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5,
    ],
    "Pop": [
        2.0, 1.5, 1.0, 0.0, -1.0, -1.5, -1.0, 0.0, 1.0, 2.0,
        3.0, 3.5, 3.0, 2.0, 1.5, 1.0, 0.5, 0.0, 0.5, 1.0,
        2.0, 3.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0,
    ],
    "Jazz": [
        4.0, 3.5, 3.0, 2.0, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.5, 1.0, 2.0, 3.0, 3.5, 3.0, 2.5, 2.0, 2.0,
        2.5, 3.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0, 0.0,
    ],
    "Classical": [
        5.0, 4.5, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.0, 3.0,
        3.0, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0,
    ],
    "Bass Boost": [
        8.0, 7.5, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "Vocal Boost": [
        -2.0, -1.5, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 4.5, 4.0,
        3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 1.0, 1.5, 2.0,
        2.5, 3.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0,
    ],
    "Treble Boost": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5,
        4.0, 4.5, 5.0, 5.5, 6.0, 6.0, 6.0, 6.0, 5.5, 5.0, 4.5,
    ],
}

# ── Parametric presets ──

PARAMETRIC_PRESETS = {
    "Flat": [],
    "Rock": [
        {"type": "LowShelf", "freq": 80, "gain": 3.0, "Q": 0.7},
        {"type": "Peak", "freq": 250, "gain": -2.0, "Q": 1.2},
        {"type": "Peak", "freq": 800, "gain": 1.5, "Q": 0.8},
        {"type": "Peak", "freq": 2500, "gain": 4.0, "Q": 1.5},
        {"type": "Peak", "freq": 6000, "gain": -1.0, "Q": 2.0},
        {"type": "HighShelf", "freq": 12000, "gain": 2.0, "Q": 0.7},
    ],
    "Pop": [
        {"type": "LowShelf", "freq": 60, "gain": 2.0, "Q": 0.7},
        {"type": "Peak", "freq": 120, "gain": -1.0, "Q": 1.0},
        {"type": "Peak", "freq": 400, "gain": 2.0, "Q": 0.8},
        {"type": "Peak", "freq": 1500, "gain": 3.0, "Q": 1.0},
        {"type": "Peak", "freq": 4000, "gain": 2.0, "Q": 1.5},
        {"type": "HighShelf", "freq": 10000, "gain": 1.0, "Q": 0.7},
    ],
    "Jazz": [
        {"type": "LowShelf", "freq": 80, "gain": 4.0, "Q": 0.6},
        {"type": "Peak", "freq": 200, "gain": -1.0, "Q": 1.0},
        {"type": "Peak", "freq": 600, "gain": 2.0, "Q": 0.9},
        {"type": "Peak", "freq": 2000, "gain": 3.0, "Q": 1.2},
        {"type": "Peak", "freq": 5000, "gain": -1.0, "Q": 2.0},
        {"type": "HighShelf", "freq": 10000, "gain": 3.0, "Q": 0.6},
    ],
    "Classical": [
        {"type": "LowShelf", "freq": 60, "gain": 4.0, "Q": 0.6},
        {"type": "Peak", "freq": 300, "gain": -1.0, "Q": 1.5},
        {"type": "Peak", "freq": 700, "gain": 2.0, "Q": 1.0},
        {"type": "Peak", "freq": 2500, "gain": 2.0, "Q": 1.0},
        {"type": "Peak", "freq": 6000, "gain": -1.0, "Q": 2.0},
        {"type": "HighShelf", "freq": 10000, "gain": 3.0, "Q": 0.6},
    ],
}


def get_preset_names() -> list[str]:
    return sorted(GRAPHIC_PRESETS.keys())


def load_graphic_preset(name: str) -> list[float]:
    """Load a 31-band graphic preset. Returns list of 31 floats in dB."""
    return list(GRAPHIC_PRESETS.get(name, GRAPHIC_PRESETS["Flat"]))


def load_parametric_preset(name: str) -> list[dict]:
    """Load a parametric preset. Returns list of band dicts."""
    return list(PARAMETRIC_PRESETS.get(name, []))


def save_custom_presets(presets: dict):
    """Save custom presets to JSON file."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(PRESETS_PATH, "w") as f:
        json.dump(presets, f, indent=2)


def load_custom_presets() -> dict:
    """Load custom presets from JSON file."""
    if os.path.exists(PRESETS_PATH):
        with open(PRESETS_PATH) as f:
            return json.load(f)
    return {}
