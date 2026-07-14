import pytest
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from core.radio.stream_probe import StreamProbeService
from core.radio.models import ProbeStatus


class _StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/valid.mp3":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("icy-name", "Test Radio")
            self.send_header("icy-genre", "Rock")
            self.send_header("icy-br", "128")
            self.send_header("icy-metaint", "8192")
            self.end_headers()
            self.wfile.write(b"X" * 1024)

        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/valid.mp3")
            self.end_headers()

        elif self.path == "/redirect-loop":
            self.send_response(302)
            self.send_header("Location", "/redirect-loop")
            self.end_headers()

        elif self.path == "/not-found":
            self.send_response(404)
            self.end_headers()

        elif self.path == "/server-error":
            self.send_response(500)
            self.end_headers()

        elif self.path == "/unsupported.mp4":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.end_headers()
            self.wfile.write(b"X" * 128)

        elif self.path == "/metadata-stream":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("icy-name", "Metadata Radio")
            self.send_header("icy-metaint", "4096")
            self.end_headers()
            meta = b"StreamTitle='Song A - Artist'" + b"\x00" * (4096 - 36)
            data = b"\x00" * 4096 + bytes([len(meta) // 16 + 1]) + meta
            self.wfile.write(data[:8192])

        elif self.path == "/malformed-metadata":
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("icy-metaint", "512")
            self.end_headers()
            broken = b"\xff\xfe\x00\x01\x02"
            self.wfile.write(b"\x00" * 512 + broken)

        elif self.path == "/timeout":
            time.sleep(5)
            self.send_response(200)
            self.end_headers()

        elif self.path == "/empty-audio":
            self.send_response(200)
            self.send_header("Content-Type", "audio/ogg")
            self.send_header("icy-name", "Empty Radio")
            self.send_header("icy-genre", "Test")
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def log_request(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    server = HTTPServer(("127.0.0.1", 0), _StreamHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


class TestStreamProbeIntegration:
    def test_valid_mp3_stream(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/valid.mp3")
        assert result.status == ProbeStatus.VALID
        assert result.icy_name == "Test Radio"
        assert result.icy_genre == "Rock"
        assert result.icy_metaint > 0
        assert result.supports_metadata is True

    def test_redirect_followed(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/redirect")
        assert result.status == ProbeStatus.VALID

    def test_404_returns_invalid(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/not-found")
        assert result.status == ProbeStatus.INVALID
        assert "404" in result.error

    def test_500_returns_invalid(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/server-error")
        assert result.status == ProbeStatus.INVALID

    def test_unsupported_content_type(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/unsupported.mp4")
        assert result.status == ProbeStatus.UNSUPPORTED

    def test_empty_audio_returns_valid(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/empty-audio")
        assert result.status == ProbeStatus.VALID
        assert result.icy_name == "Empty Radio"

    def test_cancellation_works(self, server):
        svc = StreamProbeService()
        cancelled = False

        def cancel():
            return cancelled

        cancelled = True
        result = svc.probe(f"http://127.0.0.1:{server}/valid.mp3", cancel_token=cancel)
        assert result.status == ProbeStatus.CANCELLED

    def test_probe_invalid_url(self, server):
        svc = StreamProbeService()
        result = svc.probe("not-a-url")
        assert result.status in (ProbeStatus.ERROR, ProbeStatus.INVALID)

    def test_latency_measured(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/valid.mp3")
        assert result.latency_ms > 0

    def test_content_type_detected(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/valid.mp3")
        assert result.content_type == "audio/mpeg"
        assert result.codec == "MP3"

    def test_icy_headers_parsed(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/valid.mp3")
        assert result.icy_name == "Test Radio"
        assert result.icy_genre == "Rock"
        assert result.metadata.icy_br == "128"

    def test_malformed_metadata_does_not_crash(self, server):
        svc = StreamProbeService()
        result = svc.probe(f"http://127.0.0.1:{server}/malformed-metadata")
        assert result.status == ProbeStatus.VALID

    def test_no_network_access_outside_local(self):
        svc = StreamProbeService()
        result = svc.probe("http://127.0.0.1:1/stream")
        assert result.status in (ProbeStatus.ERROR, ProbeStatus.TIMEOUT)
