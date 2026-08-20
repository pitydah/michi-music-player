import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

ListView {
    id: root
    objectName: "albumListView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.albums
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds

    delegate: MichiAlbumRow {
        required property var modelData
        width: root.width
        album: modelData
        onActivated: library.select_album(modelData.key)
    }
}
