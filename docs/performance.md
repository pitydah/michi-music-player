# Performance Testing

## Perf suites

### file-based smoke
Uses `generate()` which creates empty placeholder audio files + `LibraryDB.add_file()`.
Measures import overhead + metadata fallback + DB indexing.
Sample: 5,000 tracks.

### db-synthetic benchmark
Uses `generate_db_records()` which writes directly via `BatchWriter` + FTS rebuild.
Measures pure DB query/index performance without filesystem overhead.
Sample: 5,000 records.

## Running

```bash
# All perf tests
pytest tests/perf/ -m perf -v

# Specific test
pytest tests/perf/test_library_perf.py -m perf -v -k test_get_all
```

## Thresholds (5,000 items)

| Suite | Operation | Threshold |
|---|---:|---:|
| file-based | get_all | < 2.5s |
| file-based | search_advanced | < 1.0s |
| file-based | get_stats | < 1.0s |
| file-based | cleanup_missing_under_root | < 0.2s |
| db-synthetic | get_all | < 2.0s |

## Generating Synthetic Data

```python
# file-based smoke
from tests.perf.generate_library import generate
from library.library_db import LibraryDB
import tempfile
db = LibraryDB(":memory:")
generate(db, root=str(tempfile.mkdtemp()), count=5_000)

# db-synthetic benchmark
from tests.perf.generate_library import generate_db_records
db = LibraryDB("/tmp/perf.db")
generate_db_records(db, count=10_000)
```
