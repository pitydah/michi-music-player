import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components/states"
import "../../components"
import "."

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Dispositivos y sincronización"

    property var devicesBridge: typeof window !== "undefined" && window.devicesBridge ? window.devicesBridge : null
    property var deviceSyncService: typeof window !== "undefined" && window.deviceSyncService ? window.deviceSyncService : null

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    readonly property bool bridgeAvailable: root.devicesBridge !== null

    objectName: "devices.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Dispositivos y sincronización"
    Accessible.description: "Gestión de dispositivos y sincronización de música"
=======
>>>>>>> Stashed changes
    PageStateManager {
        id: pageState
        route: "devices"
        active: true
        onScrollYChanged: pageState.save()
    }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    Component.onCompleted: {
        if (root.devicesBridge && typeof root.devicesBridge.refresh !== "undefined")
            root.devicesBridge.refresh()
        deviceGuard.checkCapability(root.devicesBridge)
    }

<<<<<<< Updated upstream
    CapabilityGuard {
        id: deviceGuard
=======
<<<<<<< HEAD
    Loader {
        id: stateLoader
>>>>>>> Stashed changes
        anchors.fill: parent
        capabilityName: "devices_sync"

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
                    text: "Dispositivos y sincronización"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Dispositivos y sincronización"
                }

                SyncStatusPanel {
                    id: syncStatus
                    width: parent.width
                    objectName: "syncStatusPanel"
                    Accessible.name: "Estado de sincronización"
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
                    objectName: "pairedDevicesHeader"
                    Accessible.name: "Dispositivos emparejados"
                }

                Repeater {
                    model: root.devicesBridge ? root.devicesBridge.pairedDevices : []

                    DeviceCard {
                        width: parent.width
                        deviceAlias: modelData.alias || ""
                        deviceType: modelData.device || "desktop"
                        paired: true
                        objectName: "pairedDeviceCard_" + index
                        Accessible.name: modelData.alias || "Dispositivo emparejado"
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
                    Accessible.name: "No hay dispositivos emparejados"
                }

                SectionHeader {
                    id: networkHeader
                    text: "Pares detectados en red"
                    width: parent.width
                    objectName: "networkPeersHeader"
                    Accessible.name: "Pares detectados en red"
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
                        objectName: "networkPeerCard_" + index
                        Accessible.name: modelData.alias || "Par de red"
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
                    Accessible.name: "No se detectaron pares en la red"
                }

                DevicePairingDialog {
                    id: pairingDialog
                    width: parent.width
                    dialogVisible: false
                    objectName: "devicePairingDialog"
                    Accessible.name: "Diálogo de emparejamiento"
                }

                DeviceStorageView {
                    id: storageView
                    width: parent.width
                    objectName: "deviceStorageView"
                    Accessible.name: "Vista de almacenamiento"
                    activeFocusOnTab: true
                }

                DeviceTransferQueue {
                    id: transferQueue
                    width: parent.width
                    objectName: "deviceTransferQueue"
                    Accessible.name: "Cola de transferencia"
                    activeFocusOnTab: true
                }
=======
    CapabilityGuard {
        id: deviceGuard
        anchors.fill: parent
        capabilityName: "devices_sync"

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
                    text: "Dispositivos y sincronización"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.name: "Dispositivos y sincronización"
                }

                SyncStatusPanel {
                    id: syncStatus
                    width: parent.width
                    objectName: "syncStatusPanel"
                    Accessible.name: "Estado de sincronización"
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
                    objectName: "pairedDevicesHeader"
                    Accessible.name: "Dispositivos emparejados"
                }

                Repeater {
                    model: root.devicesBridge ? root.devicesBridge.pairedDevices : []

                    DeviceCard {
                        width: parent.width
                        deviceAlias: modelData.alias || ""
                        deviceType: modelData.device || "desktop"
                        paired: true
                        objectName: "pairedDeviceCard_" + index
                        Accessible.name: modelData.alias || "Dispositivo emparejado"
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
                    Accessible.name: "No hay dispositivos emparejados"
                }

                SectionHeader {
                    id: networkHeader
                    text: "Pares detectados en red"
                    width: parent.width
                    objectName: "networkPeersHeader"
                    Accessible.name: "Pares detectados en red"
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
                        objectName: "networkPeerCard_" + index
                        Accessible.name: modelData.alias || "Par de red"
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
                    Accessible.name: "No se detectaron pares en la red"
                }

                DevicePairingDialog {
                    id: pairingDialog
                    width: parent.width
                    dialogVisible: false
                    objectName: "devicePairingDialog"
                    Accessible.name: "Diálogo de emparejamiento"
                }

                DeviceStorageView {
                    id: storageView
                    width: parent.width
                    objectName: "deviceStorageView"
                    Accessible.name: "Vista de almacenamiento"
                    activeFocusOnTab: true
                }

                DeviceTransferQueue {
                    id: transferQueue
                    width: parent.width
                    objectName: "deviceTransferQueue"
                    Accessible.name: "Cola de transferencia"
                    activeFocusOnTab: true
                }
>>>>>>> origin/michi-qml-functional-wave
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
