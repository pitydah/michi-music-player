import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Connection Capabilities"
    objectName: "connectionCapabilities"
    focus: true
    id: root

    property var capabilities: []

    implicitHeight: childrenRect.height

    GlassMaterial {
        id: glass
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radius.md
        variant: "base"
        visible: root.capabilities.length > 0

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Text {
                text: "Capacidades del servidor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.capabilities

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    Text {
                        text: modelData.label || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width - 80
                        elide: Text.ElideRight
                    }

                    StatusBadge {
                        text: modelData.enabled ? "Disponible" : "No disponible"
                        kind: modelData.enabled ? "success" : "disconnected"
                    }
                }
            }
        }
    }
}
