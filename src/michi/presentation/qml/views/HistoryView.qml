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
