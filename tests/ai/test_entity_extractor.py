from __future__ import annotations

from michi_ai.v2.intent.entity_extractor import EntityExtractor, EntityType


class TestEntityExtractor:
    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_extract_artist(self):
        entities = self.extractor.extract("reproduce algo de Radiohead")
        artist_entities = [e for e in entities if e.name == EntityType.ARTIST]
        assert len(artist_entities) > 0
        assert "Radiohead" in str(artist_entities[0].value)

    def test_extract_genre(self):
        entities = self.extractor.extract("hazme un mix de rock")
        genre_entities = [e for e in entities if e.name == EntityType.GENRE]
        assert len(genre_entities) > 0
        assert genre_entities[0].value == "Rock"

    def test_extract_genre_jazz(self):
        entities = self.extractor.extract("busca jazz")
        genre_entities = [e for e in entities if e.name == EntityType.GENRE]
        assert len(genre_entities) > 0
        assert genre_entities[0].value == "Jazz"

    def test_extract_year(self):
        entities = self.extractor.extract("canciones de 1997")
        year_entities = [e for e in entities if e.name == EntityType.YEAR]
        assert len(year_entities) > 0
        assert year_entities[0].value == 1997

    def test_extract_format(self):
        entities = self.extractor.extract("convierte a flac")
        fmt_entities = [e for e in entities if e.name == EntityType.FORMAT]
        assert len(fmt_entities) > 0
        assert fmt_entities[0].value == "FLAC"

    def test_extract_format_opus(self):
        entities = self.extractor.extract("convierte a opus 128")
        fmt_entities = [e for e in entities if e.name == EntityType.FORMAT]
        assert len(fmt_entities) > 0
        assert fmt_entities[0].value == "OPUS"

    def test_extract_device(self):
        entities = self.extractor.extract("sincroniza con el dispositivo")
        dev_entities = [e for e in entities if e.name == EntityType.DEVICE]
        assert len(dev_entities) > 0

    def test_extract_quantity(self):
        entities = self.extractor.extract("los últimos 20 temas")
        qty_entities = [e for e in entities if e.name == EntityType.QUANTITY]
        assert len(qty_entities) > 0
        assert qty_entities[0].value == 20

    def test_extract_scope(self):
        entities = self.extractor.extract("agrega a la cola")
        scope_entities = [e for e in entities if e.name == EntityType.SCOPE]
        assert len(scope_entities) > 0

    def test_no_entities(self):
        entities = self.extractor.extract("hola")
        assert len(entities) == 0

    def test_multiple_entities(self):
        entities = self.extractor.extract("reproduce rock de los 90 en flac")
        names = {e.name for e in entities}
        assert EntityType.GENRE in names
        assert EntityType.FORMAT in names or EntityType.DECADE in names

    def test_ambiguation_no_scope(self):
        entities = self.extractor.extract("reproduce eso")
        ambiguities = self.extractor.extract_ambiguation("reproduce eso", entities)
        assert len(ambiguities) > 0

    def test_no_ambiguation_with_scope(self):
        from michi_ai.v2.core.models import ExtractedEntity
        entities = [
            ExtractedEntity(name=EntityType.SCOPE, value="cola", confidence=0.9),
        ]
        ambiguities = self.extractor.extract_ambiguation("agrega eso a la cola", entities)
        refs = [a for a in ambiguities if a.field == "scope"]
        assert len(refs) == 0

    def test_extract_reference(self):
        entities = self.extractor.extract("reproduce esta canción")
        ref_entities = [e for e in entities if e.name == EntityType.PATH_REFERENCE]
        assert len(ref_entities) > 0
        assert ref_entities[0].resolved is False
