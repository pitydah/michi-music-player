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
    property string coverArt: ""
    property bool _hasChanges: false
    property string _validationError: ""

    signal saved()
    signal cancelled()

    title: playlistId >= 0 ? "Editar playlist" : "Nueva playlist"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    objectName: "playlist.editorDialog"
    closePolicy: Dialog.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: root.title
    Accessible.description: "Diálogo para " + (root.playlistId >= 0 ? "editar" : "crear") + " playlist"

    Keys.onEscapePressed: {
        if (!root._hasChanges || root._validationError === "") root.reject()
    }

    onOpened: {
        nameInput.text = root.playlistName
        descInput.text = root.playlistDescription
        root._validationError = ""
        root._hasChanges = false
        nameInput.selectAll()
        nameInput.forceActiveFocus()
    }

    FocusScope {
        id: focusTrap
        anchors.fill: parent
        activeFocusOnTab: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md
            width: 340

            Text {
                text: playlistId >= 0 ? "Editar los metadatos de la playlist" : "Crear una nueva playlist"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Text {
                text: "Nombre *"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextField {
                id: nameInput
                width: parent.width
                placeholderText: "Nombre de la playlist"
                onTextChanged: {
                    root._hasChanges = true
                    root._validationError = text.trim() === "" ? "El nombre no puede estar vacío" : ""
                }
                objectName: "playlist.editorDialog.nameInput"
                Accessible.name: "Nombre de la playlist"
                KeyNavigation.tab: descInput
            }

            Text {
                text: "Descripción (opcional)"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            TextArea {
                id: descInput
                width: parent.width
                height: 80
                placeholderText: "Descripción de la playlist"
                onTextChanged: root._hasChanges = true
                objectName: "playlist.editorDialog.descInput"
                Accessible.name: "Descripción de la playlist"
                KeyNavigation.tab: coverBtn
                KeyNavigation.backtab: nameInput
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                visible: root.playlistId >= 0

                Text {
                    text: "Carátula:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                MichiButton {
                    id: coverBtn
                    text: root.coverArt ? "Cambiar" : "Seleccionar"
                    variant: "secondary"
                    onClicked: coverDialog.open()
                    objectName: "playlist.editorDialog.coverBtn"
                    Accessible.name: "Seleccionar carátula"
                    KeyNavigation.tab: okBtn
                    KeyNavigation.backtab: descInput
                }
            }

            InlineValidation {
                text: root._validationError
                visible: root._validationError !== ""
                objectName: "playlist.editorDialog.validation"
            }

            Item { width: 1; height: 1; focus: true }
        }
    }

    FileDialog {
        id: coverDialog
        title: "Seleccionar carátula"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp)", "All files (*)"]
        onAccepted: {
            root.coverArt = selectedFile.toString().replace("file://", "")
        }
    }

    onAccepted: {
        var name = nameInput.text.trim()
        if (!name) {
            root._validationError = "El nombre no puede estar vacío"
            return
        }
        if (root.playlistId >= 0) {
            if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined") {
                root.bridge.renamePlaylist(root.playlistId, name)
            }
        } else {
            if (root.bridge && typeof root.bridge.createPlaylist !== "undefined") {
                root.bridge.createPlaylist(name)
            }
        }
        root.playlistName = name
        root.playlistDescription = descInput.text
        root.saved()
    }

    onRejected: root.cancelled()
}
