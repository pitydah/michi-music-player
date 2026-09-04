import QtQuick
import QtQuick.Layouts
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

// HistoryView — playback history. LIB-A §7/24: converged on the shared
// MichiTrackTable authority (una fila/estado/header). El orden por defecto
// preserva la cronología de reproducción (sortingEnabled false).
MichiTrackTable {
    id: root
    objectName: "historyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.historyTrackRows
    playingPath: typeof playback !== "undefined" && playback ? playback.currentPath : ""
    favoriteTrackIds: library.favoriteTrackIds
    favoritePaths: library.favoritePaths
    canFavorite: true
    canQueue: library.canQueueTracks
    canNavigateEntities: true
    sortingEnabled: false
    // LIB-A §30: empty state TRUTH — search vacío ≠ sin historial.
    emptyTitle: library.searchActive ? qsTr("No history items match your search")
        : qsTr("No playback history")
    emptyMessage: library.searchActive
        ? qsTr("Try a different search or clear the current query.")
        : qsTr("Tracks you play will appear here.")
    emptyIcon: "history"

    // TrackId-first (el Bridge resuelve legacy-path:: explícito).
    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
}
