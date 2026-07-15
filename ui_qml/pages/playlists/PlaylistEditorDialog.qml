import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int playlistId: -1
    property string playlistName: ""
    property string playlistDescription: ""
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string _coverPath: ""
    property string _validationError: ""
    property bool _hasChanges: false
    property bool _saving: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string coverArt: ""
    property bool _hasChanges: false
    property string _validationError: ""
=======
    property string _coverPath: ""
    property string _validationError: ""
    property bool _hasChanges: false
    property bool _saving: false
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    signal saved(int id, string name)
    signal cancelled()

    title: playlistId >= 0 ? "Editar playlist" : "Nueva playlist"
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    width: 380
    objectName: "playlistEditorDialog"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    objectName: "playlist.editorDialog"
    closePolicy: Dialog.CloseOnEscape

>>>>>>> Stashed changes
    Accessible.role: Accessible.Dialog
    Accessible.name: title
    closePolicy: Popup.CloseOnEscape

    function validate() {
        if (nameInput.text.trim() === "") {
            root._validationError = "El nombre es obligatorio."
            return false
        }
        root._validationError = ""
        return true
    }

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: "Nombre *"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }
        TextField {
            id: nameInput
            width: parent.width
            text: root.playlistName
            placeholderText: "Nombre de la playlist"
            objectName: "editorNameInput"
            Accessible.name: "Nombre de la playlist"
            activeFocusOnTab: true
            onTextChanged: { root._hasChanges = true; root._validationError = "" }
            Keys.onReturnPressed: root.accept()
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
            text: root.playlistDescription
            placeholderText: "Descripción de la playlist"
            objectName: "editorDescriptionInput"
            Accessible.name: "Descripción de la playlist"
            activeFocusOnTab: true
            onTextChanged: root._hasChanges = true
        }

        Text {
            text: "Carátula (opcional)"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }
        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            TextField {
                id: coverInput
                width: parent.width - 80
                placeholderText: "Ruta de imagen o álbum"
                text: root._coverPath
                readOnly: true
                objectName: "editorCoverInput"
                Accessible.name: "Ruta de carátula"
            }
            MichiButton {
                text: "Examinar"
                variant: "secondary"
                objectName: "editorCoverBrowseButton"
                Accessible.name: "Examinar carátula"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: coverDialog.open()
            }
        }

        Text {
            text: root._validationError
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._validationError !== ""
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                text: root._saving ? "Guardando..." : "Guardar"
                variant: "primary"
                enabled: !root._saving
                objectName: "editorSaveButton"
                Accessible.name: "Guardar playlist"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (!root.validate()) return
                    root._saving = true
                    var name = nameInput.text.trim()
                    var desc = descInput.text.trim()
                    if (root.playlistId >= 0) {
                        if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined") {
                            root.bridge.renamePlaylist(root.playlistId, name)
                        }
                        root.saved(root.playlistId, name)
                    } else {
                        if (root.bridge && typeof root.bridge.createPlaylist !== "undefined") {
                            var result = root.bridge.createPlaylist(name)
                            var newId = result && result.id ? result.id : -1
                            root.saved(newId, name)
                        } else {
                            root.saved(-1, name)
                        }
                    }
                    root._saving = false
                    root.close()
                }
            }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                objectName: "editorCancelButton"
                Accessible.name: "Cancelar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { root.reject(); root.close() }
            }
        }
    }

    FileDialog {
        id: coverDialog
        title: "Seleccionar carátula"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp)", "All files (*)"]
        objectName: "editorCoverFileDialog"
        Accessible.name: "Seleccionar carátula"
        onAccepted: {
            root._coverPath = selectedFile.toString().replace("file://", "")
            coverInput.text = root._coverPath
        }
    }

    onOpened: {
        root._validationError = ""
        root._saving = false
        nameInput.text = root.playlistName
        descInput.text = root.playlistDescription
        root._coverPath = ""
        nameInput.selectAll()
        nameInput.forceActiveFocus()
    }

<<<<<<< Updated upstream
=======
    onRejected: root.cancelled()
=======
    width: 380
    objectName: "playlistEditorDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: title
    closePolicy: Popup.CloseOnEscape

    function validate() {
        if (nameInput.text.trim() === "") {
            root._validationError = "El nombre es obligatorio."
            return false
        }
        root._validationError = ""
        return true
    }

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: "Nombre *"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }
        TextField {
            id: nameInput
            width: parent.width
            text: root.playlistName
            placeholderText: "Nombre de la playlist"
            objectName: "editorNameInput"
            Accessible.name: "Nombre de la playlist"
            activeFocusOnTab: true
            onTextChanged: { root._hasChanges = true; root._validationError = "" }
            Keys.onReturnPressed: root.accept()
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
            text: root.playlistDescription
            placeholderText: "Descripción de la playlist"
            objectName: "editorDescriptionInput"
            Accessible.name: "Descripción de la playlist"
            activeFocusOnTab: true
            onTextChanged: root._hasChanges = true
        }

        Text {
            text: "Carátula (opcional)"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }
        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            TextField {
                id: coverInput
                width: parent.width - 80
                placeholderText: "Ruta de imagen o álbum"
                text: root._coverPath
                readOnly: true
                objectName: "editorCoverInput"
                Accessible.name: "Ruta de carátula"
            }
            MichiButton {
                text: "Examinar"
                variant: "secondary"
                objectName: "editorCoverBrowseButton"
                Accessible.name: "Examinar carátula"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: coverDialog.open()
            }
        }

        Text {
            text: root._validationError
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._validationError !== ""
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                text: root._saving ? "Guardando..." : "Guardar"
                variant: "primary"
                enabled: !root._saving
                objectName: "editorSaveButton"
                Accessible.name: "Guardar playlist"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (!root.validate()) return
                    root._saving = true
                    var name = nameInput.text.trim()
                    var desc = descInput.text.trim()
                    if (root.playlistId >= 0) {
                        if (root.bridge && typeof root.bridge.renamePlaylist !== "undefined") {
                            root.bridge.renamePlaylist(root.playlistId, name)
                        }
                        root.saved(root.playlistId, name)
                    } else {
                        if (root.bridge && typeof root.bridge.createPlaylist !== "undefined") {
                            var result = root.bridge.createPlaylist(name)
                            var newId = result && result.id ? result.id : -1
                            root.saved(newId, name)
                        } else {
                            root.saved(-1, name)
                        }
                    }
                    root._saving = false
                    root.close()
                }
            }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                objectName: "editorCancelButton"
                Accessible.name: "Cancelar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { root.reject(); root.close() }
            }
        }
    }

    FileDialog {
        id: coverDialog
        title: "Seleccionar carátula"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp)", "All files (*)"]
        objectName: "editorCoverFileDialog"
        Accessible.name: "Seleccionar carátula"
        onAccepted: {
            root._coverPath = selectedFile.toString().replace("file://", "")
            coverInput.text = root._coverPath
        }
    }

    onOpened: {
        root._validationError = ""
        root._saving = false
        nameInput.text = root.playlistName
        descInput.text = root.playlistDescription
        root._coverPath = ""
        nameInput.selectAll()
        nameInput.forceActiveFocus()
    }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    onClosed: {
        root._saving = false
    }

    QQC2.FocusTrap {
        active: root.opened
        focusItem: nameInput
    }

    Keys.onEscapePressed: { root.reject(); root.close() }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
