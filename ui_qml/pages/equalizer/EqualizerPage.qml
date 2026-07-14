import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root

    property var eq: typeof eqBridge !== "undefined" ? eqBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _viewMode: "graphic"

    function _cap(name) {
        return root.eq && root.eq.backendAvailable
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
                text: "Ecualizador"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Row {
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Ecualizador"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }

                StatusBadge {
                    text: root.eq && root.eq.backendAvailable
                          ? (root.eq.bypass ? "Bypass" : "Activo")
                          : "No disponible"
                    kind: root.eq && root.eq.backendAvailable
                          ? (root.eq.bypass ? "warning" : "success")
                          : "disconnected"
                }

                StatusBadge {
                    text: "Bit-perfect bloquea EQ"
                    kind: "error"
                    visible: root.eq && root.eq.bitperfectConflict
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root._cap("backendAvailable")

                MichiButton {
                    text: root.eq && root.eq.bypass ? "Activar EQ" : "Bypass EQ"
                    variant: root.eq && root.eq.bypass ? "primary" : "danger"
                    enabled: root._cap("backendAvailable")
                    onClicked: {
                        if (root.eq) {
                            var r = root.eq.toggleBypass(!root.eq.bypass)
                            if (!r.ok && root.notif)
                                root.notif.showMessage(r.message || r.error, "error")
                        }
                    }
                }

                MichiButton {
                    text: "Restablecer"
                    variant: "ghost"
                    enabled: root._cap("backendAvailable")
                    onClicked: {
                        if (root.eq) {
                            root.eq.reset()
                            if (root.notif) root.notif.showMessage("EQ restablecido", "info")
                        }
                    }
                }
            }

            EqualizerGraph {
                id: graph
                width: parent.width
                height: 220
                eqBridge: root.eq
                visible: root._viewMode === "graphic" && root._cap("backendAvailable")
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: "Preamp: " + (root.eq ? root.eq.preamp.toFixed(1) : "0.0") + " dB"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                MichiSlider {
                    width: 200
                    from: -24; to: 24; value: root.eq ? root.eq.preamp : 0
                    stepSize: 0.5
                    enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
                    onMoved: {
                        if (root.eq) root.eq.setPreamp(value)
                    }
                }
            }

            SectionHeader { text: "Bandas"; width: parent.width }

            Repeater {
                model: root.eq && root._viewMode === "graphic" ? root.eq.graphicBands : []

                EqualizerBandControl {
                    width: parent.width
                    freq: modelData ? modelData.freq : 0
                    gain: modelData ? modelData.gain : 0
                    index: index
                    enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
                    onGainChanged: function(idx, val) {
                        if (root.eq) root.eq.setGraphicBand(idx, val)
                    }
                }
            }

            SectionHeader { text: "Presets"; width: parent.width }

            EqualizerPresetBrowser {
                width: parent.width
                eqBridge: root.eq
                notif: root.notif
                enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Controles no disponibles marcados"; kind: "info" }
                    StatusBadge { text: root._cap("backendAvailable") ? "Backend conectado" : "Backend no disponible — solo vista"; kind: root._cap("backendAvailable") ? "success" : "disconnected" }
                }
            }
        }
    }
}
