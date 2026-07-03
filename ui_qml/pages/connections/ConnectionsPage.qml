import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Servidores y conexiones"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            MicroServerHero {
                id: microHero
                width: parent.width
                state: "not_configured"
                onScanClicked: {
                    if (typeof connectionsBridge !== "undefined" && connectionsBridge)
                        connectionsBridge.scanForServers()
                }
                onManualAddClicked: {
                    if (typeof connectionsBridge !== "undefined" && connectionsBridge)
                        connectionsBridge.addManualServer()
                }
            }

            SectionHeader {
                text: "Servidores externos"
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: typeof connectionsBridge !== "undefined" && connectionsBridge
                           ? connectionsBridge.externalServers : []

                    ExternalServerCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2
                        height: 80
                        serverName: modelData.name || "Servidor externo"
                        serverType: modelData.serverType || modelData.apiType || "API"
                    }
                }
            }

            NetworkDiscoveryPanel {
                id: discoveryPanel
                width: parent.width
                discoveredServers: []
            }

            HomeAudioAccess {
                width: parent.width
                onOpenHomeAudio: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home_audio")
                }
            }
        }
    }
}
