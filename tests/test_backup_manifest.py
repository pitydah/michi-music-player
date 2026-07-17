from core.audio_lab.backup_manifest import generate_manifest, manifest_to_csv, manifest_to_json


class TestBackupManifest:
    def test_generate_manifest_none(self):
        result = generate_manifest(None)
        assert result == []

    def test_format_json_empty(self):
        result = format_manifest_json([])
        assert result is not None
