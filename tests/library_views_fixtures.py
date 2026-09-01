"""Synthetic presentation rows for Library Views visual and scale tests."""


def make_album_row(
    key: str,
    *,
    title: str = "Album",
    artist: str = "Artist",
    year: int = 2000,
    track_count: int = 10,
    duration_ms: int = 2_400_000,
    artwork_path: str = "",
    technical_summary: str = "FLAC · 24-bit · 96 kHz",
    contains_high_resolution: bool = True,
) -> dict:
    return {
        "key": key,
        "title": title,
        "artist": artist,
        "year": year,
        "decade": f"{year // 10 * 10}s" if year > 0 else "Unknown era",
        "trackCount": track_count,
        "durationMs": duration_ms,
        "discCount": 1,
        "genres": ["Electronic"],
        "composers": [],
        "hasArtwork": bool(artwork_path),
        "artworkPath": artwork_path,
        "technicalState": "exact",
        "technicalSummary": technical_summary,
        "codecs": [technical_summary.split(" · ", 1)[0]],
        "maxSampleRateHz": 96_000,
        "maxBitDepth": 24,
        "maxChannels": 2,
        "containsDsd": False,
        "containsHighResolution": contains_high_resolution,
        "isFavorite": False,
        "isRecentlyAdded": False,
        "artworkPalette": {
            "colors": ["#152A45", "#13243D", "#0A0D14"],
            "dominant": "#152A45",
            "secondary": "#13243D",
            "backplane": "#0A0D14",
            "accentSafe": "#5C82AF",
            "luminance": 0.16,
            "warmth": -0.19,
        },
    }


def make_many_album_rows(count: int = 10_000) -> list[dict]:
    return [
        make_album_row(
            f"album::{index}",
            title=f"Album {index:05d}",
            artist=f"Artist {index % 1000:04d}",
            year=1950 + (index % 77),
            track_count=8 + (index % 9),
            contains_high_resolution=index % 7 == 0,
        )
        for index in range(count)
    ]
