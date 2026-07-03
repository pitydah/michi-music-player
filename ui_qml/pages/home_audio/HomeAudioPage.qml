import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var homeAudioBridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    Component.onCompleted: {
        if (root.homeAudioBridge && typeof root.homeAudioBridge.refresh !== "undefined")
            root.homeAudioBridge.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

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
            }

            StackLayout {
                width: parent.width
                currentIndex: modeSelector.selectedMode

                HomeAssistantPanel {
                    id: haPanel
                    width: parent.width
                    state: root.homeAudioBridge ? root.homeAudioBridge.homeAssistantState : "not_configured"
                    onConfigureClicked: {
                        if (root.homeAudioBridge) root.homeAudioBridge.configureHomeAssistant()
                    }
                    onOpenDiagnostics: {
                        if (root.homeAudioBridge) root.homeAudioBridge.openDiagnostics()
                    }
                }

                MichiMusicStreamPanel {
                    id: streamPanel
                    width: parent.width
                    streamState: root.homeAudioBridge ? root.homeAudioBridge.streamState : "concept"
                }
            }

            SectionHeader { text: "Dispositivos"; width: parent.width }

            Repeater {
                model: root.homeAudioBridge ? root.homeAudioBridge.devices : []

                ReceiverCard {
                    width: parent.width
                    receiverName: modelData.name || ""
                    receiverRoom: modelData.room || ""
                    receiverState: modelData.state || "disconnected"
                    receiverType: modelData.type || "Michi Stream"
                }
            }

            Text {
                text: "No hay dispositivos Home Audio configurados."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                visible: root.homeAudioBridge && root.homeAudioBridge.devices.length === 0
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Diagnóstico de red"
                subtitle: "Mide latencia y calidad de conexión entre dispositivos."
                variant: "base"
            }

            StatusBadge { text: "Experimental"; kind: "experimental" }
        }
    }
}
