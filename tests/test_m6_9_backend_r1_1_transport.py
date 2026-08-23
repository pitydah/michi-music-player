"""M6.9-BACKEND-R1.1 — transport read-failure truth + transient policy.

- response.read() failures (TimeoutError / OSError / IncompleteRead)
  normalize to EnrichmentTransportError and participate in the bounded
  retry policy; the response is closed.
- ONE canonical transient classifier drives retry and OFFline/FAILED
  classification; 404/500 are NOT transient.
"""

import http.client

import pytest

from michi.application.enrichment_ports import (
    EnrichmentHttpStatusError,
    EnrichmentTransportError,
    HttpRequest,
    is_transient_provider_failure,
)
from michi.infrastructure.enrichment_http import (
    ProviderRequestExecutor,
    UrllibHttpTransport,
)


class ReadFailureResponse:
    """Mimics an http.client response whose read() fails."""

    def __init__(self, error):
        self._error = error
        self.status = 200
        self.headers = {}
        self._url = "https://musicbrainz.org/x"
        self.closed = False

    def read(self, size=-1):
        raise self._error

    def getcode(self):
        return 200

    def geturl(self):
        return self._url

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def open(self, req, timeout=None):
        self.calls += 1
        return self._responses.pop(0)


class TestReadFailureNormalization:
    @pytest.mark.parametrize(
        "error",
        [
            TimeoutError("read timeout"),
            OSError("socket closed"),
            http.client.IncompleteRead(b"partial"),
            http.client.HTTPException("connection broken"),
        ],
    )
    def test_read_failures_normalize_to_transport_error(self, error):
        transport = UrllibHttpTransport(opener=FakeOpener([ReadFailureResponse(error)]))
        with pytest.raises(EnrichmentTransportError):
            transport.get(HttpRequest(url="https://musicbrainz.org/x"))

    def test_response_closed_after_read_failure(self):
        response = ReadFailureResponse(TimeoutError("boom"))
        transport = UrllibHttpTransport(opener=FakeOpener([response]))
        with pytest.raises(EnrichmentTransportError):
            transport.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert response.closed is True

    def test_read_retry_then_success(self):
        class FlakyResponse(ReadFailureResponse):
            def __init__(self, error, body=None):
                super().__init__(error)
                self._body = body if body is not None else b"{}"
                self._offset = 0
                self.status = 200

            def read(self, size=-1):
                if self._offset == 0 and self._error is not None:
                    raise self._error
                chunk = self._body[self._offset :]
                self._offset = len(self._body)
                return chunk

        good = FlakyResponse(None)
        transport = UrllibHttpTransport(
            opener=FakeOpener([FlakyResponse(TimeoutError("t")), good])
        )
        executor = ProviderRequestExecutor(transport, sleeper=lambda s: None)
        response = executor.get(HttpRequest(url="https://musicbrainz.org/x"))
        assert response.status_code == 200
        assert response.body == b"{}"

    def test_three_read_failures_final_transport_failure(self):
        transport = UrllibHttpTransport(
            opener=FakeOpener(
                [
                    ReadFailureResponse(TimeoutError("1")),
                    ReadFailureResponse(OSError("2")),
                    ReadFailureResponse(TimeoutError("3")),
                ]
            )
        )
        executor = ProviderRequestExecutor(transport, sleeper=lambda s: None)
        with pytest.raises(EnrichmentTransportError):
            executor.get(HttpRequest(url="https://musicbrainz.org/x"))


class TestCanonicalTransientClassifier:
    def test_transport_error_transient(self):
        assert is_transient_provider_failure(EnrichmentTransportError("x"))

    @pytest.mark.parametrize("status", [429, 502, 503, 504])
    def test_retryable_http_transient(self, status):
        exc = EnrichmentHttpStatusError(status, {}, "x")
        assert is_transient_provider_failure(exc) is True

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 418, 500, 501, 505])
    def test_non_retryable_http_not_transient(self, status):
        exc = EnrichmentHttpStatusError(status, {}, "x")
        assert is_transient_provider_failure(exc) is False

    def test_non_provider_exception_not_transient(self):
        assert is_transient_provider_failure(ValueError("x")) is False
        assert is_transient_provider_failure(RuntimeError("x")) is False
