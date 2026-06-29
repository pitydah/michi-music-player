"""Generate a synthetic library of tracks for performance testing."""

import random
import string
import time
from pathlib import Path

from library.batch_writer import BatchWriter, BATCH_COLUMNS, NUMERIC_DEFAULTS, FLOAT_DEFAULTS


def random_title(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _make_record(fp: str, i: int, count: int) -> dict:
    title = random_title()
    artist = f"Artist_{random.randint(0, count // 100)}"
    album = f"Album_{random.randint(0, count // 50)}"
    record = {
        "filepath": fp,
        "filename": Path(fp).name,
        "directory": str(Path(fp).parent),
        "ext": ".flac",
        "kind": "audio",
        "size": random.randint(1_000_000, 50_000_000),
        "mtime": int(time.time()),
        "duration": random.randint(120, 600),
        "channels": 2,
        "sample_rate": 44100,
        "bitrate": random.randint(800, 1411),
        "title": title,
        "artist": artist,
        "album": album,
        "albumartist": artist,
        "year": random.randint(1970, 2024),
        "genre": "Synthetic",
        "track_number": random.randint(1, 20),
        "track_total": 20,
        "disc_number": 1,
        "disc_total": 1,
        "composer": artist,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "last_scanned": int(time.time()),
        "scan_status": "ok",
    }
    for col in BATCH_COLUMNS:
        record.setdefault(col, "" if col not in NUMERIC_DEFAULTS and col not in FLOAT_DEFAULTS else 0)
    return record


def generate(db, root: str, count: int = 10_000):
    """Create synthetic audio files via db.add_file().

    This is a file-based smoke: it creates empty placeholder files and
    measures import overhead + metadata fallback + DB indexing.
    """
    start = time.perf_counter()
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        artist_dir = root_path / f"Artist_{random.randint(0, count // 100)}"
        album_dir = artist_dir / f"Album_{random.randint(0, count // 50)}"
        album_dir.mkdir(parents=True, exist_ok=True)
        fp = str(album_dir / f"track_{i:06d}.flac")
        Path(fp).write_text("")
        db.add_file(fp)

    elapsed = time.perf_counter() - start
    print(f"  file-based: generated {count} items in {elapsed:.2f}s")
    return elapsed


def generate_db_records(db, count: int = 10_000) -> None:
    """Populate LibraryDB via BatchWriter without creating audio files.

    This measures pure DB query/index performance without filesystem overhead.
    """
    start = time.perf_counter()
    writer = BatchWriter(db.conn, batch_size=500)
    for i in range(count):
        fp = f"/synthetic/track_{i:06d}.flac"
        record = _make_record(fp, i, count)
        writer.add(record)
    writer.flush()

    # Build FTS index so search_advanced works
    from library.search_index import SearchIndex
    idx = SearchIndex(db.conn)
    idx.rebuild_fts()

    elapsed = time.perf_counter() - start
    print(f"  db-synthetic: generated {count} records in {elapsed:.2f}s")
    return elapsed
