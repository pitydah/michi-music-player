"""DAC-V35-050B — strict GStreamer sink builder gates (B1..B10).

El builder REAL de GStreamerBindings se ejercita con un módulo Gst fake
inyectado (`bindings._gst = fake`): el contrato (factories, caps, device,
link, ghost pad, códigos fail-closed) es el productivo; GI real se cubre
con el smoke condicionado del port test.
"""

from __future__ import annotations

import pytest

from tests.dac.test_v35_strict_sink import _plan


def _recipe(rate: int = 44100, fmt: str = "S16_LE", device: str = "hw:CARD=DX5,DEV=0"):
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    return recipe_from_plan(_plan(rate=rate, fmt=fmt, device=device))


# ── Fake Gst (sólo lo que el builder consume) ────────────────────────


class _FakeCaps:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_size(self) -> int:
        return 1 if self.text else 0

    def to_string(self) -> str:
        return self.text


class _FakePad:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeElement:
    def __init__(self, factory: str, name: str, outer) -> None:
        self.factory_name = factory
        self.name = name
        self.props: dict = {}
        self.linked: list = []
        self._outer = outer

    def set_property(self, key, value) -> None:
        self.props[key] = value

    def get_static_pad(self, name):
        if self._outer.flags.get("static_pad_missing"):
            return None
        return _FakePad(name)

    def link(self, other) -> bool:
        self.linked.append(other)
        self._outer.links.append((self.factory_name, other.factory_name))
        return not self._outer.flags.get("link_fail", False)

    def get_factory(self):
        return _FakeFactoryRef(self.factory_name)


class _FakeFactoryRef:
    def __init__(self, name: str) -> None:
        self._name = name

    def get_name(self) -> str:
        return self._name


class _FakeBin(_FakeElement):
    def __init__(self, name: str, outer) -> None:
        super().__init__("GstBin", name, outer)
        self.children: list = []
        self.pads: list = []

    def add(self, element) -> bool:
        self.children.append(element)
        return self._outer.flags.get("add_fail") != element.factory_name

    def add_pad(self, pad) -> bool:
        self.pads.append(pad)
        return True


class _FakeGhostPad:
    def __init__(self, name: str, target) -> None:
        self.name = name
        self.target = target


class FakeGstModule:
    """Módulo Gst fake: registra creación/link y permite fallos."""

    def __init__(self, **flags) -> None:
        self.flags = flags
        self.created: list[tuple[str, str]] = []
        self.links: list[tuple[str, str]] = []
        self.caps_text: str | None = None
        outer = self

        class _Bin:
            @staticmethod
            def new(name):
                outer.created.append(("bin", name))
                if outer.flags.get("bin_fail"):
                    return None
                return _FakeBin(name, outer)

        class _ElementFactory:
            @staticmethod
            def make(factory, name):
                outer.created.append((factory, name))
                if factory in outer.flags.get("missing", ()):
                    return None
                return _FakeElement(factory, name, outer)

        class _Caps:
            @staticmethod
            def from_string(text):
                outer.caps_text = text
                if outer.flags.get("caps_fail"):
                    return None
                return _FakeCaps(text)

        class _GhostPad:
            @staticmethod
            def new(name, target):
                if outer.flags.get("ghost_fail"):
                    return None
                return _FakeGhostPad(name, target)

        self.Bin = _Bin
        self.ElementFactory = _ElementFactory
        self.Caps = _Caps
        self.GhostPad = _GhostPad


def _bindings_with(fake_gst):
    from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

    bindings = GStreamerBindings()
    bindings._gst = fake_gst  # ensure_loaded() retorna sin tocar gi
    return bindings


class _FakePipelineForInstall:
    def __init__(self, mismatch: bool = False) -> None:
        self._sink = None
        self._mismatch = mismatch

    def set_property(self, key, value) -> None:
        if key == "audio-sink":
            self._sink = value

    def get_property(self, key):
        if key == "audio-sink":
            return object() if self._mismatch else self._sink
        return None


# ── B1..B10 ──────────────────────────────────────────────────────────


def test_b1_s16_strict_sink_construction() -> None:
    fake = FakeGstModule()
    bindings = _bindings_with(fake)

    sink = bindings.build_strict_audio_sink(_recipe())

    assert sink is not None
    assert ("bin", "michi_direct_sink") in fake.created
    assert ("capsfilter", "michi_direct_caps") in fake.created
    assert ("alsasink", "michi_direct_alsa") in fake.created
    assert (
        fake.caps_text
        == "audio/x-raw,format=S16LE,rate=44100,channels=2,layout=interleaved"
    )
    alsa = next(child for child in sink.children if child.factory_name == "alsasink")
    assert alsa.props["device"] == "hw:CARD=DX5,DEV=0"
    assert fake.links == [("capsfilter", "alsasink")]
    assert len(sink.pads) == 1, "ghost pad agregado al bin"


def test_b2_s32_strict_sink_caps_exact() -> None:
    fake = FakeGstModule()
    bindings = _bindings_with(fake)

    bindings.build_strict_audio_sink(_recipe(rate=96000, fmt="S32_LE"))

    assert (
        fake.caps_text
        == "audio/x-raw,format=S32LE,rate=96000,channels=2,layout=interleaved"
    )


def test_b3_no_forbidden_elements() -> None:
    fake = FakeGstModule()
    bindings = _bindings_with(fake)

    bindings.build_strict_audio_sink(_recipe())

    factories = [name for name, _ in fake.created]
    for forbidden in (
        "audioresample",
        "audioconvert",
        "autoaudiosink",
        "pipewiresink",
        "pulsesink",
    ):
        assert forbidden not in factories


def test_b4_exact_alsa_device() -> None:
    fake = FakeGstModule()
    bindings = _bindings_with(fake)

    sink = bindings.build_strict_audio_sink(_recipe(device="hw:CARD=DX5,DEV=1"))

    alsa = next(child for child in sink.children if child.factory_name == "alsasink")
    assert alsa.props["device"] == "hw:CARD=DX5,DEV=1"


def test_b5_missing_capsfilter_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(missing=("capsfilter",))
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_CAPSFILTER_CREATE_FAILED"


def test_b6_missing_alsasink_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(missing=("alsasink",))
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_ALSASINK_CREATE_FAILED"


def test_b7_invalid_caps_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(caps_fail=True)
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_CAPS_CREATE_FAILED"


def test_b8_link_failure_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(link_fail=True)
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_SINK_LINK_FAILED"


def test_b9_ghost_pad_failure_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(ghost_fail=True)
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_GHOST_PAD_FAILED"


def test_b10_install_failure_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule()
    bindings = _bindings_with(fake)
    sink = bindings.build_strict_audio_sink(_recipe())
    pipeline = _FakePipelineForInstall(mismatch=True)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.set_audio_sink(pipeline, sink)
    assert exc_info.value.code == "DIRECT_SINK_INSTALL_FAILED"


def test_b11_install_success_verifies_identity() -> None:
    fake = FakeGstModule()
    bindings = _bindings_with(fake)
    sink = bindings.build_strict_audio_sink(_recipe())
    pipeline = _FakePipelineForInstall()
    bindings.set_audio_sink(pipeline, sink)
    assert pipeline.get_property("audio-sink") is sink


# ── B12..B14: fail-closed de add() y static pad (seal 050B) ──────────


def test_b12_capsfilter_add_failure_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(add_fail="capsfilter")
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_SINK_ADD_FAILED"


def test_b13_alsasink_add_failure_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(add_fail="alsasink")
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_SINK_ADD_FAILED"


def test_b14_missing_static_sink_pad_fails_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import DirectSinkBuildError

    fake = FakeGstModule(static_pad_missing=True)
    bindings = _bindings_with(fake)
    with pytest.raises(DirectSinkBuildError) as exc_info:
        bindings.build_strict_audio_sink(_recipe())
    assert exc_info.value.code == "DIRECT_GHOST_PAD_FAILED"
