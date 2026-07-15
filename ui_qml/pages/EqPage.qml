import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../theme"
import "../components"
import "../materials"
import "equalizer"

Item {
    id: root

    objectName: "eq.page"
    Accessible.role: Accessible.Pane
    Accessible.name: "Ecualizador"

    property var eq: typeof eqBridge !== "undefined" ? eqBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property bool _clipping: false
    property string _state: "LOADING"

    function _cap(feature) {
        if (!root.eq) return false
        if (!root.eq.backendAvailable) return false
        if (root.eq.bitperfectConflict) return false
        return true
    }

    function _notify(msg, kind) {
        if (root.notif) root.notif.showMessage(msg, kind)
    }

    function checkClipping() {
        if (!root.eq) return
        var preamp = root.eq.preamp || 0
        var maxBand = 0
        var bands = root.eq.graphicBands || []
        for (var i = 0; i < bands.length; i++) {
            var g = bands[i] ? bands[i].gain || 0 : 0
            if (Math.abs(g) > Math.abs(maxBand)) maxBand = g
        }
        root._clipping = (preamp + maxBand) > 12
    }

    Component.onCompleted: {
        if (root.eq && typeof root.eq.refresh !== "undefined") {
            root.eq.refresh()
            root._state = root.eq.backendAvailable ? "READY" : "READY"
        } else {
            root._state = "READY"
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true

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
                    text: "Estado EQ"
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
                StatusBadge {
                    text: "Clipping detectado"
                    kind: "error"
                    visible: root._clipping
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root.eq && root.eq.bypass ? "Activar EQ" : "Bypass EQ"
                    variant: root.eq && root.eq.bypass ? "primary" : "danger"
                    enabled: root._cap("backendAvailable")
                    objectName: "eq.bypassToggle"
                    Accessible.name: "Activar o desactivar ecualizador"
                    onClicked: {
                        if (root.eq) {
                            var r = root.eq.toggleBypass(!root.eq.bypass)
                            if (!r.ok && root.notif) root.notif.showMessage(r.message || r.error, "error")
                        }
                    }
                }

                MichiButton {
                    text: "Restablecer plano"
                    variant: "ghost"
                    enabled: root._cap("backendAvailable")
                    objectName: "eq.resetButton"
                    Accessible.name: "Restablecer ecualizador a plano"
                    onClicked: {
                        if (root.eq) {
                            root.eq.reset()
                            root._clipping = false
                            root._notify("EQ restablecido a plano", "info")
                        }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root._cap("backendAvailable")

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
                    enabled: root._cap("backendAvailable")
                    objectName: "eq.preampSlider"
                    accessibleName: "Preamplificador"
                    onMoved: {
                        if (root.eq) root.eq.setPreamp(value)
                        root.checkClipping()
                    }
                }
            }

            SectionHeader { text: "EQ Gráfico — 10 bandas"; width: parent.width }

            Repeater {
                model: root.eq && root._cap("backendAvailable") ? root.eq.graphicBands : []

                EqualizerBandControl {
                    width: parent.width
                    freq: modelData ? modelData.freq : 0
                    gain: modelData ? modelData.gain : 0
                    index: index
                    eqEnabled: root._cap("backendAvailable")
                    onBandGainChanged: function(idx, val) {
                        if (root.eq) root.eq.setGraphicBand(idx, val)
                        root.checkClipping()
                    }
                }
            }

            SectionHeader { text: "EQ Paramétrico — 6 bandas"; width: parent.width }

            Repeater {
                model: root.eq && root._cap("backendAvailable") ? root.eq.parametricBands : []

                Rectangle {
                    width: parent.width; height: 40
                    radius: MichiTheme.radiusSm
                    color: MichiTheme.colors.surfaceCard
                    border.color: MichiTheme.colors.borderCard

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: 40
                            text: "B" + (index + 1)
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: 80
                            text: modelData && modelData.enabled ? "Activado" : "Desactivado"
                            color: modelData && modelData.enabled ? MichiTheme.colors.success : MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: 100
                            text: modelData ? modelData.freq + " Hz" : ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: 80
                            text: modelData ? modelData.gain.toFixed(1) + " dB" : ""
                            color: modelData && modelData.gain >= 0 ? MichiTheme.colors.accentBlue : MichiTheme.colors.error
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData ? "Q: " + modelData.q.toFixed(1) : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            SectionHeader { text: "Presets"; width: parent.width }

            EqualizerPresetBrowser {
                id: presetBrowser
                width: parent.width
                eqBridge: root.eq
                notif: root.notif
                enabled: root._cap("backendAvailable")
            }

            SectionHeader { text: "Información"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: root._cap("backendAvailable") ? "DSP conectado — cambios aplicados en tiempo real" : "DSP no disponible — solo vista"; kind: root._cap("backendAvailable") ? "success" : "disconnected" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
