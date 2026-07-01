"""MPD Discovery — finds MPD instances on the local network or system."""

import logging
import subprocess

from audio.mpd.mpd_client import MpdClient
from audio.mpd.mpd_errors import MpdConnectionError

logger = logging.getLogger("michi.mpd.discovery")


def find_local_mpd(host: str = "127.0.0.1", ports: list[int] | None = None) -> list[dict]:
    """Scan common MPD ports on localhost to find running instances.

    Returns list of dicts with host, port, and version (if connected).
    """
    ports = ports or [6600, 6601, 6602, 6603]
    results = []
    for port in ports:
        client = MpdClient(host=host, port=port, timeout=2.0)
        try:
            client.connect()
            results.append({
                "host": host,
                "port": port,
                "version": client._version,
            })
            client.disconnect()
        except MpdConnectionError:
            continue
    return results


def find_mpd_processes() -> list[dict]:
    """Find MPD processes running on the system via ps.

    Returns list of dicts with pid and command.
    """
    try:
        result = subprocess.run(
            ["ps", "-e", "-o", "pid,args"],
            capture_output=True, text=True, timeout=5.0,
        )
        mpds = []
        for line in result.stdout.split("\n"):
            if "mpd" in line.lower() and "mpd_discovery" not in line:
                parts = line.strip().split(None, 1)
                if len(parts) >= 2:
                    mpds.append({"pid": parts[0], "command": parts[1]})
        return mpds
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.debug("Failed to list MPD processes: %s", e)
        return []


def format_discovery_report() -> str:
    """Human-readable discovery report."""
    lines = ["MPD Discovery Report", "=" * 40]
    local = find_local_mpd()
    if local:
        for inst in local:
            lines.append(f"  Local MPD: {inst['host']}:{inst['port']} (v{inst['version']})")
    else:
        lines.append("  No local MPD found")

    procs = find_mpd_processes()
    if procs:
        lines.append(f"  MPD processes: {len(procs)}")
        for p in procs:
            lines.append(f"    PID {p['pid']}: {p['command'][:60]}")
    else:
        lines.append("  No MPD processes detected")

    return "\n".join(lines)
