import QtQuick
import QtQuick.Layouts
import "../theme"

ListView {
    id: foldersList
    objectName: "foldersView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.folders
    clip: true
    spacing: MichiTheme.space8
    delegate: Text {
        width: foldersList.width
        height: MichiTheme.controlHeightSmall
        verticalAlignment: Text.AlignVCenter
        text: modelData.path + " · " + modelData.trackCount + " tracks"
        font.pixelSize: MichiTheme.fontSizeCaption
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }
}
