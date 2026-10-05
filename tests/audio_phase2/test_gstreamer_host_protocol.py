"""Protocol codec tests: framing, bounds, strict validation, generation fence."""

from __future__ import annotations

import json
import struct

import pytest

from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    GST_HOST_PROTOCOL_VERSION,
    MAX_FRAME_BYTES,
    FrameDecoder,
    HostEvent,
    HostOperation,
    HostProtocolError,
    MessageKind,
    encode_message,
    error_payload,
    event_is_current,
    make_message,
)


def _roundtrip(message: dict) -> dict:
    frames = FrameDecoder().feed(encode_message(message))
    assert len(frames) == 1
    return frames[0]


def test_roundtrip_every_kind_and_operation() -> None:
    for kind in MessageKind:
        message = make_message(
            kind,
            host_generation=3,
            command_generation=7,
            request_id="req-1",
            operation=HostOperation.PING,
            payload={"k": "v"},
        )
        assert _roundtrip(message) == message
    for operation in HostOperation:
        message = make_message(
            MessageKind.COMMAND,
            request_id="r",
            operation=operation,
            payload={},
        )
        assert _roundtrip(message)["operation"] == operation.value


def test_roundtrip_every_event() -> None:
    for event in HostEvent:
        message = make_message(
            MessageKind.EVENT,
            host_generation=1,
            command_generation=2,
            payload={"event": event.value, "value": 5},
        )
        assert _roundtrip(message)["payload"]["event"] == event.value


def test_fragmented_stream_reassembles() -> None:
    first = encode_message(
        make_message(MessageKind.COMMAND, request_id="a", operation=HostOperation.PING)
    )
    second = encode_message(
        make_message(
            MessageKind.EVENT, host_generation=1, payload={"event": "host_heartbeat"}
        )
    )
    blob = first + second
    decoder = FrameDecoder()
    frames: list[dict] = []
    for index in range(0, len(blob), 3):  # maximum fragmentation
        frames.extend(decoder.feed(blob[index : index + 3]))
    assert [frame["kind"] for frame in frames] == ["command", "event"]


def test_multiple_frames_in_one_chunk() -> None:
    blob = b"".join(
        encode_message(make_message(kind))
        for kind in (MessageKind.ACK, MessageKind.RESULT, MessageKind.FAULT)
    )
    frames = FrameDecoder().feed(blob)
    assert [frame["kind"] for frame in frames] == ["ack", "result", "fault"]


def test_oversized_declared_length_is_rejected() -> None:
    decoder = FrameDecoder()
    with pytest.raises(HostProtocolError) as info:
        decoder.feed(struct.pack(">I", MAX_FRAME_BYTES + 1))
    assert info.value.code == "HOST_PROTOCOL_OVERSIZED"


def test_oversized_encoded_message_is_rejected() -> None:
    message = make_message(
        MessageKind.EVENT,
        payload={"event": "host_heartbeat", "blob": "x" * (MAX_FRAME_BYTES + 100)},
    )
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code == "HOST_PROTOCOL_OVERSIZED"


def test_zero_length_frame_is_rejected() -> None:
    with pytest.raises(HostProtocolError) as info:
        FrameDecoder().feed(struct.pack(">I", 0))
    assert info.value.code == "HOST_PROTOCOL_MALFORMED"


def test_malformed_json_is_rejected() -> None:
    body = b"not-json"
    with pytest.raises(HostProtocolError) as info:
        FrameDecoder().feed(struct.pack(">I", len(body)) + body)
    assert info.value.code == "HOST_PROTOCOL_MALFORMED"


def test_non_object_json_is_rejected() -> None:
    body = json.dumps([1, 2, 3]).encode()
    with pytest.raises(HostProtocolError) as info:
        FrameDecoder().feed(struct.pack(">I", len(body)) + body)
    assert info.value.code == "HOST_PROTOCOL_MALFORMED"


def test_wrong_protocol_version_is_rejected() -> None:
    message = make_message(
        MessageKind.COMMAND, operation=HostOperation.PING, protocol_version=999
    )
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code == "HOST_PROTOCOL_VERSION"


def test_unknown_kind_and_operation_are_rejected() -> None:
    message = make_message(MessageKind.COMMAND, operation=HostOperation.PING)
    message["kind"] = "nope"
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code == "HOST_PROTOCOL_UNKNOWN_KIND"

    message = make_message(MessageKind.COMMAND)
    message["operation"] = "nope"
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code == "HOST_PROTOCOL_UNKNOWN_OPERATION"


@pytest.mark.parametrize(
    "mutation",
    [
        {"host_generation": -1},
        {"command_generation": -1},
        {"host_generation": True},
        {"command_generation": 1.5},
        {"host_generation": "1"},
        {"request_id": 5},
        {"payload": []},
    ],
)
def test_invalid_fields_are_rejected(mutation: dict) -> None:
    message = make_message(MessageKind.COMMAND, operation=HostOperation.PING)
    message.update(mutation)
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code in (
        "HOST_PROTOCOL_INVALID_FIELD",
        "HOST_PROTOCOL_MALFORMED",
    )


def test_missing_envelope_keys_are_rejected() -> None:
    message = make_message(MessageKind.COMMAND, operation=HostOperation.PING)
    del message["payload"]
    with pytest.raises(HostProtocolError) as info:
        encode_message(message)
    assert info.value.code == "HOST_PROTOCOL_MALFORMED"


def test_generation_fence_requires_both_domains() -> None:
    message = {
        "host_generation": 4,
        "command_generation": 19,
    }
    assert event_is_current(
        message, expected_host_generation=4, expected_command_generation=19
    )
    # A new host incarnation invalidates an old event even at equal pipeline
    # generation; a superseding command invalidates it inside one host.
    assert not event_is_current(
        message, expected_host_generation=5, expected_command_generation=19
    )
    assert not event_is_current(
        message, expected_host_generation=4, expected_command_generation=20
    )
    assert not event_is_current(
        message, expected_host_generation=5, expected_command_generation=20
    )


def test_error_payload_bounds_detail() -> None:
    payload = error_payload("CODE", "x" * 5000)
    assert payload["code"] == "CODE"
    assert len(payload["detail"]) == 2000


def test_protocol_version_constant_is_one() -> None:
    assert GST_HOST_PROTOCOL_VERSION == 1
