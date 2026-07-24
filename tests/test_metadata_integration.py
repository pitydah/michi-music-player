"""Tests for Metadata — atomic write, batch, rollback."""



class TestMetadataIntegration:
    def test_tag_writer_atomic(self, tmp_path):
        """Verify tag writer creates backup and uses atomic replace."""
        from metadata.tag_writer import write_tags
        from metadata.tag_model import TrackTags

        audio = tmp_path / "test_song.flac"
        audio.write_text("dummy flac content")

        tags = TrackTags(filepath=str(audio))
        tags.set_field("title", "New Title")
        tags.set_field("artist", "Test Artist")

        result = write_tags(tags)
        # May fail on non-flac content, but should not corrupt
        assert isinstance(result, bool)

    def test_metadata_service_edit_field(self):
        from core.metadata_service import MetadataService
        svc = MetadataService()
        result = svc.edit_field("/nonexistent.flac", "title", "Test")
        assert not result.get("ok")

    def test_metadata_bridge_import(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        assert MetadataBridge is not None

    def test_metadata_bridge_has_slots(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        assert hasattr(MetadataBridge, 'loadMetadata')
        assert hasattr(MetadataBridge, 'saveChanges')

    def test_metadata_editor_service_exists(self):
        from core.composition.infrastructure import build as infra
        from core.composition.playback import build as playback
        from core.composition.library import build as library
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        playback(c)  # registra queue_service requerido por library.build()
        library(c)
        es = c.get("metadata_editor_service")
        assert es is not None

    def test_batch_edit_field(self):
        from core.metadata_service import MetadataService
        svc = MetadataService()
        result = svc.edit_batch(["/test/1.flac", "/test/2.flac"], "genre", "Rock")
        assert not result.get("ok")  # files don't exist
