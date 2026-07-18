import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue Header"
    objectName: "queueHeader"
    focus: true
    property var qb: null
    property var notif: null
    property var nav: null

    implicitHeight: 36

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Text {
            text: qsTr("Cola de reproducción")
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            color: MichiTheme.colors.textPrimary
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Item { Layout.fillWidth: true }

        Text {
            text: root.qb ? root.qb.queueCount + " pistas" : ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root.qb && root.qb.queueCount > 0
        }

        MichiButton {
            objectName: "clearQueueButton"
            text: qsTr("Vaciar")
            variant: "danger"
            visible: root.qb && root.qb.queueCount > 0
            onClicked: {
                if (root.qb) {
                    root.qb.clearQueue()
                    if (root.notif) root.notif.showMessage("Cola vaciada", "info")
                }
            }
        }

        MichiButton {
            objectName: "saveQueueButton"
            text: qsTr("Guardar como playlist")
            variant: "ghost"
            visible: root.qb && root.qb.queueCount > 0
            onClicked: saveDialog.open()
        }
    }

    Dialog {
        id: saveDialog
        title: qsTr("Guardar cola como playlist")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        width: 300

        TextField {
            focusPolicy: Qt.StrongFocus
            id: playlistName
            width: parent.width
            placeholderText: qsTr("Nombre de la playlist")
        }

        onAccepted: {
            if (root.qb && playlistName.text) {
                root.qb.saveAsPlaylist(playlistName.text)
                if (root.notif) root.notif.showMessage("Playlist guardada", "info")
            }
        }
    }
}
