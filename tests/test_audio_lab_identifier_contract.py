"""Contract tests for Identifier area — honesty, no Discogs, no dead buttons."""

import os


class TestIdentifierContract:

    def test_no_discogs_imports(self):
        pages_dir = os.path.join(os.path.dirname(__file__), "..", "ui", "audio_lab")
        violations = []
        for root, _dirs, files in os.walk(os.path.abspath(pages_dir)):
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f)) as fh:
                        content = fh.read()
                    if "discogs" in content.lower():
                        violations.append(os.path.join(root, f))
        assert not violations, f"Discogs references found: {violations}"

    def test_identifier_routes_have_handlers(self):
        from legacy_widgets.ui.controllers.legacy_controllers.navigation_controller import NAV_ROUTES
        identifier_keys = [k for k in NAV_ROUTES
                           if k.startswith("audio_lab_musicbrainz")
                           or k.startswith("audio_lab_artwork")
                           or k.startswith("audio_lab_lyrics")
                           or k == "metadata_editor"]
        for key in identifier_keys:
            method_name = NAV_ROUTES.get(key)
            assert method_name, f"{key} missing from NAV_ROUTES"
            assert hasattr(ui.window.MainWindow, method_name), f"{key} → {method_name} missing"
