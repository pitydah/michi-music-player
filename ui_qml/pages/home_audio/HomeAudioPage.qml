import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    objectName: "homeAudioPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Home Audio"

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property var _volumeTimers: ({})
    property int pageState: root.ha ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    Component.onCompleted: {
        if (root.ha && typeof root.ha.refresh !== "undefined")
            root.ha.refresh()
        homeAudioGuard.checkCapability(root.ha)
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando Home Audio" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: "Home Audio no disponible" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin dispositivos Home Audio"; subtitle: "Configura dispositivos desde Conexiones" }
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
                    text: "Home Audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                HomeAudioModeSelector {
                    id: modeSelector
                    width: parent.width
                    activeFocusOnTab: true
                    KeyNavigation.tab: haPanel
                    KeyNavigation.backtab: flickable
                    Keys.onReturnPressed: { modeSelector.selectedMode = (modeSelector.selectedMode + 1) % 2 }
                    Keys.onSpacePressed: { modeSelector.selectedMode = (modeSelector.selectedMode + 1) % 2 }
                }

                StackLayout {
                    width: parent.width
                    currentIndex: modeSelector.selectedMode

                    HomeAssistantPanel {
                        id: haPanel
                        width: parent.width
                        state: root.ha ? root.ha.homeAssistantState : "not_configured"
                        onConfigureClicked: {
                            if (root.ha) root.ha.configureHomeAssistant()
                        }
                        onOpenDiagnostics: {
                            if (root.ha) root.ha.openDiagnostics()
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
                        streamState: root.ha ? root.ha.streamState : "concept"
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
                        text: "Zonas"
                        width: parent.width - 160
                        KeyNavigation.tab: zoneRepeater
                        KeyNavigation.backtab: streamPanel
                    }

                    MichiButton {
                        Accessible.role: Accessible.Button

                        id: createGroupBtn
                        activeFocusOnTab: true

                        text: "Crear grupo"
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
                    text: "Dispositivos"
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
                    text: "No hay dispositivos Home Audio configurados."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    visible: root.ha && root.ha.devices.length === 0
                }

                GlassCard {
                    id: diagCard
                    width: parent.width; height: 80
                    title: "Diagnóstico de red"
                    subtitle: "Mide latencia y calidad de conexión entre dispositivos."
                    variant: "base"
                    activeFocusOnTab: true
                    KeyNavigation.tab: statusBadge
                    KeyNavigation.backtab: devicesHeader
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                }

                StatusBadge {
                    id: statusBadge
                    text: "Multiroom"
                    kind: "experimental"
                    KeyNavigation.backtab: diagCard
                }
            }
        }
    }
}
