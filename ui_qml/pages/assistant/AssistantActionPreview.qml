import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Assistant Action Preview"
    objectName: "assistantActionPreview"
    focus: true
    id: root

    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool previewVisible: false

    signal confirm()
    signal reject()

    implicitHeight: previewVisible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.description: actionDescription

    visible: root.previewVisible
    opacity: root.previewVisible ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }

    GlassMaterial {
        radius: MichiTheme.radiusMd
        variant: root.destructive ? "danger" : "base"

        Column {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.destructive ? "⚠" : "▶"
                    color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                Column {
                    width: parent.width - 30
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: root.destructive ? "Acción destructiva" : root.actionName
                        color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    Text {
                        text: root.actionDescription
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.captionSize
                        wrapMode: Text.WordWrap
                        width: parent.width
                        visible: root.actionDescription !== ""
                    }
                }
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

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                layoutDirection: Qt.RightToLeft

                MichiButton {
                    id: confirmBtn
                    text: root.destructive ? "Sí, continuar" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirm()
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.reject()
                }
            }
        }
    }
}
