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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var deviceCompatibility: ({})
    property string deviceType: "desktop"
    property string deviceIp: ""
    property int devicePort: 0
    property var transferJobs: []
    property var transferHistory: []
    property var devicesBridge: null
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    property var deviceCapabilities: ({})

    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null
    property var jb: typeof jobBridge !== "undefined" ? jobBridge : null

    property string state: "INITIALIZING"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    signal backClicked()
    signal authorizeClicked()
    signal unauthorizeClicked()
    signal trustClicked()
    signal untrustClicked()
    signal unpairClicked()
    signal syncClicked()
    signal editProfileClicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    signal startTransferClicked()
    signal cancelTransferClicked()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    signal connectClicked()
    signal pairClicked()
    signal transferClicked(string jobId)
    signal cancelTransfer(string jobId)
    signal retryTransfer(string jobId)
    signal clearHistory()
    signal browseFiles()
    signal ejectDevice(string mountPoint)
>>>>>>> Stashed changes

    objectName: "DeviceDetailPage"
    Accessible.role: Accessible.Pane
    Accessible.name: deviceLabel || "Detalle de dispositivo"

<<<<<<< Updated upstream
=======
    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle de dispositivo: " + root.deviceLabel
=======
    signal startTransferClicked()
    signal cancelTransferClicked()

    objectName: "DeviceDetailPage"
    Accessible.role: Accessible.Pane
    Accessible.name: deviceLabel || "Detalle de dispositivo"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "devices.detailPage.backBtn"
                    Accessible.name: "Volver a lista de dispositivos"
                }
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }

            GlassMaterial {
                id: deviceInfoCard
                width: parent.width
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                height: deviceInfoColumn.height + MichiTheme.spacing.xl * 2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                height: headerColumn.height + MichiTheme.spacing.xl * 2
>>>>>>> Stashed changes
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "deviceInfoCard"
                Accessible.name: "Información del dispositivo"

                Column {
<<<<<<< Updated upstream
                    id: deviceInfoColumn
=======
                    id: headerColumn
=======
                height: deviceInfoColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radiusMd
                variant: "elevated"
                objectName: "deviceInfoCard"
                Accessible.name: "Información del dispositivo"

                Column {
                    id: deviceInfoColumn
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                    Text {
                        text: root.deviceLabel
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        Accessible.name: "Nombre del dispositivo: " + root.deviceLabel
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    Row {
                        spacing: MichiTheme.spacing.md
                        width: parent.width

                        Rectangle {
                            width: 48; height: 48; radius: MichiTheme.radiusSm
                            color: MichiTheme.colors.accentSurface
                            anchors.verticalCenter: parent.verticalCenter

                            Text {
                                anchors.centerIn: parent
                                text: {
                                    var t = root.deviceType.toLowerCase()
                                    if (t === "android" || t === "iphone") return "\u260E"
                                    if (t === "tablet") return "\u2328"
                                    if (t === "dedicated" || t === "hiby" || t === "fiio") return "\u266B"
                                    if (t === "sandisk") return "\uD83D\uDCFD"
                                    return "\uD83D\uDDA5"
                                }
                                font.pixelSize: MichiTheme.typography.pageTitleSize
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: root.deviceLabel || "Dispositivo"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.pageTitleSize
                                font.weight: MichiTheme.typography.weightBold
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: root.deviceVendor + " " + root.deviceModel
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                visible: root.deviceVendor !== "" || root.deviceModel !== ""
                            }
                        }
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                        visible: root.deviceLastContact !== ""
=======
                        visible: root.deviceIp !== ""
=======
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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        StatusBadge { text: root.deviceAuthorized ? "Autorizado" : "No autorizado"; kind: root.deviceAuthorized ? "success" : "disconnected" }
                        StatusBadge { text: root.deviceTrusted ? "Confiado" : "No confiado"; kind: root.deviceTrusted ? "success" : "disconnected" }
                        StatusBadge { text: root.deviceMountPoint !== "" ? "Montado" : "No montado"; kind: root.deviceMountPoint !== "" ? "active" : "disconnected" }
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    }
                }
            }

            DeviceStoragePanel {
                id: storagePanel
                width: parent.width
                mountPoint: root.deviceMountPoint
                storageInfo: root.deviceStorage
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                compatibilityInfo: root.deviceCompatibility
                onEjectRequested: root.ejectDevice(mountPoint)
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                objectName: "deviceActionRow"
                Accessible.name: "Acciones del dispositivo"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                width: parent.width
                wrapMode: Text.WordWrap
                objectName: "devices.detailPage.actions"
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
=======
                    Accessible.description: "Elimina la vinculación con este dispositivo"
=======
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    activeFocusOnTab: true
                    KeyNavigation.tab: transferPanel
                    KeyNavigation.backtab: profileEditButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                }
            }

            DeviceTransferPanel {
                id: transferPanel
                width: parent.width
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                bridge: root.devicesBridge
                transferJobs: root.transferJobs
                transferHistory: root.transferHistory
                onCancelTransfer: root.cancelTransfer(jobId)
                onRetryTransfer: root.retryTransfer(jobId)
                onClearHistory: root.clearHistory()
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                deviceKey: root.deviceKey
                objectName: "deviceTransferPanel"
                Accessible.name: "Panel de transferencia"
                activeFocusOnTab: true
                KeyNavigation.tab: syncHistory
                KeyNavigation.backtab: actionRow
                onStartTransferClicked: root.startTransferClicked()
                onCancelTransferClicked: root.cancelTransferClicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }

            DeviceSyncHistory {
                id: syncHistory
                width: parent.width
                deviceKey: root.deviceKey
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                historyEntries: root.transferHistory
                onClearHistoryClicked: root.clearHistory()
            }

            Text {
                text: "Nota: La transferencia de video no está soportada. Solo se admiten archivos de audio."
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.captionSize
                width: parent.width
                wrapMode: Text.WordWrap
                leftPadding: MichiTheme.spacing.md
                objectName: "devices.detailPage.audioOnlyNotice"
                Accessible.role: Accessible.Alert
                Accessible.name: "Solo audio"
                Accessible.description: "Este dispositivo solo soporta transferencia de archivos de audio. El video no está disponible."
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                objectName: "deviceSyncHistory"
                Accessible.name: "Historial de sincronización"
                activeFocusOnTab: true
                KeyNavigation.tab: flickable
                KeyNavigation.backtab: transferPanel
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
