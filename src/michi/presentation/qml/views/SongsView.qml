import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../theme"

ListView {
    id: root
    objectName: "songsView"

    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.songRows
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    headerPositioning: ListView.InlineHeader

    ScrollBar.vertical: MichiScrollBar { }

    header: Item {
        width: root.width
        height: root.count > 0 ? songsTableHeader.implicitHeight : root.height

        TrackTableHeader {
            id: songsTableHeader
            width: parent.width
            actionColumnWidth: 76
            visible: root.count > 0
        }

        EmptyState {
            anchors.fill: parent
            visible: root.count === 0
            title: qsTr("No songs in your library")
            message: qsTr("Scan a music folder from the toolbar to populate your library.")
            iconName: "track"
        }
    }

    delegate: TrackRow {
        required property int index
        required property var modelData
        width: root.width
        numberText: String(index + 1)
        title: modelData.title
        artist: modelData.artist
        album: modelData.album
        durationMs: modelData.durationMs
        quality: modelData.qualityLabel
        artworkPath: modelData.artworkPath || ""
        showArtwork: true
        playing: playback.currentPath === modelData.path
        favorite: library.favoritePaths.indexOf(modelData.path) !== -1
        showFavorite: true
        showAddToPlaylist: true
        onActivated: library.activate(index)
        onFavoriteToggled: library.toggle_favorite(modelData.path)
        onAddToPlaylistRequested: root.addTargetPath = modelData.path
    }
}
