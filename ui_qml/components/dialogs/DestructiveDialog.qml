import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../"

BaseDialog {
    id: root

    property string message: ""
    property string confirmText: "Eliminar"
    property string cancelText: "Cancelar"
    property int affectedCount: 0
    property string affectedType: "elementos"
    property string backupSuggestion: ""

    property string keyword: "CONFIRMAR"
    property bool _keywordMatched: false

    signal confirmed()
    signal cancelled()

    objectName: "DestructiveDialog"

    Accessible.description: {
        var desc = message
        if (affectedCount > 0) desc += ". " + affectedCount + " " + affectedType
        desc += ". Esta acción no se puede deshacer. Escribe " + keyword + " para confirmar."
        return desc
    }

    iconText: "\u26A0"
    titleText: "! " + root.titleText || "! Acción destructiva"

    closePolicy: root.CloseOnEscape

    onKeywordChanged: root._updateKeywordMatch()
    on_KeywordMatchedChanged: root._updateConfirmEnabled()

    function _updateConfirmEnabled() {
        buttonsItem.confirmEnabled = root._keywordMatched
    }

    contentItem: ColumnLayout {
        spacing: MichiTheme.spacing.md

        Text {
            Layout.fillWidth: true
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            Accessible.name: root.message
        }

        Text {
            Layout.fillWidth: true
            text: root.affectedCount > 0
                  ? "Afecta a " + root.affectedCount + " " + root.affectedType + "."
                  : ""
            color: MichiTheme.colors.error
            font.pixelSize: MichiTheme.typography.captionSize
            font.weight: MichiTheme.typography.weightMedium
            visible: root.affectedCount > 0
        }

        Rectangle {
    Accessible.role: Accessible.Pane
    focus: true
            Layout.fillWidth: true
            height: 36
            radius: MichiTheme.radiusSm
            color: Qt.rgba(1, 0.44, 0.44, 0.08)
            border.width: 1
            border.color: Qt.rgba(1, 0.44, 0.44, 0.20)
            visible: true

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "\u26A0"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                }

                Text {
                    Layout.fillWidth: true
                    text: "Esta acción no se puede deshacer."
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.weight: MichiTheme.typography.weightMedium
                    wrapMode: Text.WordWrap
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.backupSuggestion
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            visible: root.backupSuggestion !== ""
        }

        Text {
            text: "Escribe \"" + root.keyword + "\" para habilitar la confirmación:"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.captionSize
            font.weight: MichiTheme.typography.weightMedium
        }

        QQC2.TextField {
            Accessible.role: Accessible.EditableText

            Accessible.name: "Campo de texto"

            id: keywordInput
            activeFocusOnTab: true

            Layout.fillWidth: true
            height: MichiTheme.rowHeightComfortable
            placeholderText: root.keyword
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            focus: true
            selectByMouse: true

            Accessible.description: "Escribe " + root.keyword + " para habilitar la confirmación"

            background: Rectangle {
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surfaceInput
                border.width: parent.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
            }

            onTextChanged: {
                root._updateKeywordMatch()
            }

            Keys.onReturnPressed: {
                if (root._keywordMatched) {
                    root.open = false
                    root.confirmed()
                }
            }
            Keys.onEscapePressed: {
                root.open = false
                root.cancelled()
            }
        }
    }

    buttonsItem: RowLayout {
        spacing: MichiTheme.spacing.sm
        Layout.alignment: Qt.AlignRight
            Accessible.role: Accessible.Button

        property bool confirmEnabled: false
            activeFocusOnTab: true


        MichiButton {
            id: cancelBtn
            objectName: "destructiveDialogCancelButton"
            text: root.cancelText
            variant: "ghost"
            Layout.minimumWidth: 80
            Accessible.description: "Cancelar acción destructiva"
            onClicked: {
                root.open = false
            Accessible.role: Accessible.Button

            activeFocusOnTab: true

                root.cancelled()
            }
        }

        MichiButton {
            id: confirmBtn
            objectName: "destructiveDialogConfirmButton"
            text: root.confirmText
            variant: "danger"
            enabled: root._keywordMatched
            focus: false
            Layout.minimumWidth: 80
            Accessible.description: root._keywordMatched
                ? "Confirmar acción destructiva" : "Escribe " + root.keyword + " para habilitar"
            onClicked: {
                root.open = false
                root.confirmed()
            }
        }
    }

    function _updateKeywordMatch() {
        root._keywordMatched = keywordInput.text.trim() === root.keyword
    }

    onAccepted: {
        if (root._keywordMatched) root.confirmed()
    }
    onRejected: root.cancelled()
}
