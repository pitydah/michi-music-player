"""Contract tests for the Audio Lab hub and route wiring.

These tests keep the Audio Lab integration honest: the central hub owns the
five top-level cards, experimental pages are labelled as such, and every
Audio Lab route remains registered in the navigation layer.
"""


def test_audio_lab_top_level_sections_are_five_and_central():
    from ui.audio_lab.audio_lab_page import _SECTIONS

    keys = [section["key"] for section in _SECTIONS]
    assert keys == [
        "audio_lab_diagnostics",
        "audio_lab_identifier",
        "audio_lab_backup",
        "audio_lab_output",
        "audio_lab_intelligence",
    ]


def test_audio_lab_experimental_sections_are_not_marked_available():
    from ui.audio_lab.audio_lab_page import _SECTIONS

    status_by_key = {section["key"]: section["status"] for section in _SECTIONS}
    assert status_by_key["audio_lab_identifier"] == "experimental"
    assert status_by_key["audio_lab_backup"] == "experimental"
    assert status_by_key["audio_lab_output"] == "experimental"
    assert status_by_key["audio_lab_intelligence"] == "experimental"
    assert status_by_key["audio_lab_diagnostics"] == "proximamente"


def test_audio_lab_routes_are_registered_and_grouped_under_audio_lab():
    from ui.controllers.navigation_controller import (
        NAV_ROUTES,
        SECTION_CONFIG,
        resolve_sidebar_active_key,
    )

    expected = {
        "audio_lab",
        "audio_lab_diagnostics",
        "audio_lab_identifier",
        "audio_lab_backup",
        "audio_lab_output",
        "audio_lab_intelligence",
        "audio_lab_musicbrainz",
        "audio_lab_artwork",
        "audio_lab_lyrics",
        "audio_lab_vinyl_lab",
        "audio_lab_conversion",
        "audio_lab_organize",
        "michi_disc_lab",
        "metadata_editor",
    }

    missing_routes = expected.difference(NAV_ROUTES)
    missing_config = expected.difference(SECTION_CONFIG)
    assert not missing_routes, f"Missing NAV_ROUTES entries: {missing_routes}"
    assert not missing_config, f"Missing SECTION_CONFIG entries: {missing_config}"

    for key in expected - {"audio_lab"}:
        assert resolve_sidebar_active_key(key) == "audio_lab"
