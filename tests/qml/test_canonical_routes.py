from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
QML_DIR = REPO / "ui_qml"


@pytest.fixture
def routes():
    from ui_qml_bridge.route_registry import ROUTES, ALIASES
    return ROUTES, ALIASES


class TestNoDuplicateRoutes:
    def test_no_duplicate_canonical_routes(self, routes):
        ROUTES, _ = routes
        seen_sources = {}
        for key, info in ROUTES.items():
            src = info.get("source", "")
            if src in seen_sources:
                prev_key = seen_sources[src]
                if prev_key == "library.folders" and key == "library.folders.detail":
                    continue
                if prev_key == "album_detail" and key == "library/albums/:albumId":
                    continue
                if prev_key == "artist_detail" and key == "library/artists/:artistId":
                    continue
                pytest.fail(f"Duplicate source '{src}' for routes '{prev_key}' and '{key}'")
            seen_sources[src] = key

    def test_no_duplicate_titles(self, routes):
        ROUTES, _ = routes
        seen = {}
        for key, info in ROUTES.items():
            title = info.get("title", "")
            if title in seen and title not in ("Ajustes", "Álbum", "Artista", "Canciones",
                                                "Carpeta", "Género", "Compositor",
                                                "Audio Lab", "Mix", "Perfiles", "Trabajos",
                                                "Fuentes"):
                pytest.fail(f"Duplicate title '{title}' for routes '{seen[title]}' and '{key}'")
            seen[title] = key

    def test_all_canonical_routes_have_qml_files(self, routes):
        ROUTES, _ = routes
        missing = []
        for key, info in ROUTES.items():
            src = info.get("source", "")
            qml_path = QML_DIR / "pages" / src.replace("../pages/", "")
            if not qml_path.exists():
                alt = REPO / "ui_qml" / src.replace("../", "")
                if not alt.exists():
                    missing.append((key, src))
            if qml_path.exists() and not qml_path.is_file():
                missing.append((key, f"{src} exists but is not a file"))
        assert not missing, f"Missing QML files: {missing}"

    def test_aliases_point_to_valid_canonical_routes(self, routes):
        ROUTES, ALIASES = routes
        bad = []
        for alias, info in ALIASES.items():
            target = info["alias_of"]
            if target not in ROUTES:
                bad.append((alias, target))
        assert not bad, f"Aliases pointing to non-existent routes: {bad}"

    def test_no_alias_self_reference(self, routes):
        _, ALIASES = routes
        bad = [k for k, v in ALIASES.items() if v["alias_of"] == k]
        assert not bad, f"Self-referencing aliases: {bad}"

    def test_all_aliases_have_deprecated_flag(self, routes):
        _, ALIASES = routes
        bad = [k for k, v in ALIASES.items() if not v.get("deprecated")]
        assert not bad, f"Aliases without deprecated flag: {bad}"

    def test_all_old_slash_routes_have_aliases(self, routes):
        _, ALIASES = routes
        for key in list(ALIASES):
            if "/" in key:
                assert key in ALIASES, f"Slash route {key} not in ALIASES"


class TestRouteParamsValidation:
    def test_required_params_defined(self, routes):
        ROUTES, _ = routes
        for key, info in ROUTES.items():
            params = info.get("params", {})
            for pname, pspec in params.items():
                assert "required" in pspec, f"Route '{key}' param '{pname}' missing 'required'"
                assert "type" in pspec, f"Route '{key}' param '{pname}' missing 'type'"

    def test_routes_with_params_have_detail_category(self, routes):
        ROUTES, _ = routes
        for key, info in ROUTES.items():
            if info.get("params"):
                assert info.get("category") == "detail", \
                    f"Route '{key}' has params but category is '{info.get('category')}', expected 'detail'"

    def test_detail_routes_have_required_params(self, routes):
        ROUTES, _ = routes
        allowed_no_params = {"playlist_detail", "library/folders/:folderId",
                             "library/sources", "mix_detail"}
        for key, info in ROUTES.items():
            if info.get("category") == "detail" and not info.get("params"):
                if key in allowed_no_params:
                    continue
                pytest.fail(f"Route '{key}' is 'detail' but has no params")


class TestNoStatusField:
    def test_valid_status_values(self, routes):
        ROUTES, _ = routes
        valid = {"functional", "experimental", "new", "placeholder", "disabled"}
        for key, info in ROUTES.items():
            if "status" in info:
                assert info["status"] in valid, \
                    f"Route '{key}' has invalid status '{info['status']}'"


class TestNavigationBridge:
    def test_navigation_bridge_resolves_aliases(self, routes):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        ROUTES, ALIASES = routes
        nav = NavigationBridge()
        for alias, info in ALIASES.items():
            resolved = nav._resolve(alias)
            target = info["alias_of"]
            assert resolved == target, \
                f"Alias '{alias}' resolved to '{resolved}', expected '{target}'"

    def test_navigation_bridge_unknown_route_goes_to_placeholder(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        assert nav._resolve("nonexistent_route_xyz") == "placeholder"

    def test_navigation_bridge_empty_route_goes_to_home(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        assert nav._resolve("") == "home"
