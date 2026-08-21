import QtQuick
import QtQuick.Layouts
import "../media"
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

    header: TrackTableHeader {
        width: root.width
        actionColumnWidth: 32
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
