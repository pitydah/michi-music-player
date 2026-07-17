import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    objectName: "devicesPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Dispositivos y sincronización"

    property var devicesBridge: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property var deviceSyncService: devicesBridge

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

    CapabilityGuard {
        id: deviceGuard
        anchors.fill: parent
        capabilityName: "devices_sync"

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            contentHeight: column.height + MichiTheme.spacing.xl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

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

                Repeater {
                    model: root.devicesBridge ? root.devicesBridge.pairedDevices : []

                    DeviceCard {
                        width: parent.width
                        deviceAlias: modelData.alias || ""
                        deviceType: modelData.device || "desktop"
                        paired: true
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
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

                Repeater {
                    model: root.devicesBridge ? root.devicesBridge.peers : []

                    DeviceCard {
                        width: parent.width
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
