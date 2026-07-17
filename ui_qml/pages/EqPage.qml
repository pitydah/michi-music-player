import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Eq"
    objectName: "eqPage"
    focus: true
    id: root

    property var eq: typeof eqBridge !== "undefined" ? eqBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _selectedPreset: "Plano"
    property int pageState: root.eq ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    Component.onCompleted: {
        if (root.eq && typeof root.eq.refresh !== "undefined")
            root.eq.refresh()
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando ecualizador" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: "Ecualizador no disponible" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin presets de ecualización" }
    }

    Flickable {
        visible: root.pageState === root.stateReady
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
                text: "Ecualizador"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            StatusBadge {
                text: root.eq && root.eq.backendAvailable ? "DSP conectado" : "DSP no disponible"
                kind: root.eq && root.eq.backendAvailable ? "success" : "disconnected"
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: "Bypass"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: root.eq && root.eq.bypass ? "Activado" : "Desactivado"
                    variant: root.eq && root.eq.bypass ? "danger" : "primary"
                    enabled: root.eq ? root.eq.backendAvailable : false
                    onClicked: {
                        if (root.eq) root.eq.toggleBypass(!root.eq.bypass)
                        if (root.notif) root.notif.showMessage("Bypass " + (root.eq && root.eq.bypass ? "activado" : "desactivado"), "info")
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Preamplificador"
                subtitle: "Ganancia: " + (root.eq ? root.eq.preamp.toFixed(1) : "0.0") + " dB"
                variant: "base"
                onClicked: {
                    if (root.eq) root.eq.setPreamp(root.eq.preamp === 0.0 ? -6.0 : 0.0)
                }
            }

            SectionHeader { text: "Presets"; width: parent.width }

            Repeater {
                model: root.eq ? root.eq.presets : []

                GlassCard {
                    width: parent.width; height: 60
                    title: modelData.name || ""
                    subtitle: modelData.bands ? modelData.bands.length + " bandas" : ""
                    variant: modelData.name === (root.eq ? root.eq.currentPreset : "") ? "accent" : "base"
                    onClicked: {
                        if (root.eq) {
                            root.eq.applyPreset(modelData.name)
                            if (root.notif) root.notif.showMessage("Preset aplicado: " + modelData.name, "success")
                        }
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
                    StatusBadge { text: "Ecualizador avanzado"; kind: "info" }
                }
            }
        }
    }
}
