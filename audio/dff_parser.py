# -*- coding: utf-8 -*-
"""DSDIFF (.dff) file parser — EA IFF 85 chunks."""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class DffHeader:
    sample_rate: int      # DSD sample rate (2822400 = DSD64, 5644800 = DSD128, etc.)
    channels: int         # 2 = stereo, 5 = 5.1
    data_offset: int      # byte where DSD chunk data starts
    data_size: int        # bytes of audio data
    is_dst: bool          # True if DST compressed (unsupported)


def parse_dff(filepath: str) -> DffHeader:
    """Parse DSDIFF file and return header info."""
    with open(filepath, "rb") as f:
        # ── FRM8 container ──
        ck_id = f.read(4)
        if ck_id != b"FRM8":
            raise ValueError(f"Not a valid DFF file (expected FRM8, got {ck_id})")

        ck_size = struct.unpack(">Q", f.read(8))[0]
        form_type = f.read(4)
        if form_type != b"DSD ":
            raise ValueError(f"Not a DSD DFF file (expected DSD , got {form_type})")

        sample_rate = 0
        channels = 0
        is_dst = False
        data_offset = 0
        data_size = 0
        form_end = f.tell() + ck_size - 4

        while f.tell() < form_end:
            chunk_id = f.read(4)
            chunk_size_bytes = f.read(8)
            if len(chunk_id) < 4 or len(chunk_size_bytes) < 8:
                break
            chunk_size = struct.unpack(">Q", chunk_size_bytes)[0]
            chunk_end = f.tell() + chunk_size

            if chunk_id == b"PROP":
                # Re-read position: we need to extract from PROP
                # Reset and parse PROP sub-chunks manually
                prop_start = f.tell() - chunk_size - 12
                f.seek(prop_start + 12)  # skip PROP + size
                prop_end = f.tell() + chunk_size
                while f.tell() < prop_end:
                    sub_id = f.read(4)
                    sub_size_bytes = f.read(8)
                    if len(sub_id) < 4 or len(sub_size_bytes) < 8:
                        break
                    sub_size = struct.unpack(">Q", sub_size_bytes)[0]
                    sub_data = f.read(sub_size)
                    if sub_id == b"FS  " and len(sub_data) >= 4:
                        sample_rate = struct.unpack(">I", sub_data[:4])[0]
                    elif sub_id == b"CHNL" and len(sub_data) >= 2:
                        channels = struct.unpack(">H", sub_data[:2])[0]
                    elif sub_id == b"CMPR" and len(sub_data) >= 4:
                        comp = sub_data[:4]
                        is_dst = (comp != b"DSD " and comp != b"\x00\x00\x00\x00")
                f.seek(chunk_end)

            elif chunk_id == b"DSD ":
                data_offset = f.tell()
                data_size = chunk_size
                f.seek(chunk_end)
            else:
                f.seek(chunk_end)

        if sample_rate <= 0 or channels <= 0:
            raise ValueError(
                f"Could not read DFF properties from {filepath}. "
                f"sample_rate={sample_rate}, channels={channels}")

        return DffHeader(
            sample_rate=sample_rate,
            channels=channels,
            data_offset=data_offset,
            data_size=data_size,
            is_dst=is_dst,
        )



