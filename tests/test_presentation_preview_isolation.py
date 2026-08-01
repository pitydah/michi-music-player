# -*- coding: utf-8 -*-
"""Verify presentation preview fixtures never activate in normal runtime."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_flag_absent_by_default():
    """The preview flag is opt-in only — pytest never passes it."""
    assert "--presentation-preview" not in sys.argv


def test_main_defines_flag_gated_by_argv():
    """main.py exposes PRESENTATION_PREVIEW computed exclusively from sys.argv."""
    src = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
    assert 'PRESENTATION_PREVIEW = "--presentation-preview" in sys.argv' in src


def test_fixtures_not_imported_in_runtime():
    """Production bootstrap never imports presentation fixtures at module level.

    The only allowed reference is the lazy import inside the gated hook body.
    """
    import core.application_bootstrap as ab

    src = Path(ab.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        if "tools.presentation_preview" in line:
            assert line.startswith((" ", "\t")), (
                "fixtures import must be lazy (inside the hook), not module-level"
            )
    # The hook is gated by the flag.
    assert "PRESENTATION_PREVIEW" in src


def test_importing_bootstrap_does_not_load_fixtures():
    """Importing the bootstrap in a clean process must not load the fixtures."""
    code = (
        "import sys; import core.application_bootstrap; "
        "sys.exit(1 if 'tools.presentation_preview.fixtures' in sys.modules else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_hook_disabled_without_flag():
    """Without the flag the hook is a no-op and loads nothing."""
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    assert bootstrap._enable_presentation_preview() is False
    assert bootstrap._presentation_fixtures == {}
    assert "tools.presentation_preview.fixtures" not in sys.modules


def test_hook_loads_fixtures_only_when_flag_set(monkeypatch):
    """With the flag on, the hook loads the demo snapshot (never services)."""
    import core.application_bootstrap as ab

    monkeypatch.setattr(ab, "PRESENTATION_PREVIEW", True)
    bootstrap = ab.ApplicationBootstrap()
    assert bootstrap._enable_presentation_preview() is True
    fixtures = bootstrap._presentation_fixtures
    assert set(fixtures) == {"albums", "artists", "playlists", "tracks"}
    assert fixtures["albums"] and fixtures["tracks"]
    # Fixtures are a demo snapshot — never registered as container services.
    assert not any(
        "presentation" in name for name in bootstrap.container.list_services()
    )


def test_fixtures_are_demo_shaped():
    """Fixture dataset is well-formed for the preview harness."""
    from tools.presentation_preview.fixtures import (
        DEMO_ALBUMS,
        DEMO_ARTISTS,
        DEMO_PLAYLISTS,
        DEMO_TRACKS,
    )

    for album in DEMO_ALBUMS:
        assert {"title", "artist", "year", "track_count"} <= album.keys()
    for track in DEMO_TRACKS:
        assert {"title", "artist", "album", "duration_s"} <= track.keys()
    assert all("name" in artist for artist in DEMO_ARTISTS)
    assert all("name" in playlist for playlist in DEMO_PLAYLISTS)
