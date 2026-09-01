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
        title: modelData.title
        artist: modelData.artist
        album: modelData.album
        durationMs: modelData.durationMs
        quality: modelData.qualityLabel
        playing: playback.currentPath === modelData.path
        favorite: library.favoritePaths.indexOf(modelData.path) !== -1
        showFavorite: true
        onActivated: library.activate_path(modelData.path)
        onFavoriteToggled: library.toggle_favorite(modelData.path)
    }
}
