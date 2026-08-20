import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    cellWidth: MichiThemeState.density === "compact" ? 144 : 180
    cellHeight: MichiThemeState.density === "compact" ? 184 : 224
    clip: true
    delegate: AlbumCard {
        required property var modelData
        width: albumGrid.cellWidth - MichiSpacing.sm
        height: albumGrid.cellHeight - MichiSpacing.sm
        album: modelData
        onActivated: library.select_album(modelData.key)
    }
}
