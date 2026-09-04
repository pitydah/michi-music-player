import QtQuick
import QtQuick.Layouts
import "../media"

// POST-MERGE SEMANTIC RECOVERY (P0-03): Songs vuelve a la jerarquía
// premium MichiTrackTable (la tabla compartida con column sizing,
// sorting, artwork, playing state, queue, favorite, playlist, context
// menu, Properties, Go to Artist/Album) en lugar del ListView plano.
// TrackId = identidad · path = ubicación factual · index = proyección.
MichiTrackTable {
    id: root
    objectName: "songsView"
    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.songRows
    playingPath: typeof playback !== "undefined" && playback
        ? playback.currentPath : ""
    favoriteTrackIds: library.favoriteTrackIds
    favoritePaths: library.favoritePaths
    sortingEnabled: true
    sortColumn: library.trackSortColumn
    sortDescending: library.trackSortDescending
    canFavorite: true
    canQueue: library.canQueueTracks
    canAddToPlaylist: library.canAddTracksToPlaylists
    // PR #231 REVIEW SEAL (P1-02): no existe superficie Inspectora
    // productiva en el árbol — NO se ofrece una acción Properties sin
    // resultado observable. Rehabilitar canInspect solo con un consumer.
    canInspect: false
    canNavigateEntities: true
    // LIB-A §30: empty state TRUTH — search/género vacíos ≠ library vacía.
    emptyTitle: library.searchActive ? qsTr("No matching songs")
        : library.genreFilterActive
            ? qsTr("No tracks in %1").arg(library.selectedGenreName)
            : qsTr("No songs in your library")
    emptyMessage: library.searchActive || library.genreFilterActive
        ? qsTr("Try a different search or clear the current query.")
        : qsTr("Scan a music folder from the toolbar to populate your library.")
    emptyIcon: "track"

    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    // PR #231 REVIEW SEAL (P1-01): TrackId = identidad · path = ubicación
    // factual. El seam histórico de Playlists persiste paths canónicos —
    // el picker recibe el PATH factual (nunca el UUID) mientras todas las
    // demás intenciones (activar/favorito/cola) siguen por TrackId.
    onAddToPlaylistRequested: (trackId, path) => root.addTargetPath = path
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
    onSortRequested: column => library.sort_tracks(column)
    // LIB-A §15: dirección explícita del menú del header → aplicación.
    onSortDirectionRequested: (column, descending) =>
        library.set_track_sort(column, descending)
}
