import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "."

Item {
    id: root

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    objectName: "homeAudio.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Home Audio"
    Accessible.description: "Gestión de audio en el hogar, dispositivos y zonas"

    Component.onCompleted: {
        if (root.ha && typeof root.ha.refresh !== "undefined")
            root.ha.refresh()
    }

    Loader {
        anchors.fill: parent
        active: !root.ha
        sourceComponent: UnavailableState {
            title: "Home Audio no disponible"
            message: "El servicio de audio en el hogar no está disponible en este momento."
            explanation: "Home Audio Bridge no está configurado o el módulo no está activo."
            objectName: "homeAudio.unavailableState"
        }
    }

    FocusScope {
        id: focusScope
        visible: !!root.ha
        anchors.fill: parent
        objectName: "homeAudio.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (typeof navigationBridge !== "undefined" && navigationBridge)
                navigationBridge.navigate("home")
        }

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "homeAudio.flickableContent"

            Keys.onEscapePressed: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home")
            }

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Home Audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    objectName: "homeAudio.pageTitle"
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Home Audio"
                }

                HomeAudioModeSelector {
                    id: modeSelector
                    width: parent.width
                    objectName: "homeAudio.modeSelector"
                    Accessible.name: "Selector de modo Home Audio"
                    KeyNavigation.tab: stackLayout
                }

                StackLayout {
                    id: stackLayout
                    width: parent.width
                    currentIndex: modeSelector.selectedMode
                    objectName: "homeAudio.stackLayout"

                    HomeAssistantPanel {
                        id: haPanel
                        width: parent.width
                        state: root.ha ? root.ha.homeAssistantState : "not_configured"
                        objectName: "homeAudio.haPanel"
                        Accessible.name: "Panel de Home Assistant"
                        onConfigureClicked: {
                            if (root.ha) root.ha.configureHomeAssistant()
                        }
                        onOpenDiagnostics: {
                            if (root.ha) root.ha.openDiagnostics()
                        }
                        KeyNavigation.tab: devicesSection
                    }

                    MichiMusicStreamPanel {
                        id: streamPanel
                        width: parent.width
                        streamState: root.ha ? root.ha.streamState : "concept"
                        objectName: "homeAudio.streamPanel"
                        Accessible.name: "Panel de Michi Music Stream"
                        KeyNavigation.tab: devicesSection
                    }
                }

                SectionHeader {
                    id: devicesSection
                    text: "Dispositivos"
                    width: parent.width
                    objectName: "homeAudio.section.devices"
                    Accessible.name: "Sección de dispositivos"
                }

                Repeater {
                    model: root.ha ? root.ha.devices : []

                    ReceiverCard {
                        width: parent.width
                        receiverName: modelData.name || ""
                        receiverRoom: modelData.room || ""
                        receiverState: modelData.state || "disconnected"
                        receiverType: modelData.type || "Michi Stream"
                        objectName: "homeAudio.receiverCard." + index
                    }
                }

                Text {
                    text: "No hay dispositivos Home Audio configurados."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    visible: root.ha && root.ha.devices.length === 0
                    objectName: "homeAudio.emptyDevices"
                }

                GlassCard {
                    id: networkDiagnosticCard
                    width: parent.width
                    height: 80
                    title: "Diagnóstico de red"
                    subtitle: "Mide latencia y calidad de conexión entre dispositivos."
                    variant: "base"
                    objectName: "homeAudio.networkDiagnostic"
                    Accessible.name: "Diagnóstico de red"
                    Accessible.description: "Mide latencia y calidad de conexión entre dispositivos"
                    KeyNavigation.tab: experimentalBadge
                }

                StatusBadge {
                    id: experimentalBadge
                    text: "Experimental"
                    kind: "experimental"
                    objectName: "homeAudio.experimentalBadge"
                }
            }
        }
    }
}
