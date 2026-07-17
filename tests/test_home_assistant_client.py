"""Tests for HomeAssistantClient (QNetworkAccessManager-based)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from integrations.home_assistant.client import HomeAssistantClient


@pytest.fixture
def client():
    return HomeAssistantClient()


class TestHomeAssistantClient:
    def test_configure_sets_url_and_token(self, client):
        client.configure("http://localhost:8123", "test_token_123")
        assert client._base_url == "http://localhost:8123"
        assert client._token == "test_token_123"

    def test_configure_strips_trailing_slash(self, client):
        client.configure("http://localhost:8123/", "tok")
        assert client._base_url == "http://localhost:8123"

    def test_configure_ssl_default_true(self, client):
        assert client._verify_ssl is True

    def test_configure_ssl_false(self, client):
        client.configure("http://localhost:8123", "tok", False)
        assert client._verify_ssl is False

    def test_test_connection_emits_error_when_no_url(self, client):
        result = []
        client.connection_tested.connect(lambda ok, msg: result.append((ok, msg)))
        client.configure("", "tok")
        client.test_connection()
        assert len(result) == 1
        assert result[0][0] is False

    def test_test_connection_emits_error_when_no_token(self, client):
        result = []
        client.connection_tested.connect(lambda ok, msg: result.append((ok, msg)))
        client.configure("http://localhost:8123", "")
        client.test_connection()
        assert len(result) == 1
        assert result[0][0] is False

    @pytest.mark.skip(reason="QNetworkAccessManager is C++ Qt, cannot patch with MagicMock")
    def test_get_creates_request(self, mock_nam, client):
        client.configure("http://localhost:8123", "tok")
        client.test_connection()
        mock_nam.return_value.get.assert_called_once()

    def test_initial_state(self, client):
        assert client._base_url == ""
        assert client._token == ""
