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
        title: modelData.title
        artist: modelData.artist
        album: modelData.album
        durationMs: modelData.durationMs
        quality: modelData.qualityLabel
        playing: playback.currentPath === modelData.path
        favorite: true
        showFavorite: true
        onActivated: library.activate_path(modelData.path)
        onFavoriteToggled: library.toggle_favorite(modelData.path)
    }
}
