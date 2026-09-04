"""M9-R3 CONTEXTUAL ACTION RECOVERY — productive-consumer gates.

The historical tests accepted "any play/open token" as proof of context
support and declared Vinyl/Timeline "passive" despite their specialized
context components existing. These gates require the ACTUAL contextual
consumer per projection plus the fail-closed capability policy:

- every album projection consumes AlbumContextArea (pointer right-click)
  and MagazineView additionally routes keyboard roving (Menu/Shift+F10)
  through ONE root AlbumContextMenu with canonical offsets;
- "Add Artist to Playlist" stays fail-closed (canAddToPlaylist false)
  until PR D installs the shared playlist-target host;
- Album menu batch actions stay capability-gated (never inferred from
  signal existence);
- Genre navigation uses the identity key (never a display-name search);
- Favorites/History/Recently Added keep Add-to-Playlist hidden (routed
  only in Songs via the PR #231 picker seam).
"""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_album_context_area_consumed_by_all_six_album_projections() -> None:
    """Las SEIS proyecciones de álbum consumen AlbumContextArea — el
    right-click productivo no es un token suelto de play/open."""
    for view in (
        "media/AlbumCard.qml",
        "media/MichiAlbumRow.qml",
        "views/AlbumPathView.qml",
        "views/VinylWallView.qml",
        "views/TimelineView.qml",
        "views/MagazineView.qml",
    ):
        assert "AlbumContextArea" in _qml(view), view


def test_magazine_has_pointer_and_keyboard_context_with_canonical_offsets() -> None:
    """MagazineView: áreas pointer en hero/medium/compact, menú raíz ÚNICO
    para teclado, y mapa de índices canónico (hero 0 · medium i+1 ·
    compact i+3 · archive i+7) — sin offsets inventados."""
    magazine = _qml("views/MagazineView.qml")
    assert magazine.count("AlbumContextArea") >= 3, (
        "hero + medium + compact con contexto pointer"
    )
    assert 'objectName: "magazineRovingContextMenu"' in magazine
    assert "AlbumContextMenu {\n        id: magazineContextMenu" in magazine
    assert "function albumAtRovingIndex()" in magazine
    assert "function openRovingContext()" in magazine
    assert "function handleContextKey(event)" in magazine
    assert "Keys.onPressed: event => root.handleContextKey(event)" in magazine
    # Offsets canónicos contra los slices reales.
    assert "root.selectEditorial(0, root.heroAlbum.key)" in magazine
    assert "root.selectEditorial(index + 1, modelData.key)" in magazine
    assert "root.selectEditorial(index + 3, modelData.key)" in magazine
    assert "archiveDelegate.index + 7" in magazine
    assert "archiveDelegate.index * 2 + index + 7" in magazine
    # Menú raíz: el teclado NUNCA toca delegates privados (un solo menú).
    assert magazine.count("AlbumContextMenu {") == 1, (
        "un solo menú raíz para el roving keyboard"
    )


def test_magazine_context_selects_target_before_menu() -> None:
    """SELECT-BEFORE-MENU: cada ruta de contexto establece el target
    (selectEditorial / forceActiveFocus) ANTES del popup."""
    magazine = _qml("views/MagazineView.qml")
    hero = magazine[
        magazine.index("id: heroContext") : magazine.index("id: medContext")
    ]
    assert "root.selectEditorial(0, root.heroAlbum.key)" in hero
    assert "albumMagazine.forceActiveFocus()" in hero
    medium = magazine[
        magazine.index("id: medContext") : magazine.index("id: compContext")
    ]
    assert "root.selectEditorial(index + 1, modelData.key)" in medium
    assert "medFeature.forceActiveFocus()" in medium
    compact = magazine[
        magazine.index("id: compContext") : magazine.index(
            "// Section header for Archive"
        )
    ]
    assert "root.selectEditorial(index + 3, modelData.key)" in compact
    assert "compactFeature.forceActiveFocus()" in compact
    # Keyboard: el select ocurre DENTRO de openRovingContext antes del popup.
    roving = magazine[
        magazine.index("function openRovingContext()") : magazine.index(
            "function handleContextKey(event)"
        )
    ]
    assert roving.index("root.selectEditorial(") < roving.index("popup()")


def test_artist_add_to_playlist_is_fail_closed() -> None:
    """'Add Artist to Playlist' requiere canAddToPlaylist (default false):
    no se muestra porque exista el signal del Bridge. Ningún surface
    productivo la activa hasta PR D."""
    menu = _qml("media/ArtistContextMenu.qml")
    assert "property bool canAddToPlaylist: false" in menu
    assert "visible: root.artist !== null && root.canAddToPlaylist" in menu
    assert "library.canAddTracksToPlaylists" in menu
    area = _qml("media/ArtistContextArea.qml")
    assert "property bool canAddToPlaylist: false" in area
    assert "canAddToPlaylist: root.canAddToPlaylist" in area
    # Ningún productivo activa la capacidad (fail-close hasta PR D).
    for qml_file in Path(QML).rglob("*.qml"):
        if qml_file.name in ("ArtistContextArea.qml", "ArtistContextMenu.qml"):
            continue
        src = qml_file.read_text(encoding="utf-8", errors="ignore")
        if "ArtistContextArea" in src or "ArtistContextMenu" in src:
            assert "canAddToPlaylist: true" not in src, (
                f"{qml_file.name} activa Add Artist a Playlist sin consumer"
            )


def test_album_menu_batch_actions_require_explicit_capability() -> None:
    """Open/Play/Queue son reales; Add/Create/Properties NUNCA se infieren
    de la existencia del signal — capacidad explícita + canAddTracks."""
    menu = _qml("media/AlbumContextMenu.qml")
    assert "visible: root.album !== null && root.canAddToPlaylist" in menu
    assert "&& library.canAddTracksToPlaylists" in menu
    assert "visible: root.album !== null && root.canCreatePlaylist" in menu
    assert "visible: root.album !== null && root.canShowProperties" in menu
    assert "property bool canAddToPlaylist: false" in menu
    assert "property bool canCreatePlaylist: false" in menu
    assert "property bool canShowProperties: false" in menu
    # Open/Play reales incondicionales al álbum.
    assert 'text: qsTr("Open Album")' in menu
    assert 'text: qsTr("Play Album")' in menu


def test_genre_context_uses_identity_key_never_search() -> None:
    """Género: exact identity navigation — select_genre(key). Prohibido
    search(name) como sustituto de entidad exacta."""
    genres = _qml("views/GenresView.qml")
    assert "library.select_genre(modelData.key)" in genres
    assert "GenreContextArea" in genres
    assert "library.search(modelData.name)" not in genres
    # GenreContextArea NO ejecuta select_genre (responsabilidad del host/
    # menú): consume el menú especializado y traduce pointer/teclado.
    area = _qml("media/GenreContextArea.qml")
    assert "GenreContextMenu" in area, "el área consume el menú de género"
    assert "Qt.Key_Menu" in area, "Menu key"
    assert "Qt.Key_F10" in area, "Shift+F10"
    assert "function openMenu()" in area
    assert "Qt.RightButton" in area, "right-click real del área"


def test_favorites_history_recently_added_keep_add_to_playlist_hidden() -> None:
    """Estos hosts no activan showAddToPlaylist: el único consumer real de
    single-track add sigue siendo Songs (seam PR #231); el resto espera
    PR D (shared host)."""
    for view in (
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
        "playlists/PlaylistTrackList.qml",
    ):
        assert "showAddToPlaylist: true" not in _qml(view), view


def test_playlist_track_context_queue_is_track_id_first() -> None:
    """PlaylistTrackList: contextual Queue por TrackId cuando el miembro
    está identificado; queue.add_file SOLO para legacy explícito."""
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    assert "library.queue_track_by_id" in playlist_tracks
    # El menú del track de playlist es el especializado.
    assert "PlaylistTrackContextMenu" in playlist_tracks
    # Los hosts de tracks no usan queue.add_many (nunca batch ciego).
    assert "queue.add_many" not in playlist_tracks


def test_context_invocation_has_no_playback_or_toggle_side_effect() -> None:
    """La invocación de contexto (openMenu) nunca dispara play/open —
    revisión de los componentes de área: solo popup del menú."""
    for area in (
        "media/AlbumContextArea.qml",
        "media/ArtistContextArea.qml",
        "media/GenreContextArea.qml",
    ):
        source = _qml(area)
        block = source[
            source.index("function openMenu()") : source.index(
                "function handleContextKey"
            )
        ]
        assert "play_" not in block, area
        assert "select_album(" not in block, area
        assert "activated(" not in block, area
