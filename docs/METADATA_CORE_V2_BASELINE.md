# Metadata Core V2 — Baseline Audit

**SHA inicial:** 3bc9be749fbc236677c1bf9f42749c2910120b97
**Rama:** feature/metadata-core-v2

## Archivos auditados

- `metadata/tag_model.py` — TrackTags dataclass
- `metadata/tag_reader.py` — Mutagen tag reader (ID3, Vorbis, MP4)
- `metadata/tag_writer.py` — Mutagen tag writer
- `metadata/tag_actions.py` — Batch tag operations
- `metadata/artwork_utils.py` — Artwork resize/crop via PIL
- `metadata/rename_engine.py` — File rename by tags
- `metadata/album_summary.py` — AlbumSummary dataclass
- `metadata/review/` — Review schemas, diff, matcher, service, repository, apply, undo
- `library/metadata_extractor.py` — Full metadata extraction (Mutagen + GStreamer)
- `library/metadata_normalizer.py` — Text/artist/album normalization
- `integrations/knowledge_broker/` — MusicBrainzSyncProvider, CoverArtSyncProvider
- `integrations/enrichment/` — Async MusicBrainz provider
- `integrations/artist_metadata/` — Artist/album enrichment services

## Duplicaciones críticas

1. **4 pipelines de lectura**: tag_reader, metadata_extractor, QML bridge, TagWriter facade
2. **4 providers MusicBrainz**: knowledge_broker (sync), enrichment (async), artist_metadata (async), musicbrainz_page (direct)
3. **4 writers**: tag_writer, TagWriter facade, metadata_tag_adapter, musicbrainz_page
4. **~20 campos sin TrackTags**: replaygain, r128, acoustid, copyright, label, conductor, etc.
5. **3 convenciones de nombre**: `musicbrainz_trackid`, `mb_track_id`, `MusicBrainz Track Id`

## Formatos detectados

- MP3/ID3: lectura/escritura completa
- FLAC, Ogg Vorbis, Opus, M4A/MP4: lectura/escritura
- WAV, AIFF, APE, WMA, DSF: lectura parcial (sin escritura)

## Tests existentes: ~158

## Plan de convergencia

1. Modelo canónico (MetadataDocument, TrackMetadata, TechnicalMetadata, ArtworkMetadata)
2. Adapters por formato (Id3, Vorbis, Mp4, WaveId3, Asf, Ape, Dsf)
3. SafeReader con probe, SafeWriter con backup/verify
4. BackupService, RollbackService, JournalRepository
5. Normalizer, IdentityResolvers, Matcher
6. ProviderRegistry, MusicBrainzProvider consolidado
7. ProposalService, ReviewService, ApplyService (saga)
8. DuplicateDetection, ConsistencyService
9. Legacy wrappers (TrackTagsLegacyAdapter, read_tags/write_tags compat)
10. Tests por formato, seguridad, matching, concurrencia
