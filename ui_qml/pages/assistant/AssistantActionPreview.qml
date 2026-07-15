import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property var action: null
    property bool destructive: false
    property bool visible: false

    signal confirm()
    signal reject()

    implicitHeight: visible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.role: Accessible.Dialog
    Accessible.name: "Vista previa de acción" + (destructive ? " - Acción destructiva" : "")
    Accessible.description: actionDescription

    visible: root.visible
    opacity: root.visible ? 1.0 : 0.0
    Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }

    GlassMaterial {
        radius: MichiTheme.radiusMd
        variant: root.destructive ? "danger" : "base"

        Column {
            id: contentColumn
            id: column
    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool visible: false

    signal confirm()
    signal reject()

    implicitHeight: visible ? contentColumn.height + MichiTheme.spacing.xl * 2 : 0
    width: parent ? parent.width : 400

    Accessible.role: Accessible.Dialog
    Accessible.name: "Vista previa de acción" + (destructive ? " - Acción destructiva" : "")
    Accessible.description: actionDescription

    visible: root.visible
    opacity: root.visible ? 1.0 : 0.0
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
                spacing: MichiTheme.spacing.sm
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
                    objectName: "actionPreviewConfirm"
                    Accessible.name: root.destructive ? "Sí, continuar" : "Confirmar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirm()
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "assistant.preview.reject"
                    onClicked: root.rejectTriggered()
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
                    objectName: "actionPreviewConfirm"
                    Accessible.name: root.destructive ? "Sí, continuar" : "Confirmar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirm()
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "actionPreviewReject"
                    Accessible.name: "Cancelar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.reject()
                }
            }
        }
    }
}
