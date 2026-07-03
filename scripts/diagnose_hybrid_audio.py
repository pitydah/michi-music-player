#!/usr/bin/env python3
"""Michi Hybrid Audio Diagnostics — read-only system check.

Does NOT start/stop MPD. Does NOT modify settings. Does NOT require root.
Can run without GStreamer or PySide installed.
"""
import importlib
import os
import shutil
import socket
import subprocess
import sys

_SEP = "-" * 50


def get_git_commit():
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True, text=True, timeout=5.0,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def check_module(mod_name: str):
    try:
        importlib.import_module(mod_name)
        return "ok"
    except ImportError:
        return "not found"


def check_gstreamer():
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        ver = ".".join(str(v) for v in Gst.version())
        return f"ok ({ver})"
    except ImportError:
        return "not installed (gi)"
    except Exception as e:
        return f"error: {e}"


def check_mpd_installed():
    path = shutil.which("mpd")
    return f"yes ({path})" if path else "no"


def check_mpd_running():
    try:
        result = subprocess.run(
            ["pgrep", "-x", "mpd"], capture_output=True, text=True, timeout=3.0)
        if result.returncode == 0:
            pids = result.stdout.strip().split()
            return f"yes ({len(pids)} process(es))"
        return "no"
    except Exception:
        return "unknown"


def check_mpd_connection(host="127.0.0.1", port=6600):
    try:
        s = socket.create_connection((host, port), timeout=2.0)
        data = s.recv(256)
        s.close()
        greeting = data.decode("utf-8", errors="replace").strip()
        if greeting.startswith("OK MPD "):
            return f"ok (version {greeting[7:]})"
        return f"ok (unexpected: {greeting[:60]})"
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return f"error: {e}"
    except Exception as e:
        return f"error: {e}"


def check_profile_and_backend():
    try:
        from audio.output_profiles import get_profile, is_mpd_profile
        from core.settings_manager import get
        key = get("audio/profile") or "standard"
        prof = get_profile(key)
        return {
            "profile": f"{key} ({prof.name})",
            "backend": prof.preferred_backend,
            "bitperfect": prof.bitperfect,
            "mpd_profile": is_mpd_profile(key),
        }
    except Exception as e:
        return {"error": str(e)}


def check_registered_backends():
    try:
        from unittest.mock import MagicMock
        with (MagicMock()):
            pass
        with (MagicMock()):
            pass
        return "check requires runtime context"
    except Exception:
        return "unavailable (no runtime)"


def check_alsa_hw_params():
    proc_path = "/proc/asound"
    if not os.path.isdir(proc_path):
        return "0 (no /proc/asound)"
    count = 0
    for root, _dirs, files in os.walk(proc_path):
        if "hw_params" in files:
            try:
                with open(os.path.join(root, "hw_params")) as f:
                    if f.read().strip():
                        count += 1
            except OSError:
                pass
    return str(count)


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
    git_commit = get_git_commit()
    profile_info = check_profile_and_backend()

    print("Michi Hybrid Audio Diagnostics")
    print(_SEP)
    print(f"Commit:           {git_commit}")
    print(f"Python:           {sys.version.split()[0]}")
    print(f"Platform:         {sys.platform}")
    print(f"GStreamer:        {check_gstreamer()}")
    print(f"MPD installed:    {check_mpd_installed()}")
    print(f"MPD running:      {check_mpd_running()}")
    print(f"MPD connection:   {check_mpd_connection()}")
    print(f"Audio profile:    {profile_info.get('profile', 'unknown')}")
    print(f"Preferred backend: {profile_info.get('backend', 'unknown')}")
    print(f"Bit-perfect:      {check_bitperfect_status()}")
    print(f"ALSA hw_params:   {check_alsa_hw_params()}")
    if isinstance(profile_info, dict) and "mpd_profile" in profile_info:
        print(f"MPD profile:      {'yes' if profile_info['mpd_profile'] else 'no'}")
    print(_SEP)
    print("This script is read-only. It does not start/stop MPD or modify settings.")


if __name__ == "__main__":
    main()
