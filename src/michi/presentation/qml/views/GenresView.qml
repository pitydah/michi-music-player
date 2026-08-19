import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: genresList
    objectName: "genresView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.genres
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: genresList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.name + " · " + modelData.trackCount + " tracks"
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
