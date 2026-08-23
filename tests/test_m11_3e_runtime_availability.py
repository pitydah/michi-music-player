"""M11.3E — Engine Runtime Availability Truth Seal (deterministic)."""

import os
import shutil

import pytest

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle


class _CountingProvider:
    """Provider fake con contadores de probe/open/close (envuelve un
    provider interno; open/close del interno nunca deben invocarse en
    descubrimiento pasivo)."""

    def __init__(self, inner):
        self.inner = inner
        self.probe_count = 0
        self.open_count = 0
        self.close_count = 0

    @property
    def engine_id(self):
        return self.inner.engine_id

    def probe(self):
        self.probe_count += 1
        return self.inner.probe()

    def open(self):
        self.open_count += 1
        self.inner.open()

    def close(self):
        self.close_count += 1
        self.inner.close()


class _DescFactory:
    """Provider fake determinista — engine_id EXPLÍCITO (sin default).
    open()/close() fallan si el descubrimiento intentara activar."""

    def __init__(
        self,
        engine_id: AudioEngineId,
        *,
        available: bool,
        unavailable_reason: str | None = None,
        implemented: bool = True,
        implementation_reason: str | None = None,
    ):
        self._engine_id = engine_id
        self._available = available
        self._unavailable_reason = unavailable_reason
        self._implemented = implemented
        self._implementation_reason = implementation_reason

    @property
    def engine_id(self):
        return self._engine_id

    def probe(self):
        from michi.domain.audio_engine import (
            AudioEngineCapabilities,
            AudioEngineDescriptor,
        )

        return AudioEngineDescriptor(
            engine_id=self._engine_id,
            display_name=self._engine_id.value,
            available=self._available,
            unavailable_reason=self._unavailable_reason,
            implemented=self._implemented,
            implementation_reason=self._implementation_reason,
            capabilities=AudioEngineCapabilities(
                local_file_playback=True,
                seek=True,
                pause=True,
                volume=True,
                mute=True,
            ),
        )

    def open(self):
        raise AssertionError("descubrimiento no debe abrir providers")

    def close(self):
        raise AssertionError("descubrimiento no debe cerrar providers")


def _registry_with(*desc_factories):
    providers = [_CountingProvider(f) for f in desc_factories]
    registry = AudioEngineRegistry(providers)
    return registry, providers


@pytest.fixture(scope="module")
def qapp():
    """Instancia Qt offscreen local (patrón del repo) — sin depender de
    pytest-qt, que no está en la CI."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


@pytest.fixture
def mpd_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)


@pytest.fixture
def mpd_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpd")


class TestE1RegistrySnapshot:
    def test_e01_canonical_three_engine_order(self):
        """descriptors() en orden canónico: QT, GSTREAMER, MPD."""
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        # registro en orden ALEATORIO
        registry = AudioEngineRegistry(
            [MpdEngineProvider(), QtEngineProvider(), GStreamerEngineProvider()]
        )
        ids = [d.engine_id for d in registry.descriptors()]
        assert ids == [
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        ]

    def test_e02_unavailable_engines_stay_in_snapshot(self):
        """El snapshot conserva los engines unavailable (contract puro)."""
        registry = AudioEngineRegistry(
            [
                _DescFactory(
                    AudioEngineId.QT_MULTIMEDIA,
                    available=True,
                ),
                _DescFactory(
                    AudioEngineId.GSTREAMER,
                    available=False,
                    unavailable_reason="GI unavailable",
                ),
                _DescFactory(
                    AudioEngineId.MPD,
                    available=False,
                    unavailable_reason="mpd executable missing",
                ),
            ]
        )
        descriptors = registry.descriptors()
        assert tuple(d.engine_id for d in descriptors) == (
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        )
        assert descriptors[0].available is True
        assert descriptors[1].available is False
        assert descriptors[2].available is False


class TestE2FreshAvailability:
    def test_e03_reprobe_is_fresh_without_reconstruction(self, monkeypatch):
        """Misma registry/provider: la disponibilidad se refresca."""
        from michi.infrastructure.audio_engines.providers import MpdEngineProvider

        provider = MpdEngineProvider()
        registry = AudioEngineRegistry([provider])
        monkeypatch.setattr("shutil.which", lambda name: None)
        first = registry.descriptor(AudioEngineId.MPD)
        assert first.available is False
        assert first.implemented is True
        assert first.can_activate is False
        # el runtime aparece DURANTE la vida del proceso
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpd")
        second = registry.descriptor(AudioEngineId.MPD)
        assert second.available is True
        assert second.implemented is True
        assert second.can_activate is True
        assert provider is registry.provider(AudioEngineId.MPD)


class TestE3DimensionSeparation:
    def test_e04_available_implemented_independent(self):
        cases = [
            # available, implemented, can_activate esperado
            (False, True, False),
            (True, True, True),
            (True, False, False),
            (False, False, False),
        ]
        for available, implemented, expected in cases:
            desc = _DescFactory(
                AudioEngineId.GSTREAMER,
                available=available,
                implemented=implemented,
                unavailable_reason="runtime" if not available else None,
                implementation_reason="impl" if not implemented else None,
            ).probe()
            assert desc.can_activate is expected
            assert desc.available is available
            assert desc.implemented is implemented

    def test_e05_can_activate_equation(self):
        from michi.domain.audio_engine import AudioEngineDescriptor

        assert AudioEngineDescriptor.can_activate.fget is not None

    def test_e06_activation_blocker_priority(self):
        """Blocker: unavailable_reason gana; luego implementation_reason."""
        desc = _DescFactory(
            AudioEngineId.GSTREAMER,
            available=False,
            implemented=True,
            unavailable_reason="runtime missing",
            implementation_reason=None,
        ).probe()
        assert desc.activation_blocker == "runtime missing"
        desc2 = _DescFactory(
            AudioEngineId.GSTREAMER,
            available=True,
            implemented=False,
            unavailable_reason=None,
            implementation_reason="adapter pending",
        ).probe()
        assert desc2.activation_blocker == "adapter pending"
        desc3 = _DescFactory(
            AudioEngineId.GSTREAMER, available=True, implemented=True
        ).probe()
        assert desc3.activation_blocker is None


class TestE6MpdAvailability:
    def test_e07_mpd_missing_executable(self, mpd_missing):
        from michi.infrastructure.audio_engines.providers import MpdEngineProvider

        desc = MpdEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert desc.unavailable_reason

    def test_e08_mpd_present_executable(self, mpd_present):
        from michi.infrastructure.audio_engines.providers import MpdEngineProvider

        desc = MpdEngineProvider().probe()
        assert desc.available is True
        assert desc.implemented is True
        assert desc.can_activate is True
        assert desc.activation_blocker is None

    def test_e09_mpd_probe_no_spawn(self):
        """probe() jamás spawna el proceso (side-effect free)."""
        import inspect

        from michi.infrastructure.audio_engines.providers import MpdEngineProvider

        src = inspect.getsource(MpdEngineProvider.probe)
        assert "shutil.which" in src
        assert "Popen" not in src
        assert "subprocess" not in src
        assert "spawn" not in src.lower()


class TestE5GStreamerAvailability:
    def test_e10_missing_runtime(self, monkeypatch):
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        def broken_import(name):
            raise ImportError(f"no GI: {name}")

        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.gstreamer.GStreamerBindings.ensure_loaded",
            lambda self: broken_import("gi"),
        )
        desc = GStreamerEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert desc.unavailable_reason

    def test_e11_playbin3_missing(self, monkeypatch):
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        class FakeBindingsNoPlaybin:
            def ensure_loaded(self):
                pass

            def playbin3_available(self):
                return False

        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.gstreamer.GStreamerBindings",
            FakeBindingsNoPlaybin,
        )
        desc = GStreamerEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True
        assert desc.can_activate is False
        assert "playbin3" in (desc.unavailable_reason or "")

    def test_e12_gstreamer_fully_available(self, monkeypatch):
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        class FakeBindingsOk:
            def ensure_loaded(self):
                pass

            def playbin3_available(self):
                return True

        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.gstreamer.GStreamerBindings",
            FakeBindingsOk,
        )
        desc = GStreamerEngineProvider().probe()
        assert desc.available is True
        assert desc.implemented is True
        assert desc.can_activate is True

    def test_e12_implemented_always_true(self, monkeypatch):
        # implemented es una dimensión del ADAPTER (no del runtime): con
        # runtime ausente el descriptor sigue diciendo implemented=True
        import michi.infrastructure.audio_engines.gstreamer as gst_mod
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
        )

        class Broken:
            def ensure_loaded(self):
                raise ImportError("no GI")

        monkeypatch.setattr(gst_mod, "GStreamerBindings", Broken)
        desc = GStreamerEngineProvider().probe()
        assert desc.available is False
        assert desc.implemented is True  # la dimensión no colapsa


class TestE4QtAvailability:
    def test_e13_qt_reference_available(self):
        from michi.infrastructure.audio_engines.providers import QtEngineProvider

        desc = QtEngineProvider().probe()
        assert desc.implemented is True
        # en un entorno con PySide6, Qt está disponible
        assert desc.available is True
        assert desc.can_activate is True

    def test_e13_qt_probe_never_instantiates_backend(self):
        """probe() NO crea QtMultimediaBackend (solo importa la superficie)."""
        import inspect

        from michi.infrastructure.audio_engines.providers import QtEngineProvider

        src = inspect.getsource(QtEngineProvider.probe)
        assert "QtMultimediaBackend(" not in src
        assert "import" in src  # import lazy de la superficie


class TestE7SideEffectsAndState:
    def _three_factories(self):
        return [
            _DescFactory(AudioEngineId.QT_MULTIMEDIA, available=True),
            _DescFactory(
                AudioEngineId.GSTREAMER,
                available=False,
                unavailable_reason="GI unavailable",
            ),
            _DescFactory(
                AudioEngineId.MPD,
                available=False,
                unavailable_reason="mpd executable missing",
            ),
        ]

    def test_e14_probe_all_does_not_open_engines(self):
        """probe-all sobre TODO el registry no abre ningún engine."""
        registry, providers = _registry_with(*self._three_factories())
        registry.descriptors()
        for provider in providers:
            assert provider.open_count == 0
            assert provider.close_count == 0

    def test_e15_one_probe_per_provider_per_snapshot(self):
        """one probe / provider / snapshot — para todo el registry."""
        registry, providers = _registry_with(*self._three_factories())
        registry.descriptors()
        for provider in providers:
            assert provider.probe_count == 1
        registry.descriptors()
        for provider in providers:
            assert provider.probe_count == 2  # fresco en cada consulta

    def test_e16_availability_query_does_not_mutate_engine_state(self, qapp):
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        qt_provider = QtEngineProvider()
        registry = AudioEngineRegistry(
            [qt_provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        bootstrap._initialize_reference_audio_runtime(
            qt_provider, registry, service, router
        )
        assert service.state.lifecycle == AudioEngineLifecycle.READY
        before = (
            service.state.selected_engine_id,
            service.state.active_engine_id,
            service.state.lifecycle,
        )
        # descubrimiento pasivo
        registry.descriptors()
        registry.is_available(AudioEngineId.GSTREAMER)
        registry.can_activate(AudioEngineId.MPD)
        after = (
            service.state.selected_engine_id,
            service.state.active_engine_id,
            service.state.lifecycle,
        )
        assert after == before  # sin mutación de estado
        assert after[2] == AudioEngineLifecycle.READY
        # teardown conforme al SWITCH ORDER congelado: STOP -> router
        # UNBIND -> provider CLOSE (el router nunca queda ligado a un
        # backend cerrado)
        router.unbind()
        qt_provider.close()


class TestE9ProductionComposition:
    def test_e17_graph_has_one_provider_per_engine(self, qapp):
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        qt_provider = QtEngineProvider()
        registry = AudioEngineRegistry(
            [qt_provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        assert registry.engine_ids == (
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        )
        assert registry.provider(AudioEngineId.QT_MULTIMEDIA) is qt_provider

    def test_e18_startup_opens_only_qt(self, qapp):
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        class TrackingGst(GStreamerEngineProvider):
            opened = 0

            def open(self):
                TrackingGst.opened += 1
                return super().open()

        class TrackingMpd(MpdEngineProvider):
            opened = 0

            def open(self):
                TrackingMpd.opened += 1
                return super().open()

        qt_provider = QtEngineProvider()
        registry = AudioEngineRegistry([qt_provider, TrackingGst(), TrackingMpd()])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        bootstrap._initialize_reference_audio_runtime(
            qt_provider, registry, service, router
        )
        assert service.state.lifecycle == AudioEngineLifecycle.READY
        assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        # GStreamer y MPD NO se abren durante el startup normal
        assert TrackingGst.opened == 0
        assert TrackingMpd.opened == 0
        # teardown conforme al SWITCH ORDER congelado: STOP -> router
        # UNBIND -> provider CLOSE
        router.unbind()
        qt_provider.close()

    def test_e19_alternate_availability_does_not_change_active(self, qapp):
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        qt_provider = QtEngineProvider()
        registry = AudioEngineRegistry(
            [qt_provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        bootstrap._initialize_reference_audio_runtime(
            qt_provider, registry, service, router
        )
        # la disponibilidad de otros engines no altera el active
        assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        registry.descriptors()  # disponibilidad alterna consultada
        assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        # teardown conforme al SWITCH ORDER congelado
        router.unbind()
        qt_provider.close()


class TestE7Capabilities:
    def test_e20_capability_profiles_m11_3_only(self):
        """Solo las capacidades M11.3; sin campos de M11.4/M11.5."""
        from michi.domain.audio_engine import AudioEngineCapabilities

        cap = AudioEngineCapabilities(
            local_file_playback=True,
            seek=True,
            pause=True,
            volume=True,
            mute=True,
        )
        assert cap.local_file_playback is True
        assert cap.seek is True
        assert cap.pause is True
        assert cap.volume is True
        assert cap.mute is True
        # el contrato no define campos de DAC/bit-perfect
        assert not hasattr(cap, "exclusive_mode")
        assert not hasattr(cap, "bit_perfect")
        assert not hasattr(cap, "dsd")


class TestE21RealEnvironment:
    def test_e21_real_environment_descriptor_coherence(self):
        """Coherencia estructural con el entorno real (sin asumir
        instalación fija)."""
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        for provider in (
            QtEngineProvider(),
            GStreamerEngineProvider(),
            MpdEngineProvider(),
        ):
            desc = provider.probe()
            assert desc.implemented is True
            if desc.available:
                assert desc.can_activate is True
                assert desc.activation_blocker is None
            else:
                assert desc.can_activate is False
                assert desc.unavailable_reason

    def test_e21_mpd_truth_crosscheck(self):
        from michi.infrastructure.audio_engines.providers import MpdEngineProvider

        desc = MpdEngineProvider().probe()
        assert desc.available == (shutil.which("mpd") is not None)
