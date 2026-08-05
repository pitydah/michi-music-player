# -*- coding: utf-8 -*-
"""Contract tests for the PresentationPreviewProvider demo-data adapter."""

import sys

import pytest

from tools.presentation_preview.provider import PresentationPreviewProvider


def test_provider_defaults_to_empty_snapshot() -> None:
    """Without fixtures the provider exposes empty read-only collections."""
    provider = PresentationPreviewProvider()
    assert provider.albums == []
    assert provider.artists == []
    assert provider.tracks == []
    assert provider.playlists == []
    assert provider.is_active() is True


def test_provider_exposes_fixture_collections() -> None:
    """The provider surfaces each fixture collection through its adapters."""
    from tools.presentation_preview.fixtures import (
        DEMO_ALBUMS,
        DEMO_ARTISTS,
        DEMO_PLAYLISTS,
        DEMO_TRACKS,
    )

    fixtures = {
        "albums": list(DEMO_ALBUMS),
        "artists": list(DEMO_ARTISTS),
        "playlists": list(DEMO_PLAYLISTS),
        "tracks": list(DEMO_TRACKS),
    }
    provider = PresentationPreviewProvider(fixtures)
    assert provider.albums == DEMO_ALBUMS
    assert provider.artists == DEMO_ARTISTS
    assert provider.playlists == DEMO_PLAYLISTS
    assert provider.tracks == DEMO_TRACKS


def test_provider_ignores_unknown_fixture_keys() -> None:
    """Unknown collections in the snapshot are not exposed as adapters."""
    provider = PresentationPreviewProvider({"unknown": [{"x": 1}]})
    assert provider.albums == []
    assert provider.is_active() is True


def test_provider_snapshot_is_isolated_from_mutation() -> None:
    """Input and returned collection mutations cannot alter provider state."""
    fixtures = {"albums": [{"title": "Original", "tags": ["demo"]}]}
    provider = PresentationPreviewProvider(fixtures)

    fixtures["albums"][0]["title"] = "Changed input"
    exposed = provider.albums
    exposed[0]["title"] = "Changed output"
    exposed[0]["tags"].append("mutated")
    exposed.append({"title": "Injected"})

    assert provider.albums == [{"title": "Original", "tags": ["demo"]}]


def test_bootstrap_exposes_provider_only_when_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bootstrap wires the provider lazily inside the gated hook."""
    import core.application_bootstrap as ab

    bootstrap = ab.ApplicationBootstrap()
    assert bootstrap._presentation_provider is None

    monkeypatch.setattr(ab, "PRESENTATION_PREVIEW", True)
    assert bootstrap._enable_presentation_preview() is True
    provider = bootstrap._presentation_provider
    assert isinstance(provider, PresentationPreviewProvider)
    assert provider.is_active() is True
    assert provider.albums and provider.tracks
    assert "tools.presentation_preview.provider" in sys.modules
