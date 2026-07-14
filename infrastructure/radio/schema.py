import sqlite3


SCHEMA_VERSION = 2


def create_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            stream_url TEXT NOT NULL,
            homepage_url TEXT DEFAULT '',
            favicon_url TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            country TEXT DEFAULT '',
            language TEXT DEFAULT '',
            codec TEXT DEFAULT '',
            bitrate INTEGER DEFAULT 0,
            favorite INTEGER DEFAULT 0,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            last_played_at TEXT DEFAULT '',
            play_count INTEGER DEFAULT 0,
            last_probe_status TEXT DEFAULT '',
            last_probe_at TEXT DEFAULT '',
            deleted INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_station_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (station_id) REFERENCES radio_stations(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radio_probe_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER NOT NULL,
            probed_at TEXT NOT NULL,
            status TEXT DEFAULT '',
            content_type TEXT DEFAULT '',
            codec TEXT DEFAULT '',
            bitrate INTEGER DEFAULT 0,
            icy_name TEXT DEFAULT '',
            icy_genre TEXT DEFAULT '',
            icy_url TEXT DEFAULT '',
            icy_metaint INTEGER DEFAULT 0,
            latency_ms REAL DEFAULT 0.0,
            http_status INTEGER DEFAULT 0,
            error TEXT DEFAULT '',
            FOREIGN KEY (station_id) REFERENCES radio_stations(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stations_deleted
        ON radio_stations(deleted)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stations_favorite
        ON radio_stations(favorite)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stations_url
        ON radio_stations(stream_url)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_probe_cache_station
        ON radio_probe_cache(station_id)
    """)


def migrate(conn: sqlite3.Connection):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current < 1:
        conn.execute("PRAGMA user_version = 1")
        current = 1
    if current < 2:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stations_last_played
            ON radio_stations(last_played_at)
        """)
        conn.execute("PRAGMA user_version = 2")
