import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root
    objectName: "equalizerPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Ecualizador"

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
                    objectName: "eqBypassButton"
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
                    objectName: "eqResetButton"
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

            MichiSegmentedControl {
                id: modeSelector
                width: parent.width
                implicitHeight: 36
                model: ["Gráfico", "Paramétrico"]
                currentIndex: root._viewMode === "parametric" ? 1 : 0
                accessibleName: "Modo de ecualizador"
                visible: root._cap("backendAvailable")
                onActivated: function(index) {
                    root._viewMode = index === 1 ? "parametric" : "graphic"
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
                    onBandGainChanged: function(idx, val) {
                        if (root.eq) root.eq.setGraphicBand(idx, val)
                    }
                }
            }

            Repeater {
                model: root.eq && root._viewMode === "parametric" ? root.eq.parametricBands : []

                Item {
                    width: parent.width
                    implicitHeight: paramRow.height + MichiTheme.spacing.sm

                    Row {
                        id: paramRow
                        spacing: MichiTheme.spacing.sm
                        anchors.left: parent.left
                        anchors.right: parent.right

                        Text {
                            text: "Banda " + (index + 1)
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium
                            width: 60
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        ComboBox {
                            id: typeCombo
                            width: 100
                            model: ["peaking", "low_shelf", "high_shelf", "low_pass", "high_pass", "notch"]
                            currentIndex: {
                                var t = modelData ? modelData.type : "peaking"
                                for (var i = 0; i < typeCombo.model.length; i++) {
                                    if (typeCombo.model[i] === t) return i
                                }
                                return 0
                            }
                            enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
                            Accessible.role: Accessible.ComboBox
                            Accessible.name: "Tipo de filtro banda " + (index + 1)
                            onActivated: function(idx) {
                                if (root.eq) {
                                    var d = modelData || {}
                                    root.eq.setParametricBand(index, typeCombo.model[idx], d.freq || 0, d.gain || 0, d.enabled || false)
                                }
                            }
                        }

                        Text {
                            text: modelData ? Math.round(modelData.freq) + " Hz" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 70
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        MichiSlider {
                            id: gainSlider
                            width: 100
                            from: -24; to: 24
                            value: modelData ? modelData.gain : 0
                            stepSize: 0.5
                            enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
                            accessibleName: "Ganancia banda " + (index + 1)
                            onMoved: {
                                if (root.eq) {
                                    var d = modelData || {}
                                    root.eq.setParametricBand(index, d.type || "peaking", d.freq || 0, value, d.enabled || false)
                                }
                            }
                        }

                        Text {
                            text: "Q: " + (modelData ? modelData.q.toFixed(1) : "0.7")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 40
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        CheckBox {
                            checked: modelData ? modelData.enabled : false
                            enabled: root._cap("backendAvailable") && !(root.eq && root.eq.bitperfectConflict)
                            Accessible.name: "Habilitar banda " + (index + 1)
                            onCheckedChanged: {
                                if (root.eq) {
                                    var d = modelData || {}
                                    root.eq.setParametricBand(index, d.type || "peaking", d.freq || 0, d.gain || 0, checked)
                                }
                            }
                        }
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
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Controles no disponibles marcados"; kind: "info" }
                    StatusBadge { text: root._cap("backendAvailable") ? "Backend conectado" : "Backend no disponible — solo vista"; kind: root._cap("backendAvailable") ? "success" : "disconnected" }
                }
            }
        }
    }
}
