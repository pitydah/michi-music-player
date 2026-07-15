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

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro?"
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
<<<<<<< Updated upstream
    property string iconText: ""
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
    property bool open: false
    property bool destructive: false

    signal confirmed()
    signal cancelled()

    objectName: "ConfirmationDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: message

    visible: open

    ConfirmDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        iconType: root.destructive ? "error" : root.iconText ? "warning" : "info"
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
        width: Math.min(380, parent.width * 0.9)
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        z: 9991

        focus: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: root.title
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Text {
                text: root.message
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }

            Item { height: 1; Layout.fillWidth: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                CheckBox {
                    id: dontAskCheck
                    text: "No volver a preguntar"
                    checked: root.dontAskAgain
                    visible: root.showDontAskAgain
                    font.pixelSize: MichiTheme.typography.captionSize
                    Layout.fillWidth: true
                    onCheckedChanged: {
                        root.dontAskAgain = checked
                        root.dontAskAgainChanged(checked)
                    }
                    KeyNavigation.tab: cancelBtn
                }

                Item { Layout.fillWidth: !dontAskCheck.visible }

                MichiButton {
                    id: cancelBtn
                    text: root.cancelText
                    variant: "ghost"
                    onClicked: {
                        root.open = false
                        root.cancelled()
                    }
                    KeyNavigation.tab: confirmBtn
                    KeyNavigation.backtab: dontAskCheck.visible ? dontAskCheck : confirmBtn
                }

                MichiButton {
                    id: confirmBtn
                    text: root.confirmText
                    variant: "primary"
                    onClicked: {
                        root.open = false
                        root.confirmed()
                    }
                    KeyNavigation.backtab: cancelBtn
                }
            }
=======
    property string iconText: ""
    property bool open: false
    property bool destructive: false

    signal confirmed()
    signal cancelled()

    objectName: "ConfirmationDialog"

    Accessible.role: Accessible.Dialog
    Accessible.name: title
    Accessible.description: message

    visible: open

    ConfirmDialog {
        id: inner
        titleText: root.title
        message: root.message
        confirmText: root.confirmText
        cancelText: root.cancelText
        iconType: root.destructive ? "error" : root.iconText ? "warning" : "info"
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
