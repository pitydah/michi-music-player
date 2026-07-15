import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"

BaseDialog {
    id: root

    property string message: ""
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
    property string iconType: "info"

    property bool showDontAskAgain: false
    property bool dontAskAgain: false

    signal confirmed()
    signal cancelled()

    objectName: "ConfirmDialog"

    Accessible.description: message

    iconText: {
        if (root.iconType === "warning") return "\u26A0"
        if (root.iconType === "error") return "\u26A0"
        return "\u2139"
    }

    titleText: root.titleText || "Confirmar acción"

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

        QQC2.CheckBox {
            id: dontAskCheck
            Layout.fillWidth: true
            visible: root.showDontAskAgain
            text: "No volver a preguntar"
            checked: root.dontAskAgain
            font.pixelSize: MichiTheme.typography.captionSize
            Accessible.role: Accessible.CheckBox
            Accessible.name: "No volver a preguntar"

            onCheckedChanged: root.dontAskAgain = checked

            indicator: Rectangle {
                x: dontAskCheck.leftPadding
                y: dontAskCheck.topPadding + (dontAskCheck.availableHeight - height) / 2
                width: 18; height: 18
                radius: 4
                color: dontAskCheck.checked ? MichiTheme.colors.accentBlue : MichiTheme.colors.surfaceInput
                border.color: dontAskCheck.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard

                Rectangle {
                    anchors.centerIn: parent
                    width: 10; height: 10
                    radius: 2
                    color: MichiTheme.colors.textOnAccent
                    visible: dontAskCheck.checked
                }
            }

            contentItem: Text {
                text: dontAskCheck.text
                font: dontAskCheck.font
                color: MichiTheme.colors.textSecondary
                verticalAlignment: Text.AlignVCenter
                leftPadding: dontAskCheck.indicator.width + dontAskCheck.spacing
            }
        }
    }

    buttonsItem: RowLayout {
        spacing: MichiTheme.spacing.sm
        Layout.alignment: Qt.AlignRight
        property bool confirmEnabled: true

        MichiButton {
            id: cancelBtn
            text: root.cancelText
            variant: "ghost"
            Layout.minimumWidth: 80
            objectName: "confirmDialogCancelButton"
            Accessible.name: root.cancelText
            Accessible.description: "Cancelar acción"
            onClicked: {
                root.open = false
                root.cancelled()
            }
        }

        MichiButton {
            id: confirmBtn
            text: root.confirmText
            variant: root.iconType === "error" ? "danger" : "primary"
            focus: true
            Layout.minimumWidth: 80
            objectName: "confirmDialogConfirmButton"
            Accessible.name: root.confirmText
            Accessible.description: root.confirmText
            onClicked: {
                root.open = false
                root.confirmed()
            }
        }
    }

    onAccepted: root.confirmed()
    onRejected: root.cancelled()
}
