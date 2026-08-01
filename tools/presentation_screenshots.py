#!/usr/bin/env python3
"""Generate presentation screenshots (requires --presentation-preview)."""
from pathlib import Path

OUT_DIR = Path("artifacts/presentation_uiux")
ROUTES = [
    ("home", "home"),
    ("library", "library.albums"),
    ("nowplaying", "nowplaying"),
    ("queue", "queue"),
    ("mix", "mix"),
    ("audio_lab", "audio_lab"),
    ("ecosystem", "ecosystem"),
    ("podcasts", "streaming.podcasts"),
    ("big_server", "connections.big_server"),
    ("navidrome", "connections.navidrome"),
    ("michi_ai", "michi_ai"),
    ("settings", "settings"),
]

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Run with: python main.py --presentation-preview")
    print(f"Screenshots will be saved to {OUT_DIR}")
    print("Routes:", [r[0] for r in ROUTES])

if __name__ == "__main__":
    main()
