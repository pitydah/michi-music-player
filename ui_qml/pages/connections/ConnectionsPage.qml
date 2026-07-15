import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Servidores y conexiones"

    property var conn: typeof connectionsBridge !== "undefined" ? connectionsBridge : null

    enum State {
        LOADING,
        READY,
        EMPTY,
        ERROR,
        UNAVAILABLE
    }

    property int pageState: root.conn ? ConnectionsPage.READY : ConnectionsPage.UNAVAILABLE

    objectName: "connections.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Servidores y conexiones"
    Accessible.description: "Gestión de servidores, conexiones y detección en red"

    Component.onCompleted: {
        if (root.conn && typeof root.conn.refresh !== "undefined")
            root.conn.refresh()
        connectionGuard.checkCapability(root.conn)
    }

    CapabilityGuard {
        id: connectionGuard
    AsyncStateView {
        anchors.fill: parent
        capabilityName: "connections_michilink"

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Servidores y conexiones"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Servidores y conexiones"
                }

                MicroServerHero {
                    id: microHero
                    width: parent.width
                    objectName: "microServerHero"
                    Accessible.name: "Micro servidor"
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
                    objectName: "externalServersHeader"
                    Accessible.name: "Servidores externos"
                }

                Grid {
                    id: externalGrid
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
                            objectName: "externalServerCard_" + index
                            Accessible.name: modelData.name || "Servidor externo"
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
                        Accessible.name: "No hay servidores externos configurados"
                    }
                }

                NetworkDiscoveryPanel {
                    id: discoveryPanel
                    width: parent.width
                    objectName: "networkDiscoveryPanel"
                    Accessible.name: "Descubrimiento de red"
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

                    ManualConnectionDialog {
                        id: manualDialog
                        objectName: "connections.manualDialog"
                        onConnectRequested: function(host, port, alias) {
                            if (root.conn) root.conn.connectManual(host, port, alias)
                            manualDialog.close()
                        }
                        onCancelRequested: {
                            manualDialog.close()
                        }
                    }

                    SectionHeader {
                        id: externalSection
                        text: "Servidores externos"
                        width: parent.width
                        objectName: "connections.section.externalServers"
                        Accessible.name: "Sección de servidores externos"
                        KeyNavigation.tab: externalGrid
                        KeyNavigation.backtab: microHero
                    }

                    Grid {
                        id: externalGrid
                        width: parent.width
                        columns: 2
                        columnSpacing: MichiTheme.spacing.md
                        rowSpacing: MichiTheme.spacing.md
                        objectName: "connections.grid.externalServers"

                        Repeater {
                            model: root.conn ? root.conn.externalServers : []

                            ExternalServerCard {
                                width: (parent.width - MichiTheme.spacing.md) / 2
                                height: 80
                                serverName: modelData.name || "Servidor externo"
                                serverType: modelData.serverType || modelData.apiType || "API"
                                objectName: "connections.externalServerCard." + index
                                onConfigureClicked: {
                                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                                        navigationBridge.navigateWithParams("connection_detail", {name: modelData.name})
                                }
                            }
                        }

                        Text {
                            text: "No hay servidores externos configurados."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: parent.width
                            wrapMode: Text.WordWrap
                            visible: parent.children.length === 0
                            objectName: "connections.empty.externalServers"
                        }
                    }

                    NetworkDiscoveryPanel {
                        id: discoveryPanel
                        width: parent.width
                        discoveredServers: root.conn ? root.conn.discoveredServers : []
                        objectName: "connections.discoveryPanel"
                        Accessible.name: "Panel de descubrimiento de red"
                        onServerSelected: function(index) {
                            if (root.conn && typeof root.conn.requestPair !== "undefined")
                                root.conn.requestPair(index)
                        }
                        KeyNavigation.tab: homeAudioAccess
                        KeyNavigation.backtab: externalGrid
                    }

                    HomeAudioAccess {
                        id: homeAudioAccess
                        width: parent.width
                        objectName: "connections.homeAudioAccess"
                        Accessible.name: "Acceso a Home Audio"
                        onOpenHomeAudio: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("home_audio")
                        }
                        KeyNavigation.backtab: discoveryPanel
    CapabilityGuard {
        id: connectionGuard
        anchors.fill: parent
        capabilityName: "connections_michilink"

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Servidores y conexiones"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Servidores y conexiones"
                }

                MicroServerHero {
                    id: microHero
                    width: parent.width
                    objectName: "microServerHero"
                    Accessible.name: "Micro servidor"
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
                    objectName: "externalServersHeader"
                    Accessible.name: "Servidores externos"
                }

                Grid {
                    id: externalGrid
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
                            objectName: "externalServerCard_" + index
                            Accessible.name: modelData.name || "Servidor externo"
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
                        Accessible.name: "No hay servidores externos configurados"
                    }
                }

                NetworkDiscoveryPanel {
                    id: discoveryPanel
                    width: parent.width
                    objectName: "networkDiscoveryPanel"
                    Accessible.name: "Descubrimiento de red"
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
                    objectName: "homeAudioAccess"
                    Accessible.name: "Acceso a Home Audio"
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
