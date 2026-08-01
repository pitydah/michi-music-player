"""Demo library fixtures for presentation preview only.

These fixtures back screenshots, demos, and design reviews. They must NEVER
substitute real services and are only reachable through the gated bootstrap
hook when the app is launched with ``--presentation-preview``.
"""

DEMO_ALBUMS: list[dict] = [
    {"title": "Midnight Sessions", "artist": "Luna Vale", "year": 2024, "track_count": 12},
    {"title": "Analog Dreams", "artist": "The Analog Society", "year": 2023, "track_count": 9},
    {"title": "Neon Horizon", "artist": "Kaito", "year": 2024, "track_count": 14},
    {"title": "Silent Cartography", "artist": "Marea Alba", "year": 2022, "track_count": 10},
    {"title": "Granite & Glass", "artist": "Fermata", "year": 2021, "track_count": 8},
    {"title": "Solar Winds", "artist": "Helios Quartet", "year": 2023, "track_count": 11},
]

DEMO_TRACKS: list[dict] = [
    {"title": "Low Tide", "artist": "Luna Vale", "album": "Midnight Sessions", "duration_s": 243, "track_number": 1},
    {"title": "Velvet Circuit", "artist": "Luna Vale", "album": "Midnight Sessions", "duration_s": 198, "track_number": 2},
    {"title": "Tape Hiss Morning", "artist": "The Analog Society", "album": "Analog Dreams", "duration_s": 276, "track_number": 1},
    {"title": "Chrome Reel", "artist": "The Analog Society", "album": "Analog Dreams", "duration_s": 231, "track_number": 2},
    {"title": "Neon Horizon", "artist": "Kaito", "album": "Neon Horizon", "duration_s": 254, "track_number": 1},
    {"title": "Midnight Drive", "artist": "Kaito", "album": "Neon Horizon", "duration_s": 212, "track_number": 3},
    {"title": "Coastline Unknown", "artist": "Marea Alba", "album": "Silent Cartography", "duration_s": 305, "track_number": 1},
    {"title": "Granite & Glass", "artist": "Fermata", "album": "Granite & Glass", "duration_s": 267, "track_number": 1},
    {"title": "Corona", "artist": "Helios Quartet", "album": "Solar Winds", "duration_s": 289, "track_number": 1},
    {"title": "Perihelion", "artist": "Helios Quartet", "album": "Solar Winds", "duration_s": 322, "track_number": 2},
]

DEMO_ARTISTS: list[dict] = [
    {"name": "Luna Vale", "album_count": 1, "genre": "Dream Pop"},
    {"name": "The Analog Society", "album_count": 1, "genre": "Lo-Fi"},
    {"name": "Kaito", "album_count": 1, "genre": "Synthwave"},
    {"name": "Marea Alba", "album_count": 1, "genre": "Ambient"},
    {"name": "Fermata", "album_count": 1, "genre": "Post-Rock"},
    {"name": "Helios Quartet", "album_count": 1, "genre": "Modern Classical"},
]

DEMO_PLAYLISTS: list[dict] = [
    {"name": "Late Night Focus", "track_count": 24, "description": "Slow-burners for deep work"},
    {"name": "Analog Morning", "track_count": 16, "description": "Warm tape textures to start the day"},
    {"name": "Neon Drive", "track_count": 18, "description": "Synth-heavy night driving"},
]
