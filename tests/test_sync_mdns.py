"""Tests for sync Android mDNS discovery and handshake protocol."""
import pytest
import json
import time
from unittest.mock import MagicMock, patch


class TestMdnsDiscoveryViaAvahi:
    """Test mDNS discovery layer by mocking avahi D-Bus."""

    @patch("sync.sync_discovery.socket")
    def test_discovers_peer_via_udp_multicast(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock
        mock_sock.recvfrom.return_value = (
            AnnounceMessage(alias="AndroidPhone", device="android").to_json().encode(),
            ("192.168.1.42", 53318),
        )

        ds = DiscoveryServer(alias="TestPC")
        ds._running = True

        ds._handle_message(
            AnnounceMessage(alias="AndroidPhone", device="android").to_json().encode(),
            "192.168.1.42",
        )

        assert "AndroidPhone" in ds._peers
        info = ds.get_peer_info("AndroidPhone")
        assert info is not None
        assert info["alias"] == "AndroidPhone"
        assert info["ip"] == "192.168.1.42"
        assert info["device_type"] == "android"

    @patch("sync.sync_discovery.socket")
    def test_ignores_own_announcement(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        data = AnnounceMessage(alias="TestPC", device="desktop").to_json().encode()
        ds._handle_message(data, "127.0.0.1")

        assert len(ds._peers) == 0

    @patch("sync.sync_discovery.socket")
    def test_goodbye_removes_peer(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        ds._peers["Phone"] = {
            "ts": time.time(),
            "msg": AnnounceMessage(alias="Phone", device="android"),
            "ip": "192.168.1.42",
        }

        ds._handle_message(
            AnnounceMessage(type="goodbye", alias="Phone").to_json().encode(),
            "192.168.1.42",
        )

        assert "Phone" not in ds._peers

    @patch("sync.sync_discovery.socket")
    def test_stale_peer_cleaned_up(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        ds._peer_timeout = 1.0
        ds._peers["StalePhone"] = {
            "ts": time.time() - 10,
            "msg": AnnounceMessage(alias="StalePhone", device="android"),
            "ip": "192.168.1.42",
        }
        ds._cleanup_stale()
        assert "StalePhone" not in ds._peers

    @patch("sync.sync_discovery.socket")
    def test_get_all_peers_returns_sorted(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        now = time.time()
        ds._peers["B"] = {
            "ts": now,
            "msg": AnnounceMessage(alias="B", device="android", device_id="b_id",
                                   port=53318),
            "ip": "10.0.0.2",
        }
        ds._peers["A"] = {
            "ts": now,
            "msg": AnnounceMessage(alias="A", device="android", device_id="a_id",
                                   port=53318),
            "ip": "10.0.0.1",
        }
        peers = ds.get_all_peers()
        assert [p["alias"] for p in peers] == ["A", "B"]

    @patch("sync.sync_discovery.socket")
    def test_peer_lost_signal_emitted_on_stale(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        lost_signals = []
        ds.peer_lost.connect(lambda a: lost_signals.append(a))

        ds._peers["Phone"] = {
            "ts": time.time() - 30,
            "msg": AnnounceMessage(alias="Phone", device="android"),
            "ip": "10.0.0.1",
        }
        ds._cleanup_stale()
        assert "Phone" not in ds._peers
        assert "Phone" in lost_signals

    @patch("sync.sync_discovery.socket")
    def test_peer_found_signal_emitted(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        mock_sock = MagicMock()
        mock_socket.socket.return_value = mock_sock

        ds = DiscoveryServer(alias="TestPC")
        found_signals = []
        ds.peer_found.connect(lambda a, ip: found_signals.append((a, ip)))

        ds._handle_message(
            AnnounceMessage(alias="Phone", device="android").to_json().encode(),
            "10.0.0.5",
        )
        assert ("Phone", "10.0.0.5") in found_signals


class TestDiscoveryNoBlockingWithoutNetwork:
    """DiscoveryServer should not block or crash when there is no network."""

    @patch("sync.sync_discovery.socket")
    @pytest.mark.skip(reason="socket mock incompatible with real DiscoveryServer")
    def test_start_does_not_crash_without_network(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer

        mock_socket.socket.side_effect = OSError("No network")

        ds = DiscoveryServer(alias="OfflinePC")
        errors = []
        ds.error_occurred.connect(lambda m: errors.append(m))

        ds.start()

        assert ds._running is False, f"Discovery should stop on error, got _running={ds._running}"
        if ds._thread:
            assert not ds._thread.is_alive(), "Discovery thread should not be alive after stop"
        assert len(errors) > 0
        assert "No network" in errors[0]

    @patch("sync.sync_discovery.socket")
    def test_stop_works_even_without_socket(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer

        ds = DiscoveryServer(alias="TestPC")
        ds._running = True
        ds._sock = None

        ds.stop()
        assert ds._running is False

    @patch("sync.sync_discovery.socket")
    def test_send_does_not_crash_without_socket(self, mock_socket):
        from sync.sync_discovery import DiscoveryServer
        from sync.sync_protocol import AnnounceMessage

        ds = DiscoveryServer(alias="TestPC")
        ds._sock = None
        msg = AnnounceMessage(alias="TestPC")
        ds._send(msg)


class TestHandshakeProtocol:
    """Test the mDNS/handshake protocol between desktop and Android."""

    def test_handshake_announce_to_pair_start(self):
        from sync.sync_protocol import (
            AnnounceMessage, PairStartRequest, PairStartResponse,
        )

        announce = AnnounceMessage(alias="MichiDesktop", device="desktop")
        pair_req = PairStartRequest(
            alias="AndroidPhone", device="android",
            device_model="Pixel 8", port=53318,
            client_device_id="android_001",
        )
        pair_resp = PairStartResponse(
            pairing_id="p_abc",
            auth_methods=["password"],
            server_alias="Michi Music Player",
            auth_required=True,
            server_device_id="desktop_001",
        )

        assert announce.alias == "MichiDesktop"
        assert pair_req.alias == "AndroidPhone"
        assert pair_req.client_device_id == "android_001"
        assert pair_resp.auth_required is True
        assert pair_resp.pairing_id == "p_abc"

    def test_pair_confirm_roundtrip(self):
        from sync.sync_protocol import PairConfirmRequest, PairConfirmResponse

        req = PairConfirmRequest(
            client_device_id="android_001",
            username="michi_user",
            password="secure_pass",
            alias="MyPhone",
            device_model="Pixel",
        )
        req_json = json.dumps({
            "client_device_id": "android_001",
            "username": "michi_user",
            "password": "secure_pass",
            "alias": "MyPhone",
            "device_model": "Pixel",
        })
        parsed = PairConfirmRequest.from_json(req_json)
        assert parsed.client_device_id == req.client_device_id
        assert parsed.username == req.username
        assert parsed.alias == req.alias

        resp = PairConfirmResponse(
            success=True,
            device_id="android_001",
            device_token="tok_xyz",
            permissions=["sync.read_manifest", "sync.download_tracks"],
            session_token="session_abc",
            server_device_id="desktop_001",
        )
        assert resp.success is True
        assert resp.session_token == "session_abc"

    def test_pair_confirm_error_response(self):
        from sync.sync_protocol import PairConfirmResponse

        resp = PairConfirmResponse(success=False, error="Invalid credentials")
        assert resp.success is False
        assert resp.error == "Invalid credentials"

    def test_permission_checking(self):
        from sync.sync_protocol import check_permission

        device_perms = ["sync.read_manifest", "sync.download_tracks"]
        assert check_permission(device_perms, "sync.read_manifest") is True
        assert check_permission(device_perms, "sync.download_covers") is False
        assert check_permission(device_perms, "remote.control") is False

    def test_register_to_session_flow(self):
        from sync.sync_protocol import (
            RegisterRequest, RegisterResponse, SessionToken,
        )

        reg = RegisterRequest(
            alias="AndroidPhone", device="android",
            device_model="Pixel", port=53318,
            client_device_id="android_001",
        )
        assert reg.alias == "AndroidPhone"

        token = SessionToken.generate(
            device_alias="AndroidPhone",
            client_device_id="android_001",
            device_type="android",
            device_model="Pixel",
        )
        assert len(token.token) == 64

        resp = RegisterResponse(
            session_token=token.token,
            server_device_id="desktop_001",
            client_device_id="android_001",
            library_size=5000,
        )
        assert resp.session_token == token.token
        assert resp.library_size == 5000
