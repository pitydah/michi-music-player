import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

ListView {
    id: root
    objectName: "artistsView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.artists
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds

    delegate: MichiEntityRow {
        required property var modelData
        width: root.width
        iconName: "artist"
        title: modelData.name
        subtitle: modelData.albumCount + " albums"
        technical: modelData.trackCount + " tracks"
        interactive: false
    }
}
