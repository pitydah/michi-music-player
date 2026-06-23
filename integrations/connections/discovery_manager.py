"""Discovery manager — auto-detect music servers on the local network."""

from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass

logger = logging.getLogger("michi.connections.discovery")

KNOWN_PORTS = {
    "navidrome": 4533,
    "subsonic": 4040,
    "airsonic": 4040,
    "jellyfin_http": 8096,
    "jellyfin_https": 8920,
    "home_assistant": 8123,
    "snapcast_tcp": 1704,
    "snapcast_http": 1780,
    "jellyfin_udp": 7359,
}


@dataclass
class DiscoveredServer:
    host: str
    port: int
    server_type: str = "unknown"
    name: str = ""
    protocol: str = "http"
    discovered_by: str = "port_scan"


class DiscoveryManager:
    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout
        self._results: list[DiscoveredServer] = []
        self._scanning = False

    def cancel(self):
        self._scanning = False

    def scan_known_ports(self, target_host: str = "") -> list[DiscoveredServer]:
        self._scanning = True
        self._results = []

        hosts = self._get_local_hosts() if not target_host else [target_host]
        for host in hosts:
            if not self._scanning:
                break
            for srv_type, port in KNOWN_PORTS.items():
                if not self._scanning:
                    break
                if self._try_port(host, port):
                    srv = DiscoveredServer(
                        host=host, port=port,
                        server_type=srv_type,
                        discovered_by="port_scan",
                    )
                    self._results.append(srv)

        return self._deduplicate()

    def scan_mdns(self) -> list[DiscoveredServer]:
        results: list[DiscoveredServer] = []
        try:
            import subprocess
            proc = subprocess.run(
                ["avahi-browse", "-t", "-p", "_http._tcp"],
                capture_output=True, text=True, timeout=10,
            )
            for line in proc.stdout.splitlines():
                if "Navidrome" in line or "Subsonic" in line or "Jellyfin" in line:
                    parts = line.split(";")
                    if len(parts) >= 8:
                        results.append(DiscoveredServer(
                            host=parts[6], port=int(parts[7]),
                            server_type="unknown", name=parts[3],
                            discovered_by="mdns",
                        ))
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        return results

    def scan_jellyfin_udp(self) -> list[DiscoveredServer]:
        results: list[DiscoveredServer] = []
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(3)
            msg = b"who is JellyfinServer?"
            sock.sendto(msg, ("255.255.255.255", 7359))
            start = time.time()
            while time.time() - start < 5:
                try:
                    data, addr = sock.recvfrom(1024)
                    results.append(DiscoveredServer(
                        host=addr[0], port=KNOWN_PORTS["jellyfin_http"],
                        server_type="jellyfin", name=data.decode(errors="replace"),
                        discovered_by="jellyfin_udp",
                    ))
                except socket.timeout:
                    break
            sock.close()
        except Exception as e:
            logger.debug("Jellyfin UDP scan failed: %s", e)
        return results

    def classify_server(self, host: str, port: int) -> str:
        import urllib.request
        urls = [
            (f"http://{host}:{port}/rest/ping", "navidrome"),
            (f"http://{host}:{port}/System/Info/Public", "jellyfin"),
            (f"http://{host}:{port}/api/", "home_assistant"),
        ]
        for url, srv_type in urls:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status < 500:
                        return srv_type
            except Exception:
                pass
        return "unknown"

    def build_discovered_server(self, discovered: DiscoveredServer) -> DiscoveredServer:
        discovered.server_type = self.classify_server(discovered.host, discovered.port)
        return discovered

    def deduplicate(self) -> list[DiscoveredServer]:
        return self._deduplicate()

    def _deduplicate(self) -> list[DiscoveredServer]:
        seen = {}
        for s in self._results:
            key = f"{s.host}:{s.port}"
            if key not in seen:
                seen[key] = s
        return list(seen.values())

    @staticmethod
    def _get_local_hosts() -> list[str]:
        hosts = []
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            parts = ip.rsplit(".", 1)
            if len(parts) == 2:
                prefix = parts[0]
                for i in range(1, 21):
                    hosts.append(f"{prefix}.{i}")
        except Exception:
            pass
        hosts.insert(0, "127.0.0.1")
        hosts.insert(0, "localhost")
        return hosts

    def _try_port(self, host: str, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
