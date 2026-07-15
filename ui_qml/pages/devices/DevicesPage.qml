import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components/states"
import "../../components"
import "."

Item {
    id: root

    property var devicesBridge: typeof window !== "undefined" && window.devicesBridge ? window.devicesBridge : null
    property var deviceSyncService: typeof window !== "undefined" && window.deviceSyncService ? window.deviceSyncService : null

    readonly property bool bridgeAvailable: root.devicesBridge !== null

    objectName: "devices.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Dispositivos y sincronización"
    Accessible.description: "Gestión de dispositivos y sincronización de música"

    Component.onCompleted: {
        if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
            root.devicesBridge.refresh()
    }

    Loader {
        id: stateLoader
        anchors.fill: parent
        objectName: "devices.stateLoader"
    }

    Loader {
        id: contentLoader
        anchors.fill: parent
        objectName: "devices.contentLoader"
    }

    function updateState() {
        if (!root.devicesBridge) {
            stateLoader.setSource("../../components/states/MichiUnavailableState.qml", {
                title: "Servicio no disponible",
                message: "El servicio de dispositivos no está disponible. El puente de sincronización no se ha inicializado.",
                details: "Verifica que SyncManager y DeviceSyncService estén configurados.",
                primaryActionText: "Reintentar",
                objectName: "devices.unavailableState",
                Accessible: {
                    name: "Servicio no disponible",
                    description: "El puente de dispositivos no está disponible"
                }
            })
            stateLoader.item.primaryActionRequested.connect(function() {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("devices.list")
            })
            contentLoader.active = false
            return
        }

        var pgState = root.devicesBridge.pageState || "INITIALIZING"

        switch (pgState) {
            case "UNAVAILABLE":
                stateLoader.setSource("../../components/states/MichiUnavailableState.qml", {
                    title: "Servicio no disponible",
                    message: "El servicio de sincronización no está disponible en este momento.",
                    details: root.devicesBridge.bridgeErrorMessage || "",
                    primaryActionText: "Reintentar",
                    objectName: "devices.unavailableState",
                    Accessible: {
                        name: "Servicio no disponible",
                        description: "El servicio de sincronización no está disponible"
                    }
                })
                stateLoader.item.primaryActionRequested.connect(function() {
                    if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
                        root.devicesBridge.refresh()
                })
                contentLoader.active = false
                break
            case "INITIALIZING":
            case "LOADING":
                stateLoader.setSource("../../components/states/MichiLoadingState.qml", {
                    title: "Cargando dispositivos",
                    message: "Buscando dispositivos y pares en la red...",
                    objectName: "devices.loadingState",
                    Accessible: {
                        name: "Cargando dispositivos",
                        description: "Espera mientras se buscan dispositivos"
                    }
                })
                contentLoader.active = false
                break
            case "ERROR":
                stateLoader.setSource("../../components/states/MichiErrorState.qml", {
                    title: "Error de sincronización",
                    message: root.devicesBridge.bridgeErrorMessage || "Ocurrió un error al cargar los dispositivos.",
                    details: root.devicesBridge.bridgeErrorMessage || "",
                    primaryActionText: "Reintentar",
                    objectName: "devices.errorState",
                    Accessible: {
                        name: "Error de sincronización",
                        description: root.devicesBridge.bridgeErrorMessage || "Ocurrió un error"
                    }
                })
                stateLoader.item.primaryActionRequested.connect(function() {
                    if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
                        root.devicesBridge.refresh()
                })
                contentLoader.active = false
                break
            case "EMPTY":
                stateLoader.active = false
                contentLoader.active = true
                contentLoader.item.emptyVisible = true
                contentLoader.item.contentVisible = false
                break
            case "READY":
                stateLoader.active = false
                contentLoader.active = true
                contentLoader.item.emptyVisible = false
                contentLoader.item.contentVisible = true
                break
            default:
                stateLoader.setSource("../../components/states/MichiLoadingState.qml", {
                    title: "Inicializando...",
                    objectName: "devices.initializingState"
                })
                contentLoader.active = false
        }
    }

    Connections {
        target: root.devicesBridge
        function onStateChanged() {
            root.updateState()
        }
    }

    Component {
        id: contentComponent

        FocusScope {
            id: focusScope
            anchors.fill: parent
            objectName: "devices.focusScope"
            activeFocusOnTab: true
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Contenido de dispositivos"

            property bool emptyVisible: false
            property bool contentVisible: true

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
                objectName: "devices.flickableContent"

                Keys.onEscapePressed: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                }

                Column {
                    id: column
                    width: parent.width
                    spacing: MichiTheme.spacing.lg

                    PageHeader {
                        title: "Dispositivos y sincronización"
                        badgeText: {
                            if (!root.devicesBridge) return ""
                            return root.devicesBridge.serverActive ? "Servidor activo" : "Servidor inactivo"
                        }
                        badgeKind: root.devicesBridge && root.devicesBridge.serverActive ? "active" : "disconnected"
                        width: parent.width
                        objectName: "devices.pageHeader"
                        Accessible.name: "Encabezado de dispositivos"
                    }

                    SyncStatusPanel {
                        id: syncStatus
                        width: parent.width
                        serverActive: root.devicesBridge ? root.devicesBridge.serverActive : false
                        serverPort: root.devicesBridge ? root.devicesBridge.serverPort : 53318
                        peerCount: root.devicesBridge ? root.devicesBridge.peers.length : 0
                        onStartServer: { if (root.devicesBridge) root.devicesBridge.startServer() }
                        onStopServer: { if (root.devicesBridge) root.devicesBridge.stopServer() }
                        objectName: "devices.syncStatusPanel"
                        Accessible.name: "Panel de estado de sincronización"
                    }

                    Text {
                        text: "Nota: La sincronización de video no está soportada. Solo audio."
                        color: MichiTheme.colors.warning
                        font.pixelSize: MichiTheme.typography.captionSize
                        width: parent.width
                        wrapMode: Text.WordWrap
                        leftPadding: MichiTheme.spacing.sm
                        visible: root.devicesBridge && root.devicesBridge.serverActive
                        objectName: "devices.audioOnlyNotice"
                        Accessible.role: Accessible.Alert
                        Accessible.name: "Solo audio"
                        Accessible.description: "La transferencia de video no está soportada. Solo se admiten archivos de audio."
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width
                        visible: root.devicesBridge && root.devicesBridge.serverActive

                        MichiButton {
                            text: "Vincular dispositivo"
                            variant: "primary"
                            onClicked: {
                                if (typeof navigationBridge !== "undefined" && navigationBridge)
                                    navigationBridge.navigate("devices.pair")
                            }
                            objectName: "devices.toolbar.pairButton"
                            Accessible.name: "Vincular nuevo dispositivo"
                            Accessible.description: "Abre la página de vinculación de dispositivos"
                            KeyNavigation.tab: discoverButton
                            KeyNavigation.backtab: syncStatus
                        }

                        MichiButton {
                            id: discoverButton
                            text: "Descubrir dispositivos"
                            variant: "secondary"
                            onClicked: {
                                if (root.devicesBridge && typeof root.devicesBridge.discoverDevices !== "undefined")
                                    root.devicesBridge.discoverDevices()
                            }
                            objectName: "devices.toolbar.discoverButton"
                            Accessible.name: "Descubrir dispositivos en la red"
                            Accessible.description: "Busca dispositivos disponibles en la red local"
                            KeyNavigation.tab: pairedHeader
                            KeyNavigation.backtab: root.findChild("devices.toolbar.pairButton")
                        }
                    }

                    SectionHeader {
                        id: pairedHeader
                        text: "Dispositivos emparejados"
                        width: parent.width
                        visible: root.devicesBridge && root.devicesBridge.pairedDevices.length > 0
                        objectName: "devices.section.pairedHeader"
                        Accessible.name: "Sección de dispositivos emparejados"
                    }

                    Repeater {
                        id: pairedRepeater
                        model: root.devicesBridge ? root.devicesBridge.pairedDevices : []
                        objectName: "devices.list.pairedList"

                        delegate: FocusScope {
                            width: parent.width
                            height: 96
                            objectName: "devices.list.pairedItem." + index
                            activeFocusOnTab: true

                            Accessible.role: Accessible.Button
                            Accessible.name: "Abrir detalle de " + (modelData.alias || "dispositivo emparejado")
                            Accessible.description: "Muestra la información detallada y opciones del dispositivo"

                            Keys.onReturnPressed: {
                                if (typeof navigationBridge !== "undefined" && navigationBridge) {
                                    var key = modelData.key || modelData.serial || ""
                                    if (key)
                                        navigationBridge.navigate("devices.detail", {device_id: key})
                                }
                            }
                            Keys.onSpacePressed: {
                                if (typeof navigationBridge !== "undefined" && navigationBridge) {
                                    var key = modelData.key || modelData.serial || ""
                                    if (key)
                                        navigationBridge.navigate("devices.detail", {device_id: key})
                                }
                            }

                            GlassCard {
                                anchors.fill: parent
                                title: modelData.alias || "Dispositivo"
                                subtitle: {
                                    var parts = []
                                    if (modelData.vendor) parts.push(modelData.vendor)
                                    if (modelData.model) parts.push(modelData.model)
                                    if (modelData.device) parts.push(modelData.device)
                                    return parts.join(" ") || "Tipo: " + (modelData.device || "desconocido")
                                }
                                interactive: true
                                objectName: "devices.card.pairedCard." + index

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof navigationBridge !== "undefined" && navigationBridge) {
                                            var key = modelData.key || modelData.serial || ""
                                            if (key)
                                                navigationBridge.navigate("devices.detail", {device_id: key})
                                        }
                                    }
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.rightMargin: MichiTheme.spacing.md
                                    spacing: MichiTheme.spacing.xs

                                    StatusBadge {
                                        text: "Vinculado"
                                        kind: "success"
                                    }
                                }
                            }
                        }
                    }

                    MichiEmptyState {
                        id: emptyPaired
                        iconName: "devices"
                        title: "Sin dispositivos emparejados"
                        subtitle: "Vincula un dispositivo para sincronizar tu música."
                        showAction: true
                        actionText: "Vincular dispositivo"
                        visible: root.devicesBridge && root.devicesBridge.pairedDevices.length === 0
                        width: parent.width
                        objectName: "devices.empty.pairedEmpty"
                        Accessible.name: "Sin dispositivos emparejados"
                        Accessible.description: "No hay dispositivos emparejados. Vincula un dispositivo para sincronizar música."

                        onActionClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("devices.pair")
                        }
                    }

                    SectionHeader {
                        id: peersHeader
                        text: "Pares detectados en red"
                        width: parent.width
                        visible: root.devicesBridge && root.devicesBridge.peers.length > 0
                        objectName: "devices.section.peersHeader"
                        Accessible.name: "Sección de pares detectados en red"
                    }

                    Repeater {
                        id: peersRepeater
                        model: root.devicesBridge ? root.devicesBridge.peers : []
                        objectName: "devices.list.peersList"

                        delegate: FocusScope {
                            width: parent.width
                            height: 96
                            objectName: "devices.list.peerItem." + index
                            activeFocusOnTab: true

                            Accessible.role: Accessible.Button
                            Accessible.name: "Conectar con " + (modelData.alias || "peer en " + (modelData.ip || "red"))
                            Accessible.description: "Inicia la conexión con el dispositivo detectado en la red"

                            Keys.onReturnPressed: {
                                if (root.devicesBridge && typeof root.devicesBridge.connectToPeer !== "undefined")
                                    root.devicesBridge.connectToPeer(modelData.ip || "", modelData.port || 0)
                            }
                            Keys.onSpacePressed: {
                                if (root.devicesBridge && typeof root.devicesBridge.connectToPeer !== "undefined")
                                    root.devicesBridge.connectToPeer(modelData.ip || "", modelData.port || 0)
                            }

                            GlassCard {
                                anchors.fill: parent
                                title: modelData.alias || "Peer"
                                subtitle: (modelData.ip || "") + ":" + (modelData.port || 0) + " · " + (modelData.device || "desktop")
                                interactive: true
                                objectName: "devices.card.peerCard." + index

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.devicesBridge && typeof root.devicesBridge.connectToPeer !== "undefined")
                                            root.devicesBridge.connectToPeer(modelData.ip || "", modelData.port || 0)
                                    }
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.rightMargin: MichiTheme.spacing.md
                                    spacing: MichiTheme.spacing.xs

                                    MichiButton {
                                        text: "Conectar"
                                        variant: "primary"
                                        implicitHeight: 28
                                        onClicked: {
                                            if (root.devicesBridge && typeof root.devicesBridge.connectToPeer !== "undefined")
                                                root.devicesBridge.connectToPeer(modelData.ip || "", modelData.port || 0)
                                        }
                                        objectName: "devices.action.connectBtn." + index
                                        Accessible.name: "Conectar con " + (modelData.alias || "peer")
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        id: noPeersText
                        text: "No se detectaron pares en la red."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width
                        visible: root.devicesBridge && root.devicesBridge.peers.length === 0
                        objectName: "devices.empty.noPeers"
                    }

                    DeviceTransferPanel {
                        id: transferPanel
                        width: parent.width
                        bridge: root.devicesBridge
                        transferJobs: root.devicesBridge ? root.devicesBridge.transferJobs : []
                        transferHistory: root.devicesBridge ? root.devicesBridge.transferHistory : []
                        visible: root.devicesBridge && root.devicesBridge.serverActive
                        onCancelTransfer: { if (root.devicesBridge) root.devicesBridge.cancelTransfer(jobId) }
                        onRetryTransfer: { if (root.devicesBridge) root.devicesBridge.retryTransfer(jobId) }
                        onClearHistory: { if (root.devicesBridge) root.devicesBridge.clearTransferHistory() }
                        objectName: "devices.transferPanel"
                    }
                }
            }
        }
    }

    onDevicesBridgeChanged: {
        contentLoader.sourceComponent = contentComponent
        root.updateState()
    }

    Component.onCompleted: {
        contentLoader.sourceComponent = contentComponent
        root.updateState()
    }
}
