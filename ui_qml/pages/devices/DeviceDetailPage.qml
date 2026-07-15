import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
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

    objectName: "DeviceDetailPage"
    Accessible.role: Accessible.Pane
    Accessible.name: deviceLabel || "Detalle de dispositivo"

    onDeviceKeyChanged: {
        if (deviceKey) {
            state = "LOADING"
            if (root.dv && typeof root.dv.loadDeviceDetail === "function") {
                var result = root.dv.loadDeviceDetail(deviceKey)
                if (result && result.ok) {
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
        activeFocusOnTab: true
        KeyNavigation.tab: backButton
        visible: root.state !== "UNAVAILABLE" && root.state !== "ERROR"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            MichiButton {
                id: backButton
                text: "< Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                objectName: "deviceDetailBackButton"
                Accessible.name: "Volver a lista de dispositivos"
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
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "deviceInfoCard"
                Accessible.name: "Información del dispositivo"

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
                        Accessible.name: "Nombre del dispositivo: " + root.deviceLabel
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
                            objectName: "authorizedBadge"
                            Accessible.name: text
                        }
                        StatusBadge {
                            text: root.deviceTrusted ? "Confiado" : "No confiado"
                            kind: root.deviceTrusted ? "success" : "disconnected"
                            objectName: "trustedBadge"
                            Accessible.name: text
                        }
                    }
                }
            }

            DeviceStoragePanel {
                id: storagePanel
                width: parent.width
                mountPoint: root.deviceMountPoint
                storageInfo: root.deviceStorage
                objectName: "deviceStoragePanel"
                Accessible.name: "Panel de almacenamiento"
                activeFocusOnTab: true
                KeyNavigation.tab: compatView
                KeyNavigation.backtab: deviceInfoCard
            }

            DeviceCompatibilityView {
                id: compatView
                width: parent.width
                protocol: root.deviceProtocol
                objectName: "deviceCompatibilityView"
                Accessible.name: "Compatibilidad de formatos"
                activeFocusOnTab: true
                KeyNavigation.tab: profileEditor
                KeyNavigation.backtab: storagePanel
            }

            DeviceSyncProfileEditor {
                id: profileEditor
                width: parent.width
                deviceKey: root.deviceKey
                objectName: "deviceSyncProfileEditor"
                Accessible.name: "Editor de perfil de sincronización"
                activeFocusOnTab: true
                KeyNavigation.tab: actionRow
                KeyNavigation.backtab: compatView
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm
                objectName: "deviceActionRow"
                Accessible.name: "Acciones del dispositivo"

                MichiButton {
                    id: syncButton
                    text: "Sincronizar"
                    variant: "primary"
                    onClicked: root.syncClicked()
                    objectName: "syncButton"
                    Accessible.name: "Iniciar sincronización"
                    activeFocusOnTab: true
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
                    objectName: "authorizeButton"
                    Accessible.name: root.deviceAuthorized ? "Desautorizar dispositivo" : "Autorizar dispositivo"
                    activeFocusOnTab: true
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
                    objectName: "trustButton"
                    Accessible.name: root.deviceTrusted ? "Revocar confianza" : "Confiar en dispositivo"
                    activeFocusOnTab: true
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
                    objectName: "editProfileButton"
                    Accessible.name: "Editar perfil de sincronización"
                    activeFocusOnTab: true
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
                    objectName: "unpairButton"
                    Accessible.name: "Desvincular dispositivo"
                    activeFocusOnTab: true
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
                objectName: "deviceTransferPanel"
                Accessible.name: "Panel de transferencia"
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
                objectName: "deviceSyncHistory"
                Accessible.name: "Historial de sincronización"
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
        objectName: "deviceDetailLoadingState"
        Accessible.name: "Cargando información del dispositivo"
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
        objectName: "deviceDetailUnavailableState"
        Accessible.name: "Servicio de dispositivos no disponible"
        onPrimaryActionRequested: {
            if (root.dv && typeof root.dv.refresh === "function") {
                root.dv.refresh()
                state = "LOADING"
                Qt.callLater(function() {
                    if (root.dv && typeof root.dv.loadDeviceDetail === "function") {
                        var r = root.dv.loadDeviceDetail(deviceKey)
                        state = r && r.ok ? "READY" : "ERROR"
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
        objectName: "deviceDetailErrorState"
        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Error al cargar dispositivo"

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
                        state = r && r.ok ? "READY" : "ERROR"
                    }
                }
                objectName: "deviceDetailRetryButton"
                Accessible.name: "Reintentar cargar dispositivo"
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Volver"
                variant: "ghost"
                onClicked: root.backClicked()
                objectName: "deviceDetailErrorBackButton"
                Accessible.name: "Volver a lista de dispositivos"
            }
        }
    }

    CancellationBanner {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        visible: root.state === "CANCELLING"
        objectName: "deviceDetailCancellationBanner"
        Accessible.name: "Cancelando transferencia"
    }
}
