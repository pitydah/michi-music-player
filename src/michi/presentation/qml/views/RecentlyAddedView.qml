import QtQuick
import QtQuick.Layouts
import "../media"

MichiTrackTable {
    id: root
    objectName: "recentlyView"
    property string addTargetTrackId: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    rows: library.recentlyAddedTrackRows
    playingPath: typeof playback !== "undefined" && playback
        ? playback.currentPath : ""
    favoriteTrackIds: library.favoriteTrackIds
    favoritePaths: library.favoritePaths
    canFavorite: true
    canQueue: library.canQueueTracks
    canAddToPlaylist: library.canAddTracksToPlaylists
    canInspect: true
    canNavigateEntities: true
    emptyTitle: qsTr("Nothing added recently")
    emptyMessage: qsTr("Newly imported tracks will appear here.")
    emptyIcon: "recent"

    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    onAddToPlaylistRequested: trackId => root.addTargetTrackId = trackId
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
}
