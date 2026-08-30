"""Playlist appearance persistence, asset lifecycle and presentation gates."""

import json
import sqlite3
from pathlib import Path

from PySide6.QtCore import QUrl

from michi.application.navigation_service import NavigationService
from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import (
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
)
from michi.infrastructure.playlist_artwork_store import FilesystemPlaylistArtworkStore
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.playlists_bridge import PlaylistsBridge, local_path_from_url


class MemoryPlaylistsPort:
    def __init__(self, playlists=()) -> None:
        self.items = tuple(playlists)
        self.navigation = PlaylistNavigationState()
        self.save_count = 0

    def load(self):
        return self.items

    def save(self, playlists):
        self.items = tuple(playlists)
        self.save_count += 1

    def load_navigation(self):
        return self.navigation

    def save_navigation(self, state):
        self.navigation = state

    def save_state(self, playlists, navigation):
        # R3-02: atomic compound write (single logical in-memory operation).
        self.items = tuple(playlists)
        self.navigation = navigation
        self.save_count += 1


def test_playlist_appearance_defaults_to_auto() -> None:
    playlist = Playlist(playlist_id="p1", name="Legacy-safe")
    assert playlist.appearance == PlaylistAppearance()
    assert playlist.appearance.hero_mode is PlaylistHeroMode.AUTO
    assert playlist.appearance.hero_image_path == ""


def test_legacy_persistence_loads_auto_without_writeback(tmp_path: Path) -> None:
    db_path = tmp_path / "michi.db"
    legacy_payload = json.dumps(
        [{"id": "p1", "name": "Legacy", "track_paths": ["/a.flac"]}]
    )
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE library_prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
        (legacy_payload,),
    )
    connection.commit()
    connection.close()

    loaded = SqlitePlaylistsRepository(db_path).load()

    assert loaded[0].appearance.hero_mode is PlaylistHeroMode.AUTO
    connection = sqlite3.connect(db_path)
    persisted = connection.execute(
        "SELECT value FROM library_prefs WHERE key = 'playlists'"
    ).fetchone()[0]
    connection.close()
    assert persisted == legacy_payload


def test_all_hero_modes_round_trip_through_sqlite(tmp_path: Path) -> None:
    repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
    appearances = (
        PlaylistAppearance(),
        PlaylistAppearance(
            hero_mode=PlaylistHeroMode.SOLID,
            hero_solid_color="#102030",
        ),
        PlaylistAppearance(
            hero_mode=PlaylistHeroMode.GRADIENT,
            hero_gradient_colors=("#102030", "#405060", "#708090"),
            hero_gradient_angle=225,
        ),
        PlaylistAppearance(
            hero_mode=PlaylistHeroMode.IMAGE,
            hero_image_path="/managed/playlist_p4_hero.webp",
        ),
    )
    repo.save(
        tuple(
            Playlist(playlist_id=f"p{index}", name=f"Mode {index}", appearance=value)
            for index, value in enumerate(appearances, start=1)
        )
    )
    assert tuple(item.appearance for item in repo.load()) == appearances


def test_malformed_appearance_degrades_field_by_field_without_writeback(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "michi.db"
    payload = json.dumps(
        [
            {
                "id": "p1",
                "name": "Tolerant",
                "track_paths": [],
                "appearance": {
                    "hero_mode": "gradient",
                    "hero_solid_color": "not-a-color",
                    "hero_gradient_colors": ["#102030", "broken"],
                    "hero_gradient_angle": float("inf"),
                    "hero_image_path": 42,
                },
            }
        ]
    )
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE library_prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)", (payload,)
    )
    connection.commit()
    connection.close()

    appearance = SqlitePlaylistsRepository(db_path).load()[0].appearance

    assert appearance == PlaylistAppearance(hero_mode=PlaylistHeroMode.GRADIENT)
    connection = sqlite3.connect(db_path)
    stored = connection.execute(
        "SELECT value FROM library_prefs WHERE key = 'playlists'"
    ).fetchone()[0]
    connection.close()
    assert stored == payload


def _real_png(tmp_path: Path, name: str) -> Path:
    """Real decodable PNG — required since asset validation (P1-01)."""
    from PySide6.QtGui import QImage

    img = QImage(64, 64, QImage.Format_RGB32)
    img.fill(0xFF581C)
    path = tmp_path / name
    assert img.save(str(path), "PNG")
    return path


def test_cover_and_hero_workflow_survives_restart_and_resets(tmp_path: Path) -> None:
    db_path = tmp_path / "michi.db"
    store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
    cover_source = _real_png(tmp_path, "cover.png")
    hero_source = _real_png(tmp_path, "hero.png")
    repository = SqlitePlaylistsRepository(db_path)
    service = PlaylistService(playlists_port=repository, artwork_store=store)
    playlist = service.create_playlist("Restart")

    managed_cover = service.set_custom_cover(playlist.playlist_id, cover_source)
    managed_hero = service.set_custom_hero_image(playlist.playlist_id, hero_source)
    restarted = PlaylistService(playlists_port=repository, artwork_store=store)
    persisted = restarted.get_playlist(playlist.playlist_id)
    assert persisted is not None
    assert persisted.custom_cover_path == managed_cover
    assert persisted.appearance.hero_mode is PlaylistHeroMode.IMAGE
    assert persisted.appearance.hero_image_path == managed_hero

    restarted.remove_custom_cover(playlist.playlist_id)
    restarted.set_hero_auto(playlist.playlist_id)
    reset = PlaylistService(
        playlists_port=repository, artwork_store=store
    ).get_playlist(playlist.playlist_id)
    assert reset is not None
    assert reset.custom_cover_path == ""
    assert reset.appearance.hero_mode is PlaylistHeroMode.AUTO
    assert reset.appearance.hero_image_path == ""
    assert not Path(managed_cover).exists()
    assert not Path(managed_hero).exists()


def test_unrelated_mutations_preserve_appearance_metadata() -> None:
    appearance = PlaylistAppearance(
        hero_mode=PlaylistHeroMode.GRADIENT,
        hero_gradient_colors=("#102030", "#405060", "#708090"),
        hero_gradient_angle=45,
    )
    port = MemoryPlaylistsPort(
        [
            Playlist(
                playlist_id="p1",
                name="Original",
                track_paths=("/one.flac", "/two.flac"),
                appearance=appearance,
            )
        ]
    )
    service = PlaylistService(playlists_port=port)

    service.rename_playlist("p1", "Renamed")
    service.add_track("p1", "/three.flac")
    service.move_track("p1", 2, 0)
    service.remove_track("p1", 1)
    service.set_custom_cover("p1", "/cover.jpg")
    service.remove_custom_cover("p1")

    assert service.get_playlist("p1").appearance == appearance


def test_cover_and_hero_assets_are_independent_and_cleaned(tmp_path: Path) -> None:
    store = FilesystemPlaylistArtworkStore(tmp_path / "managed")
    cover_source = _real_png(tmp_path, "cover.png")
    hero_source = _real_png(tmp_path, "hero.png")
    port = MemoryPlaylistsPort([Playlist(playlist_id="p1", name="Visual")])
    service = PlaylistService(playlists_port=port, artwork_store=store)

    cover_path = Path(service.set_custom_cover("p1", cover_source))
    hero_path = Path(service.set_custom_hero_image("p1", hero_source))
    assert cover_path.name.startswith("playlist_p1_")
    assert cover_path.suffix == ".png"
    assert hero_path.name.startswith("playlist_p1_hero_")
    assert hero_path.suffix == ".png"

    service.remove_custom_cover("p1")
    current = service.get_playlist("p1")
    assert not cover_path.exists()
    assert hero_path.exists()
    assert current.appearance.hero_mode is PlaylistHeroMode.IMAGE
    assert current.appearance.hero_image_path == str(hero_path)

    # A non-image hero owns no managed hero file and never recreates cover.
    service.set_hero_solid("p1", "#123456")
    current = service.get_playlist("p1")
    assert not hero_path.exists()
    assert current.custom_cover_path == ""
    assert current.appearance.hero_mode is PlaylistHeroMode.SOLID

    service.set_custom_cover("p1", cover_source)
    replacement_hero = Path(service.set_custom_hero_image("p1", hero_source))
    service.delete_playlist("p1")
    assert not cover_path.exists()
    assert not replacement_hero.exists()


def test_qurl_normalization_is_central_and_rejects_remote_urls(tmp_path: Path) -> None:
    spaced = tmp_path / "my cover.png"
    local_url = QUrl.fromLocalFile(str(spaced))
    assert local_path_from_url(local_url) == spaced
    assert local_path_from_url(local_url.toString()) == spaced
    assert local_path_from_url(str(spaced)) == spaced
    assert local_path_from_url(QUrl("https://example.com/cover.png")) is None


def test_bridge_projects_and_mutates_appearance_without_owning_selection() -> None:
    port = MemoryPlaylistsPort([Playlist(playlist_id="p1", name="Bridge")])
    service = PlaylistService(playlists_port=port)
    navigation = NavigationService()
    navigation.navigate_to_playlist("p1")
    bridge = PlaylistsBridge(service, navigation_service=navigation)
    try:
        assert bridge.set_hero_gradient("p1", ["#102030", "#405060", "#708090"], 405)
        row = bridge.property("playlists")[0]
        selected = bridge.property("selectedPlaylistAppearance")
        assert row["heroMode"] == "gradient"
        assert row["heroGradientAngle"] == 45
        assert selected["heroGradientColors"] == ["#102030", "#405060", "#708090"]
        assert bridge.property("selectedPlaylistId") == "p1"
    finally:
        bridge.dispose()


def test_auto_palette_resets_when_all_artwork_sources_disappear() -> None:
    playlist = Playlist(
        playlist_id="p1", name="Palette", custom_cover_path="/cover.jpg"
    )
    service = PlaylistService(playlists_port=MemoryPlaylistsPort([playlist]))
    bridge = PlaylistsBridge(service)
    try:
        bridge._auto_palettes["p1"] = ["#112233", "#445566", "#778899"]
        bridge._auto_palette_for(playlist, [])
        service.remove_custom_cover("p1")

        colors = bridge._auto_palette_for(service.get_playlist("p1"), [])

        assert "p1" not in bridge._auto_palettes
        assert colors == ["#152A45", "#13243D", "#0A0D14"]
    finally:
        bridge.dispose()


def test_qml_appearance_and_michipeek_contracts() -> None:
    qml = Path("src/michi/presentation/qml")
    card = (qml / "playlists/PlaylistCard.qml").read_text(encoding="utf-8")
    wall = (qml / "views/VinylWallView.qml").read_text(encoding="utf-8")
    panel = (qml / "playlists/PlaylistAppearancePanel.qml").read_text(encoding="utf-8")
    hero = (qml / "playlists/PlaylistHeroBackground.qml").read_text(encoding="utf-8")
    detail = (qml / "playlists/PlaylistDetailView.qml").read_text(encoding="utf-8")
    overview = (qml / "playlists/PlaylistsView.qml").read_text(encoding="utf-8")
    peek = (qml / "playlists/MichiPeek.qml").read_text(encoding="utf-8")
    peek_svg = (qml / "assets/michi-peek.svg").read_text(encoding="utf-8")

    assert "MichiPeek" in card
    assert "vinylDisc" not in card
    assert "vinylDisc" in wall
    assert card.count('iconName: "play"') == 1
    assert "contextMenu.visible" in card
    assert "!MichiAccessibility.reducedMotion" in card
    assert "Layout.preferredWidth: 240" in card
    assert "implicitWidth: 48" in card
    assert 'variant: "primary"' in card
    assert "root.selected && MichiAccessibility.keyboardMode" in card
    assert "implicitWidth: 92" in peek
    assert "implicitHeight: 168" in peek
    assert "Math.min(36, width * 0.37)" in peek
    assert "SequentialAnimation" in peek
    assert 'viewBox="0 0 92 160"' in peek_svg
    assert "<image" not in peek_svg
    assert "metadata" not in peek_svg.lower()
    for mode in ('"auto"', '"solid"', '"gradient"', '"image"'):
        assert mode in panel
        assert mode in hero
    assert "Gradient.Horizontal" in hero
    assert "MichiMaterialTexture" in hero
    assert "signalContour" in hero
    assert 'root.heroMode !== "image"' in hero
    # R2 P2-02: managed hero assets are IMMUTABLE content-addressed
    # candidates — content changes change the URL, so caching is safe.
    assert "cache: true" in hero
    assert panel.count("set_custom_hero_from_url") == 1
    assert "root.draftHeroImageUrl = selectedFile" in panel
    assert "Copying and persistence happen" in panel
    assert "PlaylistAppearancePanel" in detail
    assert "PlaylistAppearancePanel" in overview
    assert "substring(7)" not in detail + overview + panel
    assert "set_custom_cover_from_url" in panel
    assert "formatPlaylistSummary" in card + detail + overview
