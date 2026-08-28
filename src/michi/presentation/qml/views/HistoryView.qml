import QtQuick
import QtQuick.Layouts
import "../media"

MichiTrackTable {
    id: root
    objectName: "historyView"
    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.historyTrackRows
    playingPath: typeof playback !== "undefined" && playback
        ? playback.currentPath : ""
    favoritePaths: library.favoritePaths
    canFavorite: true
    canQueue: library.canQueueTracks
    canAddToPlaylist: library.canAddTracksToPlaylists
    canInspect: true
    canNavigateEntities: true
    emptyTitle: qsTr("No playback history")
    emptyMessage: qsTr("Tracks you play will appear here.")
    emptyIcon: "history"

    onTrackActivated: (path, _index) => library.activate_path(path)
    onFavoriteRequested: path => library.toggle_favorite(path)
    onQueueRequested: path => library.queue_track(path)
    onAddToPlaylistRequested: path => root.addTargetPath = path
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
}
