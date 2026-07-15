import QtQuick
<<<<<<< Updated upstream
import "../theme"
import "dialogs"
=======
<<<<<<< HEAD
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
=======
import "../theme"
import "dialogs"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

Item {
    id: root

    property string title: "Acción destructiva"
    property string message: "Esta acción no se puede deshacer."
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    property string confirmKeyword: ""
>>>>>>> Stashed changes
    property string confirmText: "Eliminar"
    property string cancelText: "Cancelar"
    property string keyword: "ELIMINAR"
    property string keywordPrompt: "Escribe \"" + root.keyword + "\" para confirmar:"
    property bool open: false
<<<<<<< Updated upstream
=======
    property string objectName: "destructiveActionDialog"
=======
    property string confirmText: "Eliminar"
    property string cancelText: "Cancelar"
    property string keyword: "ELIMINAR"
    property string keywordPrompt: "Escribe \"" + root.keyword + "\" para confirmar:"
    property bool open: false
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    signal confirmed()
    signal cancelled()

<<<<<<< Updated upstream
    objectName: "DestructiveActionDialog"
=======
<<<<<<< HEAD
    visible: root.open
    focus: root.open
>>>>>>> Stashed changes

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: message + ". Escribe " + keyword + " para confirmar."

    visible: open

    DestructiveDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        keyword: root.keyword
        open: root.open

        onConfirmed: {
            root.open = false
            root.confirmed()
        }
<<<<<<< Updated upstream
        onCancelled: {
            root.open = false
            root.cancelled()
=======
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(400, parent.width * 0.9)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.error
        z: 9991

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: "\u26A0"
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    color: MichiTheme.colors.error
                }
                Text {
                    text: root.title
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Text {
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Text {
                text: root.affectedCount > 0 ? root.affectedCount + " elemento" + (root.affectedCount !== 1 ? "s" : "") + " afectado" + (root.affectedCount !== 1 ? "s" : "") : ""
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.captionSize
                font.weight: MichiTheme.typography.weightMedium
                visible: root.affectedCount > 0
            }

            Text {
                text: root.confirmKeyword !== "" ? "Escribe \"" + root.confirmKeyword + "\" para confirmar:" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: root.confirmKeyword !== ""
            }

            TextField {
                id: keywordInput
                visible: root.confirmKeyword !== ""
                Layout.fillWidth: true
                placeholderText: root.confirmKeyword
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                focus: true
                KeyNavigation.tab: cancelDlgBtn
            }

            Item { height: 1; Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                Item { Layout.fillWidth: true }

                MichiButton {
                    id: cancelDlgBtn
                    text: root.cancelText
                    variant: "ghost"
                    onClicked: {
                        root.open = false
                        root.cancelled()
                    }
                    KeyNavigation.tab: confirmDlgBtn
                    KeyNavigation.backtab: root.confirmKeyword !== "" ? keywordInput : confirmDlgBtn
                }

                MichiButton {
                    id: confirmDlgBtn
                    text: root.confirmText
                    variant: "danger"
                    enabled: root.confirmKeyword === "" || keywordInput.text === root.confirmKeyword
                    onClicked: {
                        root.open = false
                        root.confirmed()
                    }
                    KeyNavigation.backtab: cancelDlgBtn
                }
            }
=======
    objectName: "DestructiveActionDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: message + ". Escribe " + keyword + " para confirmar."

    visible: open

    DestructiveDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        keyword: root.keyword
        open: root.open

        onConfirmed: {
            root.open = false
            root.confirmed()
        }
        onCancelled: {
            root.open = false
            root.cancelled()
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
