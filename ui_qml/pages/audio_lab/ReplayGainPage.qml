import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string pageState: "INPUT_READY"
    property string rgMode: "auto"
    property real preamp: 0.0
    property real headroom: 6.0
    property var rgResult: null
    property string rgError: ""

    objectName: "replayGain.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "ReplayGain"

    function startAnalysis() {
        if (!root.labService) return
        root.pageState = "ANALYSING"
        root.rgError = ""
        root.rgResult = null
        var result = root.labService.startReplayGain("/dummy")
        if (result && result.ok) {
            root.rgResult = result
            root.pageState = "COMPLETED"
        } else {
            root.rgError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function cancelAnalysis() {
        root.pageState = "INPUT_READY"
        root.rgResult = null
    }

    function applyTags() {
        if (!root.labService) return
        root.pageState = "APPLYING"
    }

    function clearTags() {
        if (!root.labService) return
        root.pageState = "CLEARING"
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "replayGain.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
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
                    text: "ReplayGain"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "ReplayGain"
                }

                Text {
                    text: "Análisis de ganancia, normalización de loudness, etiquetas de replaygain."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                AudioInputSelection {}
                AudioSelectionSummary { width: parent.width }

                SectionHeader { text: "Modo de análisis"; width: parent.width; objectName: "replaygain.section.mode" }

                Row {
                    spacing: MichiTheme.spacing.md
                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                        title: "Track"; subtitle: "Ganancia por pista"
                        variant: root.rgMode === "track" ? "accent" : "base"
                        objectName: "replaygain.mode.track"
                        Accessible.name: "Modo Track"
                        onClicked: root.rgMode = "track"
                        Keys.onReturnPressed: root.rgMode = "track"
                        Keys.onSpacePressed: root.rgMode = "track"
                    }
                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                        title: "Album"; subtitle: "Ganancia uniforme por álbum"
                        variant: root.rgMode === "album" ? "accent" : "base"
                        objectName: "replaygain.mode.album"
                        Accessible.name: "Modo Album"
                        onClicked: root.rgMode = "album"
                        Keys.onReturnPressed: root.rgMode = "album"
                        Keys.onSpacePressed: root.rgMode = "album"
                    }
                }

                GlassCard {
                    width: parent.width; height: 60
                    title: "Automático"; subtitle: "Detectar modo según selección"
                    variant: root.rgMode === "auto" ? "accent" : "base"
                    objectName: "replaygain.mode.auto"
                    Accessible.name: "Modo Automático"
                    onClicked: root.rgMode = "auto"
                    Keys.onReturnPressed: root.rgMode = "auto"
                    Keys.onSpacePressed: root.rgMode = "auto"
                }

                SectionHeader { text: "Parámetros"; width: parent.width; objectName: "replaygain.section.params" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "replaygain.params"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Column {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "Preamplificación: " + root.preamp.toFixed(1) + " dB"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                            MichiSlider {
                                id: preampSlider
                                objectName: "replaygain.preampSlider"
                                width: parent.width; from: -12; to: 12; value: root.preamp; stepSize: 0.5
                                accessibleName: "Preamplificación"
                                onMoved: function(v) { root.preamp = v }
                            }
                        }

                        Column {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "Margen de pico: " + root.headroom.toFixed(1) + " dB"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                            MichiSlider {
                                id: headroomSlider
                                objectName: "replaygain.headroomSlider"
                                width: parent.width; from: 0; to: 12; value: root.headroom; stepSize: 0.5
                                accessibleName: "Margen de pico"
                                onMoved: function(v) { root.headroom = v }
                            }
                        }
                    }
                }

                SectionHeader { text: "Acciones"; width: parent.width; objectName: "replaygain.section.actions" }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.pageState === "ANALYSING" ? "Cancelar" : "Analizar"
                        variant: root.pageState === "ANALYSING" ? "danger" : "primary"
                        objectName: root.pageState === "ANALYSING" ? "replaygain.cancelBtn" : "replaygain.analyzeBtn"
                        enabled: root.pageState !== "APPLYING" && root.pageState !== "CLEARING"
                        onClicked: { if (root.pageState === "ANALYSING") root.cancelAnalysis(); else root.startAnalysis() }
                        Accessible.name: root.pageState === "ANALYSING" ? "Cancelar análisis" : "Analizar ReplayGain"
                    }
                    MichiButton {
                        text: "Aplicar etiquetas"
                        variant: "secondary"
                        objectName: "replaygain.applyBtn"
                        enabled: root.rgResult !== null && root.pageState !== "APPLYING" && root.pageState !== "CLEARING"
                        onClicked: root.applyTags()
                        Accessible.name: "Aplicar etiquetas ReplayGain"
                    }
                    MichiButton {
                        text: "Limpiar etiquetas"
                        variant: "danger"
                        objectName: "replaygain.clearBtn"
                        enabled: root.pageState !== "APPLYING" && root.pageState !== "CLEARING"
                        onClicked: root.clearTags()
                        Accessible.name: "Limpiar etiquetas ReplayGain"
                    }
                }

                SectionHeader { text: "Resultados"; width: parent.width; objectName: "replaygain.section.results" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : "status"
                    objectName: "replaygain.results"
                    height: 80
                    Text {
                        anchors.centerIn: parent
                        text: root.pageState === "ANALYSING" ? "Analizando..." : (root.pageState === "APPLYING" ? "Aplicando etiquetas..." : (root.pageState === "CLEARING" ? "Limpiando etiquetas..." : (root.pageState === "COMPLETED" ? "Análisis completado" : (root.pageState === "FAILED" ? "Error: " + root.rgError : "Selecciona archivos y modo para analizar"))))
                        color: root.pageState === "FAILED" ? MichiTheme.colors.error : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        width: parent.width - MichiTheme.spacing.xl * 2
                    }
                }

                MichiButton {
                    text: "Volver"; variant: "ghost"
                    objectName: "replaygain.backBtn"
                    onClicked: { if (root.nav) root.nav.back() }
                    Accessible.name: "Volver"
                }
            }
        }
    }
}
