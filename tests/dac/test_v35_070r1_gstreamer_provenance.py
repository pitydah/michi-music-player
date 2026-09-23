"""ST70R1-10..12 selected GStreamer audio-branch provenance gates."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings


class _IteratorResult:
    OK = "ok"
    DONE = "done"
    RESYNC = "resync"


class _Gst:
    IteratorResult = _IteratorResult


class _Iterator:
    def __init__(self, values):
        self._values = iter(values)

    def next(self):
        try:
            return _IteratorResult.OK, next(self._values)
        except StopIteration:
            return _IteratorResult.DONE, None


class _InterruptedIterator(_Iterator):
    def __init__(self, value):
        self._value = value
        self._returned_value = False

    def next(self):
        if not self._returned_value:
            self._returned_value = True
            return _IteratorResult.OK, self._value
        return _IteratorResult.RESYNC, None


class _Structure:
    def __init__(self, fmt: str, rate: int, channels: int, sbits: int | None = None):
        self._values = {
            "format": fmt,
            "rate": rate,
            "channels": channels,
            "significant-bits": sbits,
        }

    def get_string(self, name):
        value = self._values.get(name)
        return value if isinstance(value, str) else None

    def get_int(self, name):
        value = self._values.get(name)
        return (value is not None, value or 0)


class _Caps:
    def __init__(self, fmt: str, rate: int, channels: int, sbits: int | None = None):
        self._structure = _Structure(fmt, rate, channels, sbits)

    def get_size(self):
        return 1

    def get_structure(self, index):
        assert index == 0
        return self._structure


class _Factory:
    def __init__(self, name: str, klass: str):
        self._name = name
        self._klass = klass

    def get_name(self):
        return self._name

    def get_metadata(self, name):
        return self._klass if name == "klass" else None


class _Pad:
    def __init__(self, caps=None):
        self._caps = caps
        self._peer = None
        self._parent = None

    def get_current_caps(self):
        return self._caps

    def get_peer(self):
        return self._peer

    def get_parent_element(self):
        return self._parent


class _Element:
    def __init__(self, name: str, klass: str, *, src_caps=None):
        self._factory = _Factory(name, klass)
        self.src = _Pad(src_caps)
        self.src._parent = self
        self._sink_pads = []

    def get_factory(self):
        return self._factory

    def iterate_src_pads(self):
        return _Iterator((self.src,))

    def iterate_sink_pads(self):
        return _Iterator(tuple(self._sink_pads))


class _Alsa(_Element):
    def __init__(self, effective_caps):
        super().__init__("alsasink", "Sink/Audio")
        self.sink = _Pad(effective_caps)
        self.sink._parent = self

    def get_static_pad(self, name):
        return self.sink if name == "sink" else None

    def get_property(self, name):
        if name == "device":
            return "hw:CARD=DX5,DEV=0"
        if name == "slave-method":
            return "none"
        return None

    def provide_clock(self):
        return "alsa-clock"


class _CapsFilter(_Element):
    def __init__(self, upstream):
        super().__init__("capsfilter", "Filter/Audio")
        self.sink = _Pad()
        self.sink._parent = self
        self.sink._peer = upstream.src if upstream is not None else None

    def get_static_pad(self, name):
        return self.sink if name == "sink" else None


class _SinkBin:
    def __init__(self, capsfilter, alsa, upstream):
        self._children = {
            "michi_direct_caps": capsfilter,
            "michi_direct_alsa": alsa,
        }
        self.sink = _Pad()
        self.sink._parent = self
        self.sink._peer = upstream.src if upstream is not None else None

    def get_by_name(self, name):
        return self._children.get(name)

    def get_static_pad(self, name):
        return self.sink if name == "sink" else None


class _Pipeline:
    def __init__(self, sink_bin, elements):
        self._sink_bin = sink_bin
        self._elements = tuple(elements)

    def get_property(self, name):
        if name == "audio-sink":
            return self._sink_bin
        if name == "volume":
            return 1.0
        if name == "mute":
            return False
        return None

    def iterate_recurse(self):
        return _Iterator(self._elements)

    def get_clock(self):
        return "alsa-clock"


@dataclass(frozen=True)
class _Recipe:
    plan_id: str = "plan-r1"


def _snapshot(
    order: tuple[str, ...],
    *,
    selected_decoder: bool = True,
    selected_upstream=None,
):
    decoder_a = _Element(
        "flacdec", "Codec/Decoder/Audio", src_caps=_Caps("S24_3LE", 96_000, 2, 24)
    )
    decoder_b = _Element(
        "avdec_aac", "Codec/Decoder/Audio", src_caps=_Caps("S16_LE", 44_100, 2, 16)
    )
    by_name = {"A": decoder_a, "B": decoder_b}
    # A real Gst ghost-pad target is paired with an internal ProxyPad whose
    # parent is not the upstream decoder. Provenance must enter through the
    # strict sink bin's external ghost pad instead of assuming that the
    # capsfilter target pad peers directly with the decoder.
    capsfilter = _CapsFilter(None)
    alsa = _Alsa(_Caps("S32_LE", 96_000, 2, 24))
    upstream = selected_upstream or (decoder_a if selected_decoder else None)
    pipeline = _Pipeline(
        _SinkBin(capsfilter, alsa, upstream),
        tuple(by_name[name] for name in order) + (capsfilter, alsa),
    )
    bindings = GStreamerBindings()
    bindings._gst = _Gst()
    return bindings.snapshot_direct_runtime(
        pipeline,
        _Recipe(),
        execution_generation=1,
        port_generation=2,
    )


def test_st70r1_10_selected_branch_decoder_provenance_wins():
    snapshot = _snapshot(("A", "B"))
    assert (snapshot.decoded_rate_hz, snapshot.decoded_format) == (96_000, "S24_3LE")


def test_st70r1_11_unrelated_audio_decoder_cannot_satisfy_direct():
    snapshot = _snapshot(("B", "A"), selected_decoder=False)
    assert snapshot.decoded_format is None
    assert snapshot.decoded_rate_hz is None
    assert snapshot.decoded_channels is None


@pytest.mark.parametrize("order", [("A", "B"), ("B", "A")])
def test_st70r1_12_decoder_selection_is_invariant_to_traversal_order(order):
    snapshot = _snapshot(order)
    assert (snapshot.decoded_rate_hz, snapshot.decoded_format) == (96_000, "S24_3LE")


def test_st70r1_12_multiple_reachable_decoders_are_ambiguous():
    decoder_a = _Element(
        "flacdec", "Codec/Decoder/Audio", src_caps=_Caps("S24_3LE", 96_000, 2, 24)
    )
    decoder_b = _Element(
        "avdec_aac", "Codec/Decoder/Audio", src_caps=_Caps("S16_LE", 44_100, 2, 16)
    )
    mixer = _Element("audiomixer", "Filter/Audio")
    for decoder in (decoder_a, decoder_b):
        sink_pad = _Pad()
        sink_pad._parent = mixer
        sink_pad._peer = decoder.src
        mixer._sink_pads.append(sink_pad)

    snapshot = _snapshot(
        ("A", "B"),
        selected_upstream=mixer,
    )

    # Two distinct audio producers feeding one branch stay ambiguous: no
    # decoded truth is published rather than guessing (R110R1 §17 keeps this).
    assert snapshot.decoded_format is None
    assert snapshot.decoded_rate_hz is None
    assert snapshot.decoded_channels is None


def test_st70r1_12_interrupted_branch_walk_cannot_publish_partial_decoder_truth():
    decoder = _Element(
        "flacdec", "Codec/Decoder/Audio", src_caps=_Caps("S24_3LE", 96_000, 2, 24)
    )
    branch = _Element("branch", "Filter/Audio")
    sink_pad = _Pad()
    sink_pad._parent = branch
    sink_pad._peer = decoder.src
    branch.iterate_sink_pads = lambda: _InterruptedIterator(sink_pad)

    snapshot = _snapshot(("A", "B"), selected_upstream=branch)

    assert snapshot.graph_inspection_complete is False
    assert snapshot.decoded_format is None
    assert snapshot.decoded_rate_hz is None
    assert snapshot.decoded_channels is None
