import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "."

Item {
    objectName: "connectionsPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Servidores y conexiones"

    property var conn: typeof connectionsBridge !== "undefined" ? connectionsBridge : null

    MichiResponsive { id: responsive; availableWidth: root.width }

    Component.onCompleted: {
        if (root.conn && typeof root.conn.refresh !== "undefined")
            root.conn.refresh()
        connectionGuard.checkCapability(root.conn)
    }

    CapabilityGuard {
        id: connectionGuard
        anchors.fill: parent
        capabilityName: "connections_michilink"

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: responsive.pageMargin
            contentHeight: column.height + MichiTheme.spacing.xl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.md

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
                    activeFocusOnTab: true
                    KeyNavigation.tab: externalHeader
                    KeyNavigation.backtab: flickable
                    Keys.onReturnPressed: onScanClicked()
                    Keys.onSpacePressed: onScanClicked()
                }

                SectionHeader {
                    id: externalHeader
                    text: "Servidores externos"
                    width: parent.width
                }

                Flow {
                    id: externalGrid
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.conn ? root.conn.externalServers : []

                        ExternalServerCard {
                            width: responsive.compact ? parent.width
                                 : responsive.medium ? (parent.width - MichiTheme.spacing.md) / 2
                                                     : (parent.width - MichiTheme.spacing.md * 2) / 3
                            height: 80
                            serverName: modelData.name || "Servidor externo"
                            serverType: modelData.serverType || modelData.apiType || "API"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
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
                    activeFocusOnTab: true
                    KeyNavigation.tab: homeAudioAccess
                    KeyNavigation.backtab: externalGrid
                    Keys.onReturnPressed: onServerSelected(0)
                    Keys.onSpacePressed: onServerSelected(0)
                }

                HomeAudioAccess {
                    id: homeAudioAccess
                    width: parent.width
                    activeFocusOnTab: true
                    KeyNavigation.backtab: discoveryPanel
                    Keys.onReturnPressed: onOpenHomeAudio()
                    Keys.onSpacePressed: onOpenHomeAudio()
                    onOpenHomeAudio: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }
            }
        }
    }
}
