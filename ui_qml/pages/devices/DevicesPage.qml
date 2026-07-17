import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "."

Item {
    objectName: "devicesPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Dispositivos y sincronización"

    property var devicesBridge: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property var deviceSyncService: devicesBridge
    property int pageState: root.devicesBridge ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    MichiResponsive { id: responsive; availableWidth: root.width }

    PageStateManager {
        id: pageState
        route: "devices"
        active: true
        onScrollYChanged: pageState.save()
    }

    Component.onCompleted: {
        if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
            root.devicesBridge.refresh()
        deviceGuard.checkCapability(root.devicesBridge)
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando dispositivos" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: "Servicio de dispositivos no disponible" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin dispositivos"; subtitle: "Configura dispositivos desde Conexiones" }
    }

    CapabilityGuard {
        id: deviceGuard
        anchors.fill: parent
        capabilityName: "devices_sync"

        Flickable {
            id: flickable
            visible: root.pageState === root.stateReady
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
                    text: "Dispositivos y sincronización"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                SyncStatusPanel {
                    id: syncStatus
                    width: parent.width
                    serverActive: root.devicesBridge ? root.devicesBridge.serverActive : false
                    serverPort: root.devicesBridge ? root.devicesBridge.serverPort : 53318
                    peerCount: root.devicesBridge ? root.devicesBridge.peers.length : 0
                    onStartServer: { if (root.devicesBridge) root.devicesBridge.startServer() }
                    onStopServer: { if (root.devicesBridge) root.devicesBridge.stopServer() }
                    activeFocusOnTab: true
                    KeyNavigation.tab: pairedHeader
                    KeyNavigation.backtab: flickable
                    Keys.onReturnPressed: {
                        if (syncStatus.serverActive) syncStatus.onStopServer()
                        else syncStatus.onStartServer()
                    }
                    Keys.onSpacePressed: {
                        if (syncStatus.serverActive) syncStatus.onStopServer()
                        else syncStatus.onStartServer()
                    }
                }

                SectionHeader {
                    id: pairedHeader
                    text: "Dispositivos emparejados"
                    width: parent.width
                }

                Flow {
                    id: pairedFlow
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.devicesBridge ? root.devicesBridge.pairedDevices : []

                        DeviceCard {
                            width: responsive.compact ? parent.width
                                 : responsive.medium ? (parent.width - MichiTheme.spacing.md) / 2
                                                     : (parent.width - MichiTheme.spacing.md * 2) / 3
                            deviceAlias: modelData.alias || ""
                            deviceType: modelData.device || "desktop"
                            paired: true
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
                }

                Text {
                    text: "No hay dispositivos emparejados."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    visible: root.devicesBridge && root.devicesBridge.pairedDevices.length === 0
                }

                SectionHeader {
                    id: networkHeader
                    text: "Pares detectados en red"
                    width: parent.width
                }

                Flow {
                    id: peersFlow
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Repeater {
                        model: root.devicesBridge ? root.devicesBridge.peers : []

                        DeviceCard {
                            width: responsive.compact ? parent.width
                                 : responsive.medium ? (parent.width - MichiTheme.spacing.md) / 2
                                                     : (parent.width - MichiTheme.spacing.md * 2) / 3
                            deviceAlias: modelData.alias || ""
                            deviceIp: modelData.ip || ""
                            devicePort: modelData.port || 0
                            deviceType: modelData.device || "desktop"
                            paired: false
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                        }
                    }
                }

                Text {
                    text: "No se detectaron pares en la red."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    visible: root.devicesBridge && root.devicesBridge.peers.length === 0
                }

                DevicePairingDialog {
                    id: pairingDialog
                    width: parent.width
                    dialogVisible: false
                }

                DeviceStorageView {
                    id: storageView
                    width: parent.width
                    activeFocusOnTab: true
                }

                DeviceTransferQueue {
                    id: transferQueue
                    width: parent.width
                    activeFocusOnTab: true
                }
            }
        }
    }
}
