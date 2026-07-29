import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "."

Item {
    objectName: "homeAudioPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Home Audio"

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property var _volumeTimers: ({})
    property bool diagnosticsVisible: false
    property int selectedMode: 0
    property int pageState: {
        if (!root.ha) return stateUnavailable
        if (root.ha.available === false) return stateUnavailable
        if (root.ha.streamState === "error") return stateError
        return stateReady
    }

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3
    readonly property int stateUnavailable: 4

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        if (root.ha && typeof root.ha.refresh === "function")
            root.ha.refresh()
        var s = root.pageState
        homeAudioGuard.checkCapability(root.ha)
    }

    Component.onCompleted: {
        if (root.ha && typeof root.ha.refresh !== "undefined")
            root.ha.refresh()
        homeAudioGuard.checkCapability(root.ha)
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: qsTr("Cargando Home Audio") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: qsTr("Home Audio no disponible") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateUnavailable
        sourceComponent: UnavailableState {
            title: qsTr("Home Audio no disponible")
            message: qsTr("Configura un servicio Home Audio para usar esta sección.")
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: qsTr("Sin dispositivos Home Audio"); subtitle: "Configura dispositivos desde Conexiones" }
    }

    CapabilityGuard {
        id: homeAudioGuard
        anchors.fill: parent
        capabilityName: "home_audio"

        Flickable {
            visible: root.pageState === root.stateReady
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
                    text: qsTr("Home Audio")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Grid {
                    id: modeSelector
                    width: parent.width
                    columns: Math.min(2, responsive.columnCount)
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md

                    Repeater {
                        model: [
                            {
                                title: qsTr("Home Assistant"),
                                subtitle: qsTr("Integración con asistentes del hogar")
                            },
                            {
                                title: qsTr("Michi Music Stream"),
                                subtitle: qsTr("Streaming local del ecosistema Michi")
                            }
                        ]

                        GlassCard {
                            width: (modeSelector.width - modeSelector.columnSpacing * (modeSelector.columns - 1)) / modeSelector.columns
                            height: 120
                            title: modelData.title
                            subtitle: modelData.subtitle
                            selected: root.selectedMode === index
                            activeFocusOnTab: true
                            KeyNavigation.tab: haPanel
                            KeyNavigation.backtab: flickable
                            onClicked: root.selectedMode = index
                        }
                    }
                }

                StackLayout {
                    width: parent.width
                    currentIndex: root.selectedMode

                    HomeAssistantPanel {
                        id: haPanel
                        width: parent.width
                        state: root.ha ? root.ha.homeAssistantState : "not_configured"
                        onConfigureClicked: function(host, port, token) {
                            if (root.ha) root.ha.configureHa(host, port, token)
                        }
                        onDisconnectClicked: {
                            if (root.ha) root.ha.disconnectHa()
                        }
                        onOpenDiagnostics: {
                            root.diagnosticsVisible = true
                        }
                        activeFocusOnTab: true
                        KeyNavigation.tab: streamPanel
                        KeyNavigation.backtab: modeSelector
                        Keys.onReturnPressed: onConfigureClicked()
                        Keys.onSpacePressed: onConfigureClicked()
                    }

                    MichiMusicStreamPanel {
                        id: streamPanel
                        width: parent.width
                        streamState: root.ha ? (root.ha.streamState || "concept") : "concept"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: haPanel
                        Keys.onReturnPressed: activate()
                        Keys.onSpacePressed: activate()
                    }
                }

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    SectionHeader {
                        id: zonesHeader
                        text: qsTr("Zonas")
                        width: parent.width - 160
                        KeyNavigation.tab: zoneRepeater
                        KeyNavigation.backtab: streamPanel
                    }

                    MichiButton {
                        Accessible.role: Accessible.Button

                        id: createGroupBtn
                        activeFocusOnTab: true

                        text: qsTr("Crear grupo")
                        variant: "primary"
                        visible: root.ha && root.ha.zonesSupported
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("group_editor")
                        }
                        anchors.verticalCenter: zonesHeader.verticalCenter
                    }
                }

                Repeater {
                    id: zoneRepeater
                    model: root.ha ? root.ha.zones : []

                    Item {
                        width: parent.width
                        height: zoneCard.height

                        ZoneCard {
                            id: zoneCard
                            width: parent.width
                            zoneName: modelData.name || ""
                            deviceCount: modelData.devices ? modelData.devices.length : 0
                            zoneStatus: modelData.state || modelData.status || "idle"
                            isMuted: modelData.muted || false
                            volume: modelData.volume || 0
                            hasLatency: (modelData.latency_ms || 0) > 0

                            onZoneCardClicked: {
                                if (typeof navigationBridge !== "undefined" && navigationBridge)
                                    navigationBridge.navigateWithParams("zone_detail", {zoneId: modelData.id || ""})
                            }

                            onZoneCardVolumeChanged: function(vol) {
                                if (root.ha && typeof root.ha.setZoneVolume !== "undefined")
                                    root.ha.setZoneVolume(modelData.id || "", vol / 100.0)
                            }

                            onZoneMuteToggled: {
                                if (root.ha && typeof root.ha.setZoneMute !== "undefined")
                                    root.ha.setZoneMute(modelData.id || "", !modelData.muted)
                            }
                        }
                    }
                }

                SectionHeader {
                    id: devicesHeader
                    text: qsTr("Dispositivos")
                    width: parent.width
                }

                Repeater {
                    model: root.ha ? root.ha.devices : []

                    ReceiverCard {
                        width: parent.width
                        receiverName: modelData.name || ""
                        receiverRoom: modelData.room || ""
                        receiverState: modelData.state || "disconnected"
                        receiverType: modelData.type || "Michi Stream"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }
                }

                Text {
                    text: qsTr("No hay dispositivos Home Audio configurados.")
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    visible: root.ha && root.ha.devices.length === 0
                }

                GlassCard {
                    id: diagCard
                    width: parent.width; height: 80
                    title: qsTr("Diagnóstico de red")
                    subtitle: qsTr("Mide latencia y calidad de conexión entre dispositivos.")
                    variant: "base"
                    activeFocusOnTab: true
                    KeyNavigation.tab: statusBadge
                    KeyNavigation.backtab: devicesHeader
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root.diagnosticsVisible = true
                }

                StatusBadge {
                    id: statusBadge
                    text: qsTr("Multiroom")
                    kind: "experimental"
                    KeyNavigation.backtab: diagCard
                }
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: root.diagnosticsVisible
        z: 10
        sourceComponent: DiagnosticsPage {
            onCloseRequested: root.diagnosticsVisible = false
        }
    }

    Connections {
        target: root.ha
        function onStateChanged() {
            // Force property re-evaluation
            var s = root.pageState
        }
    }
}
