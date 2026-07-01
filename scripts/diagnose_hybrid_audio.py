#!/usr/bin/env python3
"""Michi Hybrid Audio Diagnostics — read-only system check.

Does NOT start/stop MPD. Does NOT modify settings. Does NOT require root.
"""
import os
import shutil
import socket
import sys

_SEP = "-" * 50


def check_gstreamer():
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        return "ok"
    except Exception:
        return "error"


def check_mpd_installed():
    return "yes" if shutil.which("mpd") else "no"


def check_mpd_connection(host="127.0.0.1", port=6600):
    try:
        s = socket.create_connection((host, port), timeout=2.0)
        data = s.recv(256)
        s.close()
        greeting = data.decode("utf-8", errors="replace").strip()
        if greeting.startswith("OK MPD "):
            return f"ok (version {greeting[7:]})"
        return f"ok (unexpected greeting: {greeting[:50]})"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return f"error: {e}"
    except Exception as e:
        return f"error: {e}"


def check_profile():
    try:
        from audio.output_profiles import get_profile
        from core.settings_manager import get
        key = get("audio/profile") or "standard"
        prof = get_profile(key)
        return f"{key} ({prof.name}) -> backend: {prof.preferred_backend}"
    except Exception as e:
        return f"error: {e}"


def check_alsa_hw_params():
    proc_path = "/proc/asound"
    if not os.path.isdir(proc_path):
        return "0 (no /proc/asound)"
    count = 0
    for root, _dirs, files in os.walk(proc_path):
        if "hw_params" in files:
            count += 1
    return f"{count}"


def check_registered_backends():
    try:
        from audio.player_service import PlayerService
        from audio.player import PlaybackState
        from unittest.mock import MagicMock
        engine = MagicMock()
        engine._state = PlaybackState.STOPPED
        engine.state = PlaybackState.STOPPED
        svc = PlayerService(engine)
        backends = list(svc._hybrid._backends.keys()) if hasattr(svc._hybrid, '_backends') else []
        return f"{backends}" if backends else "gstreamer"
    except Exception as e:
        return f"error: {e}"


def check_bitperfect_status():
    try:
        from audio.output_profiles import get_profile
        from core.settings_manager import get
        key = get("audio/profile") or "standard"
        prof = get_profile(key)
        if prof.bitperfect:
            return "requested (bit-perfect profile active)"
        return "off (non-bitperfect profile)"
    except Exception as e:
        return f"error: {e}"


def main():
    print("Michi Hybrid Audio Diagnostics")
    print(_SEP)
    print(f"Python:           {sys.version.split()[0]}")
    print(f"Platform:         {sys.platform}")
    print(f"GStreamer:        {check_gstreamer()}")
    print(f"MPD installed:    {check_mpd_installed()}")
    if shutil.which("mpd"):
        mpd_path = shutil.which("mpd")
        print(f"MPD binary:       {mpd_path}")
    print(f"MPD connection:   {check_mpd_connection()}")
    print(f"Audio profile:    {check_profile()}")
    print(f"ALSA hw_params:   {check_alsa_hw_params()}")
    print(f"Bit-perfect:      {check_bitperfect_status()}")


if __name__ == "__main__":
    main()
