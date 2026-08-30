import QtQuick
import QtQuick.Layouts
import "../media"

MichiTrackTable {
    id: root
    objectName: "songsView"
    property string addTargetTrackId: ""

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
    canInspect: true
    canNavigateEntities: true
    emptyTitle: qsTr("No songs in your library")
    emptyMessage: qsTr("Scan a music folder from the toolbar to populate your library.")
    emptyIcon: "track"

    onTrackActivated: (trackId, path, index) => library.activate_track_by_id(trackId)
    onFavoriteRequested: trackId => library.toggle_favorite_by_id(trackId)
    onQueueRequested: trackId => library.queue_track_by_id(trackId)
    onAddToPlaylistRequested: trackId => root.addTargetTrackId = trackId
    onGoToAlbumRequested: albumKey => library.select_album(albumKey)
    onGoToArtistRequested: artistKey => library.select_artist(artistKey)
    onSortRequested: column => library.sort_tracks(column)
}
