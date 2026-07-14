import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int playlistId: -1
    property string playlistName: ""
    property string playlistDescription: ""
    property bool _hasChanges: false

    signal saved()
    signal cancelled()

    title: playlistId >= 0 ? "Editar playlist" : "Nueva playlist"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2; y: (parent.height - height) / 3

    Column {
        spacing: MichiTheme.spacing.md; width: 320

        Text {
            text: "Nombre"; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }
        TextField {
            id: nameInput; width: parent.width
            text: root.playlistName; placeholderText: "Nombre de la playlist"
            onTextChanged: root._hasChanges = true
        }

        Text {
            text: "Descripción (opcional)"; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize; visible: root.playlistId >= 0
        }
        TextArea {
            id: descInput; width: parent.width; height: 60
            text: root.playlistDescription; placeholderText: "Descripción"
            visible: root.playlistId >= 0
            onTextChanged: root._hasChanges = true
        }
    }

    onAccepted: {
        var name = nameInput.text.trim()
        if (!name) return
        if (root.playlistId >= 0) {
            if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined") {
                root.bridge.renamePlaylist(root.playlistId, name)
            }
        } else {
            if (root.bridge && typeof root.bridge.createPlaylist !== "undefined") {
                root.bridge.createPlaylist(name)
            }
        }
        root.saved()
    }

    onRejected: root.cancelled()
    onOpened: { nameInput.text = root.playlistName; nameInput.selectAll(); nameInput.forceActiveFocus() }
}
