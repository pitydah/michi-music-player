import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Popup {
    id: root

    property string folderPath: ""
    property var bridge: null

    signal playRequested()
    signal queueRequested()
    signal openInFilesystemRequested()
    signal rescanRequested()
    signal excludeRequested()

    width: 200
    height: 160
    modal: true

    Column {
        anchors.fill: parent; spacing: 0

        Repeater {
            model: [
                {label: "Reproducir", action: "play"},
                {label: "Añadir a cola", action: "queue"},
                {label: "Abrir en gestor archivos", action: "open"},
                {label: "Reescanear", action: "rescan"},
                {label: "Excluir de biblioteca", action: "exclude"},
            ]

            Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Folder Context Menu"
    objectName: "folderContextMenu"
    focus: true
                width: parent.width; height: 32; color: "transparent"
                Text {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: MichiTheme.spacing.sm
                    text: modelData.label
                    color: modelData.action === "exclude" ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.close()
                        if (modelData.action === "play") root.playRequested()
                        else if (modelData.action === "queue") root.queueRequested()
                        else if (modelData.action === "open") root.openInFilesystemRequested()
                        else if (modelData.action === "rescan") root.rescanRequested()
                        else if (modelData.action === "exclude") root.excludeRequested()
                    }
                }
            }
        }
    }
}
