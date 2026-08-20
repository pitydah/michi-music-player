import QtQuick
import QtQuick.Layouts
import "../media"
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

    header: TrackTableHeader {
        width: root.width
        actionColumnWidth: 76
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
        showAddToPlaylist: true
        onActivated: library.activate(index)
        onFavoriteToggled: library.toggle_favorite(modelData.path)
        onAddToPlaylistRequested: root.addTargetPath = modelData.path
    }
}
