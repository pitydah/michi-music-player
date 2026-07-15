import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property var action: null
    property bool destructive: false
    property int affectedCount: 0

    signal confirmTriggered()
    signal rejectTriggered()

    Accessible.role: Accessible.Panel
    Accessible.name: "Vista previa de acción"

    implicitHeight: column.height + MichiTheme.spacing.lg * 2
    visible: root.action !== null

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        variant: root.destructive ? "status" : "base"
        border.color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.borderCard

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: root.action ? root.action.description || root.action.name || "" : ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                    width: parent.width - 80
                }

                StatusBadge {
                    text: root.destructive ? "Destructivo" : "Seguro"
                    kind: root.destructive ? "error" : "success"
                }
            }

            Text {
                text: root.affectedCount > 0 ? root.affectedCount + " elemento(s) afectado(s)" : ""
                color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }

            Text {
                text: root.destructive ? "Esta acción no se puede deshacer. Revisa los cambios antes de confirmar." : "Revisa los cambios antes de confirmar."
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.destructive
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width
                layoutDirection: Qt.RightToLeft

                MichiButton {
                    text: "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    objectName: "assistant.preview.confirm"
                    Accessible.name: "Confirmar acción"
                    Accessible.description: root.destructive ? "Acción destructiva" : ""
                    onClicked: root.confirmTriggered()
                }

                MichiButton {
                    text: "Rechazar"
                    variant: "ghost"
                    objectName: "assistant.preview.reject"
                    onClicked: root.rejectTriggered()
                }
            }
        }
    }
}
