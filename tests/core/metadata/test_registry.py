from core.metadata.registry import MetadataFormatRegistry


class TestMetadataFormatRegistry:
    def test_default_registry_has_formats(self):
        reg = MetadataFormatRegistry.default_registry()
        assert len(reg.all()) >= 5

    def test_get_by_extension_mp3(self):
        reg = MetadataFormatRegistry.default_registry()
        cap = reg.get_by_extension("mp3")
        assert cap is not None
        assert cap.format_id == "mp3_id3"
        assert cap.readable is True
        assert cap.writable is True

    def test_get_by_extension_flac(self):
        reg = MetadataFormatRegistry.default_registry()
        cap = reg.get_by_extension("flac")
        assert cap is not None
        assert cap.readable is True
        assert cap.lossless_write is True

    def test_get_unknown(self):
        reg = MetadataFormatRegistry.default_registry()
        cap = reg.get_by_extension("xyz")
        assert cap is None

    def test_is_readable(self):
        reg = MetadataFormatRegistry.default_registry()
        assert reg.is_readable("mp3") is True
        assert reg.is_readable("flac") is True
        assert reg.is_readable("xyz") is False

    def test_is_writable(self):
        reg = MetadataFormatRegistry.default_registry()
        assert reg.is_writable("mp3") is True
        assert reg.is_writable("wav") is False

    def test_list_readable(self):
        reg = MetadataFormatRegistry.default_registry()
        readable = reg.list_readable()
        assert len(readable) >= 5

    def test_list_writable(self):
        reg = MetadataFormatRegistry.default_registry()
        writable = reg.list_writable()
        assert len(writable) >= 4

    def test_get_by_id(self):
        reg = MetadataFormatRegistry.default_registry()
        cap = reg.get("flac")
        assert cap is not None
        assert "flac" in cap.extensions

    def test_register_custom(self):
        reg = MetadataFormatRegistry()
        from core.metadata.models import FormatCapability
        reg.register(FormatCapability(format_id="custom", extensions=["cst"],
                                       readable=True))
        assert reg.is_readable("cst") is True
