import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Assistant Confirmation"
    objectName: "assistantConfirmationDialog"
    focus: true
    id: root

    property string pageState: "LOADING"
    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool dialogVisible: false

    signal confirmed()
    signal cancelled()

    anchors.fill: parent
    visible: root.dialogVisible
    z: 10000
    Component.onCompleted: root.pageState = "READY"

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
        radius: MichiTheme.radius.md
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
                Accessible.role: Accessible.Icon
                Accessible.name: root.destructive ? "Advertencia: Acción destructiva" : "Confirmar acción"
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
                    radius: MichiTheme.radius.xs
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
                    Accessible.role: Accessible.Button

                    text: root.destructive ? "Eliminar" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirmed()
                }

                    Accessible.role: Accessible.Button

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.cancelled()
                }
            }
        }
    }
}
