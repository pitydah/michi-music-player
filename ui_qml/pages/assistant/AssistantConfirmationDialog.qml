import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool visible: false

    signal confirmed()
    signal cancelled()

    anchors.fill: parent
    visible: root.visible
    z: 10000

    Accessible.role: Accessible.Dialog
    Accessible.name: "Confirmar acción" + (destructive ? " - Acción destructiva" : "")
    Accessible.description: actionDescription

    Keys.onEscapePressed: root.cancelled()

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        opacity: 0.8

        MouseArea {
            anchors.fill: parent
            onClicked: root.cancelled()
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 400
        implicitHeight: dialogColumn.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
        focus: true

        Keys.onEscapePressed: root.cancelled()

        Column {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Text {
                width: parent.width
                text: root.destructive ? "⚠ Acción destructiva" : "Confirmar acción"
                color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.actionDescription || root.actionName
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Repeater {
                model: root.affectedItems
                visible: root.affectedItems.length > 0

                Rectangle {
                    width: parent.width
                    height: 28
                    radius: MichiTheme.radiusXs
                    color: MichiTheme.colors.surfaceSubtle

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight
                        width: parent.width - MichiTheme.spacing.md
                    }
                }
            }

            Text {
                width: parent.width
                text: "¿Estás seguro?"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                layoutDirection: Qt.RightToLeft

                MichiButton {
                    text: root.destructive ? "Eliminar" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    objectName: "confirmationDialogConfirm"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirmed()
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "confirmationDialogCancel"
                    Accessible.name: "Cancelar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.cancelled()
                }
            }
        }
    }
}
