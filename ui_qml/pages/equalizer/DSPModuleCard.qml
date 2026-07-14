import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property string title: ""
    property bool active: false
    property bool available: true
    property var conflicts: []

    implicitHeight: 60

    GlassCard {
        width: parent.width; height: parent.height
        title: root.title
        subtitle: root.available
            ? (root.active ? "Activo" : "Inactivo")
            : "No disponible"
        variant: root.active ? "accent" : root.available ? "base" : "base"

        Row {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: "En conflicto: " + root.conflicts.join(", ")
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root.conflicts.length > 0
                anchors.verticalCenter: parent.verticalCenter
            }

            StatusBadge {
                text: root.available ? (root.active ? "Activo" : "Inactivo") : "No disponible"
                kind: root.available ? (root.active ? "success" : "info") : "disconnected"
            }
        }
    }
}
