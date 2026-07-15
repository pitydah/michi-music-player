import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

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
    }

    AsyncStateView {
        anchors.fill: parent
        state: root.pageState

        loadingContent: LoadingState {
            title: "Cargando conexiones"
            message: "Verificando servidores y conexiones de red"
        }

        emptyContent: EmptyState {
            iconText: "!"
            title: "Sin conexiones"
            subtitle: "No se encontraron servidores. Agrega uno manualmente o escanea la red."
            actionText: "Buscar servidores"
            showAction: true
            onActionClicked: {
                if (root.conn) root.conn.scanForServers()
            }
        }

        errorContent: ErrorState {
            title: "Error de conexión"
            message: root.conn ? root.conn.lastError : "No se pudo conectar con el servicio"
            retryText: "Reintentar"
            onRetryRequested: {
                if (root.conn) root.conn.refresh()
            }
        }

        unavailableContent: UnavailableState {
            title: "Conexiones no disponibles"
            message: "El servicio de conexiones no está disponible en este momento."
            explanation: "Michi Micro Server no está configurado o el módulo de conexiones no está activo."
        }

        FocusScope {
            id: focusScope
            anchors.fill: parent
            objectName: "connections.focusScope"
            activeFocusOnTab: true

            Keys.onEscapePressed: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home")
            }

            Flickable {
                id: flickable
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                contentHeight: column.height + MichiTheme.spacing.xxl
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                focus: true
                objectName: "connections.flickableContent"

                Keys.onEscapePressed: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                }

                Column {
                    id: column
                    width: parent.width
                    spacing: MichiTheme.spacing.lg

                    Text {
                        id: pageTitle
                        text: "Servidores y conexiones"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        objectName: "connections.pageTitle"
                        Accessible.role: Accessible.Heading
                        Accessible.name: "Servidores y conexiones"
                    }

                    MicroServerHero {
                        id: microHero
                        width: parent.width
                        state: root.conn ? root.conn.microServerState : "not_configured"
                        objectName: "connections.microServerHero"
                        Accessible.name: "Hero de Micro Servidor"
                        onScanClicked: {
                            if (root.conn) root.conn.scanForServers()
                        }
                        onManualAddClicked: {
                            if (root.conn) manualDialog.open()
                        }
                        KeyNavigation.tab: externalSection
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
                    }
                }
            }
        }
    }
}
