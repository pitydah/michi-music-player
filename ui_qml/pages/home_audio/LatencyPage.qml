import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de latencia"

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property string zoneId: ""
    property string zoneName: ""
    property int currentLatencyMs: 0
    property int minLatency: 0
    property int maxLatency: 500
    property string _state: "READY"
    property string _errorMessage: ""

    signal backClicked()
    signal latencyApplied(string zoneId, int latencyMs)
    signal resetRequested(string zoneId)

    objectName: "LatencyPage"
    Accessible.description: "Ajusta la latencia de sincronización para la zona"

    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root._state === "LOADING" ? AsyncStateView.LOADING
             : root._state === "ERROR" ? AsyncStateView.ERROR
             : root._state === "UNAVAILABLE" ? AsyncStateView.UNAVAILABLE
             : AsyncStateView.READY
        title: root._state === "ERROR" ? "Error de configuración" : "Latencia no disponible"
        message: root._errorMessage || "El control de latencia solo está disponible con Snapcast"
        retryAvailable: root._state === "ERROR"
        onRetryRequested: { root._state = "READY"; root._errorMessage = "" }

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true
            objectName: "latencyFlickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        text: "Volver"
                        variant: "ghost"
                        objectName: "latencyBackButton"
                        Accessible.name: "Volver a detalle de zona"
                        activeFocusOnTab: true
                        KeyNavigation.tab: latencyHeader
                        onClicked: root.backClicked()
                        Keys.onReturnPressed: root.backClicked()
                        Keys.onSpacePressed: root.backClicked()
                    }

                    Text {
                        id: latencyHeader
                        text: "Latencia — " + root.zoneName
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                        Accessible.name: "Latencia para " + root.zoneName
                    }
                }

                Text {
                    text: "Ajusta la latencia para sincronizar la reproducción entre zonas."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width * 0.7
                }

                GlassCard {
                    id: latencyCard
                    width: parent.width
                    title: "Control de latencia"
                    variant: "base"
                    objectName: "latencyControlCard"
                    Accessible.name: "Control de latencia"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Row {
                            width: parent.width
                            spacing: MichiTheme.spacing.sm

                            Text {
                                text: "Latencia actual:"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: root.currentLatencyMs + " ms"
                                color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.cardTitleSize
                                font.weight: MichiTheme.typography.weightSemiBold
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MichiSlider {
                            id: latencySlider
                            width: parent.width
                            from: root.minLatency
                            to: root.maxLatency
                            value: root.currentLatencyMs
                            stepSize: 5
                            accessibleName: "Latencia en milisegundos"
                            accessibleDescription: root.currentLatencyMs + " ms"
                            onMoved: root.currentLatencyMs = value
                            objectName: "latencySlider"
                            activeFocusOnTab: true
                        }

                        Row {
                            width: parent.width
                            Text {
                                text: root.minLatency + " ms"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                            Item { width: parent.width - 120; height: 1 }
                            Text {
                                text: root.maxLatency + " ms"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                            }
                        }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        id: applyBtn
                        text: "Aplicar"
                        variant: "primary"
                        objectName: "latencyApplyButton"
                        Accessible.name: "Aplicar latencia de " + root.currentLatencyMs + " ms"
                        activeFocusOnTab: true
                        KeyNavigation.tab: resetBtn
                        KeyNavigation.backtab: latencySlider
                        onClicked: {
                            if (root.ha && typeof root.ha.setLatency === "function") {
                                var result = root.ha.setLatency(root.zoneId, root.currentLatencyMs)
                                if (result && result.ok) {
                                    root.latencyApplied(root.zoneId, root.currentLatencyMs)
                                } else {
                                    root._errorMessage = (result && result.error) || "Error al aplicar latencia"
                                    root._state = "ERROR"
                                }
                            }
                        }
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }

                    MichiButton {
                        id: resetBtn
                        text: "Restablecer"
                        variant: "ghost"
                        objectName: "latencyResetButton"
                        Accessible.name: "Restablecer latencia a 0 ms"
                        activeFocusOnTab: true
                        KeyNavigation.backtab: applyBtn
                        onClicked: {
                            root.currentLatencyMs = 0
                            root.resetRequested(root.zoneId)
                        }
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                    }
                }

                StatusBadge {
                    visible: root.ha === null
                    text: "Bridge no disponible"
                    kind: "disconnected"
                    objectName: "latencyBridgeStatus"
                    Accessible.name: "Bridge de Home Audio no disponible"
                }
            }
        }
    }
}
