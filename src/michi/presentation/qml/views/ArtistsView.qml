import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: artistsList
    objectName: "artistsView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.artists
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: artistsList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.name + " · " + modelData.trackCount + " tracks · " + modelData.albumCount + " albums"
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
