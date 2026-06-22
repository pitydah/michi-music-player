"""AutoEQ integration — load headphone presets from local cache or GitHub."""

import json
import os
import urllib.request

CACHE_DIR = os.path.expanduser("~/.local/share/michi-music-player/autoeq")


def search_headphone(query: str) -> list[str]:
    """Search local cache for matching headphone presets."""
    if not os.path.isdir(CACHE_DIR):
        return []
    results = []
    for fn in os.listdir(CACHE_DIR):
        if fn.endswith(".json") and query.lower() in fn.lower():
            results.append(fn.replace(".json", "").replace("_", " "))
    return sorted(results)[:20]


def load_headphone_preset(model: str) -> list[dict]:
    """Load AutoEQ preset from local cache."""
    slug = model.replace(" ", "_").replace("/", "_") + ".json"
    path = os.path.join(CACHE_DIR, slug)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Preset not found locally: {model}")

    with open(path) as f:
        data = json.load(f)

    # AutoEQ stores bands as "preamp", "filters": [{type, frequency, gain, Q}]
    bands = []
    for entry in data.get("filters", []):
        bands.append({
            "type": entry.get("type", "Peak"),
            "freq": entry.get("frequency", 1000.0),
            "gain": entry.get("gain", 0.0),
            "Q": entry.get("Q", entry.get("q", 1.41)),
        })

    return bands


def download_autoeq_index() -> list[str]:
    """Download list of available AutoEQ presets from GitHub."""
    url = ("https://raw.githubusercontent.com/jaakkopasanen/AutoEq/"
           "master/results/INDEX.md")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8")
        # Parse markdown links
        models = []
        for line in text.splitlines():
            if "[" in line and "oratory1990" in line:
                parts = line.split("](")
                if len(parts) >= 2:
                    model = parts[0].strip("[")
                    if model:
                        models.append(model)
        return models
    except Exception:
        return []


def download_preset(model: str) -> list[dict]:
    """Download a specific AutoEQ preset from GitHub."""
    # Construct URL
    slug = model.replace(" ", "%20")
    url = (
        "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/"
        f"master/results/oratory1990/harman_over-ear_2018/{slug}/{slug}.json"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Cache locally
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(
            CACHE_DIR, model.replace(" ", "_").replace("/", "_") + ".json")
        with open(cache_path, "w") as f:
            json.dump(data, f)

        bands = []
        for entry in data.get("filters", []):
            bands.append({
                "type": entry.get("type", "Peak"),
                "freq": entry.get("frequency", 1000.0),
                "gain": entry.get("gain", 0.0),
                "Q": entry.get("Q", entry.get("q", 1.41)),
            })
        return bands
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e
