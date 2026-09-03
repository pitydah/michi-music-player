import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

// RecentlyAddedView — Recently imported tracks with temporal section headers
ListView {
    id: root
    objectName: "recentlyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.recentlyAddedTrackRows
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    headerPositioning: ListView.InlineHeader

    ScrollBar.vertical: MichiScrollBar { }

    header: Item {
        width: root.width
        height: root.count > 0 ? recentlyTableHeader.implicitHeight : root.height

        TrackTableHeader {
            id: recentlyTableHeader
            width: parent.width
            actionColumnWidth: 32
            visible: root.count > 0
        }

        EmptyState {
            anchors.fill: parent
            visible: root.count === 0
            title: qsTr("Nothing added recently")
            message: qsTr("Newly imported tracks will appear here.")
            iconName: "recent"
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
        favorite: modelData.trackId
            ? library.favoriteTrackIds.indexOf(modelData.trackId) !== -1
            : library.favoritePaths.indexOf(modelData.path) !== -1
        showFavorite: true
        canQueue: Boolean(modelData.trackId) && library.canQueueTracks
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
