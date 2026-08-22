"""M11.3A: engine provider probes + AudioEngineService gates."""

import inspect
import os

import pytest
from PySide6.QtGui import QGuiApplication

from michi.application.audio_engine_registry import (
    AudioEngineProviderPort,
    AudioEngineRegistry,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.domain.audio_engine import AudioEngineDescriptor, AudioEngineId
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

        provider = QtEngineProvider()
        port = provider.open()
        assert isinstance(port, AudioPort)
        provider.close()  # release resources cleanly

    def test_open_is_deterministic_same_instance(self, qapp):
        provider = QtEngineProvider()
        first = provider.open()
        second = provider.open()
        assert first is second  # no uncontrolled parallel Qt engines
        provider.close()

    def test_close_exception_safety_releases_ownership(self, qapp):
        """A failing stop() must not leave a phantom owned backend."""
        from michi.application.ports import AudioPort

        class BoomBackend(AudioPort):
            def load(self, file_path): ...
            def play(self): ...
            def pause(self): ...
            def resume(self): ...
            def stop(self):
                raise RuntimeError("stop failed")

            def set_volume(self, value): ...
            def set_muted(self, muted): ...
            def seek(self, position_ms): ...
            def position(self):
                return 0

            def duration(self):
                return 0

            def subscribe_end_of_media(self, cb): ...
            def unsubscribe_end_of_media(self, cb): ...
            def subscribe_position_changed(self, cb): ...
            def unsubscribe_position_changed(self, cb): ...
            def subscribe_duration_changed(self, cb): ...
            def unsubscribe_duration_changed(self, cb): ...
            def subscribe_media_accepted(self, cb): ...
            def unsubscribe_media_accepted(self, cb): ...
            def subscribe_media_rejected(self, cb): ...
            def unsubscribe_media_rejected(self, cb): ...
            def subscribe_playback_state_changed(self, cb): ...
            def unsubscribe_playback_state_changed(self, cb): ...

        import pytest

        from michi.infrastructure.audio_engines.providers import QtEngineProvider

        provider = QtEngineProvider()
        provider._backend = BoomBackend()
        with pytest.raises(RuntimeError, match="stop failed"):
            provider.close()
        # ownership released despite the failure: no phantom owned engine
        assert provider._backend is None
        # second close: idempotent, no error
        provider.close()

    def test_close_idempotent_and_reopen_fresh(self, qapp):
        provider = QtEngineProvider()
        first = provider.open()
        provider.close()
        provider.close()  # idempotent — no error
        second = provider.open()
        assert second is not first  # fresh backend after close
        assert second is provider.open()  # deterministic again
        provider.close()

    def test_no_qt_import_at_module_time(self):
        """Base wheel usability: module import must not require QtMultimedia
        (probe imports it lazily)."""
        import michi.infrastructure.audio_engines.providers as mod

        assert "PySide6" not in inspect.getsource(mod)


class TestGStreamerProvider:
    def test_probe_is_lazy_and_truthful(self):
        desc = GStreamerEngineProvider().probe()
        assert desc.engine_id == AudioEngineId.GSTREAMER
        # M11.3C: implemented=True; available solo cuando gi/Gst 1.0 carga
        assert desc.implemented is True
        if not desc.available:
            assert desc.unavailable_reason is not None

    def test_open_returns_audio_port(self, qapp):
        from michi.application.ports import AudioPort

        provider = GStreamerEngineProvider()
        port = provider.open()
        assert isinstance(port, AudioPort)
        provider.close()

    def test_ownership_deterministic(self, qapp):
        provider = GStreamerEngineProvider()
        first = provider.open()
        second = provider.open()
        assert first is second  # same owned port until close
        provider.close()
        provider.close()  # idempotent
        third = provider.open()
        assert third is not first  # fresh adapter after close
        provider.close()

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


class TestProviderActivation:
    def test_qt_can_activate(self):
        desc = QtEngineProvider().probe()
        assert desc.can_activate is True
        assert desc.activation_blocker is None

    def test_gstreamer_implemented_runtime_dependent(self):
        """M11.3C: implemented=True; can_activate = available (GI runtime)."""
        desc = GStreamerEngineProvider().probe()
        assert desc.implemented is True
        assert desc.can_activate == desc.available
        assert desc.capabilities.local_file_playback is True
        assert desc.capabilities.seek is True
        assert desc.capabilities.pause is True
        assert desc.capabilities.volume is True
        assert desc.capabilities.mute is True

    def test_mpd_blocked_by_implementation(self):
        desc = MpdEngineProvider().probe()
        assert desc.implemented is False
        assert desc.can_activate is False
        assert desc.implementation_reason is not None
        assert "M11.3D" in desc.implementation_reason

    def test_missing_dependency_unavailable_reason(self):
        class Missing(AudioEngineProviderPort):
            @property
            def engine_id(self):
                return AudioEngineId.GSTREAMER

            def probe(self):
                return AudioEngineDescriptor(
                    engine_id=self.engine_id,
                    display_name="GStreamer",
                    available=False,
                    unavailable_reason="gi/Gst typelib no disponible",
                    implemented=True,
                )

            def open(self):
                raise NotImplementedError

            def close(self):
                pass

        desc = Missing().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert "typelib" in desc.unavailable_reason
        assert desc.activation_blocker == desc.unavailable_reason


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
        assert descriptors[1].implemented is True  # GStreamer (M11.3C)
        assert descriptors[2].implemented is False  # MPD (M11.3D)


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
