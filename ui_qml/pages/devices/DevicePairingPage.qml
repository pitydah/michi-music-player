import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Device Pairing"
    objectName: "devicePairingPage"
    id: root
    focus: true

    property var dv: typeof devicesBridge !== "undefined" ? devicesBridge : null

    property string pairingState: "idle"
    property string discoveredDeviceName: ""
    property string discoveredDeviceType: ""
    property string discoveredDeviceIp: ""
    property int discoveredDevicePort: 0

    signal backClicked()
    signal pairRequested(string name, string type)
    signal cancelRequested()


    Keys.onEscapePressed: root.backClicked()

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        visible: root.pairingState !== "loading"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            MichiButton {
                Accessible.role: Accessible.Button

                id: backButton
                text: qsTr("< Volver")
                variant: "ghost"
                onClicked: root.backClicked()
                activeFocusOnTab: true
                KeyNavigation.tab: sectionTitle
                KeyNavigation.backtab: flickable
                Keys.onReturnPressed: clicked()
                Keys.onSpacePressed: clicked()
            }

            Text {
                id: sectionTitle
                text: qsTr("Vincular nuevo dispositivo")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            GlassMaterial {
                id: discoveryCard
                width: parent.width
                height: discoveryColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radius.md
                variant: "elevated"

                Column {
                    id: discoveryColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("Dispositivos detectados")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: qsTr("Busca dispositivos en la red o conéctalos manualmente.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    MichiButton {
                        text: qsTr("Escanear red")
                        variant: "secondary"
                        onClicked: {
                            if (root.dv && typeof root.dv.discoverDevices === "function") {
                                var result = root.dv.discoverDevices()
                                if (result && result.ok) {
                                    var disc = root.dv.discovered || []
                                    if (disc.length > 0) {
                                        root.discoveredDeviceName = disc[0].alias || disc[0].name || ""
                                        root.discoveredDeviceType = disc[0].device || disc[0].type || ""
                                        root.discoveredDeviceIp = disc[0].ip || ""
                                        root.discoveredDevicePort = disc[0].port || 0
                                    }
                                }
                            }
                        }
                        activeFocusOnTab: true
                        KeyNavigation.tab: manualConnectionSection
                        KeyNavigation.backtab: backButton
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                    }

                    Repeater {
                        model: root.dv && root.dv.discovered ? root.dv.discovered : []

                        GlassMaterial {
                            width: parent.width
                            height: 56
                            radius: MichiTheme.radius.sm
                            variant: "base"

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                Column {
                                    width: parent.width - 140
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        text: modelData.alias || modelData.name || "Desconocido"
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        font.weight: MichiTheme.typography.weightMedium
                                        elide: Text.ElideRight
                                        width: parent.width
                                    }

                                    Text {
                                        text: (modelData.ip || "") + ":" + (modelData.port || "")
                                        color: MichiTheme.colors.textMuted
                                        font.pixelSize: MichiTheme.typography.metaSize
                                        visible: modelData.ip
                                    }
                                }

                                MichiButton {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: qsTr("Vincular")
                                    variant: "primary"
                                    onClicked: root.pairRequested(
                                        modelData.alias || modelData.name || "",
                                        modelData.device || modelData.type || ""
                                    )
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.discoveredDeviceName = modelData.alias || modelData.name || ""
                                    root.discoveredDeviceType = modelData.device || modelData.type || ""
                                    root.discoveredDeviceIp = modelData.ip || ""
                                    root.discoveredDevicePort = modelData.port || 0
                                }
                                cursorShape: Qt.PointingHandCursor
                            }
                        }
                    }

                    Text {
                        text: qsTr("No se detectaron dispositivos.")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.dv && root.dv.discovered && root.dv.discovered.length === 0
                    }
                }
            }

            GlassMaterial {
                id: manualConnectionSection
                width: parent.width
                height: manualColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radius.md
                variant: "base"

                Column {
                    id: manualColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: qsTr("Conexión manual")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        width: parent.width

                        Column {
                            width: parent.width * 0.45
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: qsTr("Dirección IP")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                focusPolicy: Qt.StrongFocus
                                id: manualIpField
                                width: parent.width
                                placeholderText: qsTr("192.168.1.100")
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualPortField
                                KeyNavigation.backtab: scanNetworkButton
                            }
                        }

                        Column {
                            width: parent.width * 0.25
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: qsTr("Puerto")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                focusPolicy: Qt.StrongFocus
                                id: manualPortField
                                width: parent.width
                                placeholderText: qsTr("53318")
                                text: qsTr("53318")
                                activeFocusOnTab: true
                                KeyNavigation.tab: manualAuthField
                                KeyNavigation.backtab: manualIpField
                            }
                        }

                        Column {
                            width: parent.width * 0.30
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: qsTr("Código de autorización")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            TextField {
                                focusPolicy: Qt.StrongFocus
                                id: manualAuthField
                                width: parent.width
                                placeholderText: qsTr("Opcional")
                                activeFocusOnTab: true
                                KeyNavigation.tab: connectManualButton
                                KeyNavigation.backtab: manualPortField
                            }
                        }
                    }

                    MichiButton {
                        id: connectManualButton
                        text: qsTr("Conectar")
                        variant: "primary"
                        onClicked: {
                            if (root.dv && typeof root.dv.pairDevice === "function") {
                                var ip = manualIpField.text.trim()
                                if (ip === "") return
                                var port = parseInt(manualPortField.text.trim()) || 53318
                                var auth = manualAuthField.text.trim()
                                var result = root.dv.pairDevice(ip, port, auth)
                                if (result && result.ok) {
                                    root.pairingState = "paired"
                                }
                            }
                        }
                        activeFocusOnTab: true
                        KeyNavigation.tab: cancelButton
                        KeyNavigation.backtab: manualAuthField
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                    }
                }
            }

            GlassMaterial {
                id: pairingStatusCard
                width: parent.width
                height: statusColumn.height + MichiTheme.spacing.xl * 2
                radius: MichiTheme.radius.md
                variant: root.pairingState === "paired" ? "accent" : "base"
                visible: root.pairingState !== "idle"

                Column {
                    id: statusColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: qsTr("Estado de vinculación")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    StatusBadge {
                        text: {
                            switch (root.pairingState) {
                                case "pairing": return "Vinculando…"
                                case "paired": return "Vinculado"
                                case "failed": return "Error"
                                default: return "Inactivo"
                            }
                        }
                        kind: {
                            switch (root.pairingState) {
                                case "paired": return "success"
                                case "failed": return "error"
                                default: return "active"
                            }
                        }
                    }
                    Text {
                        text: root.discoveredDeviceName ? "Dispositivo: qsTr(" + root.discoveredDeviceName : ")"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    id: cancelButton
                    text: qsTr("Cancelar")
                    variant: "ghost"
                    onClicked: root.cancelRequested()
                    activeFocusOnTab: true
                    KeyNavigation.tab: backButton
                    KeyNavigation.backtab: connectManualButton
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }

                MichiButton {
                    text: qsTr("Finalizar")
                    variant: "primary"
                    visible: root.pairingState === "paired"
                    onClicked: root.backClicked()
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                }
            }
        }
    }

    LoadingState {
        id: loadingState
        anchors.centerIn: parent
        title: qsTr("Buscando dispositivos")
        message: qsTr("Escaneando la red local…")
        busy: true
        visible: root.pairingState === "loading"
    }

    UnavailableState {
        anchors.centerIn: parent
        title: qsTr("Servicio no disponible")
        message: qsTr("El servicio de dispositivos no está disponible.")
        details: "Inicia el servidor de sincronización para descubrir dispositivos."
        primaryActionText: "Reintentar"
        secondaryActionText: "Volver"
        visible: !root.dv
        onPrimaryActionRequested: {
            if (root.dv && typeof root.dv.refresh === "function")
                root.dv.refresh()
        }
        onSecondaryActionRequested: root.backClicked()
    }
}
