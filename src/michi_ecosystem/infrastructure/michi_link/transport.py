"""UDP multicast and mDNS discovery sources (michi-link DISCOVERY spec).

Constants and TXT shapes mirror ``docs/DISCOVERY.md`` from michi-link; the
canonical verification stays in ``verification.py`` (E2). Sockets are
injectable and polling is non-blocking so callers keep I/O off the GUI thread.
"""

from __future__ import annotations

import json
import socket
import threading
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any

from michi_ecosystem.domain.discovery import MdnsHint
from michi_ecosystem.ports.discovery import RawAnnounce

MULTICAST_GROUP = "224.0.0.167"
MULTICAST_PORT = 53318
MAX_ANNOUNCE_BYTES = 8192
MDNS_SERVICE = "_michi-link._tcp.local"
OFFLINE_TIMEOUT_MS = 90_000
ANNOUNCE_INTERVAL_MS = 30_000
MAX_DATAGRAMS_PER_POLL = 256
MAX_BUFFERED_MDNS_HINTS = 1024


class DatagramError(ValueError):
    """A raw discovery datagram or TXT set is malformed."""


def parse_datagram(data: bytes) -> Mapping[str, Any]:
    """Decode a single JSON announce datagram (max 8 KiB, spec)."""
    if len(data) > MAX_ANNOUNCE_BYTES:
        raise DatagramError(f"announce exceeds {MAX_ANNOUNCE_BYTES} bytes")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DatagramError(f"invalid announce JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DatagramError("announce must be a JSON object")
    return payload


def parse_mdns_txt(properties: Mapping[str, str | bytes]) -> MdnsHint:
    """Parse the minimum TXT set (never trust material, never capabilities)."""

    def text(key: str) -> str:
        # Zeroconf exposes TXT keys as bytes. Looking up only string keys
        # silently drops EVERY real service announcement.
        value = properties.get(key, properties.get(key.encode("ascii"), ""))
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        result = str(value).strip()
        if len(result) > 512:
            raise DatagramError("mDNS TXT field exceeds limit")
        return result

    device_id = text("device_id")
    service = text("service")
    if not device_id or not service:
        raise DatagramError("mDNS TXT is missing device_id or service")
    roles = tuple(part for part in text("roles").split(",") if part)
    return MdnsHint(
        device_id=device_id,
        service=service,
        api_version=text("api_version"),
        roles=roles,
        auth_strategy=text("auth_strategy"),
        michi_id=text("michi_id"),
    )


class UdpDiscoverySource:
    """Multicast announce source (224.0.0.167:53318)."""

    def __init__(
        self,
        *,
        socket_factory: Callable[..., socket.socket] | None = None,
        max_datagrams_per_poll: int = MAX_DATAGRAMS_PER_POLL,
    ) -> None:
        if (
            not isinstance(max_datagrams_per_poll, int)
            or isinstance(max_datagrams_per_poll, bool)
            or max_datagrams_per_poll < 1
        ):
            raise ValueError("max_datagrams_per_poll must be positive")
        self._socket_factory = socket_factory or socket.socket
        self._socket: socket.socket | None = None
        self.max_datagrams_per_poll = max_datagrams_per_poll

    def start(self) -> None:
        if self._socket is not None:
            return
        sock = self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", MULTICAST_PORT))
            membership = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            sock.setblocking(False)
        except Exception:
            sock.close()
            raise
        self._socket = sock

    def poll(self) -> tuple[RawAnnounce, ...]:
        if self._socket is None:
            return ()
        announces: list[RawAnnounce] = []
        # Budget one poll so a hostile/busy multicast LAN cannot monopolize
        # the worker or grow a single returned batch without bound.
        for _ in range(self.max_datagrams_per_poll):
            try:
                data, address = self._socket.recvfrom(MAX_ANNOUNCE_BYTES + 1)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            host = address[0] if isinstance(address, tuple) and address else None
            announces.append(RawAnnounce(payload=data, source_host=host))
        return tuple(announces)

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None


class CompositeDiscoverySource:
    """Composes the UDP announce source with mDNS hints.

    UDP signed announces provide cryptographic identity evidence; mDNS stays a
    presence hint only (never identity, never trust).
    """

    def __init__(self, *, udp, mdns=None) -> None:
        self._udp = udp
        self._mdns = mdns

    def start(self) -> None:
        self._udp.start()
        if self._mdns is not None:
            self._mdns.start()

    def poll(self) -> tuple[RawAnnounce, ...]:
        return self._udp.poll()

    def poll_hints(self) -> tuple[MdnsHint, ...]:
        if self._mdns is None:
            return ()
        return self._mdns.poll()

    def close(self) -> None:
        self._udp.close()
        if self._mdns is not None:
            self._mdns.close()


class MdnsDiscoverySource:
    """mDNS TXT source via zeroconf (minimum set only; never trust material)."""

    def __init__(self) -> None:
        self._zeroconf: Any = None
        self._browser: Any = None
        # Zeroconf delivers events on its own worker thread.
        self._hints: deque[MdnsHint] = deque(maxlen=MAX_BUFFERED_MDNS_HINTS)
        self._hints_lock = threading.Lock()

    def start(self) -> None:
        from zeroconf import ServiceBrowser, Zeroconf

        self._zeroconf = Zeroconf()
        self._browser = ServiceBrowser(
            self._zeroconf, MDNS_SERVICE, handlers=[self._on_service]
        )

    def _on_service(
        self, zeroconf: Any, service_type: str, name: str, state_change: Any
    ) -> None:
        from zeroconf import ServiceStateChange

        if state_change not in (ServiceStateChange.Added, ServiceStateChange.Updated):
            return
        info = zeroconf.get_service_info(service_type, name, timeout=2000)
        if info is None:
            return
        try:
            hint = parse_mdns_txt(info.properties)
        except DatagramError:
            return
        with self._hints_lock:
            self._hints.append(hint)

    def poll(self) -> tuple[MdnsHint, ...]:
        with self._hints_lock:
            hints = tuple(self._hints)
            self._hints.clear()
        return hints

    def close(self) -> None:
        if self._browser is not None:
            self._browser.cancel()
            self._browser = None
        if self._zeroconf is not None:
            self._zeroconf.close()
            self._zeroconf = None
