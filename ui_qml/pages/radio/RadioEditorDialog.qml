import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var stationData: null
    property bool isEditing: root.stationData !== null && root.stationData !== undefined
    property bool _testing: false
    property string _testResult: ""
    property bool _testOk: false

    title: isEditing ? "Editar emisora" : "Añadir emisora"
    modal: true
    width: Math.min(parent.width * 0.85, 480)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    padding: MichiTheme.spacing.lg

    objectName: "radioEditorDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: "Formulario para " + (isEditing ? "editar" : "añadir") + " emisora de radio"

    onOpened: {
        if (root.isEditing) {
            nameField.text = root.stationData.name || ""
            urlField.text = root.stationData.url || ""
            genreField.text = root.stationData.genre || ""
            countryField.text = root.stationData.country || ""
            langField.text = root.stationData.language || ""
        } else {
            nameField.text = ""
            urlField.text = ""
            genreField.text = ""
            countryField.text = ""
            langField.text = ""
        }
        _testResult = ""
        _testOk = false
        nameField.forceActiveFocus()
    }

    onClosed: {
        _testResult = ""
        _testOk = false
    }

    function validateUrl(url) {
        return url.match(/^https?:\/\/.+/i) !== null
    }

    function sanitizeUrl(url) {
        var u = url.trim()
        if (u === "") return ""
        if (!u.match(/^https?:\/\//i)) u = "http://" + u
        return u
    }

    function testConnection() {
        var url = sanitizeUrl(urlField.text)
        if (!validateUrl(url)) {
            _testResult = "URL no válida"
            _testOk = false
            return
        }
        _testing = true
        _testResult = "Probando conexión..."
        _testOk = false
        if (root.rd && typeof root.rd.getMetadata === "function") {
            var result = root.rd.getMetadata(url)
            _testing = false
            if (result && result.ok) {
                _testResult = "Conexión exitosa"
                _testOk = true
            } else {
                _testResult = "Error: " + (result ? result.error : "no se pudo conectar")
                _testOk = false
            }
        } else {
            _testing = false
            _testResult = "Servicio no disponible"
            _testOk = false
        }
    }

    function saveStation() {
        var name = nameField.text.trim()
        var url = sanitizeUrl(urlField.text)
        if (name === "" || url === "") return

        if (root.isEditing) {
            if (root.rd && typeof root.rd.editStation === "function") {
                root.rd.editStation(
                    root.stationData.id || 0,
                    name, url,
                    genreField.text.trim(),
                    countryField.text.trim()
                )
            }
        } else {
            if (root.rd && typeof root.rd.addStation === "function") {
                root.rd.addStation(name, url, genreField.text.trim(), countryField.text.trim())
            }
        }
        root.close()
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.md

        SearchField {
            id: nameField
            width: parent.width
            placeholderText: "Nombre de la emisora"
            onTextChangedByUser: {}
            objectName: "radioEditorDialog.nameField"
            Accessible.name: "Nombre de la emisora"
            KeyNavigation.tab: urlField
        }

        SearchField {
            id: urlField
            width: parent.width
            placeholderText: "URL del stream (http://...)"
            validator: RegExpValidator { regExp: /^(https?:\/\/)?[^\s]+$/ }
            onTextChangedByUser: {
                _testResult = ""
                _testOk = false
            }
            objectName: "radioEditorDialog.urlField"
            Accessible.name: "URL del stream"
            KeyNavigation.tab: genreField
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            Text {
                text: _testResult
                color: _testOk ? MichiTheme.colors.success : MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.captionSize
                anchors.verticalCenter: parent.verticalCenter
                visible: _testResult !== ""
                width: parent.width - 130
                elide: Text.ElideRight
            }

            MichiButton {
                text: _testing ? "Probando..." : "Probar conexión"
                variant: "ghost"
                enabled: !_testing && urlField.text.trim() !== ""
                implicitHeight: 28
                onClicked: testConnection()
                objectName: "radioEditorDialog.testButton"
                Accessible.name: "Probar conexión con la emisora"
            }
        }

        SearchField {
            id: genreField
            width: parent.width
            placeholderText: "Género (opcional)"
            objectName: "radioEditorDialog.genreField"
            Accessible.name: "Género de la emisora"
            KeyNavigation.tab: countryField
        }

        SearchField {
            id: countryField
            width: parent.width
            placeholderText: "País (opcional)"
            objectName: "radioEditorDialog.countryField"
            Accessible.name: "País de la emisora"
            KeyNavigation.tab: langField
        }

        SearchField {
            id: langField
            width: parent.width
            placeholderText: "Idioma (opcional)"
            objectName: "radioEditorDialog.langField"
            Accessible.name: "Idioma de la emisora"
            KeyNavigation.tab: buttonRow
        }

        Row {
            id: buttonRow
            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter
            KeyNavigation.tab: nameField

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                onClicked: root.close()
                objectName: "radioEditorDialog.cancelButton"
                Accessible.name: "Cancelar"
            }

            MichiButton {
                text: root.isEditing ? "Guardar cambios" : "Añadir emisora"
                variant: "primary"
                enabled: nameField.text.trim() !== "" && urlField.text.trim() !== ""
                onClicked: saveStation()
                objectName: "radioEditorDialog.saveButton"
                Accessible.name: root.isEditing ? "Guardar cambios de la emisora" : "Añadir nueva emisora"
            }
        }
    }
}
