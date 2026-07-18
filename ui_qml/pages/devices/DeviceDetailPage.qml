import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Detail"
    objectName: "deviceDetailPage"
    id: root
    focus: true

    property string deviceKey: ""
    property string deviceLabel: ""
    property string deviceVendor: ""
    property string deviceModel: ""
    property string deviceProtocol: ""
    property string deviceMountPoint: ""
    property bool deviceAuthorized: false
    property bool deviceTrusted: false
    property string deviceLastContact: ""
    property var deviceStorage: ({})
    property var deviceCapabilities: ({})

    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property var jb: typeof jobBridge !== "undefined" ? jobBridge : null

    property string state: "INITIALIZING"

    signal backClicked()
    signal authorizeClicked()
    signal unauthorizeClicked()
    signal trustClicked()
    signal untrustClicked()
    signal unpairClicked()
    signal syncClicked()
    signal editProfileClicked()
    signal startTransferClicked()
    signal cancelTransferClicked()


    Connections {
        target: root
        function onAuthorizeClicked() {
            if (root.dv && typeof root.dv.authorizeDevice === "function") {
                root.dv.authorizeDevice(root.deviceKey)
            }
        }
        function onTrustClicked() {
            if (root.dv && typeof root.dv.trustDevice === "function") {
                root.dv.trustDevice(root.deviceKey)
            }
        }
        function onSyncClicked() {
            if (root.dv && typeof root.dv.startSync === "function") {
                root.dv.startSync(root.deviceKey)
            }
        }
        function onEditProfileClicked() {
            if (typeof navigationBridge !== "undefined" && navigationBridge) {
                navigationBridge.navigate("devices.profile_editor")
            }
        }
    }

    onDeviceKeyChanged: {
        if (deviceKey) {
            state = "LOADING"
            if (root.dv && typeof root.dv.loadDeviceDetail === "function") {
                var result = root.dv.loadDeviceDetail(deviceKey)
                if (result && result.ok) {
                    var d = result.detail || {}
                    root.deviceLabel = d.label || ""
                    root.deviceVendor = d.vendor || ""
                    root.deviceModel = d.model || ""
                    root.deviceProtocol = d.protocol || ""
                    root.deviceMountPoint = d.mount_point || ""
                    root.deviceAuthorized = !!d.authorized
                    root.deviceTrusted = !!d.trusted
                    root.deviceLastContact = d.last_contact || ""
                    root.deviceStorage = d.storage || ({})
                    root.deviceCapabilities = d.capabilities || ({})
                    state = "READY"
                } else {
                    state = "ERROR"
                }
            } else {
                state = "UNAVAILABLE"
            }
        }
    }

    Keys.onEscapePressed: root.backClicked()
    Keys.onTabPressed: {
        if (focusScope.children.length > 0) {
            focusScope.children[0].forceActiveFocus()
        }
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        KeyNavigation.tab: backButton
        visible: root.state !== "UNAVAILABLE" && root.state !== "ERROR"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            MichiButton {
                Accessible.role: Accessible.Button

                id: backButton
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                activeFocusOnTab: true
                KeyNavigation.tab: deviceInfoCard
                KeyNavigation.backtab: flickable
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
            }

            GlassMaterial {
                id: deviceInfoCard
                width: parent.width
                height: deviceInfoColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radius.md
                variant: "elevated"

                Column {
                    id: deviceInfoColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.deviceLabel
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: root.deviceVendor + " " + root.deviceModel
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.deviceVendor !== "" || root.deviceModel !== ""
                    }

                    Text {
                        text: "Protocolo: " + root.deviceProtocol
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.deviceProtocol !== ""
                    }

                    Text {
                        text: "Punto de montaje: " + root.deviceMountPoint
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.deviceMountPoint !== ""
                    }

                    Text {
                        text: "Último contacto: " + root.deviceLastContact
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.deviceLastContact !== ""
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        StatusBadge {
                            text: root.deviceAuthorized ? "Autorizado" : "No autorizado"
                            kind: root.deviceAuthorized ? "success" : "disconnected"
                        }
                        StatusBadge {
                            text: root.deviceTrusted ? "Confiado" : "No confiado"
                            kind: root.deviceTrusted ? "success" : "disconnected"
                        }
                    }
                }
            }

            DeviceStoragePanel {
                id: storagePanel
                width: parent.width
                mountPoint: root.deviceMountPoint
                storageInfo: root.deviceStorage
                activeFocusOnTab: true
                KeyNavigation.tab: compatView
                KeyNavigation.backtab: deviceInfoCard
            }

            DeviceCompatibilityView {
                id: compatView
                width: parent.width
                protocol: root.deviceProtocol
                activeFocusOnTab: true
                KeyNavigation.tab: profileEditor
                KeyNavigation.backtab: storagePanel
            }

            DeviceSyncProfileEditor {
                id: profileEditor
                width: parent.width
                deviceKey: root.deviceKey
                activeFocusOnTab: true
                KeyNavigation.tab: actionRow
                KeyNavigation.backtab: compatView
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    id: syncButton
                    text: "Sincronizar"
                    variant: "primary"
                    onClicked: root.syncClicked()
                    KeyNavigation.tab: authButton
                    KeyNavigation.backtab: profileEditor
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    id: authButton
                    text: root.deviceAuthorized ? "Desautorizar" : "Autorizar"
                    variant: "secondary"
                    onClicked: root.deviceAuthorized ? root.unauthorizeClicked() : root.authorizeClicked()
                    KeyNavigation.tab: trustButton
                    KeyNavigation.backtab: syncButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    id: trustButton
                    text: root.deviceTrusted ? "No confiar" : "Confiar"
                    variant: "ghost"
                    onClicked: root.deviceTrusted ? root.untrustClicked() : root.trustClicked()
                    KeyNavigation.tab: profileEditButton
                    KeyNavigation.backtab: authButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    id: profileEditButton
                    text: "Editar perfil"
                    variant: "ghost"
                    onClicked: root.editProfileClicked()
                    KeyNavigation.tab: unpairButton
                    KeyNavigation.backtab: trustButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    id: unpairButton
                    text: "Desvincular"
                    variant: "danger"
                    onClicked: root.unpairClicked()
                    KeyNavigation.tab: transferPanel
                    KeyNavigation.backtab: profileEditButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }
            }

            DeviceTransferPanel {
                id: transferPanel
                width: parent.width
                deviceKey: root.deviceKey
                activeFocusOnTab: true
                KeyNavigation.tab: syncHistory
                KeyNavigation.backtab: actionRow
                onStartTransferClicked: root.startTransferClicked()
                onCancelTransferClicked: root.cancelTransferClicked()
            }

            DeviceSyncHistory {
                id: syncHistory
                width: parent.width
                deviceKey: root.deviceKey
                activeFocusOnTab: true
                KeyNavigation.tab: flickable
                KeyNavigation.backtab: transferPanel
            }
        }
    }

    LoadingState {
        id: loadingState
        anchors.centerIn: parent
        title: "Cargando dispositivo"
        message: "Obteniendo información del dispositivo…"
        busy: true
        visible: root.state === "LOADING" || root.state === "INITIALIZING"
    }

    UnavailableState {
        id: unavailableState
        anchors.centerIn: parent
        title: "Servicio no disponible"
        message: "El servicio de dispositivos no está disponible. Conecta un dispositivo o inicia el servidor de sincronización."
        details: "Los detalles del dispositivo requieren el servicio de sincronización."
        primaryActionText: "Reintentar"
        secondaryActionText: "Volver"
        visible: root.state === "UNAVAILABLE"
        onPrimaryActionRequested: {
            if (root.dv && typeof root.dv.refresh === "function") {
                root.dv.refresh()
                state = "LOADING"
                Qt.callLater(function() {
                    if (root.dv && typeof root.dv.loadDeviceDetail === "function") {
                        var r = root.dv.loadDeviceDetail(deviceKey)
                        if (r && r.ok) {
                            var d = r.detail || {}
                            root.deviceLabel = d.label || ""
                            root.deviceVendor = d.vendor || ""
                            root.deviceModel = d.model || ""
                            root.deviceProtocol = d.protocol || ""
                            root.deviceMountPoint = d.mount_point || ""
                            root.deviceAuthorized = !!d.authorized
                            root.deviceTrusted = !!d.trusted
                            root.deviceLastContact = d.last_contact || ""
                            root.deviceStorage = d.storage || ({})
                            root.deviceCapabilities = d.capabilities || ({})
                            state = "READY"
                        } else {
                            state = "ERROR"
                        }
                    }
                })
            }
        }
        onSecondaryActionRequested: root.backClicked()
    }

    Item {
        id: errorState
        anchors.centerIn: parent
        visible: root.state === "ERROR"

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md
            width: Math.min(implicitWidth, parent.width * 0.85)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Error"
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "No se pudo cargar la información del dispositivo."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Reintentar"
                onClicked: {
                    state = "LOADING"
                    if (root.dv && typeof root.dv.loadDeviceDetail === "function") {
                        var r = root.dv.loadDeviceDetail(deviceKey)
                        if (r && r.ok) {
                            var d = r.detail || {}
                            root.deviceLabel = d.label || ""
                            root.deviceVendor = d.vendor || ""
                            root.deviceModel = d.model || ""
                            root.deviceProtocol = d.protocol || ""
                            root.deviceMountPoint = d.mount_point || ""
                            root.deviceAuthorized = !!d.authorized
                            root.deviceTrusted = !!d.trusted
                            root.deviceLastContact = d.last_contact || ""
                            root.deviceStorage = d.storage || ({})
                            root.deviceCapabilities = d.capabilities || ({})
                            state = "READY"
                        } else {
                            state = "ERROR"
                        }
                    }
                }
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Volver"
                variant: "ghost"
                onClicked: root.backClicked()
            }
        }
    }

    CancellationBanner {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root.state === "CANCELLING"
    }
}
