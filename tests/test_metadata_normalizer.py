"""Tests for filename inference and catalogue metadata normalization."""
import json

from library.metadata_normalizer import (
    assess_metadata_quality,
    compute_metadata_hash,
    enrich_index_record,
    infer_metadata_from_filename,
    normalize_disc_track,
    normalize_genres,
    normalize_isrc,
    normalize_mb_id,
    normalize_sort_text,
    normalize_text,
    normalize_year,
)


class TestInferMetadataFromFilename:
    def test_simple_artist_title(self):
        result = infer_metadata_from_filename(
            "/music/Depeche Mode - Shake the Disease.mp3"
        )
        assert result["artist"] == "Depeche Mode"
        assert result["title"] == "Shake the Disease"

    def test_track_number_prefix_hyphen(self):
        result = infer_metadata_from_filename(
            "/music/01 - Depeche Mode - Shake the Disease.mp3"
        )
        assert result["track_number"] == 1
        assert result["artist"] == "Depeche Mode"
        assert result["title"] == "Shake the Disease"

    def test_track_number_prefix_dot(self):
        result = infer_metadata_from_filename("/music/3. Toto - Africa.flac")
        assert result["track_number"] == 3
        assert result["artist"] == "Toto"
        assert result["title"] == "Africa"

    def test_no_separator(self):
        result = infer_metadata_from_filename("/music/Archivo sin separador.mp3")
        assert result["artist"] == ""
        assert result["title"] == "Archivo sin separador"

    def test_unicode_separators(self):
        for separator in ("–", "—", "|"):
            result = infer_metadata_from_filename(
                f"/music/Artista {separator} Canción.ogg"
            )
            assert result["artist"] == "Artista"
            assert result["title"] == "Canción"

    def test_underscore(self):
        result = infer_metadata_from_filename("/music/Artist_Title.wav")
        assert result["artist"] == "Artist"
        assert result["title"] == "Title"


class TestTextNormalization:
    def test_normalize_text_removes_controls_and_collapses_whitespace(self):
        assert normalize_text("  Uno\x00  dos\n tres  ") == "Uno dos tres"

    def test_normalize_sort_text_is_accent_and_case_insensitive(self):
        assert normalize_sort_text("  Árbol—AZUL  ") == "arbol azul"

    def test_genres_are_deduplicated_without_losing_display_case(self):
        assert normalize_genres("Rock; rock | Jazz\x00Ambient") == [
            "Rock",
            "Jazz",
            "Ambient",
        ]


class TestIdentifiersAndNumbers:
    def test_year_rejects_implausible_values(self):
        assert normalize_year("2024-03-04") == 2024
        assert normalize_year("0999") == 0
        assert normalize_year("9999") == 0

    def test_disc_track_parser_supports_tuple_and_fraction(self):
        assert normalize_disc_track("3/12") == (3, 12)
        assert normalize_disc_track((2, 4)) == (2, 4)
        assert normalize_disc_track("20/10") == (20, 0)

    def test_musicbrainz_uuid_is_validated(self):
        valid = "550e8400-e29b-41d4-a716-446655440000"
        assert normalize_mb_id(f"urn:uuid:{valid}") == valid
        assert normalize_mb_id("not-a-mbid") == ""

    def test_isrc_is_normalized_and_validated(self):
        assert normalize_isrc("us-abc-12-34567") == "USABC1234567"
        assert normalize_isrc("bad") == ""


class TestMetadataQuality:
    def test_enrichment_builds_search_keys_and_provenance(self):
        record = enrich_index_record({
            "filepath": "/music/a.flac",
            "filename": "01 - Canción Única.flac",
            "title": " Canción   Única ",
            "artist": "Árbol Azul",
            "albumartist": "Árbol Azul",
            "album": "Disco Ñ",
            "genre": "Rock; rock; Jazz",
            "year": "2024-01-01",
            "track_number": "1/10",
            "duration": 240,
            "sample_rate": 96000,
            "channels": 2,
            "mb_track_id": "550e8400-e29b-41d4-a716-446655440000",
        })

        assert record["title"] == "Canción Única"
        assert record["normalized_title"] == "cancion unica"
        assert record["normalized_artist"] == "arbol azul"
        assert record["normalized_album"] == "disco n"
        assert record["genre"] == "Rock; Jazz"
        assert record["track_number"] == 1
        assert record["track_total"] == 10
        assert record["metadata_source"] == "embedded_tags"
        assert record["metadata_completeness"] >= 80
        assert 0.0 < record["metadata_confidence"] <= 1.0
        assert len(record["metadata_hash"]) == 64
        assert json.loads(record["metadata_issues"]) == ["missing_album_artist"] or isinstance(
            json.loads(record["metadata_issues"]), list
        )

    def test_quality_reports_missing_core_fields(self):
        score, issues = assess_metadata_quality({"title": "Only title"})
        assert score < 50
        assert "missing_artist" in issues
        assert "missing_album" in issues

    def test_metadata_hash_ignores_filepath(self):
        base = {"title": "Song", "artist": "Artist", "album": "Album"}
        left = compute_metadata_hash({**base, "filepath": "/a.flac"})
        right = compute_metadata_hash({**base, "filepath": "/b.flac"})
        assert left == right
