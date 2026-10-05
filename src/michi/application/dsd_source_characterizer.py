"""DSD source characterizer — static, deterministic DSF/DFF source truth.

AP2-F07 / R11-F07 and seal 212: container facts, elementary-stream truth and
decoded/runtime truth are deliberately separate. This module implements only
the CONTAINER and ELEMENTARY layers by parsing the bytes; it never starts a
GStreamer pipeline, never touches ALSA and never claims output capability.
Decoded runtime facts belong to a later phase.

Failure semantics: a transient inability to observe (missing file, busy file)
is UNKNOWN — never negative capability evidence; positively identified
encodings the parser cannot handle (e.g. DST compression) are UNSUPPORTED,
which is distinct from UNKNOWN.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from michi.domain.dsd_signal import DsdPacking, DsdSignalFormat

PROVIDER = "static-parser"

SOURCE_DSD_CONTAINER_UNKNOWN = "SOURCE_DSD_CONTAINER_UNKNOWN"
SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN = "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
SOURCE_DSD_RATE_UNIT_INVALID = "SOURCE_DSD_RATE_UNIT_INVALID"
SOURCE_DSD_GROUPING_UNKNOWN = "SOURCE_DSD_GROUPING_UNKNOWN"
SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN = "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"
#: F07 extension: transient inability to observe is never a negative claim.
SOURCE_DSD_TRANSIENT_UNAVAILABLE = "SOURCE_DSD_TRANSIENT_UNAVAILABLE"

_DSF_MAGIC = b"DSD "
_DSF_FMT_MAGIC = b"fmt "
_DSF_DATA_MAGIC = b"data"
_DSF_FIXED_HEADER_BYTES = 92

_DFF_FORM_MAGIC = b"FRM8"
_DFF_FORM_TYPE = b"DSD "
_DFF_COMPRESSION_UNCOMPRESSED = b"DSD "
_DFF_PROP_CAP_BYTES = 4 * 1024 * 1024

_DSF_CHANNEL_LAYOUTS: dict[int, tuple[str, ...]] = {
    1: ("FC",),
    2: ("FL", "FR"),
}
_DFF_CHANNEL_POSITIONS: dict[bytes, str] = {
    b"SLFT": "FL",
    b"SRGT": "FR",
    b"C   ": "FC",
    b"LFE ": "LFE",
}


class ElementaryEncoding(StrEnum):
    PCM = "pcm"
    DSD = "dsd"
    COMPRESSED = "compressed"
    UNKNOWN = "unknown"


class DsdSourceStatus(StrEnum):
    DSD_PROVEN = "dsd_proven"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ContainerAudioFacts:
    container: str | None
    codec: str | None
    channels: int | None
    nominal_dsd_bits_per_second_per_channel: int | None
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class ElementaryStreamObservation:
    encoding: ElementaryEncoding
    caps_media_type: str | None
    caps_fields: tuple[tuple[str, str], ...]
    provider: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class DsdSourceCharacterization:
    container_facts: ContainerAudioFacts
    elementary: ElementaryStreamObservation
    signal: DsdSignalFormat | None
    status: DsdSourceStatus
    failure_code: str | None
    evidence_refs: tuple[str, ...]


class DsdSourceCharacterizer:
    """Deterministic DSF/DFF source truth from bytes; no runtime commands."""

    def characterize(self, path: Path) -> DsdSourceCharacterization:
        candidate = Path(path)
        try:
            if not candidate.is_file():
                return self._transient(candidate)
        except OSError:
            return self._transient(candidate)
        try:
            with candidate.open("rb") as handle:
                head = handle.read(_DSF_FIXED_HEADER_BYTES)
        except OSError:
            return self._transient(candidate)
        if head[:4] == _DSF_MAGIC:
            return self._characterize_dsf(candidate, head)
        if head[:4] == _DFF_FORM_MAGIC:
            return self._characterize_dff(candidate, head)
        return self._unknown_container(candidate)

    # ------------------------------------------------------------------ #
    # DSF
    # ------------------------------------------------------------------ #

    def _characterize_dsf(self, path: Path, head: bytes) -> DsdSourceCharacterization:
        name = path.name
        if len(head) < _DSF_FIXED_HEADER_BYTES or head[28:32] != _DSF_FMT_MAGIC:
            return self._unknown_container(path)
        (dsd_size,) = struct.unpack_from("<Q", head, 4)
        (file_size,) = struct.unpack_from("<Q", head, 12)
        (fmt_size,) = struct.unpack_from("<Q", head, 32)
        if dsd_size != 28 or fmt_size != 52:
            return self._unknown_container(path)
        (format_id,) = struct.unpack_from("<I", head, 44)
        (channel_type,) = struct.unpack_from("<I", head, 48)
        (channel_count,) = struct.unpack_from("<I", head, 52)
        (rate,) = struct.unpack_from("<I", head, 56)
        (bits_per_sample,) = struct.unpack_from("<I", head, 60)
        if head[80:84] != _DSF_DATA_MAGIC:
            return self._unknown_container(path)
        (data_size,) = struct.unpack_from("<Q", head, 84)
        try:
            actual_size = path.stat().st_size
        except OSError:
            return self._transient(path)
        if (
            data_size == 0
            or file_size > actual_size
            or _DSF_FIXED_HEADER_BYTES + data_size > actual_size
        ):
            return self._unknown_container(path)

        container_ref = f"dsf:header:{name}"
        elementary_ref = f"dsf:elementary:{name}"
        if format_id != 0:
            return self._result(
                container=("dsf", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.COMPRESSED,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNSUPPORTED_ENCODING,
                failure_code=SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
            )
        if rate <= 0 or rate % 8:
            return self._result(
                container=("dsf", channel_count, None, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_RATE_UNIT_INVALID,
            )
        if bits_per_sample == 8:
            packing = DsdPacking.DSD_U8
        else:
            # bits_per_sample 1 (bit-packed) is not proven by this parser.
            return self._result(
                container=("dsf", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_GROUPING_UNKNOWN,
            )
        layout = _DSF_CHANNEL_LAYOUTS.get(channel_type)
        if layout is None or channel_count != len(layout):
            return self._result(
                container=("dsf", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
            )
        signal = DsdSignalFormat(
            bit_rate_hz=rate,
            channels=channel_count,
            packing=packing,
            layout=layout,
        )
        return self._proven(
            container=("dsf", channel_count, rate, container_ref),
            signal=signal,
            elementary_ref=elementary_ref,
        )

    # ------------------------------------------------------------------ #
    # DFF (DSDIFF)
    # ------------------------------------------------------------------ #

    def _characterize_dff(self, path: Path, head: bytes) -> DsdSourceCharacterization:
        name = path.name
        if len(head) < 12 or head[8:12] != _DFF_FORM_TYPE:
            return self._unknown_container(path)
        (form_size,) = struct.unpack_from(">I", head, 4)
        container_ref = f"dff:header:{name}"
        elementary_ref = f"dff:elementary:{name}"
        try:
            actual_size = path.stat().st_size
            if 8 + form_size > actual_size:
                return self._unknown_container(path)
            parsed = self._walk_dff_chunks(path, actual_size)
        except OSError:
            return self._transient(path)
        if parsed is None:
            return self._unknown_container(path)
        rate, channel_ids, compression, data_size = parsed
        if data_size is None or data_size == 0:
            return self._unknown_container(path)
        channel_count = len(channel_ids) if channel_ids is not None else None
        if compression is None:
            return self._result(
                container=("dff", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
            )
        if compression != _DFF_COMPRESSION_UNCOMPRESSED:
            return self._result(
                container=("dff", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.COMPRESSED,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNSUPPORTED_ENCODING,
                failure_code=SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
            )
        if rate is None or rate <= 0 or rate % 8:
            return self._result(
                container=("dff", channel_count, None, container_ref),
                encoding=ElementaryEncoding.DSD,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_RATE_UNIT_INVALID,
            )
        if not channel_ids:
            return self._result(
                container=("dff", None, rate, container_ref),
                encoding=ElementaryEncoding.DSD,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
            )
        positions = tuple(_DFF_CHANNEL_POSITIONS.get(raw) for raw in channel_ids)
        if any(position is None for position in positions):
            return self._result(
                container=("dff", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.DSD,
                elementary_ref=elementary_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
            )
        signal = DsdSignalFormat(
            bit_rate_hz=rate,
            channels=len(channel_ids),
            packing=DsdPacking.DSD_U8,
            layout=positions,  # type: ignore[arg-type]
        )
        return self._proven(
            container=("dff", len(channel_ids), rate, container_ref),
            signal=signal,
            elementary_ref=elementary_ref,
        )

    @staticmethod
    def _walk_dff_chunks(
        path: Path, actual_size: int
    ) -> tuple[int | None, tuple[bytes, ...] | None, bytes | None, int | None] | None:
        rate: int | None = None
        channel_ids: tuple[bytes, ...] | None = None
        compression: bytes | None = None
        data_size: int | None = None
        with path.open("rb") as handle:
            offset = 12
            while offset + 8 <= actual_size:
                handle.seek(offset)
                header = handle.read(8)
                if len(header) < 8:
                    return None
                chunk_id = header[:4]
                (chunk_size,) = struct.unpack(">I", header[4:8])
                body = offset + 8
                if body + chunk_size > actual_size:
                    return None
                if chunk_id == b"PROP":
                    if chunk_size > _DFF_PROP_CAP_BYTES:
                        return None
                    prop = handle.read(chunk_size)
                    (
                        rate,
                        channel_ids,
                        compression,
                    ) = DsdSourceCharacterizer._parse_dff_prop(
                        prop, rate, channel_ids, compression
                    )
                elif chunk_id == b"DSD ":
                    data_size = chunk_size
                    break
                offset = body + chunk_size + (chunk_size % 2)
        return rate, channel_ids, compression, data_size

    @staticmethod
    def _parse_dff_prop(
        prop: bytes,
        rate: int | None,
        channel_ids: tuple[bytes, ...] | None,
        compression: bytes | None,
    ) -> tuple[int | None, tuple[bytes, ...] | None, bytes | None]:
        if len(prop) < 4 or prop[:4] != b"SND ":
            return rate, channel_ids, compression
        offset = 4
        while offset + 8 <= len(prop):
            chunk_id = prop[offset : offset + 4]
            (chunk_size,) = struct.unpack_from(">I", prop, offset + 4)
            body = offset + 8
            if body + chunk_size > len(prop):
                break
            if chunk_id == b"FS  " and chunk_size >= 4:
                (rate,) = struct.unpack_from(">I", prop, body)
            elif chunk_id == b"CHNL" and chunk_size >= 2:
                (count,) = struct.unpack_from(">H", prop, body)
                if count > 0 and 2 + 4 * count <= chunk_size:
                    channel_ids = tuple(
                        bytes(prop[body + 2 + index * 4 : body + 6 + index * 4])
                        for index in range(count)
                    )
            elif chunk_id == b"CMPR" and chunk_size >= 4:
                compression = bytes(prop[body : body + 4])
            offset = body + chunk_size + (chunk_size % 2)
        return rate, channel_ids, compression

    # ------------------------------------------------------------------ #
    # result builders
    # ------------------------------------------------------------------ #

    def _proven(
        self,
        *,
        container: tuple[str, int, int, str],
        signal: DsdSignalFormat,
        elementary_ref: str,
    ) -> DsdSourceCharacterization:
        container_name, channels, rate, container_ref = container
        caps_fields = (
            ("format", signal.packing.value),
            ("rate", str(signal.source_rate.gst_byte_rate_per_channel)),
            ("channels", str(channels)),
        )
        elementary = ElementaryStreamObservation(
            encoding=ElementaryEncoding.DSD,
            caps_media_type="audio/x-dsd",
            caps_fields=caps_fields,
            provider=PROVIDER,
            evidence_ref=elementary_ref,
        )
        container_facts = ContainerAudioFacts(
            container=container_name,
            codec="dsd",
            channels=channels,
            nominal_dsd_bits_per_second_per_channel=rate,
            evidence_ref=container_ref,
        )
        return DsdSourceCharacterization(
            container_facts=container_facts,
            elementary=elementary,
            signal=signal,
            status=DsdSourceStatus.DSD_PROVEN,
            failure_code=None,
            evidence_refs=(container_ref, elementary_ref),
        )

    def _result(
        self,
        *,
        container: tuple[str | None, int | None, int | None, str],
        encoding: ElementaryEncoding,
        elementary_ref: str,
        signal: DsdSignalFormat | None,
        status: DsdSourceStatus,
        failure_code: str,
    ) -> DsdSourceCharacterization:
        container_name, channels, rate, container_ref = container
        elementary = ElementaryStreamObservation(
            encoding=encoding,
            caps_media_type=None,
            caps_fields=(),
            provider=PROVIDER,
            evidence_ref=elementary_ref,
        )
        container_facts = ContainerAudioFacts(
            container=container_name,
            codec=None if container_name is None else "dsd",
            channels=channels,
            nominal_dsd_bits_per_second_per_channel=rate,
            evidence_ref=container_ref,
        )
        return DsdSourceCharacterization(
            container_facts=container_facts,
            elementary=elementary,
            signal=signal,
            status=status,
            failure_code=failure_code,
            evidence_refs=(container_ref, elementary_ref),
        )

    def _unknown_container(self, path: Path) -> DsdSourceCharacterization:
        name = path.name
        return self._result(
            container=(None, None, None, f"container:{name}:unknown"),
            encoding=ElementaryEncoding.UNKNOWN,
            elementary_ref=f"elementary:{name}:unknown",
            signal=None,
            status=DsdSourceStatus.UNKNOWN,
            failure_code=SOURCE_DSD_CONTAINER_UNKNOWN,
        )

    def _transient(self, path: Path) -> DsdSourceCharacterization:
        name = path.name
        return self._result(
            container=(None, None, None, f"container:{name}:unreadable"),
            encoding=ElementaryEncoding.UNKNOWN,
            elementary_ref=f"elementary:{name}:unreadable",
            signal=None,
            status=DsdSourceStatus.UNKNOWN,
            failure_code=SOURCE_DSD_TRANSIENT_UNAVAILABLE,
        )
