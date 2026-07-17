import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Network Discovery"
    objectName: "networkDiscoveryPanel"
    focus: true
    id: root

    property var discoveredServers: []

    signal serverSelected(int index)

    implicitHeight: 300

    GlassMaterial {
        anchors.fill: parent
        variant: "base"
        radius: MichiTheme.radius.md

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Descubrimiento en red"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Servidores Michi detectados en la red local"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.discoveredServers.length > 0
            }

            Repeater {
                model: root.discoveredServers

                DiscoveryResultCard {
                    width: parent.width
                    height: 120
                    serverName: modelData.name || ""
                    serverHost: modelData.host || ""
                    serverType: modelData.type || ""
                    serverStatus: modelData.status || "disconnected"
                    ctaText: "Conectar"
                    onCtaClicked: root.serverSelected(index)
                }
            }

            Text {
                text: "No se encontraron servidores en la red. Asegúrate de que Michi Micro Server esté ejecutándose."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.discoveredServers.length === 0
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }
}
