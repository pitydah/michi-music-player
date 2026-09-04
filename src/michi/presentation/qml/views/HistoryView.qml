import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

// HistoryView — Track playback history with intelligent temporal section headers
ListView {
    id: root
    objectName: "historyView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.historyTrackRows
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    headerPositioning: ListView.InlineHeader

    ScrollBar.vertical: MichiScrollBar { }

    header: Item {
        width: root.width
        height: root.count > 0 ? historyTableHeader.implicitHeight : root.height

        TrackTableHeader {
            id: historyTableHeader
            width: parent.width
            actionColumnWidth: 32
            visible: root.count > 0
        }

        EmptyState {
            anchors.fill: parent
            visible: root.count === 0
            title: qsTr("No playback history")
            message: qsTr("Tracks you play will appear here.")
            iconName: "history"
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
        favorite: {
            // M9-R3 CONVERGENCE SEAL: el favorito puede vivir como id
            // canónico (T1), como proyección legacy (legacy-path::<path>)
            // o como path-only (pre-migración) — los tres se chequean.
            if (typeof library === "undefined" || !library)
                return false
            if (modelData.trackId
                    && library.favoriteTrackIds.indexOf(
                        String(modelData.trackId)) !== -1)
                return true
            if (modelData.path) {
                if (library.favoriteTrackIds.indexOf(
                        "legacy-path::" + modelData.path) !== -1)
                    return true
                if (!modelData.trackId
                        && library.favoritePaths.indexOf(
                            modelData.path) !== -1)
                    return true
            }
            return false
        }
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
