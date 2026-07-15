import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property real progress: 0.0
    property bool indeterminate: false
    property string statusText: ""
    property bool cancelEnabled: false
    property string cancelText: "Cancelar"
    property string objectName: "progressState"

    signal cancelRequested()

    Accessible.role: Accessible.Panel
    Accessible.name: root.statusText !== "" ? root.statusText : "Progreso"
    Accessible.description: !root.indeterminate ? Math.round(root.progress * 100) + "%" : "Indeterminado"

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.md
        width: Math.min(implicitWidth, 320)

        MichiProgressBar {
            id: progressBar
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            value: root.progress * 100
            indeterminate: root.indeterminate
            accessibleName: root.Accessible.name
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.statusText
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: !root.indeterminate ? Math.round(root.progress * 100) + "%" : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            visible: !root.indeterminate
        }

        MichiButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.cancelText
            variant: "ghost"
            visible: root.cancelEnabled
            onClicked: root.cancelRequested()
        }
    }
}
