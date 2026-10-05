"""DSD source characterizer — real-format static DSF/DSDIFF source truth.

AP2-F07 / R11-F07 and seal 212: container facts, elementary-stream truth and
decoded/runtime truth are deliberately separate. This module implements only
the CONTAINER and ELEMENTARY layers by parsing bytes; it never starts a
GStreamer pipeline, never touches ALSA and never claims output capability.

Format authorities (behaviour cross-checked against independent implementations,
algorithms reimplemented from the format facts, no external code copied):

* DSF (Sony "DSF File Format Specification" behaviour, cross-checked against
  FFmpeg ``libavformat/dsfdec.c`` and WavPack ``cli/dsf.c``): every chunk size
  includes the 12-byte chunk header (payload = size - 12); the file-size field
  equals the real file size; the sample count is the per-channel count of
  1-bit samples; the block size groups per-channel planar bytes; and
  ``bits-per-sample`` carries bit order: 1 -> LSB-first, 8 -> MSB-first.
* DSDIFF/DFF (Philips DSDIFF 1.5 behaviour, cross-checked against WavPack
  ``cli/dsdiff.c`` + ``cli/dsdiff_write.c``): every chunk header is a 4-byte ID
  plus a 64-bit big-endian data size (12 bytes); the FRM8 size is
  ``file_size - 12``; PROP data is ``"SND "`` plus even-padded child chunks;
  the ``DSD `` data-chunk size excludes its header; audio is MSB-first and
  channel-interleaved; CMPR must prove ``"DSD "`` (uncompressed).

Failure semantics: a transient inability to observe (missing file, busy file,
source changed mid-parse) is UNKNOWN — never negative capability evidence;
positively identified encodings outside F07 support (DST compression) are
UNSUPPORTED, which is distinct from UNKNOWN.
"""

from __future__ import annotations

import hashlib
import os
import stat
import struct
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)

PROVIDER = "static-parser"

SOURCE_DSD_CONTAINER_UNKNOWN = "SOURCE_DSD_CONTAINER_UNKNOWN"
SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN = "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN"
SOURCE_DSD_RATE_UNIT_INVALID = "SOURCE_DSD_RATE_UNIT_INVALID"
SOURCE_DSD_GROUPING_UNKNOWN = "SOURCE_DSD_GROUPING_UNKNOWN"
SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN = "SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN"
#: F07 extensions: transient inability to observe is never a negative claim.
SOURCE_DSD_TRANSIENT_UNAVAILABLE = "SOURCE_DSD_TRANSIENT_UNAVAILABLE"

_DSF_MAGIC = b"DSD "
_DSF_FMT_MAGIC = b"fmt "
_DSF_DATA_MAGIC = b"data"
_DSF_FIXED_HEADER_BYTES = 92
_DSF_FORMAT_VERSION = 1
_DSF_FORMAT_ID_DSD_RAW = 0

_DFF_FORM_MAGIC = b"FRM8"
_DFF_FORM_TYPE = b"DSD "
_DFF_CHUNK_HEADER_BYTES = 12
_DFF_COMPRESSION_UNCOMPRESSED = b"DSD "
_DFF_PROP_CAP_BYTES = 4 * 1024 * 1024
_DFF_MAX_CHUNK_SCAN = 1024
_DFF_SIZE_UNSET = -1  # 0xFFFFFFFFFFFFFFFF: writer did not know the final size

#: DSF standard channel types 1..7 (cross-checked against the DSF
#: specification table and FFmpeg's `dsf_channel_layout`).
_DSF_CHANNEL_LAYOUTS: dict[int, tuple[str, ...]] = {
    1: ("FC",),
    2: ("FL", "FR"),
    3: ("FL", "FR", "FC"),
    4: ("FL", "FR", "BL", "BR"),
    5: ("FL", "FR", "FC", "BC"),
    6: ("FL", "FR", "FC", "BL", "BR"),
    7: ("FL", "FR", "FC", "LFE", "BL", "BR"),
}

#: DSDIFF standard channel identifiers (WavPack cross-check: it reads exactly
#: these; MLFT/MRGT are the multi-channel front pair).
_DFF_CHANNEL_POSITIONS: dict[bytes, str] = {
    b"SLFT": "FL",
    b"MLFT": "FL",
    b"SRGT": "FR",
    b"MRGT": "FR",
    b"C   ": "FC",
    b"LFE ": "LFE",
    b"LS  ": "SL",
    b"RS  ": "SR",
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


def _structural_ref(container: str, structural_bytes: bytes, size_bytes: int) -> str:
    """Bounded structural fingerprint: distinguishes same-name artifacts."""
    digest = hashlib.sha256()
    digest.update(container.encode("ascii"))
    digest.update(struct.pack("<Q", max(0, int(size_bytes))))
    digest.update(structural_bytes)
    return f"{container}:structural:{digest.hexdigest()[:16]}"


def _u64le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 8], "little", signed=False)


def _i64be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 8], "big", signed=True)


def _u32le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


class DsdSourceCharacterizer:
    """Deterministic real-format DSF/DFF source truth; no runtime commands."""

    def characterize(self, path: Path) -> DsdSourceCharacterization:
        candidate = Path(path)
        try:
            handle = candidate.open("rb")
        except OSError:
            return self._transient(candidate, "source unreadable")
        try:
            stat_before = os.fstat(handle.fileno())
            if not stat.S_ISREG(stat_before.st_mode):
                return self._transient(candidate, "source is not a regular file")
            result = self._characterize_open(candidate, handle, stat_before.st_size)
            stat_after = os.fstat(handle.fileno())
            if (
                stat_before.st_size != stat_after.st_size
                or stat_before.st_mtime_ns != stat_after.st_mtime_ns
                or stat_before.st_ino != stat_after.st_ino
            ):
                return self._transient(
                    candidate, "source changed during characterization"
                )
            return result
        except OSError:
            return self._transient(candidate, "source read failure")
        finally:
            handle.close()

    # ------------------------------------------------------------------ #
    # container dispatch
    # ------------------------------------------------------------------ #

    def _characterize_open(
        self, path: Path, handle, actual_size: int
    ) -> DsdSourceCharacterization:
        head = handle.read(16)
        if head[:4] == _DSF_MAGIC:
            return self._characterize_dsf(path, handle, head, actual_size)
        if head[:4] == _DFF_FORM_MAGIC:
            return self._characterize_dff(path, handle, head, actual_size)
        return self._unknown_container(
            path, _structural_ref("source", head, actual_size)
        )

    # ------------------------------------------------------------------ #
    # DSF
    # ------------------------------------------------------------------ #

    def _characterize_dsf(
        self, path: Path, handle, head: bytes, actual_size: int
    ) -> DsdSourceCharacterization:
        header = head + handle.read(_DSF_FIXED_HEADER_BYTES - len(head))
        container_ref = _structural_ref("dsf", header, actual_size)

        if len(header) < _DSF_FIXED_HEADER_BYTES or header[28:32] != _DSF_FMT_MAGIC:
            return self._unknown_container(path, container_ref)
        dsd_size = _u64le(header, 4)
        file_size = _u64le(header, 12)
        meta_offset = _u64le(header, 20)
        fmt_size = _u64le(header, 32)
        format_version = _u32le(header, 40)
        format_id = _u32le(header, 44)
        channel_type = _u32le(header, 48)
        channel_count = _u32le(header, 52)
        rate = _u32le(header, 56)
        bits_per_sample = _u32le(header, 60)
        sample_count = _u64le(header, 64)
        block_size = _u32le(header, 72)
        reserved = _u32le(header, 76)
        data_magic = header[80:84]
        data_size = _u64le(header, 84)

        if dsd_size != 28 or fmt_size != 52 or data_magic != _DSF_DATA_MAGIC:
            return self._unknown_container(path, container_ref)
        if format_version != _DSF_FORMAT_VERSION or reserved != 0:
            return self._unknown_container(path, container_ref)
        if file_size != 0 and file_size != actual_size:
            return self._unknown_container(path, container_ref)
        if format_id != _DSF_FORMAT_ID_DSD_RAW:
            return self._result(
                container=("dsf", channel_count or None, None, container_ref),
                encoding=ElementaryEncoding.COMPRESSED,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNSUPPORTED_ENCODING,
                failure_code=SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
            )
        if rate <= 0 or rate % 8:
            return self._result(
                container=("dsf", channel_count or None, None, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_RATE_UNIT_INVALID,
            )
        # Channel type and count must agree with the standard table.
        layout = _DSF_CHANNEL_LAYOUTS.get(channel_type)
        if layout is None or channel_count != len(layout):
            return self._result(
                container=("dsf", channel_count or None, rate, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
            )
        if sample_count <= 0 or block_size <= 0 or bits_per_sample not in (1, 8):
            return self._result(
                container=("dsf", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.UNKNOWN,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=SOURCE_DSD_GROUPING_UNKNOWN,
            )

        data_payload_size = data_size - 12
        if (
            data_payload_size <= 0
            or _DSF_FIXED_HEADER_BYTES + data_payload_size > actual_size
        ):
            return self._unknown_container(path, container_ref)
        # Real DSF layout: per-channel 1-bit samples grouped in planar blocks.
        blocks = (sample_count + block_size * 8 - 1) // (block_size * 8)
        expected_payload = blocks * block_size * channel_count
        if data_payload_size != expected_payload:
            return self._unknown_container(path, container_ref)
        if meta_offset != 0 and not (
            _DSF_FIXED_HEADER_BYTES + data_payload_size <= meta_offset < actual_size
        ):
            return self._unknown_container(path, container_ref)

        bit_order = DsdBitOrder.LSBF if bits_per_sample == 1 else DsdBitOrder.MSBF
        signal = DsdSignalFormat(
            bit_rate_hz=rate,
            channels=channel_count,
            packing=DsdPacking.DSD_U8,
            bit_order=bit_order,
            organization=DsdOrganization.PLANAR,
            layout=layout,
        )
        return self._proven(
            container=("dsf", channel_count, rate, container_ref),
            signal=signal,
            elementary_ref=container_ref,
            extra_caps=(("bits-per-sample", str(bits_per_sample)),),
        )

    # ------------------------------------------------------------------ #
    # DFF (DSDIFF)
    # ------------------------------------------------------------------ #

    def _characterize_dff(
        self, path: Path, handle, head: bytes, actual_size: int
    ) -> DsdSourceCharacterization:
        form_size = _i64be(head, 4)
        if len(head) < 16 or head[12:16] != _DFF_FORM_TYPE:
            return self._unknown_container(
                path, _structural_ref("dff", head, actual_size)
            )
        if form_size != _DFF_SIZE_UNSET and form_size + 12 != actual_size:
            return self._unknown_container(
                path, _structural_ref("dff", head, actual_size)
            )
        structural = bytearray(head)
        try:
            parsed = self._walk_dff_chunks(handle, actual_size, structural)
        except OSError:
            return self._transient(path, "source read failure")
        container_ref = _structural_ref("dff", bytes(structural), actual_size)
        if parsed is None:
            return self._unknown_container(path, container_ref)
        rate, channel_ids, compression, data_size = parsed

        def failure(
            code: str,
            *,
            encoding=ElementaryEncoding.UNKNOWN,
            channels=None,
            rate_value=None,
        ):
            return self._result(
                container=("dff", channels, rate_value, container_ref),
                encoding=encoding,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNKNOWN,
                failure_code=code,
            )

        channel_count = len(channel_ids) if channel_ids is not None else None
        if data_size is None or data_size <= 0:
            return self._unknown_container(path, container_ref)
        if compression is None:
            return failure(
                SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
                channels=channel_count,
                rate_value=rate,
            )
        if compression != _DFF_COMPRESSION_UNCOMPRESSED:
            return self._result(
                container=("dff", channel_count, rate, container_ref),
                encoding=ElementaryEncoding.COMPRESSED,
                elementary_ref=container_ref,
                signal=None,
                status=DsdSourceStatus.UNSUPPORTED_ENCODING,
                failure_code=SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN,
            )
        if rate is None or rate <= 0 or rate % 8:
            return failure(
                SOURCE_DSD_RATE_UNIT_INVALID,
                encoding=ElementaryEncoding.DSD,
                channels=channel_count,
            )
        if not channel_ids:
            return failure(
                SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
                encoding=ElementaryEncoding.DSD,
                rate_value=rate,
            )
        positions = tuple(_DFF_CHANNEL_POSITIONS.get(raw) for raw in channel_ids)
        if any(position is None for position in positions) or len(
            set(positions)
        ) != len(positions):
            return failure(
                SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN,
                encoding=ElementaryEncoding.DSD,
                channels=channel_count,
                rate_value=rate,
            )
        signal = DsdSignalFormat(
            bit_rate_hz=rate,
            channels=len(channel_ids),
            packing=DsdPacking.DSD_U8,
            bit_order=DsdBitOrder.MSBF,
            organization=DsdOrganization.INTERLEAVED,
            layout=positions,  # type: ignore[arg-type]
        )
        return self._proven(
            container=("dff", len(channel_ids), rate, container_ref),
            signal=signal,
            elementary_ref=container_ref,
        )

    def _walk_dff_chunks(
        self, handle, actual_size: int, structural: bytearray
    ) -> tuple[int | None, tuple[bytes, ...] | None, bytes | None, int | None] | None:
        rate: int | None = None
        channel_ids: tuple[bytes, ...] | None = None
        compression: bytes | None = None
        data_size: int | None = None
        offset = 16  # 12-byte FRM8 header + 4-byte "DSD " form type
        for _ in range(_DFF_MAX_CHUNK_SCAN):
            if offset + _DFF_CHUNK_HEADER_BYTES > actual_size:
                break
            handle.seek(offset)
            chunk_header = handle.read(_DFF_CHUNK_HEADER_BYTES)
            if len(chunk_header) < _DFF_CHUNK_HEADER_BYTES:
                return None
            structural += chunk_header
            chunk_id = chunk_header[:4]
            chunk_size = _i64be(chunk_header, 4)
            if (
                chunk_size < 0
                or offset + _DFF_CHUNK_HEADER_BYTES + chunk_size > actual_size
            ):
                return None
            body = offset + _DFF_CHUNK_HEADER_BYTES
            if chunk_id == b"PROP":
                if chunk_size < 4 or chunk_size > _DFF_PROP_CAP_BYTES:
                    return None
                prop = handle.read(chunk_size)
                if len(prop) != chunk_size:
                    return None
                structural += prop
                parsed = self._parse_dff_prop(prop)
                if parsed is None:
                    return None
                rate, channel_ids, compression = parsed
            elif chunk_id == b"DSD ":
                data_size = chunk_size
                break
            elif chunk_id == b"FVER":
                if chunk_size != 4:
                    return None
            offset = body + chunk_size + (chunk_size % 2)
        return rate, channel_ids, compression, data_size

    @staticmethod
    def _parse_dff_prop(
        prop: bytes,
    ) -> tuple[int | None, tuple[bytes, ...] | None, bytes | None] | None:
        if len(prop) < 4:
            return None
        rate: int | None = None
        channel_ids: tuple[bytes, ...] | None = None
        compression: bytes | None = None
        offset = 4
        while offset + _DFF_CHUNK_HEADER_BYTES <= len(prop):
            child_id = prop[offset : offset + 4]
            child_size = _i64be(prop, offset + 4)
            if child_size <= 0 or offset + _DFF_CHUNK_HEADER_BYTES + child_size > len(
                prop
            ):
                return None
            body = offset + _DFF_CHUNK_HEADER_BYTES
            if child_id == b"FS  ":
                if child_size != 4:
                    return None
                rate = int.from_bytes(prop[body : body + 4], "big", signed=False)
            elif child_id == b"CHNL":
                if child_size < 2:
                    return None
                count = int.from_bytes(prop[body : body + 2], "big", signed=False)
                if 2 + 4 * count != child_size:
                    return None
                channel_ids = tuple(
                    bytes(prop[body + 2 + index * 4 : body + 6 + index * 4])
                    for index in range(count)
                )
            elif child_id == b"CMPR":
                if child_size < 4:
                    return None
                compression = bytes(prop[body : body + 4])
            offset = body + child_size + (child_size % 2)
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
        extra_caps: tuple[tuple[str, str], ...] = (),
    ) -> DsdSourceCharacterization:
        container_name, channels, rate, container_ref = container
        caps_fields = (
            ("format", signal.packing.value),
            ("rate", str(signal.source_rate.gst_byte_rate_per_channel)),
            ("channels", str(channels)),
            *extra_caps,
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

    def _unknown_container(
        self, path: Path, container_ref: str | None = None
    ) -> DsdSourceCharacterization:
        ref = container_ref or _structural_ref("source", b"", 0)
        return self._result(
            container=(None, None, None, ref),
            encoding=ElementaryEncoding.UNKNOWN,
            elementary_ref=ref,
            signal=None,
            status=DsdSourceStatus.UNKNOWN,
            failure_code=SOURCE_DSD_CONTAINER_UNKNOWN,
        )

    def _transient(self, path: Path, detail: str) -> DsdSourceCharacterization:
        ref = _structural_ref("source", detail.encode("ascii", "replace"), 0)
        return self._result(
            container=(None, None, None, ref),
            encoding=ElementaryEncoding.UNKNOWN,
            elementary_ref=ref,
            signal=None,
            status=DsdSourceStatus.UNKNOWN,
            failure_code=SOURCE_DSD_TRANSIENT_UNAVAILABLE,
        )
