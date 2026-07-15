import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var qb: null
    property var notif: null
    property var nav: null

    implicitHeight: 36
    objectName: "queue.header"

    RowLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Text {
            id: titleText
            text: "Cola de reproducción"
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            color: MichiTheme.colors.textPrimary
            font.weight: MichiTheme.typography.weightSemiBold
            objectName: "queue.header.title"
            Accessible.role: Accessible.Heading
            Accessible.name: "Cola de reproducción"
        }

        Item { Layout.fillWidth: true }

        Text {
            id: countText
            text: root.qb ? root.qb.queueCount + " pistas" : ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root.qb && root.qb.queueCount > 0
            objectName: "queue.header.count"
            Accessible.name: text
        }

        MichiButton {
            id: clearBtn
            text: "Vaciar"
            variant: "danger"
            visible: root.qb && root.qb.queueCount > 0
            objectName: "queue.header.clear"
            Accessible.name: "Vaciar cola"
            onClicked: {
                if (root.qb) {
                    root.qb.clearQueue()
                    if (root.notif) root.notif.showMessage("Cola vaciada", "info")
                }
            }
        }

        MichiButton {
            id: saveBtn
            text: "Guardar como playlist"
            variant: "ghost"
            visible: root.qb && root.qb.queueCount > 0
            objectName: "queue.header.saveAsPlaylist"
            Accessible.name: "Guardar cola como playlist"
            onClicked: saveDialog.open()
        }
    }

    Dialog {
        id: saveDialog
        title: "Guardar cola como playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        width: 300
        objectName: "queue.saveDialog"

        Accessible.role: Accessible.Dialog
        Accessible.name: "Guardar cola como playlist"

        TextField {
            id: playlistName
            width: parent.width
            placeholderText: "Nombre de la playlist"
            objectName: "queue.saveDialog.nameInput"
            Accessible.name: "Nombre de la playlist"
        }

        onAccepted: {
            if (root.qb && playlistName.text) {
                root.qb.saveAsPlaylist(playlistName.text)
                if (root.notif) root.notif.showMessage("Playlist guardada", "info")
            }
        }
    }
}
