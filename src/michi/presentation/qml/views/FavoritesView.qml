import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../theme"

ListView {
    id: root
    objectName: "favoritesView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.favoriteTrackRows
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    headerPositioning: ListView.InlineHeader

    ScrollBar.vertical: MichiScrollBar { }

    header: Item {
        width: root.width
        height: root.count > 0 ? favoritesTableHeader.implicitHeight : root.height

        TrackTableHeader {
            id: favoritesTableHeader
            width: parent.width
            actionColumnWidth: 32
            visible: root.count > 0
        }

        EmptyState {
            anchors.fill: parent
            visible: root.count === 0
            title: qsTr("No favorites yet")
            message: qsTr("Tap the heart on any track to save it here.")
            iconName: "heart"
        }
    }

    delegate: TrackRow {
        required property int index
        required property var modelData
        width: root.width
        numberText: String(index + 1)
        trackId: modelData.trackId || ""
        filePath: modelData.path || ""
        title: modelData.title
        artist: modelData.artist
        artistKey: modelData.artistKey || ""
        album: modelData.album
        albumKey: modelData.albumKey || ""
        artworkPath: modelData.artworkPath || ""
        formatKey: modelData.formatKey || "unknown"
        formatLabel: modelData.formatLabel || modelData.qualityLabel || "UNKNOWN"
        durationMs: modelData.durationMs
        quality: modelData.qualityLabel
        playing: playback.currentPath === modelData.path
        favorite: true
        showFavorite: true
        canQueue: Boolean(modelData.trackId)
            && modelData.unavailable !== true
            && library.canQueueTracks
        canGoToAlbum: albumKey.length > 0
        canGoToArtist: artistKey.length > 0
        onActivated: {
            if (modelData.trackId)
                library.activate_track_by_id(modelData.trackId)
            else
                library.activate_path(modelData.path)
        }
        onFavoriteToggled: {
            if (modelData.trackId)
                library.toggle_favorite_by_id(modelData.trackId)
            else
                library.toggle_favorite(modelData.path)
        }
        onQueueRequested: if (modelData.trackId)
            library.queue_track_by_id(modelData.trackId)
        onGoToAlbumRequested: if (albumKey.length > 0)
            library.select_album(albumKey)
        onGoToArtistRequested: if (artistKey.length > 0)
            library.select_artist(artistKey)
    }
}
