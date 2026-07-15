import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string title: "Confirmar acción"
    property string message: "¿Estás seguro?"
    property string confirmText: "Confirmar"
    property string cancelText: "Cancelar"
    property bool open: false
    property bool showDontAskAgain: false
    property bool dontAskAgain: false
    property string objectName: "confirmationDialog"

    signal confirmed()
    signal cancelled()
    signal dontAskAgainChanged(bool checked)

    visible: root.open
    focus: root.open

    Accessible.role: Accessible.Dialog
    Accessible.name: root.title
    Accessible.description: root.message

    Keys.onEscapePressed: {
        root.open = false
        root.cancelled()
    }
    Keys.onReturnPressed: {
        root.open = false
        root.confirmed()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9990

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.cancelled()
            }
        }
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
                }

                Item { Layout.fillWidth: !dontAskCheck.visible }

                MichiButton {
                    text: root.cancelText
                    variant: "ghost"
                    onClicked: {
                        root.open = false
                        root.cancelled()
                    }
                }

                MichiButton {
                    text: root.confirmText
                    variant: "primary"
                    onClicked: {
                        root.open = false
                        root.confirmed()
                    }
                }
            }
        }
    }
}
