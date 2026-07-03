import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var conn: typeof connectionsBridge !== "undefined" ? connectionsBridge : null

    Component.onCompleted: {
        if (root.conn && typeof root.conn.refresh !== "undefined")
            root.conn.refresh()
    }

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
                state: root.conn ? root.conn.microServerState : "not_configured"
                onScanClicked: {
                    if (root.conn) root.conn.scanForServers()
                }
                onManualAddClicked: {
                    if (root.conn) root.conn.addManualServer()
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
                    model: root.conn ? root.conn.externalServers : []

                    ExternalServerCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2
                        height: 80
                        serverName: modelData.name || "Servidor externo"
                        serverType: modelData.serverType || modelData.apiType || "API"
                    }
                }

                Text {
                    text: "No hay servidores externos configurados."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                    width: parent.width; wrapMode: Text.WordWrap
                    visible: parent.children.length === 0
                }
            }

            NetworkDiscoveryPanel {
                id: discoveryPanel
                width: parent.width
                discoveredServers: root.conn ? root.conn.discoveredServers : []
                onServerSelected: function(index) {
                    if (root.conn && typeof root.conn.requestPair !== "undefined")
                        root.conn.requestPair(index)
                }
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
