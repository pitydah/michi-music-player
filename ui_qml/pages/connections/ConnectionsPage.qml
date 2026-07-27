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
    property int pageState: root.conn ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    MichiResponsive { id: responsive; availableWidth: root.width }

    Component.onCompleted: {
        if (root.conn && typeof root.conn.refresh !== "undefined")
            root.conn.refresh()
        connectionGuard.checkCapability(root.conn)
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: qsTr("Cargando conexiones") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: Component {
            UnavailableState {
                width: Math.min(540, root.width * 0.86)
                title: qsTr("Conexiones no disponibles")
                message: qsTr("El servicio de conexiones no está activo. Configúralo para enlazar servidores Subsonic, Navidrome, Jellyfin y dispositivos compatibles.")
                primaryActionText: qsTr("Abrir ajustes")
                onPrimaryActionRequested: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("settings")
                }
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: MichiBanner { message: qsTr("Sin conexiones — configura servidores para conectar tu ecosistema"); kind: "info"; dismissible: false }
    }

    CapabilityGuard {
        id: connectionGuard
        anchors.fill: parent
        capabilityName: "connections_michilink"

        Flickable {
            visible: root.pageState === root.stateReady
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
                    text: qsTr("Servidores y conexiones")
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
                    text: qsTr("Servidores externos")
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
                            Keys.onReturnPressed: clicked()
                            Keys.onSpacePressed: clicked()
                        }
                    }

                    Text {
                        text: qsTr("No hay servidores externos configurados.")
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

                SectionHeader {
                    text: qsTr("Servicios compatibles")
                    width: parent.width
                }

                Text {
                    text: qsTr("Integraciones adicionales planificadas o en desarrollo.")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    width: parent.width
                    wrapMode: Text.WordWrap
                }

                Grid {
                    width: parent.width
                    columns: responsive.compact ? 2 : 4
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 88
                        title: qsTr("Michi Big Server")
                        subtitle: qsTr("Servidor central de biblioteca musical. Protocolo en estabilizacion.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("connections.big_server")
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: qsTr("Planificado")
                            kind: "neutral"
                        }
                    }

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 88
                        title: qsTr("Navidrome")
                        subtitle: qsTr("Servidor musical compatible Subsonic.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("connections.navidrome")
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: qsTr("Planificado")
                            kind: "neutral"
                        }
                    }

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 88
                        title: qsTr("Jellyfin")
                        subtitle: qsTr("Servidor multimedia con streaming de audio.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("connections.jellyfin")
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: qsTr("Planificado")
                            kind: "neutral"
                        }
                    }

                    GlassCard {
                        width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                        height: 88
                        title: qsTr("Home Assistant")
                        subtitle: qsTr("Automatizacion y control por voz. Requiere configuracion.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("connections.home_assistant")
                        }

                        StatusBadge {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: MichiTheme.spacing.sm
                            text: qsTr("Configurar")
                            kind: "warning"
                        }
                    }
                }
            }
        }
    }
}
