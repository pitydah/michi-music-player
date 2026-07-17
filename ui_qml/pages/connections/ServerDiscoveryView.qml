import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Server Discovery View"
    objectName: "serverDiscoveryView"
    focus: true
    id: root

    property var discoveredServers: []
    property bool scanning: false

    signal serverSelected(int index)
    signal scanRequested()
    signal addManualClicked()

    implicitHeight: 300

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: root.scanning ? "Buscando..." : "Buscar servidores"
                variant: "primary"
                enabled: !root.scanning
                onClicked: root.scanRequested()
            }

            MichiButton {
                text: "Agregar manualmente"
                variant: "ghost"
                onClicked: root.addManualClicked()
            }
        }

        GlassMaterial {
            width: parent.width
            height: parent.height - 60
            radius: MichiTheme.radius.md
            variant: "base"

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Servidores detectados"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Repeater {
                    model: root.discoveredServers

                    DiscoveryResultCard {
                        width: parent.width
                        height: 80
                        serverName: modelData.name || modelData.host || ""
                        serverHost: modelData.host || ""
                        serverType: modelData.type || "Michi Micro Server"
                        serverStatus: modelData.status || "detected"
                        ctaText: "Conectar"
                        onCtaClicked: root.serverSelected(index)
                    }
                }

                Text {
                    text: root.scanning ? "Escaneando la red..." : "No se encontraron servidores."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: root.discoveredServers.length === 0 && !root.scanning
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
            }
        }
    }
}
