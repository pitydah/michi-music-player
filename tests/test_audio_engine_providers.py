"""M11.3A: engine provider probes + AudioEngineService gates."""

import inspect
import os

import pytest
from PySide6.QtGui import QGuiApplication

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_service import AudioEngineService
from michi.domain.audio_engine import AudioEngineId
from michi.infrastructure.audio_engines.providers import (
    GStreamerEngineProvider,
    MpdEngineProvider,
    QtEngineProvider,
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


class TestQtProvider:
    def test_reference_engine_available(self):
        desc = QtEngineProvider().probe()
        assert desc.engine_id == AudioEngineId.QT_MULTIMEDIA
        assert desc.display_name == "Qt Multimedia"
        assert desc.available is True
        assert desc.implemented is True

    def test_open_returns_audio_port(self, qapp):
        from michi.application.ports import AudioPort

        port = QtEngineProvider().open()
        assert isinstance(port, AudioPort)
        port.stop()  # release resources cleanly

    def test_no_qt_import_at_module_time(self):
        """Base wheel usability: module import must not require QtMultimedia
        (probe imports it lazily)."""
        import michi.infrastructure.audio_engines.providers as mod

        assert "PySide6" not in inspect.getsource(mod)


class TestGStreamerProvider:
    def test_probe_is_lazy_and_truthful(self):
        desc = GStreamerEngineProvider().probe()
        assert desc.engine_id == AudioEngineId.GSTREAMER
        # truthful: available only when gi/Gst 1.0 loads; implemented=False
        # (the adapter belongs to M11.3C) regardless of availability
        assert desc.implemented is False
        if not desc.available:
            assert desc.unavailable_reason is not None

    def test_open_not_implemented_in_a(self):
        with pytest.raises(NotImplementedError):
            GStreamerEngineProvider().open()

    def test_no_gi_import_at_module_time(self):
        """gi must never be imported by shared modules at import time."""
        import michi.infrastructure.audio_engines.providers as mod

        src = inspect.getsource(mod)
        # the module itself must not contain a top-level `import gi`
        assert "import gi" not in src.split("def probe")[0]


class TestMpdProvider:
    def test_probe_truthful(self):
        desc = MpdEngineProvider().probe()
        assert desc.engine_id == AudioEngineId.MPD
        assert desc.implemented is False
        if not desc.available:
            assert "mpd" in (desc.unavailable_reason or "")

    def test_open_not_implemented_in_a(self):
        with pytest.raises(NotImplementedError):
            MpdEngineProvider().open()

    def test_probe_does_not_spawn(self):
        """probe() must never spawn MPD nor touch system MPD paths."""
        import ast

        import michi.infrastructure.audio_engines.providers as mod

        tree = ast.parse(inspect.getsource(mod))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imported.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imported.add(n.module or "")
        assert "subprocess" not in imported
        # probe() solo descubre el binario; nunca lo ejecuta
        probe_src = inspect.getsource(MpdEngineProvider.probe)
        assert "shutil.which" in probe_src
        assert "subprocess" not in probe_src
        assert "Popen" not in probe_src


class TestProviderComposition:
    def test_canonical_registry_with_all_providers(self):
        registry = AudioEngineRegistry(
            [
                QtEngineProvider(),
                GStreamerEngineProvider(),
                MpdEngineProvider(),
            ]
        )
        assert registry.engine_ids == (
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        )
        descriptors = registry.descriptors()
        assert descriptors[0].available is True  # Qt reference
        # GStreamer/MPD: installed status varies by machine; implemented is
        # always False in M11.3A
        assert all(d.implemented is False for d in descriptors[1:])


class TestAudioEngineService:
    def test_owns_immutable_state(self):
        service = AudioEngineService()
        assert service.state.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert service.state.active_engine_id is None

    def test_subscribe_idempotent(self):
        service = AudioEngineService()
        calls = []
        cb = lambda: calls.append(1)  # noqa: E731
        service.subscribe_changed(cb)
        service.subscribe_changed(cb)  # duplicate no-op
        service.unsubscribe_changed(lambda: None)  # unknown no-op
        assert len(service._subscribers) == 1

    def test_unsubscribe_idempotent(self):
        service = AudioEngineService()
        cb = lambda: None  # noqa: E731
        service.subscribe_changed(cb)
        service.unsubscribe_changed(cb)
        service.unsubscribe_changed(cb)
        assert service._subscribers == []

    def test_registry_projection_honest(self):
        registry = AudioEngineRegistry(
            [QtEngineProvider(), GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        assert service.registry is registry
        assert registry.is_available(AudioEngineId.QT_MULTIMEDIA) is True

    def test_framework_free(self):
        import michi.application.audio_engine_service as mod

        src = inspect.getsource(mod)
        for forbidden in (
            "import PySide6",
            "import gi",
            "import subprocess",
            "import socket",
            "import sqlite3",
        ):
            assert forbidden not in src, f"service leaked {forbidden}"

    def test_no_playback_or_queue_mutation(self):
        """The service owns engine state only — it must not reference
        PlaybackState or QueueState."""
        import michi.application.audio_engine_service as mod

        src = inspect.getsource(mod)
        assert "PlaybackState" not in src
        assert "QueueState" not in src
