import QtQuick
import QtQuick.Layouts
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

// RecentlyAddedView — LIB-A §7/24: converged on the shared MichiTrackTable
// authority. Orden de proyección 'recientes' preservado.
MichiTrackTable {
    id: root
    objectName: "recentlyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.recentlyAddedTrackRows
    playingPath: typeof playback !== "undefined" && playback ? playback.currentPath : ""
    favoriteTrackIds: library.favoriteTrackIds
    favoritePaths: library.favoritePaths
    canFavorite: true
    canQueue: library.canQueueTracks
    canNavigateEntities: true
    sortingEnabled: false
    // LIB-A §30: empty state TRUTH.
    emptyTitle: library.searchActive
        ? qsTr("No recently added tracks match your search")
        : qsTr("Nothing added recently")
    emptyMessage: library.searchActive
        ? qsTr("Try a different search or clear the current query.")
        : qsTr("Tracks you add to your library will appear here.")
    emptyIcon: "recent"

    // TrackId-first (el Bridge resuelve legacy-path:: explícito).
    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
}
