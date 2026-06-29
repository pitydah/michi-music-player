"""UDP multicast discovery — announce + listen for music sync peers.

Inspired by LocalSend's multicast_discovery.dart (UDP 224.0.0.167).
Announces every 5s, listens continuously for peer responses.
"""

import socket
import struct
import threading
import time

from PySide6.QtCore import QObject, Signal
from sync.sync_protocol import (
    AnnounceMessage, MULTICAST_GROUP, MULTICAST_PORT,
    ANNOUNCE_INTERVAL,
)


class DiscoveryServer(QObject):
    """UDP multicast discovery for finding music sync peers on LAN."""

    peer_found = Signal(str, str)      # alias, ip
    peer_lost = Signal(str)            # alias
    discovery_started = Signal()
    discovery_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, alias: str = "MichiMusicPlayer", parent=None,
                 auth_required: bool = False):
        super().__init__(parent)
        self._alias = alias
        self._auth_required = auth_required
        self._running = False
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None
        self._peers: dict[str, dict] = {}       # alias → {ts, msg, ip}
        self._peer_timeout = 15.0              # seconds before "lost"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.discovery_started.emit()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                import logging
                logging.getLogger("michi").debug("Sync discovery task failed")
            self._sock = None
        self.discovery_stopped.emit()

    def _run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self._sock.bind(("", MULTICAST_PORT))

            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP),
                              socket.INADDR_ANY)
            self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self._sock.settimeout(1.0)
        except Exception as e:
            self.error_occurred.emit(f"Discovery socket: {e}")
            self._running = False
            return

        last_announce = 0.0
        last_cleanup = 0.0

        while self._running:
            now = time.time()

            # Announce periodically
            if now - last_announce >= ANNOUNCE_INTERVAL:
                self._announce()
                last_announce = now

            # Cleanup stale peers
            if now - last_cleanup >= self._peer_timeout:
                self._cleanup_stale()
                last_cleanup = now

            # Listen for peers
            try:
                data, addr = self._sock.recvfrom(4096)
                self._handle_message(data, addr[0])
            except socket.timeout:
                pass
            except OSError:
                continue

        if self._sock:
            self._send_goodbye()
            try:
                self._sock.close()
            except Exception:
                import logging
                logging.getLogger("michi").debug("Sync discovery task failed")
            self._sock = None

    def _announce(self):
        from sync.sync_protocol import make_device_id
        msg = AnnounceMessage(
            type="announce", alias=self._alias,
            device="desktop", port=MULTICAST_PORT,
            device_id=make_device_id(),
            auth_required=self._auth_required,
        )
        self._send(msg)

    def _send_goodbye(self):
        msg = AnnounceMessage(
            type="goodbye", alias=self._alias,
            device="desktop", port=MULTICAST_PORT,
        )
        self._send(msg)

    def _send(self, msg: AnnounceMessage):
        if not self._sock:
            return
        try:
            data = msg.to_json().encode("utf-8")
            self._sock.sendto(data, (MULTICAST_GROUP, MULTICAST_PORT))
        except Exception:
                import logging
                logging.getLogger("michi").debug("Sync discovery: failed to close socket")

    def _handle_message(self, data: bytes, ip: str):
        try:
            msg = AnnounceMessage.from_json(data.decode("utf-8"))
        except Exception:
            return

        # Ignore our own announcements (same alias + same device type)
        if msg.alias == self._alias and msg.device == "desktop":
            return

        if msg.type == "goodbye":
            if msg.alias in self._peers:
                del self._peers[msg.alias]
                self.peer_lost.emit(msg.alias)
            return

        # Announce or response
        was_new = msg.alias not in self._peers
        self._peers[msg.alias] = {"ts": time.time(), "msg": msg, "ip": ip}

        if was_new:
            self.peer_found.emit(msg.alias, ip)

    def get_peer_info(self, alias: str) -> dict | None:
        """Return stored announce message for a peer, or None."""
        entry = self._peers.get(alias)
        if entry:
            return {
                "alias": entry["msg"].alias,
                "device_id": entry["msg"].device_id or f"sync_{alias}",
                "device_type": entry["msg"].device,
                "device_model": entry["msg"].device_model,
                "port": entry["msg"].port,
                "ip": entry["ip"],
            }
        return None

    def _cleanup_stale(self):
        """Remove peers not seen recently."""
        now = time.time()
        stale = [a for a, v in self._peers.items()
                 if now - v["ts"] > self._peer_timeout]
        for alias in stale:
            del self._peers[alias]
            self.peer_lost.emit(alias)

    def get_all_peers(self) -> list[dict]:
        peers = []
        for alias in sorted(self._peers.keys()):
            info = self.get_peer_info(alias)
            if info:
                peers.append(info)
        return peers

    @property
    def alias(self) -> str:
        return self._alias

    @alias.setter
    def alias(self, value: str):
        self._alias = value

    @property
    def peers(self) -> list[str]:
        return sorted(self._peers.keys())
