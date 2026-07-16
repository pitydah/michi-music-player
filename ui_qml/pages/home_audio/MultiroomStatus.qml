import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Multiroom Status"
    objectName: "multiroomStatus"
    focus: true
    id: root

    property string zoneId: ""
    property var zoneDevices: []
    property bool syncActive: false

    implicitHeight: childrenRect.height

    GlassMaterial {
        width: parent.width
        height: column.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        variant: "base"

        Column {
            id: column
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: "Estado multiroom"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
                StatusBadge {
                    text: root.syncActive ? "Sincronizado" : "Sin sincronizar"
                    kind: root.syncActive ? "success" : "disconnected"
                }
            }

            Text {
                text: root.zoneDevices.length > 0 ? root.zoneDevices.length + " dispositivo(s) en la zona" : "Sin dispositivos en esta zona"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Repeater {
                model: root.zoneDevices

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    Text {
                        text: modelData.name || "Dispositivo"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width - 100
                        elide: Text.ElideRight
                    }

                    StatusBadge {
                        text: modelData.connected ? "Conectado" : "Desconectado"
                        kind: modelData.connected ? "success" : "disconnected"
                    }
                }
            }
        }
    }
}
