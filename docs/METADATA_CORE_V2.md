# Metadata Core V2 — Architecture & Usage

## Overview

Canonical metadata subsystem for Michi Music Player. Format-agnostic reader/writer with per-format Mutagen adapters, safe backup/rollback, SQLite journal, normalization, MusicBrainz/CoverArt providers.

## Architecture

```
MetadataService
├── MetadataReader         (probe, read, read_many)
├── MetadataWriter         (write, verify, backup)
├── MetadataFormatRegistry (capability matrix per format)
├── MetadataNormalizer     (Unicode, trim, ISRC, MBID)
├── MetadataBackupService  (full file backup/restore)
├── MetadataRollbackService(rollback with verification)
├── MetadataJournalRepository (SQLite operation journal)
├── MusicBrainzProvider    (consolidated MB provider)
├── CoverArtProvider       (Cover Art Archive provider)
└── Cancellation           (token-based cancellation)
```

## Supported Formats

| Format | Read | Write | Artwork | Lyrics | MBIDs |
|--------|------|-------|---------|--------|-------|
| MP3 (ID3) | ✅ | ✅ | ✅ | ✅ | ✅ |
| FLAC | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ogg Vorbis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Opus | ✅ | ✅ | ✅ | ✅ | ✅ |
| M4A/MP4 | ✅ | ✅ | ✅ | ✅ | ✅ |
| WAV | ✅ | ❌ | ❌ | ❌ | ❌ |
| AIFF | ✅ | ❌ | ❌ | ❌ | ❌ |
| APE | ✅ | ❌ | ❌ | ❌ | ❌ |
| WMA/ASF | ✅ | ❌ | ❌ | ❌ | ❌ |
| DSF | ✅ | ❌ | ❌ | ❌ | ❌ |

## Models

- `TrackMetadata` — 40+ typed fields (genres as list, int/null for numbers)
- `TechnicalMetadata` — immutable container/codec/bitrate/samplerate
- `ArtworkMetadata` — hash-based dedup, lazy data reference
- `MetadataDocument` — composite: track + technical + artworks
- `MetadataPatch` — typed field changes with confidence/source/reason
- `MetadataOperationResult` — typed with code, warnings, retryable
- `FormatCapability` — per-format capability declaration

## Key Modules

| Module | Responsibility |
|--------|---------------|
| `core/metadata/models.py` | All dataclasses, enums, compute_file_signature |
| `core/metadata/reader.py` | Mutagen-based reader with per-format ID3/MP4/Vorbis |
| `core/metadata/writer.py` | Mutagen-based writer with field-level granularity |
| `core/metadata/registry.py` | Format capability matrix |
| `core/metadata/normalizer.py` | Unicode, ISRC, MBID, year parsing |
| `core/metadata/backup_rollback.py` | Full file backup and restore |
| `core/metadata/journal.py` | SQLite durable operation log |
| `core/metadata/service.py` | MetadataService facade |
| `integrations/musicbrainz/provider.py` | Consolidated MB search/lookup |
| `integrations/coverart/provider.py` | Cover Art Archive resolver |

## Usage

```python
from core.metadata.service import MetadataService
from core.metadata.models import TrackMetadata, MetadataFieldChange
from core.metadata.enums import FieldOperation, BackupPolicy

svc = MetadataService()

# Probe a file
result = svc.probe("/music/song.flac")

# Read metadata
result = svc.read("/music/song.flac", include_artwork_metadata=True)
if result.ok:
    doc = result.data["document"]
    print(doc.track.title, doc.track.artists)

# Write changes
changes = [
    MetadataFieldChange(field="title", new_value="New Title",
                        operation=FieldOperation.SET, selected=True),
]
svc.write("/music/song.flac", doc, changes,
          backup_policy=BackupPolicy.FULL_FILE_BACKUP)
```

## Tests

```bash
pytest tests/core/metadata -q --timeout=480
```
