import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
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

    ScrollBar.vertical: MichiScrollBar { }

    header: EmptyState {
        width: root.width
        height: root.height
        visible: root.count === 0
        title: qsTr("No folders found")
        message: qsTr("Scan a music folder to discover folder navigation.")
        iconName: "folder"
    }

    delegate: MichiEntityRow {
        required property var modelData
        width: root.width
        iconName: "folder"
        title: modelData.path
        technical: modelData.trackCount + " tracks"
        interactive: false
    }
}
