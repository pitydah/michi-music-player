import QtQuick
import QtQuick.Layouts
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

// FavoritesView — LIB-A §7/24: converged on the shared MichiTrackTable
// authority. Orden de proyección de membresía preservado.
MichiTrackTable {
    id: root
    objectName: "favoritesView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.favoriteTrackRows
    playingPath: typeof playback !== "undefined" && playback ? playback.currentPath : ""
    favoriteTrackIds: library.favoriteTrackIds
    favoritePaths: library.favoritePaths
    canFavorite: true
    canQueue: library.canQueueTracks
    canNavigateEntities: true
    sortingEnabled: false
    // LIB-A §30: empty state TRUTH.
    emptyTitle: library.searchActive ? qsTr("No matching favorites")
        : qsTr("No favorites yet")
    emptyMessage: library.searchActive
        ? qsTr("Try a different search or clear the current query.")
        : qsTr("Tap the heart on any track to keep it here.")
    emptyIcon: "heart"

    // TrackId-first (el Bridge resuelve legacy-path:: explícito).
    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
}
