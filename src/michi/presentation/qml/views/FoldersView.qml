import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

ListView {
    id: root
    objectName: "foldersView"

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: library.folders
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds

    delegate: MichiEntityRow {
        required property var modelData
        width: root.width
        iconName: "folder"
        title: modelData.path
        technical: modelData.trackCount + " tracks"
        interactive: false
    }
}
