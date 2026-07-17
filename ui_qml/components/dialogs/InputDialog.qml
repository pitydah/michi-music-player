import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../"

BaseDialog {
    id: root

    property string label: ""
    property string placeholderText: ""
    property string initialText: ""
    property alias text: inputField.text

    property bool required: false
    property string pattern: ""
    property int minLength: 0
    property int maxLength: 0
    property string validationError: ""

    property string confirmText: "Aceptar"
    property string cancelText: "Cancelar"

    signal confirmed()
    signal cancelled()

    objectName: "InputDialog"

    Accessible.description: label + (validationError ? ". Error: " + validationError : "")

    titleText: root.titleText || "Entrada de datos"

    contentItem: ColumnLayout {
        spacing: MichiTheme.spacing.md

        Text {
            id: labelText
            text: root.label
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            visible: root.label !== ""
            Accessible.name: root.label
        }

        QQC2.TextField {
            id: inputField
            Accessible.name: "Campo de texto"

            activeFocusOnTab: true

            Layout.fillWidth: true
            height: MichiTheme.rowHeightComfortable
            placeholderText: root.placeholderText
            text: root.initialText
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            focus: true
            selectByMouse: true
            maximumLength: root.maxLength > 0 ? root.maxLength : 32767

            Accessible.role: Accessible.EditableText
            Accessible.description: validationError || ""

            background: Rectangle {
                radius: MichiTheme.radius.sm
                color: MichiTheme.colors.surfaceInput
                border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                border.color: {
                    if (root.validationError) return MichiTheme.colors.error
                    if (parent.activeFocus) return MichiTheme.colors.borderFocus
                    return MichiTheme.colors.borderCard
                }
            }

            onTextChanged: {
                if (root.validationError) root.validationError = ""
            }

            Keys.onReturnPressed: {
                if (root.validate()) {
                    root.open = false
                    root.confirmed()
                }
            }
            Keys.onEscapePressed: {
                root.open = false
                root.cancelled()
            }
        }

        Text {
            id: errorText
            Layout.fillWidth: true
            text: root.validationError
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            visible: root.validationError !== ""
            Accessible.description: root.validationError
        }
    }

    buttonsItem: RowLayout {
        spacing: MichiTheme.spacing.sm
        Layout.alignment: Qt.AlignRight
        property bool confirmEnabled: !root.validationError
            Accessible.role: Accessible.Button

            activeFocusOnTab: true


        MichiButton {
            id: cancelBtn
            text: root.cancelText
            variant: "ghost"
            Layout.minimumWidth: 80
            onClicked: {
                root.open = false
                root.cancelled()
            Accessible.role: Accessible.Button

            activeFocusOnTab: true

            }
        }

        MichiButton {
            id: confirmBtn
            text: root.confirmText
            variant: "primary"
            focus: true
            enabled: !root.validationError
            Layout.minimumWidth: 80
            Accessible.description: root.validationError || ""
            onClicked: {
                if (root.validate()) {
                    root.open = false
                    root.confirmed()
                }
            }
        }
    }

    function validate() {
        if (root.required && root.text.trim() === "") {
            root.validationError = "Este campo es obligatorio."
            return false
        }
        if (root.minLength > 0 && root.text.length < root.minLength) {
            root.validationError = "Mínimo " + root.minLength + " caracteres."
            return false
        }
        if (root.maxLength > 0 && root.text.length > root.maxLength) {
            root.validationError = "Máximo " + root.maxLength + " caracteres."
            return false
        }
        if (root.pattern !== "") {
            var regex = new RegExp(root.pattern)
            if (!regex.test(root.text)) {
                root.validationError = "El formato no es válido."
                return false
            }
        }
        root.validationError = ""
        return true
    }

    onAccepted: {
        if (root.validate()) root.confirmed()
    }
    onRejected: root.cancelled()
}
