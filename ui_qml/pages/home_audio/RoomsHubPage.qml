import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    id: root
    objectName: "roomsHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Habitaciones y zonas")

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property string selectedZoneId: ""
    property bool loading: false
    property string pageError: ""
    readonly property var zones: root.ha && root.ha.zones ? root.ha.zones : []
    readonly property int pageState: root.loading ? AsyncStateView.LOADING
                                                  : root.pageError !== "" ? AsyncStateView.ERROR
                                                                          : !root.ha ? AsyncStateView.ERROR
                                                                                     : AsyncStateView.READY

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        root.refreshRooms()
        root.selectedZoneId = params ? (params.zoneId || params.zone_id || "") : ""
    }

    function refreshRooms() {
        root.pageError = ""
        if (!root.ha || typeof root.ha.refresh !== "function") {
            root.loading = false
            root.pageError = qsTr("El servicio Home Audio no está disponible.")
            return
        }
        root.loading = true
        var result = root.ha.refresh()
        if (result && result.pending) return
        root.loading = false
        if (result && result.ok === false)
            root.pageError = result.error || qsTr("No se pudieron actualizar las zonas.")
    }

    Connections {
        target: root.ha
        function onStateChanged() { /* reactive updates */ }
    }

    AsyncStateView {
        anchors.fill: parent
        state: root.pageState
        title: root.loading ? qsTr("Actualizando zonas") : qsTr("No se pudieron cargar las zonas")
        message: root.loading ? qsTr("Consultando dispositivos y grupos.") : qsTr("Comprueba el servicio e inténtalo de nuevo.")
        details: root.pageError
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: root.refreshRooms()

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            contentHeight: column.height + MichiTheme.spacing.xl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                // Header
                RowLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: qsTr("Zonas y dispositivos")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.pageTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: root.zones.length + qsTr(" zonas configuradas")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }

                    MichiButton {
                        text: qsTr("Detectar dispositivos")
                        variant: "primary"
                        onClicked: {
                            if (root.ha && root.ha.discoverReceivers)
                                root.ha.discoverReceivers()
                        }
                    }
                }

                // Room cards with controls
                Repeater {
                    model: root.zones.length === 0 ? [null] : root.zones

                    GlassCard {
                        width: parent.width
                        height: responsive.compact ? 180 : 140
                        variant: "base"
                        visible: modelData !== null
                        selected: modelData && String(modelData.id || "") === root.selectedZoneId

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            // Header row: name + badge
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.sm

                                MichiIcon {
                                    iconKey: "rooms"
                                    size: 22
                                    color: MichiTheme.colors.accentPrimary
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData ? (modelData.name || qsTr("Zona sin nombre")) : ""
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                }

                                StatusBadge {
                                    text: modelData ? {
                                        var s = modelData.state || modelData.status || ""
                                        if (s === "playing") return qsTr("Reproduciendo")
                                        if (s === "active") return qsTr("Activa")
                                        if (s === "idle") return qsTr("En espera")
                                        return s
                                    } : ""
                                    kind: modelData ? {
                                        var s = modelData.state || modelData.status || ""
                                        if (s === "playing") return "success"
                                        if (s === "active") return "success"
                                        return "info"
                                    } : "info"
                                }
                            }

                            // Device info
                            Text {
                                text: {
                                    if (!modelData) return ""
                                    var devs = modelData.receivers || modelData.members || []
                                    return devs.length + qsTr(" dispositivos")
                                }
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                            }

                            // Controls row
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.sm
                                Layout.topMargin: MichiTheme.spacing.xs

                                MichiButton {
                                    text: qsTr("Abrir")
                                    variant: "primary"
                                    implicitHeight: 32
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (typeof navigationBridge !== "undefined" && navigationBridge && modelData && modelData.id)
                                            navigationBridge.navigate("zone_detail", { zoneId: modelData.id })
                                    }
                                }

                                MichiButton {
                                    text: qsTr("Volumen")
                                    variant: "ghost"
                                    implicitHeight: 32
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (typeof navigationBridge !== "undefined" && navigationBridge && modelData && modelData.id)
                                            navigationBridge.navigate("zone_detail", { zoneId: modelData.id })
                                    }
                                }

                                MichiButton {
                                    text: qsTr("Fuente")
                                    variant: "ghost"
                                    implicitHeight: 32
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (typeof navigationBridge !== "undefined" && navigationBridge && modelData && modelData.id)
                                            navigationBridge.navigate("zone_detail", { zoneId: modelData.id })
                                    }
                                }
                            }
                        }
                    }
                }

                // Empty state
                GlassCard {
                    width: parent.width
                    height: 100
                    variant: "base"
                    visible: root.zones.length === 0

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("No hay zonas configuradas")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Text {
                            text: qsTr("Detecta dispositivos en tu red o agrega manualmente un servidor Snapcast.")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
