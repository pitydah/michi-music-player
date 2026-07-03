import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    Component.onCompleted: {
        if (root.ha && typeof root.ha.refresh !== "undefined")
            root.ha.refresh()
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
                    state: root.ha ? root.ha.homeAssistantState : "not_configured"
                    onConfigureClicked: {
                        if (root.ha) root.ha.configureHomeAssistant()
                    }
                    onOpenDiagnostics: {
                        if (root.ha) root.ha.openDiagnostics()
                    }
                }

                MichiMusicStreamPanel {
                    id: streamPanel
                    width: parent.width
                    streamState: root.ha ? root.ha.streamState : "concept"
                }
            }

            SectionHeader { text: "Dispositivos"; width: parent.width }

            Repeater {
                model: root.ha ? root.ha.devices : []

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
                visible: root.ha && root.ha.devices.length === 0
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
